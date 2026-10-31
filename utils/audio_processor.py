import glob
import os
import shutil
import subprocess

import yt_dlp

# Longest video accepted from a link. Keeps a shared server from being tied up.
MAX_VIDEO_MINUTES = 90

# Chunks shorter than this are dropped. ffmpeg can leave a tiny leftover
# piece at the end, and transcription APIs reject audio that short.
MIN_CHUNK_SECONDS = 1.0

# 16 kHz, mono, 16-bit PCM WAV: 32,000 bytes per second plus a 44-byte header.
_WAV_BYTES_PER_SECOND = 16000 * 2
_WAV_HEADER_BYTES = 44


def _download_failed_message(exc: Exception) -> str:
    detail = str(exc).replace("ERROR: ", "").strip()[-160:]
    return (
        "The video could not be downloaded. YouTube often blocks downloads from "
        "cloud servers, and the video may also be private or removed. "
        "Please upload the audio or video file instead. "
        f"(Details: {detail})"
    )


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg was not found. Install it locally, or on Streamlit Cloud "
            "add a line 'ffmpeg' to packages.txt."
        )


def download_youtube_audio(url: str, work_dir: str, max_minutes: int = MAX_VIDEO_MINUTES) -> str:
    """Download only the audio track into work_dir and return its path."""
    base_opts = {"quiet": True, "no_warnings": True, "noplaylist": True}

    # Check the length first so a very long video is rejected before downloading.
    try:
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(_download_failed_message(exc)) from exc
    duration = info.get("duration")
    if duration and duration > max_minutes * 60:
        raise ValueError(
            f"This video is {duration // 60} minutes long. The limit is {max_minutes} minutes."
        )

    opts = {
        **base_opts,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(work_dir, "download.%(ext)s"),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(_download_failed_message(exc)) from exc

    files = glob.glob(os.path.join(work_dir, "download.*"))
    if not files:
        raise RuntimeError("The download finished but no audio file was found.")
    return max(files, key=os.path.getsize)


def convert_and_chunk(input_path: str, chunks_dir: str, chunk_minutes: int = 10) -> list:
    """Convert to mono 16 kHz WAV and split into chunks in one ffmpeg pass.

    ffmpeg streams the file, so the whole recording is never loaded into RAM
    (pydub decodes everything into memory, which is risky on a small server).
    """
    _require_ffmpeg()
    os.makedirs(chunks_dir, exist_ok=True)
    pattern = os.path.join(chunks_dir, "chunk_%03d.wav")

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", input_path,
        "-vn",                      # ignore any video stream
        "-ac", "1",                 # mono
        "-ar", "16000",             # 16 kHz
        "-c:a", "pcm_s16le",
        "-f", "segment",
        "-segment_time", str(chunk_minutes * 60),
        "-reset_timestamps", "1",
        pattern,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or "").strip()[-400:]
        raise RuntimeError(f"ffmpeg could not process this file. {tail}") from exc

    chunks = []
    for path in sorted(glob.glob(os.path.join(chunks_dir, "chunk_*.wav"))):
        seconds = max(0, os.path.getsize(path) - _WAV_HEADER_BYTES) / _WAV_BYTES_PER_SECOND
        if seconds < MIN_CHUNK_SECONDS:
            os.remove(path)  # tiny leftover at the end of the recording
        else:
            chunks.append(path)

    if not chunks:
        raise RuntimeError("No usable audio was found. The recording may be empty or too short.")
    return chunks


def process_input(source: str, work_dir: str, chunk_minutes: int = 10) -> list:
    """Return a list of chunk file paths, all stored inside work_dir.

    The caller owns work_dir and should create it with
    tempfile.TemporaryDirectory() so everything is deleted afterwards.
    """
    downloaded = None
    if source.startswith(("http://", "https://")):
        print("Detected a link. Downloading audio...")
        downloaded = download_youtube_audio(source, work_dir)
        input_path = downloaded
    else:
        if not os.path.isfile(source):
            raise FileNotFoundError(f"File not found: {source}")
        print("Detected a local file. Converting...")
        input_path = source

    print("Converting and chunking audio...")
    chunks = convert_and_chunk(input_path, os.path.join(work_dir, "chunks"), chunk_minutes)

    # The raw download is no longer needed once the chunks exist.
    if downloaded and os.path.exists(downloaded):
        os.remove(downloaded)

    print(f"Audio ready: {len(chunks)} chunk(s) created.")
    return chunks