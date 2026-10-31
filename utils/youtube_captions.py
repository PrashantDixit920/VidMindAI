"""YouTube transcript helpers.

1. fetch_captions(): use Supadata first (works through a hosted API), then
   fall back to youtube-transcript-api for environments where it is available.
2. clean_pasted_transcript(): tidy a transcript copied from YouTube's
   "Show transcript" panel (removes timestamps).
"""

import os
import re
import time
from urllib.parse import parse_qs, urlparse

import requests

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TIMESTAMP_LINE = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s*$")
_TIMESTAMP_PREFIX = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s+")

CAPTION_LANGUAGES = ("en", "en-IN", "en-US", "en-GB", "hi")
MIN_CAPTION_WORDS = 20

SUPADATA_TRANSCRIPT_URL = "https://api.supadata.ai/v1/transcript"
SUPADATA_POLL_INTERVAL_SECONDS = 3
SUPADATA_MAX_POLL_ATTEMPTS = 120


class CaptionsUnavailable(Exception):
    """Raised when captions cannot be read. The message is safe to show to users."""


def extract_video_id(url: str):
    """Return the 11-character video ID from common YouTube link formats, or None."""
    url = (url or "").strip()
    if _VIDEO_ID.match(url):
        return url

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    candidate = ""

    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                candidate = parts[1]

    return candidate if _VIDEO_ID.match(candidate) else None


def _transcript_text(content) -> str:
    """Normalize Supadata's plain-text or timestamped-segment response."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = " ".join(
            str(segment.get("text", "")).strip()
            for segment in content
            if isinstance(segment, dict) and str(segment.get("text", "")).strip()
        )
    else:
        text = ""

    return re.sub(r"\s+", " ", text).strip()


def _supadata_request(url: str, api_key: str) -> str:
    """Fetch a transcript from Supadata, polling when the API returns a job ID."""
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    params = {
        "url": url,
        "text": "true",
        "mode": "auto",
    }

    try:
        response = requests.get(
            SUPADATA_TRANSCRIPT_URL,
            headers=headers,
            params=params,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()

        job_id = data.get("jobId")
        if job_id:
            for _ in range(SUPADATA_MAX_POLL_ATTEMPTS):
                time.sleep(SUPADATA_POLL_INTERVAL_SECONDS)
                job_response = requests.get(
                    f"{SUPADATA_TRANSCRIPT_URL}/{job_id}",
                    headers=headers,
                    timeout=30,
                )
                job_response.raise_for_status()
                job_data = job_response.json()
                status = job_data.get("status")

                if status == "completed":
                    data = job_data.get("result") or job_data
                    break
                if status == "failed":
                    error = job_data.get("error") or job_data.get("message") or "transcription job failed"
                    raise CaptionsUnavailable(f"Supadata could not transcribe this video: {error}")
            else:
                raise CaptionsUnavailable("Supadata transcription timed out. Please try again later.")

        transcript = _transcript_text(data.get("content"))
        if not transcript:
            api_message = data.get("message") or data.get("error")
            raise CaptionsUnavailable(
                f"Supadata did not return a transcript{': ' + str(api_message) if api_message else ''}"
            )

        return transcript

    except CaptionsUnavailable:
        raise
    except requests.HTTPError as exc:
        response = exc.response
        status = response.status_code if response is not None else None
        detail = ""
        if response is not None:
            try:
                payload = response.json()
                detail = payload.get("message") or payload.get("error") or ""
            except ValueError:
                detail = response.text[:200]

        if status == 401:
            reason = "the Supadata API key is invalid"
        elif status == 402:
            reason = "the Supadata account has run out of credits"
        elif status == 403:
            reason = "Supadata denied access to this video"
        elif status == 429:
            reason = "the Supadata rate limit was reached"
        else:
            reason = f"Supadata returned HTTP {status}"

        if detail:
            reason += f" ({detail})"
        raise CaptionsUnavailable(reason) from exc
    except (requests.Timeout, requests.ConnectionError) as exc:
        raise CaptionsUnavailable("could not connect to Supadata; check the server connection and try again") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise CaptionsUnavailable("Supadata returned an unexpected transcript response") from exc


def _youtube_transcript_api(url: str, video_id: str, languages) -> str:
    """Fallback to the original library when it is available."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise CaptionsUnavailable("the youtube-transcript-api package is not installed") from exc

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=list(languages))
    except Exception as exc:  # the library raises many specific error types
        name = type(exc).__name__
        if name in ("RequestBlocked", "IpBlocked"):
            reason = "YouTube blocked this server from reading captions"
        elif name == "TranscriptsDisabled":
            reason = "captions are turned off for this video"
        elif name == "NoTranscriptFound":
            reason = "no English or Hindi captions were found"
        elif name in ("VideoUnavailable", "VideoUnplayable"):
            reason = "the video is unavailable"
        else:
            reason = f"captions could not be read ({name})"
        raise CaptionsUnavailable(reason) from exc

    text = " ".join(
        snippet.text.strip()
        for snippet in fetched
        if getattr(snippet, "text", "").strip()
    )
    return re.sub(r"\s+", " ", text).strip()


def fetch_captions(url: str, languages=CAPTION_LANGUAGES) -> str:
    """Return the video's transcript, preferring Supadata, or raise CaptionsUnavailable.

    Set SUPADATA_API_KEY in the environment or Streamlit secrets. If it is not
    configured or the hosted API fails, the original youtube-transcript-api
    implementation is attempted as a fallback.
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise CaptionsUnavailable("the link does not look like a YouTube video")

    api_key = os.getenv("SUPADATA_API_KEY")
    supadata_problem = ""

    if api_key:
        try:
            text = _supadata_request(url, api_key)
            if len(text.split()) < MIN_CAPTION_WORDS:
                raise CaptionsUnavailable("the Supadata transcript was too short to use")
            return text
        except CaptionsUnavailable as exc:
            supadata_problem = str(exc)
    else:
        supadata_problem = "SUPADATA_API_KEY is not set"

    try:
        text = _youtube_transcript_api(url, video_id, languages)
    except CaptionsUnavailable as exc:
        raise CaptionsUnavailable(
            f"Supadata: {supadata_problem}. YouTube captions fallback: {exc}"
        ) from exc

    if len(text.split()) < MIN_CAPTION_WORDS:
        raise CaptionsUnavailable("the captions were too short to use")

    return text


def clean_pasted_transcript(raw: str) -> str:
    """Remove timestamps from a transcript copied from YouTube and join the lines."""
    lines = []
    for line in (raw or "").splitlines():
        if not line.strip() or _TIMESTAMP_LINE.match(line):
            continue
        lines.append(_TIMESTAMP_PREFIX.sub("", line).strip())
    return re.sub(r"\s+", " ", " ".join(lines)).strip()
