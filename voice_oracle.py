"""
Voice Oracle — speak your "why" questions, hear the answers.

Requires (install once):
    pip install SpeechRecognition pyttsx3 sounddevice numpy

Usage:
    python voice_oracle.py
"""

import io
import os
import sys
import time
import wave
from pathlib import Path

# ---------- load .env --------------------------------------------------------

_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------- dependency check -------------------------------------------------

def _check_deps() -> None:
    missing = []
    for pkg, label in [
        ("speech_recognition", "SpeechRecognition"),
        ("pyttsx3",            "pyttsx3"),
        ("sounddevice",        "sounddevice"),
        ("numpy",              "numpy"),
    ]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(label)

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print(f"Install with:\n    pip install {' '.join(missing)}")
        sys.exit(1)

# ---------- Claude client ----------------------------------------------------

import anthropic


def _make_client() -> anthropic.Anthropic:
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    headers = {"anthropic-workspace-id": workspace_id} if workspace_id else {}
    return anthropic.Anthropic(default_headers=headers)

# ---------- Neo4j ------------------------------------------------------------

def _try_neo4j_driver():
    try:
        from graph.query import get_driver
        return get_driver()
    except Exception:
        return None


def _get_context(question: str, driver) -> str:
    if driver is not None:
        try:
            from graph.query import get_graph_context
            ctx = get_graph_context(question, driver)
            if ctx:
                return f"--- KNOWLEDGE GRAPH ---\n{ctx}\n--- END GRAPH ---"
        except Exception as exc:
            print(f"[Neo4j error: {exc}]")

    kb_dir = Path(__file__).parent / "knowledge_base"
    if not kb_dir.exists():
        return ""
    parts: list[str] = []
    for fpath in sorted(kb_dir.rglob("*")):
        if fpath.is_file():
            try:
                parts.append(
                    f"=== {fpath.relative_to(kb_dir)} ===\n"
                    + fpath.read_text(encoding="utf-8", errors="replace")
                )
            except OSError:
                pass
    return ("--- KNOWLEDGE BASE ---\n" + "\n\n".join(parts) + "\n--- END ---") if parts else ""

# ---------- system prompt (voice-optimised) ----------------------------------

_SYSTEM_PROMPT = (
    "You are Swimple's voice-enabled codebase onboarding engineer. "
    "Answer 'why' questions about the codebase in plain, natural spoken English — "
    "no markdown, no bullet points, no code blocks, no asterisks, because your response "
    "will be read aloud. Keep answers concise: 2–4 sentences unless the question clearly "
    "needs more detail. Cite specific component or technology names. "
    "Answer ONLY from the knowledge context supplied; say you don't know if it isn't covered."
)

# ---------- audio recording (sounddevice, no C++ required) -------------------

_SAMPLE_RATE  = 16_000
_MAX_SECS     = 12
_SILENCE_RMS  = 400   # amplitude threshold — tune if too sensitive
_SILENCE_SECS = 1.6   # seconds of quiet that ends the recording


def _record() -> bytes | None:
    """Record until silence, return raw PCM int16 bytes or None."""
    import sounddevice as sd
    import numpy as np

    print("Listening...  (speak now, pause to stop)", flush=True)

    frames: list = []
    silent_frames = 0
    speaking = False
    silence_limit = int(_SILENCE_SECS * _SAMPLE_RATE)
    total_limit   = int(_MAX_SECS    * _SAMPLE_RATE)
    total_frames  = 0

    def _cb(indata, frame_count, time_info, status):
        nonlocal silent_frames, speaking, total_frames
        pcm = (indata * 32768).astype("int16")
        rms = float(np.sqrt(np.mean(pcm.astype("float32") ** 2)))
        if rms > _SILENCE_RMS:
            speaking = True
            silent_frames = 0
        elif speaking:
            silent_frames += frame_count
        frames.append(pcm.copy())
        total_frames += frame_count

    with sd.InputStream(
        samplerate=_SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=1024,
        callback=_cb,
    ):
        while True:
            time.sleep(0.05)
            if total_frames >= total_limit:
                break
            if speaking and silent_frames >= silence_limit:
                break

    if not frames or not speaking:
        print("(no speech detected — try again)\n")
        return None

    import numpy as np
    audio = np.concatenate(frames, axis=0).astype("int16")
    return audio.tobytes()


def _pcm_to_wav(pcm_bytes: bytes) -> io.BytesIO:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # int16 = 2 bytes
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm_bytes)
    buf.seek(0)
    return buf

# ---------- STT & TTS --------------------------------------------------------

def _transcribe(pcm_bytes: bytes) -> str | None:
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    wav_buf = _pcm_to_wav(pcm_bytes)
    print("Transcribing...", flush=True)
    try:
        with sr.AudioFile(wav_buf) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("(couldn't understand — please repeat)\n")
        return None
    except sr.RequestError as exc:
        print(f"(STT service error: {exc})\n")
        return None


def _speak(text: str, engine) -> None:
    clean = (
        text
        .replace("**", "").replace("*", "")
        .replace("`",  "").replace("#",  "")
        .replace("•",  "").replace("→", "to")
    )
    engine.say(clean)
    engine.runAndWait()

# ---------- oracle call ------------------------------------------------------

def _ask_oracle(
    question: str,
    client: anthropic.Anthropic,
    driver,
    messages: list,
) -> str:
    context = _get_context(question, driver)
    system  = _SYSTEM_PROMPT + (f"\n\n{context}" if context else "")
    messages.append({"role": "user", "content": question})

    print("Oracle: ", end="", flush=True)
    response_text = ""
    with client.messages.stream(
        model="claude-opus-5",
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            print(chunk, end="", flush=True)
            response_text += chunk
    print("\n")
    messages.append({"role": "assistant", "content": response_text})
    return response_text

# ---------- entry point ------------------------------------------------------

def run() -> None:
    _check_deps()

    import pyttsx3

    client   = _make_client()
    driver   = _try_neo4j_driver()
    messages: list[dict] = []

    engine = pyttsx3.init()
    engine.setProperty("rate", 170)

    mode = "Neo4j knowledge graph" if driver else "flat-file mode"
    print(f"\nVoice Oracle — {mode}")
    print("Speak your question. Say 'quit' or 'exit' to stop.\n")

    engine.say("Voice Oracle ready. Ask me anything about your codebase.")
    engine.runAndWait()

    while True:
        pcm = _record()
        if pcm is None:
            continue

        question = _transcribe(pcm)
        if question is None:
            continue

        print(f"You: {question}\n")

        if question.lower().strip() in ("quit", "exit", "stop", "bye", "goodbye"):
            engine.say("Goodbye.")
            engine.runAndWait()
            break

        response = _ask_oracle(question, client, driver, messages)
        _speak(response, engine)

    if driver:
        driver.close()


if __name__ == "__main__":
    run()
