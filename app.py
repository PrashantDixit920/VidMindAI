import html
import os
import re
import tempfile

import streamlit as st
from dotenv import load_dotenv

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarize import summarize, generate_title
from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

st.set_page_config(
    page_title="VidMindAI: Watch less, know more",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ====================================================================== CSS
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #0e0b1f;
  --surface: #17132f;
  --surface-2: #201a42;
  --line: #31295f;
  --text: #eeeaff;
  --muted: #a39dd0;
  --indigo: #7371fc;
  --violet: #a594f9;
  --lilac: #cdc1ff;
  --ink: #120e2b;
}

/* ---------- base ---------- */
html, body, .stApp, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
.stApp {
  color: var(--text);
  background:
    radial-gradient(900px 500px at 85% -10%, rgba(115,113,252,.28), transparent 60%),
    radial-gradient(700px 420px at -5% 105%, rgba(165,148,249,.18), transparent 60%),
    var(--bg);
}
.stApp p, .stApp li, .stApp label, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: var(--text); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 1180px; }
hr { border-color: var(--line) !important; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #17132f 0%, #110e26 100%);
  border-right: 1px solid var(--line);
}
.brand { display:flex; align-items:center; gap:12px; margin: 4px 0 6px 0; }
.brand-mark {
  width:40px; height:40px; border-radius:12px; display:grid; place-items:center; font-size:1.2rem;
  background: linear-gradient(135deg, var(--indigo), var(--violet));
  box-shadow: 0 6px 22px rgba(115,113,252,.45);
}
.brand-name { font-weight:800; font-size:1.15rem; letter-spacing:-.01em; }
.brand-sub { color: var(--muted); font-size:.82rem; margin-bottom: 14px; }

/* ---------- inputs ---------- */
[data-testid="stWidgetLabel"] p { color: var(--lilac) !important; font-weight:600; font-size:.88rem; }
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
  background: var(--surface-2) !important;
  color: var(--text) !important;
  border: 1px solid var(--line) !important;
  border-radius: 12px !important;
}
.stTextInput input::placeholder { color: #7f78b0 !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--indigo) !important; box-shadow: 0 0 0 3px rgba(115,113,252,.3) !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: var(--surface-2) !important; }
[data-baseweb="popover"] li { color: var(--text) !important; }
[data-testid="stFileUploaderDropzone"] {
  background: var(--surface-2); border: 1.5px dashed var(--violet); border-radius: 14px;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--muted) !important; }
[data-testid="stFileUploaderDropzone"] button { background: var(--surface); border:1px solid var(--line); color: var(--text) !important; }
div[role="radiogroup"] label { color: var(--text) !important; }

/* ---------- buttons ---------- */
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, var(--indigo), var(--violet)) !important;
  color: var(--ink) !important; font-weight: 700 !important; border: none !important;
  border-radius: 12px !important; padding: .65rem 1.1rem !important;
  box-shadow: 0 8px 24px rgba(115,113,252,.38);
  transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button[kind="primary"] p, [data-testid="stBaseButton-primary"] p { color: var(--ink) !important; font-weight:700; }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
  transform: translateY(-1px); box-shadow: 0 12px 30px rgba(115,113,252,.5);
}
.stButton > button[kind="secondary"], [data-testid="stBaseButton-secondary"] {
  background: var(--surface-2) !important; color: var(--text) !important;
  border: 1px solid var(--line) !important; border-radius: 12px !important; font-weight: 600 !important;
}
.stButton > button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--violet) !important; color: var(--lilac) !important;
}
button:focus-visible { outline: 3px solid var(--lilac) !important; outline-offset: 2px; }

/* ---------- hero ---------- */
.hero {
  position: relative; overflow: hidden;
  border: 1px solid var(--line); border-radius: 24px; padding: 44px 44px 40px 44px; margin-bottom: 26px;
  background:
    radial-gradient(600px 260px at 90% 0%, rgba(165,148,249,.30), transparent 65%),
    linear-gradient(135deg, #1b1640 0%, #120e2b 100%);
}
.hero h1 { font-size: 2.7rem; line-height: 1.08; font-weight: 800; letter-spacing: -.025em; margin: 0 0 14px 0; max-width: 640px; }
.hero h1 .glow {
  background: linear-gradient(90deg, var(--lilac), var(--indigo));
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
}
.hero p { color: var(--muted); font-size: 1.05rem; max-width: 560px; margin: 0; line-height: 1.6; }
.wave { display:flex; align-items:center; gap:5px; height:64px; margin-top: 30px; }
.wave i {
  display:block; width:5px; border-radius:4px; height: 14px;
  background: linear-gradient(180deg, var(--lilac), var(--indigo));
  animation: bounce 1.5s ease-in-out infinite;
}
@keyframes bounce { 0%,100% { height: 10px; opacity:.55; } 50% { height: 58px; opacity:1; } }
@media (prefers-reduced-motion: reduce) { .wave i { animation: none; height: 28px; } }

.result-hero { padding: 30px 36px; }
.result-hero h1 { font-size: 2rem; margin-bottom: 14px; }
.chips { display:flex; flex-wrap:wrap; gap:8px; }
.chip {
  display:inline-flex; align-items:center; gap:6px; padding: 6px 12px; border-radius: 999px;
  background: rgba(115,113,252,.16); border: 1px solid rgba(165,148,249,.4);
  color: var(--lilac); font-size:.84rem; font-weight:600; max-width: 100%;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}

/* ---------- stat tiles ---------- */
.tile {
  background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px;
  position: relative; overflow: hidden;
}
.tile::before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background: var(--c, var(--indigo)); }
.tile .label { color: var(--muted); font-size:.82rem; font-weight:600; }
.tile .value { font-size: 1.75rem; font-weight: 800; color: var(--text); letter-spacing:-.02em; margin-top:2px; }
.tile .value small { font-size:.85rem; color: var(--muted); font-weight:600; margin-left:4px; }

/* ---------- tabs ---------- */
[data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--line); }
button[data-baseweb="tab"] { background: transparent; padding: 10px 16px; border-radius: 10px 10px 0 0; }
button[data-baseweb="tab"] p { color: var(--muted) !important; font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] p { color: var(--lilac) !important; }
[data-baseweb="tab-highlight"] { background: linear-gradient(90deg, var(--indigo), var(--violet)) !important; height: 3px !important; }
[data-baseweb="tab-border"] { background: transparent !important; }

/* ---------- content ---------- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] .summary-marker) {
  background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 8px 12px;
}
.summary-text p, .summary-text li { line-height: 1.75; font-size: 1.02rem; }

.item {
  display:flex; gap:14px; align-items:flex-start; padding: 16px 18px; margin-bottom: 12px;
  background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--c);
  border-radius: 14px; line-height: 1.6;
  transition: border-color .15s ease, background .15s ease;
}
.item:hover { background: var(--surface-2); border-color: var(--c); }
.item .dot {
  flex: 0 0 28px; height: 28px; border-radius: 9px; display:grid; place-items:center;
  font-weight: 800; font-size: .9rem; color: var(--ink); background: var(--c);
}
.item .body { padding-top: 2px; }
.item b { color: var(--lilac); }
.empty {
  border: 1.5px dashed var(--line); border-radius: 16px; padding: 28px; text-align:center; color: var(--muted);
}

.transcript {
  font-family: 'JetBrains Mono', monospace; font-size: .88rem; line-height: 1.85; color: #dcd7f7;
  background: #0b0919; border: 1px solid var(--line); border-radius: 16px;
  padding: 22px 24px; max-height: 460px; overflow-y: auto; white-space: pre-wrap;
}
.transcript mark { background: var(--violet); color: var(--ink); padding: 1px 4px; border-radius: 4px; font-weight: 600; }
.hit {
  padding: 12px 16px; margin-bottom: 8px; background: var(--surface); border:1px solid var(--line);
  border-radius: 12px; line-height: 1.6;
}
.hit mark { background: var(--violet); color: var(--ink); padding: 1px 4px; border-radius: 4px; font-weight: 600; }

/* how-it-works cards (empty state) */
.step { background: var(--surface); border:1px solid var(--line); border-radius:16px; padding: 20px; height:100%; }
.step h4 { margin: 10px 0 6px 0; font-size: 1.02rem; }
.step p { color: var(--muted) !important; margin:0; font-size:.93rem; line-height:1.55; }
.step .ico { width:38px; height:38px; border-radius:11px; display:grid; place-items:center; font-size:1.15rem;
  background: rgba(115,113,252,.2); border:1px solid rgba(165,148,249,.4); }
.sample-title { font-weight:700; margin: 28px 0 12px 0; color: var(--lilac); }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {
  background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: linear-gradient(135deg, rgba(115,113,252,.30), rgba(165,148,249,.18));
  border-color: rgba(165,148,249,.5);
}
[data-testid="stChatInput"] { background: var(--surface-2); border: 1px solid var(--line); border-radius: 16px; }
[data-testid="stChatInput"] textarea { color: var(--text) !important; }

/* ---------- status / expander ---------- */
[data-testid="stStatusWidget"], [data-testid="stExpander"], details {
  background: var(--surface) !important; border: 1px solid var(--line) !important; border-radius: 14px !important;
}
[data-testid="stAlert"] { border-radius: 14px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ================================================================== state
for key, val in {"result": None, "chat": [], "source_label": "", "language": "english"}.items():
    st.session_state.setdefault(key, val)

# ================================================================ helpers
ACCENTS = {
    "action": ("#7371fc", "✓"),
    "decision": ("#a594f9", "◆"),
    "question": ("#cdc1ff", "?"),
}


def esc(text: str) -> str:
    return html.escape(str(text))


def inline_md(text: str) -> str:
    """Escape, then allow **bold** only."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(text))


def to_items(value) -> list[str]:
    """Normalise extractor output (str or list) into a clean list of items."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    items: list[str] = []
    for line in str(value).splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(?:[-*•]|\d+[.)])\s+(.*)", s)
        if m:
            items.append(m.group(1).strip())
        elif line[:1] in (" ", "\t") and items:
            items[-1] += " " + s
        elif s.endswith(":") and len(s) < 40:
            continue  # section label such as "Action items:"
        else:
            items.append(s)
    return items


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(f"- {v}" for v in value)
    return str(value)


def render_items(value, kind: str, empty_msg: str):
    items = to_items(value)
    if not items:
        st.markdown(f'<div class="empty">{esc(empty_msg)}</div>', unsafe_allow_html=True)
        return
    color, glyph = ACCENTS[kind]
    cards = "".join(
        f'<div class="item" style="--c:{color}"><div class="dot">{glyph}</div>'
        f'<div class="body">{inline_md(it)}</div></div>'
        for it in items
    )
    st.markdown(cards, unsafe_allow_html=True)


def highlight(text: str, query: str) -> str:
    safe = esc(text)
    if not query:
        return safe
    return re.sub(
        f"({re.escape(esc(query))})", r"<mark>\1</mark>", safe, flags=re.IGNORECASE
    )


def wave_html(n: int = 34) -> str:
    bars = "".join(
        f'<i style="animation-delay:{(i * 0.09) % 1.4:.2f}s"></i>' for i in range(n)
    )
    return f'<div class="wave" aria-hidden="true">{bars}</div>'


def build_export(result: dict) -> str:
    return (
        f"# {result['title']}\n\n"
        f"## Summary\n{as_text(result['summary'])}\n\n"
        f"## Action items\n{as_text(result['action_items'])}\n\n"
        f"## Key decisions\n{as_text(result['key_decisions'])}\n\n"
        f"## Open questions\n{as_text(result['open_questions'])}\n\n"
        f"## Transcript\n{result['transcript']}\n"
    )


def run_pipeline_ui(source: str, language: str) -> dict:
    """Same steps as run_pipeline(), with live progress."""
    with st.status("Processing your video…", expanded=True) as status:
        # All downloads and chunks live in a temp folder that is deleted
        # as soon as transcription finishes (or fails).
        with tempfile.TemporaryDirectory() as work_dir:
            st.write("🎧 Fetching and splitting audio")
            chunks = process_input(source, work_dir)

            st.write("📝 Transcribing speech")
            transcript = transcribe_all(chunks, language=language)

        st.write("✍️ Writing title and summary")
        title = generate_title(transcript)
        summary = summarize(transcript)

        st.write("🔎 Finding action items, decisions and open questions")
        action_items = extract_action_items(transcript)
        decisions = extract_key_decisions(transcript)
        questions = extract_questions(transcript)

        st.write("🧠 Indexing transcript for chat")
        rag_chain = build_rag_chain(transcript)

        status.update(label="Done. Your video is ready.", state="complete", expanded=False)

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


# ================================================================ sidebar
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">🎬</div>'
        '<div class="brand-name">VidMind</div></div>'
        '<div class="brand-sub">Watch less. Know more.</div>',
        unsafe_allow_html=True,
    )

    input_mode = st.radio("Source", ["YouTube link", "Upload a file"], horizontal=True)

    source, uploaded = None, None
    if input_mode == "YouTube link":
        source = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=…")
    else:
        uploaded = st.file_uploader(
            "Audio or video file",
            type=["mp3", "wav", "m4a", "mp4", "mov", "mkv", "webm"],
        )

    language = st.selectbox("Spoken language", ["english", "hinglish"])
    st.write("")
    process_clicked = st.button("Process video", type="primary", use_container_width=True)

    if st.session_state.result:
        st.divider()
        if st.button("Start over", use_container_width=True):
            st.session_state.result = None
            st.session_state.chat = []
            st.session_state.source_label = ""
            st.rerun()

# ================================================================== run
if process_clicked:
    tmp_path = None
    try:
        if input_mode == "Upload a file":
            if uploaded is None:
                st.sidebar.error("Choose a file to upload first.")
                st.stop()
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name
            source_value, label = tmp_path, uploaded.name
        else:
            if not source or not source.strip():
                st.sidebar.error("Paste a YouTube link first.")
                st.stop()
            source_value, label = source.strip(), source.strip()

        st.session_state.result = run_pipeline_ui(source_value, language)
        st.session_state.chat = []
        st.session_state.source_label = label
        st.session_state.language = language
    except Exception as exc:
        st.error(
            f"Processing stopped: {exc}\n\n"
            "Check the link or file, your API keys in `.env`, and that ffmpeg is installed."
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# ============================================================== main view
result = st.session_state.result

# ---------------------------------------------------------- empty state
if not result:
    st.markdown(
        f"""
        <div class="hero">
          <h1>Watch less. <span class="glow">Know more.</span></h1>
          <p>VidMind turns any YouTube link or recording into a summary, action items,
          decisions and open questions, then lets you ask the video anything.</p>
          {wave_html()}
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    for col, ico, head, body in [
        (c1, "🔗", "Add a source", "Use a YouTube link, or upload audio or video from your device."),
        (c2, "🌐", "Pick the language", "Choose English, or Hinglish for speech that mixes Hindi and English."),
        (c3, "💬", "Read, then ask", "Review the notes, then ask follow-up questions in the Chat tab."),
    ]:
        col.markdown(
            f'<div class="step"><div class="ico">{ico}</div><h4>{head}</h4><p>{body}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sample-title">What the results look like</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    for col, kind, text in [
        (s1, "action", "**Priya** to share the revised launch deck with the team by Friday."),
        (s2, "decision", "Rollout starts in **Pune and Bengaluru** before expanding to other cities."),
        (s3, "question", "Who will own vendor onboarding once **Arjun** moves to the new project?"),
    ]:
        color, glyph = ACCENTS[kind]
        col.markdown(
            f'<div class="item" style="--c:{color}"><div class="dot">{glyph}</div>'
            f'<div class="body">{inline_md(text)}</div></div>',
            unsafe_allow_html=True,
        )
    st.stop()

# -------------------------------------------------------- results header
label = st.session_state.source_label
short_label = label if len(label) <= 70 else label[:67] + "…"
st.markdown(
    f"""
    <div class="hero result-hero">
      <h1>{esc(result['title'])}</h1>
      <div class="chips">
        <span class="chip">🌐 {esc(st.session_state.language.title())}</span>
        <span class="chip">🎞️ {esc(short_label)}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

n_actions = len(to_items(result["action_items"]))
n_decisions = len(to_items(result["key_decisions"]))
n_questions = len(to_items(result["open_questions"]))
word_count = len(result["transcript"].split())

tiles = [
    ("Transcript", f"{word_count:,}<small>words</small>", "#7371fc"),
    ("Action items", str(n_actions), ACCENTS["action"][0]),
    ("Key decisions", str(n_decisions), ACCENTS["decision"][0]),
    ("Open questions", str(n_questions), ACCENTS["question"][0]),
]
for col, (lab, val, color) in zip(st.columns(4), tiles):
    col.markdown(
        f'<div class="tile" style="--c:{color}"><div class="label">{lab}</div>'
        f'<div class="value">{val}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
    [
        "Summary",
        f"Action items ({n_actions})",
        f"Key decisions ({n_decisions})",
        f"Open questions ({n_questions})",
        "Transcript",
        "Chat",
    ]
)

with tab_summary:
    with st.container(border=True):
        st.markdown('<span class="summary-marker"></span>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-text">\n\n{as_text(result["summary"])}\n\n</div>', unsafe_allow_html=True)

with tab_actions:
    render_items(result["action_items"], "action", "No action items were found in this video.")

with tab_decisions:
    render_items(result["key_decisions"], "decision", "No key decisions were found in this video.")

with tab_questions:
    render_items(result["open_questions"], "question", "No open questions were found in this video.")

with tab_transcript:
    left, right = st.columns([3, 1])
    query = left.text_input("Find in transcript", placeholder="Type a word or phrase")
    right.write("")
    right.write("")
    right.download_button(
        "Download notes",
        data=build_export(result),
        file_name="vidmind_notes.md",
        mime="text/markdown",
        use_container_width=True,
    )
    transcript = result["transcript"]
    if query.strip():
        sentences = re.split(r"(?<=[.!?।])\s+", transcript)
        hits = [s for s in sentences if query.lower() in s.lower()]
        st.caption(f"{len(hits)} matching sentence(s)")
        if hits:
            st.markdown(
                "".join(f'<div class="hit">{highlight(h, query.strip())}</div>' for h in hits),
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="empty">No matches. Try a different word.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="transcript">{esc(transcript)}</div>', unsafe_allow_html=True)

with tab_chat:
    st.caption("Answers come from this video's transcript only.")

    if not st.session_state.chat:
        suggestions = [
            "What are the main takeaways?",
            "Who is responsible for what?",
            "What was decided, and why?",
        ]
        for col, s in zip(st.columns(len(suggestions)), suggestions):
            if col.button(s, key=f"sugg_{s}", use_container_width=True):
                st.session_state.pending_question = s
                st.rerun()

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    typed = st.chat_input("Ask something about the video")
    question = typed or st.session_state.pop("pending_question", None)

    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Looking through the transcript…"):
                try:
                    answer = ask_question(result["rag_chain"], question)
                except Exception as exc:
                    answer = f"I couldn't answer that: {exc}"
            st.markdown(answer)
        st.session_state.chat.append({"role": "assistant", "content": answer})