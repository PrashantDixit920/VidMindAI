# VidMindAI

**Watch less. Know more.**

VidMindAI is an AI-powered video assistant that transforms YouTube videos and audio/video recordings into structured notes. Generate summaries, action items, key decisions and open questions, then interact with your video through AI-powered chat.

## 🚀 Live Demo

**[Try VidMindAI](https://vidmindai.streamlit.app/)**

Explore the application directly in your browser — no local installation required.

## ✨ Features

- **Multiple input options**
  - **YouTube URL:** Fetches video transcripts using the Supadata API. Retrieves existing captions when available and uses AI-powered transcription when captions are unavailable.
  - **Upload a file:** Supports audio and video formats including MP3, WAV, M4A, MP4, MOV, MKV and WEBM.
  - **Paste transcript:** Paste text copied from YouTube's transcript panel. Timestamps are removed automatically.
- **Two transcription languages:** English and Hinglish (mixed Hindi and English speech, transcribed and translated into English).
- **Structured AI notes:** Automatically generates video titles, summaries, action items, key decisions and open questions.
- **Searchable transcript:** Find specific words or phrases and download the complete notes as a Markdown file.
- **Chat with your video:** Ask questions and receive context-aware answers based on the transcript using Retrieval-Augmented Generation (RAG).
- **Dark, responsive UI:** Built with Streamlit and custom styling.

## ⚙️ How It Works

### YouTube URL workflow

```text
        YouTube URL
             |
             v
       Supadata API
             |
             v
   Existing captions available?
        /           \
      Yes            No
       |              |
       v              v
  Retrieve       AI-generated
  captions        transcript
       \              /
        \            /
             v
       Transcript text
             |
             v
   AI-powered summarization
             |
             v
  Title, summary, action items,
  decisions and open questions
             |
             v
      RAG index creation
             |
             v
       Chat with video
```

### Uploaded audio/video workflow

```text
      Uploaded audio/video
               |
               v
       Audio extraction
               |
               v
    Mono 16 kHz WAV chunks
            (FFmpeg)
               |
               v
         Transcription
        /             \
    English          Hinglish
    Whisper          Sarvam AI
        \             /
               |
               v
        Transcript text
               |
               v
     AI notes + RAG chat
```

Temporary audio files are created in a separate folder for each run and deleted after transcription finishes. Each browser session maintains its own transcript and chat, keeping users' sessions separate.

## 📁 Project Structure

```text
vidmind/
├── app.py                  # Streamlit application (entry point)
├── core/
│   ├── transcriber.py      # Whisper and Sarvam transcription
│   ├── summarize.py        # Title and summary generation
│   ├── extractor.py        # Action items, decisions, questions
│   └── rag_engine.py       # RAG chain and question answering
├── utils/
│   └── audio_processor.py  # Audio download, conversion and chunking
├── youtube_captions.py     # YouTube transcript retrieval via Supadata
├── .streamlit/
│   └── config.toml         # Streamlit theme settings
├── requirements.txt
├── packages.txt            # System packages for Streamlit Cloud
└── .gitignore
```

## 💻 Run Locally

### Requirements

- Python 3.10 or newer
- FFmpeg installed and available in your system PATH
- API keys for the services you use

Download FFmpeg: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/PrashantDixit920/VidMindAI.git
cd VidMindAI
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file in the project root and add your API keys.

**5. Run the application**

```bash
streamlit run app.py
```

Install FFmpeg if it is not already installed:

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: `choco install ffmpeg`

## 🔑 Configuration

VidMindAI uses environment variables for API credentials and model configuration.

For local development, configure them in your `.env` file. For Streamlit Cloud, add them under **App Settings → Secrets**.

| Variable | Required | Description |
|---|---|---|
| `SUPADATA_API_KEY` | Yes, for YouTube URLs | API key for retrieving or generating YouTube transcripts through Supadata. |
| `SARVAM_API_KEY` | For Hinglish | Your Sarvam AI API key. |
| `SARVAM_STT_MODEL` | No | Sarvam transcription model. Defaults to `saaras:v2.5`. |
| `WHISPER_MODEL` | No | Whisper model size for English transcription. Defaults to `small`. |
| LLM provider API key | Yes | API key for the model used to generate summaries, extract information and answer questions. |

### Example `.env`

```env
SUPADATA_API_KEY=your-supadata-api-key
SARVAM_API_KEY=your-sarvam-api-key
SARVAM_STT_MODEL=saaras:v2.5
WHISPER_MODEL=small

# Add your LLM provider API key here
```

**Important:** Never commit your real `.env` file or expose API keys in your source code. Keep `.env` listed in `.gitignore`.

## ☁️ Deploy on Streamlit Community Cloud

**1. Push your project to GitHub.**

Make sure `requirements.txt` and `packages.txt` are included. Your `packages.txt` should contain:

```text
ffmpeg
```

**2. Create a Streamlit Cloud application.**

Visit [Streamlit Community Cloud](https://share.streamlit.io/), connect your GitHub repository and set the main application file to `app.py`.

**3. Configure Streamlit Secrets.**

Open **Advanced settings → Secrets** and add your credentials in TOML format:

```toml
SUPADATA_API_KEY = "your-supadata-api-key"

SARVAM_API_KEY = "your-sarvam-api-key"
SARVAM_STT_MODEL = "saaras:v2.5"
WHISPER_MODEL = "small"

# Add your LLM provider API key here
```

**4. Deploy and test.**

Once deployment is complete, test the application with:
- A YouTube video that has existing captions.
- A YouTube video without existing captions.
- An uploaded audio/video file.
- A pasted transcript.

### Supadata API Integration

VidMindAI uses the [Supadata API](https://supadata.ai/) to make YouTube transcription more reliable on cloud deployments.

The integration supports two transcription scenarios:

- **Native captions:** Retrieves existing YouTube captions when available.
- **AI-generated transcription:** If native captions are unavailable, Supadata can generate a transcript using AI when the API is configured with `mode="auto"`.

This avoids depending entirely on downloading YouTube audio from Streamlit Cloud servers, where YouTube may restrict requests from data-center IP addresses.

**Things to keep in mind:**
- AI-generated transcription consumes more API credits than retrieving existing captions.
- API usage is subject to Supadata's rate limits and available credits.
- Private, deleted, restricted or inaccessible videos may not be transcribable.
- If the API request fails, the application's existing audio-download fallback may still be subject to YouTube restrictions.

Documentation: [Supadata API](https://docs.supadata.ai/)

### Other Deployment Considerations

- **Memory limitations:** Streamlit Community Cloud's free resources are limited. Running Whisper locally for English transcription can require significant memory. A hosted transcription API is useful for cloud deployments.
- **Video duration:** Videos longer than 90 minutes are rejected by default. Adjust `MAX_VIDEO_MINUTES` in `utils/audio_processor.py` if required.
- **Upload size:** Uploads are limited to 200 MB by default. This can be adjusted using `maxUploadSize` under `[server]` in `.streamlit/config.toml`.

## 🛠️ Troubleshooting

| Problem | What to check |
|---|---|
| Supadata returns 401 or 403 | Check whether `SUPADATA_API_KEY` is configured correctly. |
| Supadata returns 402 | Check your available API credits or subscription. |
| Supadata returns 429 | API rate limit reached. Wait and try again. |
| YouTube transcript unavailable | Check whether the video is accessible and whether Supadata can generate a transcript. |
| YouTube audio download fails | YouTube may be blocking cloud requests. Try another video or upload the media file. |
| FFmpeg was not found | Install FFmpeg locally or add it to `packages.txt` on Streamlit Cloud. |
| Sarvam returns 401 or 403 | Check your `SARVAM_API_KEY`. |
| Sarvam returns 429 | Rate limit reached. Wait a moment and retry. |
| Transcript is empty | The audio may be silent or too short. |

## 🧰 Built With

- [Python](https://www.python.org/)
- [Streamlit](https://streamlit.io/)
- [Supadata API](https://supadata.ai/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Sarvam AI](https://www.sarvam.ai/)
- [LangChain](https://www.langchain.com/)

---

**VidMindAI — Watch less. Know more.**

[🚀 Try the Live Application](https://vidmindai.streamlit.app/) · [GitHub Repository](https://github.com/PrashantDixit920/VidMindAI)