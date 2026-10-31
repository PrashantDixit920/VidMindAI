import math
import os
import time

import requests
import whisper
from pydub import AudioSegment

SARVAM_STT_TRANSLATE_URL = "https://api.sarvam.ai/speech-to-text-translate"

# Sarvam's sync API accepts at most 30 seconds per request.
SARVAM_MAX_PIECE_SECONDS = 25
# Anything shorter than this is skipped; Sarvam rejects extremely short audio.
MIN_PIECE_MS = 1000

_model = None


# Settings are read when needed (not at import time), so keys loaded later by
# load_dotenv() or copied in from st.secrets are still picked up.
def _whisper_model_name() -> str:
    return os.getenv("WHISPER_MODEL", "small")


def _sarvam_key() -> str | None:
    return os.getenv("SARVAM_API_KEY")


def _sarvam_model() -> str:
    return os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")


# ------------------------------------------------------------------ Whisper
def load_model():
    global _model
    if _model is None:
        _model = whisper.load_model(_whisper_model_name())
    return _model


def transcribe_chunk_whisper(chunk_path: str) -> str:
    model = load_model()
    result = model.transcribe(chunk_path, task="transcribe")
    return result["text"]


# ------------------------------------------------------------------- Sarvam
def _send_to_sarvam(piece_path: str, retries: int = 3) -> str:
    """Send one WAV piece (30 s or less) to Sarvam and return the English transcript."""
    headers = {"api-subscription-key": _sarvam_key()}
    data = {"model": _sarvam_model(), "with_diarization": "false"}

    for attempt in range(1, retries + 1):
        try:
            with open(piece_path, "rb") as f:
                files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
                response = requests.post(
                    SARVAM_STT_TRANSLATE_URL,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=120,
                )
        except (requests.Timeout, requests.ConnectionError):
            if attempt < retries:
                time.sleep(2 * attempt)
                continue
            raise

        if response.ok:
            return response.json().get("transcript", "")

        # Rate limits and temporary server errors are worth retrying.
        if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(2 * attempt)
            continue

        print(f"\nSarvam returned {response.status_code}")
        print(f"Response body: {response.text}\n")
        response.raise_for_status()

    return ""


def transcribe_chunk_sarvam(chunk_path: str) -> str:
    """
    Sarvam's sync API only accepts audio up to 30 seconds. Split the chunk into
    equal pieces of 25 seconds or less, send each one, and join the transcripts.
    Equal pieces mean there is never a tiny leftover at the end.
    """
    if not _sarvam_key():
        raise RuntimeError("SARVAM_API_KEY is not set (check your .env or Streamlit secrets).")

    audio = AudioSegment.from_wav(chunk_path)
    total_ms = len(audio)
    if total_ms < MIN_PIECE_MS:
        return ""

    max_piece_ms = SARVAM_MAX_PIECE_SECONDS * 1000
    n_pieces = math.ceil(total_ms / max_piece_ms)
    piece_ms = math.ceil(total_ms / n_pieces)

    parts = []
    attempted = 0
    failed = 0

    for i, start in enumerate(range(0, total_ms, piece_ms)):
        piece = audio[start:start + piece_ms]
        if len(piece) < MIN_PIECE_MS:
            continue

        attempted += 1
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")

        try:
            parts.append(_send_to_sarvam(piece_path))
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (401, 403):
                raise RuntimeError(
                    "Sarvam rejected the API key. Check SARVAM_API_KEY."
                ) from exc
            failed += 1
            print(f"Skipping piece {i} of {os.path.basename(chunk_path)} (HTTP {status}).")
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

    if attempted and failed == attempted:
        raise RuntimeError("Sarvam could not transcribe any part of this audio.")
    if failed:
        print(f"Warning: {failed} of {attempted} pieces failed and were left out.")

    return " ".join(p.strip() for p in parts if p and p.strip())


# ------------------------------------------------------------------ Routing
def transcribe_chunk(chunk_path: str, language: str = "english") -> str:
    """
    Route one chunk to Whisper or Sarvam depending on language choice.
    - english  -> Whisper (local model)
    - hinglish -> Sarvam (translates to English while transcribing)
    """
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(chunk_path)
    return transcribe_chunk_whisper(chunk_path)


def transcribe_all(chunks: list, language: str = "english") -> str:
    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    print(f"Using {engine} for transcription.")

    texts = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Transcribing chunk {i} of {len(chunks)}...")
        text = transcribe_chunk(chunk, language=language)
        if text and text.strip():
            texts.append(text.strip())

    return " ".join(texts)