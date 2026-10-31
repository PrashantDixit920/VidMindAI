# VidMindAI

**Watch less. Know more.**

VidMindAI turns a YouTube link or a recording into a summary, action items, key decisions and open questions, then lets you chat with the video. It runs as a Streamlit app.

## Features

- **Three ways in:**
  - **YouTube link:** VidMind first reads the video's existing captions (fast, no download). If there are none, it falls back to downloading the audio.
  - **Upload a file:** audio or video (mp3, wav, m4a, mp4, mov, mkv, webm).
  - **Paste transcript:** copy the text from YouTube's "Show transcript" panel and paste it in. Timestamps are removed automatically. No download or transcription is needed.
- **Two languages:** English, or Hinglish (mixed Hindi and English speech, transcribed and translated to English).
- **Structured notes:** title, summary, action items, key decisions and open questions.
- **Searchable transcript:** find any word or phrase, and download everything as a Markdown file.
- **Chat with the video:** ask questions and get answers based on the transcript (retrieval-augmented generation, or RAG).
- **Dark, responsive UI:** built with Streamlit and custom styling.

## How it works

```
YouTube link / uploaded file
        |
        v
  audio extraction  ->  mono 16 kHz WAV chunks (ffmpeg)
        |
        v
  transcription      English: Whisper   |   Hinglish: Sarvam AI
        |
        v
  title, summary, action items, decisions, questions
        |
        v
  RAG index over the transcript  ->  chat
```

Temporary audio files are created in a throwaway folder for each run and deleted as soon as transcription finishes. Each browser session keeps its own transcript and chat, so users do not see each other's data.

## Project structure

```
vidmind/
├── app.py                  # Streamlit app (entry point)
├── core/
│   ├── transcriber.py      # Whisper and Sarvam transcription
│   ├── summarize.py        # title and summary
│   ├── extractor.py        # action items, decisions, open questions
│   └── rag_engine.py       # RAG chain and question answering
├── utils/
│   └── audio_processor.py  # download, convert and chunk audio
├── .streamlit/
│   └── config.toml         # dark theme settings
├── requirements.txt
├── packages.txt            # system packages for Streamlit Cloud (ffmpeg)
└── .gitignore
```

## Run it locally

**Requirements:** Python 3.10 or newer, and [ffmpeg](https://ffmpeg.org/download.html) installed and on your PATH.

```bash
# 1. Clone and enter the project
git clone https://github.com/PrashantDixit920/VidMindAI.git
cd vidmind

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your keys (see the table below)
cp .env.example .env             # then edit .env

# 5. Start the app
streamlit run app.py
```

Install ffmpeg with `brew install ffmpeg` (macOS), `sudo apt install ffmpeg` (Ubuntu/Debian) or `choco install ffmpeg` (Windows).

## Configuration

Settings are read from environment variables. Locally they come from a `.env` file. On Streamlit Cloud they come from the app's **Secrets**.

<!-- TODO: add the key your summarize, extractor and RAG code uses (for example OPENAI_API_KEY) to this table and to .env.example. -->

| Variable | Required | Description |
| --- | --- | --- |
| `SARVAM_API_KEY` | For Hinglish | Your Sarvam AI API key. |
| `SARVAM_STT_MODEL` | No | Sarvam model name. Defaults to `saaras:v2.5`. |
| `WHISPER_MODEL` | No | Whisper model size for English. Defaults to `small`. |
| *LLM provider key* | Yes | The key for the model that writes summaries, extracts items and answers questions. |

Example `.env.example`:

```env
SARVAM_API_KEY=your-sarvam-key
SARVAM_STT_MODEL=saaras:v2.5
WHISPER_MODEL=small
# Add your LLM provider key here
```

Never commit your real `.env` file. It is already listed in `.gitignore`.

## Deploy on Streamlit Community Cloud

1. Push the project to a GitHub repository. Check that `requirements.txt` and `packages.txt` are included. `packages.txt` should contain one line: `ffmpeg`.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app from the repository and set the main file to `app.py`.
3. Open **Advanced settings → Secrets** and paste your keys in TOML format:

   ```toml
   SARVAM_API_KEY = "your-sarvam-key"
   SARVAM_STT_MODEL = "saaras:v2.5"
   # your LLM provider key
   ```

4. Deploy, then test with an uploaded file and with a YouTube link.

### Good to know when deploying

- **YouTube links may fail on cloud servers.** YouTube often blocks requests from data-center IP addresses, for both caption lookups and audio downloads, so a link that works on your laptop may fail once deployed. **Upload a file** and **Paste transcript** are the reliable options on the hosted app.
- **Memory is limited on the free tier** (roughly 1 GB). Running Whisper locally for English may not fit. A hosted transcription API is a safer choice for a public deployment.
- **Video length is capped.** Links longer than 90 minutes are rejected. Change `MAX_VIDEO_MINUTES` in `utils/audio_processor.py` to adjust this.
- **Uploads are limited to 200 MB by default.** Raise the limit with `maxUploadSize` under `[server]` in `.streamlit/config.toml`.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `ffmpeg was not found` | Install ffmpeg locally, or add `ffmpeg` to `packages.txt` on Streamlit Cloud. |
| Sarvam returns 401 or 403 | `SARVAM_API_KEY` is missing or wrong. |
| Sarvam returns 429 | Rate limit. The app retries a few times; wait a moment and try again. |
| YouTube download fails | Try a different link, update `yt-dlp` (`pip install -U yt-dlp`), or upload the file instead. |
| Transcript is empty | The audio may be silent or too short (under about a second). |

## Built with

[Streamlit](https://streamlit.io), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [ffmpeg](https://ffmpeg.org), [OpenAI Whisper](https://github.com/openai/whisper), [Sarvam AI](https://www.sarvam.ai) and [LangChain](https://www.langchain.com).