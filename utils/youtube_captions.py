"""Shortcuts that skip audio download and transcription.

1. fetch_captions(): read the captions YouTube already has for a video.
   No download, ffmpeg or JavaScript runtime needed. YouTube may still block
   this on cloud servers, so callers should be ready to fall back.
2. clean_pasted_transcript(): tidy a transcript copied from YouTube's
   "Show transcript" panel (removes timestamps).
"""

import re
from urllib.parse import parse_qs, urlparse

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TIMESTAMP_LINE = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s*$")
_TIMESTAMP_PREFIX = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s+")

CAPTION_LANGUAGES = ("en", "en-IN", "en-US", "en-GB", "hi")
MIN_CAPTION_WORDS = 20


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
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                candidate = parts[1]

    return candidate if _VIDEO_ID.match(candidate) else None


def fetch_captions(url: str, languages=CAPTION_LANGUAGES) -> str:
    """Return the video's captions as one block of text, or raise CaptionsUnavailable."""
    video_id = extract_video_id(url)
    if not video_id:
        raise CaptionsUnavailable("the link does not look like a YouTube video")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise CaptionsUnavailable(
            "the youtube-transcript-api package is not installed"
        ) from exc

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

    text = " ".join(s.text.strip() for s in fetched if getattr(s, "text", "").strip())
    text = re.sub(r"\s+", " ", text).strip()
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