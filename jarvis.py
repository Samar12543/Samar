"""
J.A.R.V.I.S — HOLOGRAPHIC AI INTERFACE v5.1
Complete HUD Revamp with Massive Arc Reactor
Iron Man Aesthetic | Futuristic UI | 5-Ring Arc Reactor
FIXED: Complete responses, faster first message, faster voice chat, Mohali weather
"""

import sys, os, json, requests, urllib.parse, threading, multiprocessing
import queue, subprocess, math, hashlib, random, platform, webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFrame, QSizePolicy,
    QListWidget, QListWidgetItem, QScrollArea, QStackedWidget,
    QGraphicsOpacityEffect, QGridLayout, QProgressBar, QSlider,
    QSpacerItem, QTextEdit, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPointF, QRectF,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSize, QUrl, QRect
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QLinearGradient, QPalette,
    QPen, QRadialGradient, QConicalGradient, QFontDatabase, QPolygonF,
    QPainterPath, QDesktopServices, QPixmap, QIcon
)

# ═══════════════════════════════════════════════════════════
#  CONSTANTS — FIXED: Higher token limits, faster response
# ═══════════════════════════════════════════════════════════
PARTICLE_COUNT       = 50
ANIMATION_FPS        = 60
MODEL_WARMUP_ENABLED = True
OLLAMA_MODEL         = "qwen2.5:3b"
HISTORY_DIR          = os.path.expanduser("~/.jarvis_chats")
VOICE_CACHE          = os.path.expanduser("~/piper_voices/cache/")
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(VOICE_CACHE, exist_ok=True)
PIPER_VOICE_MODEL    = os.path.expanduser(
    "~/piper_voices/en_GB-northern_english_male-medium.onnx")
USER_NAME = "SAMAR"
OS_VERSION = "v2.6.2"

# FIXED: Higher token limits to prevent incomplete responses
MAX_TOKENS_TEXT      = 2048
MAX_TOKENS_VOICE     = 1536
CTX_SIZE_SMALL       = 1536
CTX_SIZE_LARGE       = 4096
OLLAMA_KEEP_ALIVE    = "30m"
OLLAMA_TIMEOUT       = 180

# FIXED: Faster response settings
TEMPERATURE          = 0.6
TOP_P                = 0.85
TOP_K                = 30
REPEAT_PENALTY       = 1.05

# Weather location
WEATHER_LOCATION     = "Mohali,Punjab,India"
WEATHER_REFRESH_MS   = 15 * 60 * 1000

# Enhanced Color Palette
C_CYAN       = QColor(0, 212, 255)
C_CYAN2      = QColor(0, 150, 200)
C_CYAN_DIM   = QColor(0, 100, 150)
C_GOLD       = QColor(255, 180, 0)
C_GREEN      = QColor(0, 255, 136)
C_RED        = QColor(255, 59, 48)
C_BG         = QColor(2, 6, 14)
C_PANEL      = QColor(4, 14, 30)
C_BORDER     = QColor(0, 150, 200, 80)
C_WHITE      = QColor(240, 250, 255)
C_GLOW       = QColor(0, 212, 255, 60)
C_BRIGHT     = QColor(0, 229, 255, 200)

# ═══════════════════════════════════════════════════════════
#  FONT HELPERS
# ═══════════════════════════════════════════════════════════
def _mono(size, bold=False):
    return QFont("Courier New", size, QFont.Weight.Bold if bold else QFont.Weight.Normal)

def _orbitron(size, bold=False):
    f = QFont("Orbitron", size)
    f.setBold(bold)
    return f

def _rajdhani(size, bold=False):
    f = QFont("Rajdhani", size)
    f.setBold(bold)
    return f

def _label(text, size=8, color="rgba(0,212,255,200)", bold=False, spacing="1px"):
    l = QLabel(text)
    l.setFont(_mono(size, bold))
    l.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return l

# ═══════════════════════════════════════════════════════════
#  SYSTEM UTILITIES
# ═══════════════════════════════════════════════════════════
def _open_path(path):
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        elif sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass

def _open_url(url):
    webbrowser.open(url)

def _run_app(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

SHORTCUT_ACTIONS = {
    "Documents": lambda: _open_path(os.path.expanduser("~/Documents")),
    "Downloads": lambda: _open_path(os.path.expanduser("~/Downloads")),
    "Videos":    lambda: _open_path(os.path.expanduser("~/Movies")),
    "Images":    lambda: _open_path(os.path.expanduser("~/Pictures")),
    "Music":     lambda: _open_path(os.path.expanduser("~/Music")),
    "Gmail":     lambda: _open_url("https://mail.google.com"),
    "Programs":  lambda: _open_path("/Applications" if sys.platform == "darwin" else "C:\\Program Files"),
    "Wikipedia": lambda: _open_url("https://wikipedia.org"),
}

TOOL_ACTIONS = {
    "Open Calculator": lambda: _run_app(["open", "-a", "Calculator"] if sys.platform == "darwin"
                                         else ["calc"] if sys.platform == "win32" else ["gnome-calculator"]),
    "Search the Web":  lambda: _open_url("https://google.com"),
    "Open Notepad":    lambda: _run_app(["open", "-a", "TextEdit"] if sys.platform == "darwin"
                                          else ["notepad"] if sys.platform == "win32" else ["gedit"]),
    "Take a Screenshot": lambda: _run_app(["screencapture", "-i"] if sys.platform == "darwin"
                                            else ["snippingtool"] if sys.platform == "win32"
                                            else ["gnome-screenshot", "-a"]),
}

# ═══════════════════════════════════════════════════════════
#  CHAT HISTORY
# ═══════════════════════════════════════════════════════════
def list_saved_chats():
    return sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)

def load_chat(filename):
    with open(os.path.join(HISTORY_DIR, filename)) as f:
        return json.load(f)

def save_chat(messages, filename=None):
    if not messages: return None
    if not filename:
        filename = datetime.now().strftime("chat_%Y%m%d_%H%M%S.json")
    with open(os.path.join(HISTORY_DIR, filename), "w") as f:
        json.dump(messages, f, indent=2)
    return filename

def delete_chat(filename):
    p = os.path.join(HISTORY_DIR, filename)
    if os.path.exists(p): os.remove(p)

# ═══════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════
_PROMPT_CACHE = {"text": "", "ts": 0}

def build_system_prompt():
    import time
    now_ts = time.time()
    if now_ts - _PROMPT_CACHE["ts"] < 60 and _PROMPT_CACHE["text"]:
        return _PROMPT_CACHE["text"]
    now = datetime.now()
    prompt = (
        f"You are Jarvis, a highly intelligent AI assistant. "
        f"Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}. "
        f"Always use this when asked about the date or time. "
        f"Be concise, confident, and slightly witty. Keep answers brief unless detail is needed. "
        f"IMPORTANT: Always finish your sentences completely — never stop mid-sentence. "
        f"ONLY if someone directly asks who made you, say Samarbir Singh — "
        f"a real software developer who built you using Python, Ollama, and LLaMA. "
        f"You are NOT from the Marvel universe — only mention if directly asked. "
        f"You have access to real-time news for current events. "
        f"Do NOT say you lack real-time information. "
        f"Never mention your creator, origin, or Marvel unprompted."
    )
    _PROMPT_CACHE["text"] = prompt
    _PROMPT_CACHE["ts"] = now_ts
    return prompt

# ═══════════════════════════════════════════════════════════
#  REAL-TIME NEWS
# ═══════════════════════════════════════════════════════════
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
_HTTP_LOCAL = threading.local()

def _http():
    session = getattr(_HTTP_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update(_HEADERS)
        _HTTP_LOCAL.session = session
    return session
import xml.etree.ElementTree as ET
import re as _re

def _ollama_options(num_predict, num_ctx, for_voice=False):
    return {
        "num_ctx": num_ctx,
        "num_predict": num_predict,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "repeat_penalty": REPEAT_PENALTY,
        "num_thread": 0,
        "num_gpu": 99,
        "num_batch": 384 if for_voice else 512,
        "num_keep": 0,
    }

def _stream_ollama(prompt, max_tokens, ctx_size, on_token=None, for_voice=False):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": _ollama_options(max_tokens, ctx_size, for_voice),
    }
    resp = _http().post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
        stream=True,
    )
    resp.raise_for_status()

    full = ""
    done_reason = ""
    eval_count = 0
    for line in resp.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        text = chunk.get("response", "")
        if text:
            full += text
            if on_token:
                on_token(text)
        if chunk.get("done"):
            done_reason = chunk.get("done_reason", "")
            eval_count = int(chunk.get("eval_count") or 0)
            break
    return full, done_reason, eval_count

def _looks_cut_off(text, done_reason, eval_count, max_tokens):
    # Primary signals from Ollama — most reliable
    if done_reason in {"length", "num_predict"}:
        return True
    if eval_count and eval_count >= max_tokens - 8:
        return True
    # Fallback: response ends mid-word (last token is an incomplete word fragment).
    # We only trigger this when the response is long enough that a cut-off is plausible
    # AND the last character is a plain letter/digit — not any punctuation at all.
    # This avoids false positives on responses ending with !, ?, —, ), ", etc.
    stripped = text.strip()
    if len(stripped) > 120:
        last_char = stripped[-1]
        if last_char.isalpha():
            # Ends with a bare word — very likely cut off mid-sentence
            return True
    return False

def _parse_rss(content, max_results=10):
    try:
        root = ET.fromstring(content)
        for elem in root.iter():
            if "}" in elem.tag: elem.tag = elem.tag.split("}", 1)[1]
        items = root.findall(".//item") or root.findall(".//entry")
        out = []
        for item in items[:max_results]:
            title = (item.findtext("title") or "").strip()
            title = title.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">")
            pubdate = (item.findtext("pubDate") or item.findtext("updated") or "").strip()
            desc = _re.sub(r"<[^>]+>", "", (item.findtext("description") or "").strip())[:150]
            if title: out.append((title, pubdate[:22], desc))
        return out
    except Exception: return []

def fetch_google_news_rss(query, max_results=10):
    encoded = urllib.parse.quote(query)
    try:
        r = _http().get(
            f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en",
            headers=_HEADERS, timeout=7)
        if r.status_code == 200:
            items = _parse_rss(r.content, max_results)
            if items:
                lines = [f"REAL-TIME NEWS — '{query}':"]
                for n,(t,d,desc) in enumerate(items,1):
                    lines.append(f"{n}. {t}" + (f"  [{d}]" if d else ""))
                return "\n".join(lines)
    except Exception: pass
    return ""

def fetch_context(query):
    results = {}
    def _g(): results["g"] = fetch_google_news_rss(query)
    t = threading.Thread(target=_g, daemon=True); t.start(); t.join(timeout=6)
    return results.get("g","")

def fetch_context_quick(query, wait=0.25):
    results = {}
    def _g(): results["g"] = fetch_google_news_rss(query)
    t = threading.Thread(target=_g, daemon=True)
    t.start()
    t.join(timeout=wait)
    return results.get("g", "")

def build_continuation_prompt(original_prompt, partial):
    tail = partial.strip()[-900:]
    return (
        f"{build_system_prompt()}\n\n"
        "Your previous response was cut off mid-word or mid-sentence by the token limit. "
        "Complete ONLY the unfinished sentence. Do not add new sentences, do not summarize, "
        "do not say anything beyond finishing the sentence that was cut off.\n\n"
        f"User request:\n{original_prompt}\n\n"
        f"Partial response (complete only the last unfinished sentence):\n{tail}"
    )

def needs_realtime(text):
    triggers = [
        "news", "latest", "today", "current", "recent", "happening", "update", "broke",
        "who won", "result", "score", "election", "weather", "price", "stock",
        "headline", "what's going on", "what is going on", "tell me about",
        "what happened", "any updates", "new developments", "recently",
    ]
    return any(t in text.lower() for t in triggers)

# ═══════════════════════════════════════════════════════════
#  VOICE / TTS
# ═══════════════════════════════════════════════════════════
def _cache_key(text):
    return os.path.join(VOICE_CACHE, hashlib.md5(text.encode()).hexdigest() + ".wav")

_PIPER_VOICE = None
_PIPER_LOCK = threading.Lock()

def speak_with_piper(text):
    global _PIPER_VOICE
    cache_file = _cache_key(text)
    if os.path.exists(cache_file): return cache_file
    try:
        import io, piper, wave
        if not os.path.exists(PIPER_VOICE_MODEL): return None
        with _PIPER_LOCK:
            if _PIPER_VOICE is None:
                _PIPER_VOICE = piper.PiperVoice.load(PIPER_VOICE_MODEL)
            voice = _PIPER_VOICE
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf: voice.synthesize_wav(text, wf)
        buf.seek(0)
        with open(cache_file, "wb") as f: f.write(buf.getvalue())
        return cache_file
    except Exception: return None

def preload_piper_voice():
    global _PIPER_VOICE
    if not os.path.exists(PIPER_VOICE_MODEL):
        return
    try:
        import piper
        with _PIPER_LOCK:
            if _PIPER_VOICE is None:
                _PIPER_VOICE = piper.PiperVoice.load(PIPER_VOICE_MODEL)
        speak_with_piper("Ready.")
    except Exception:
        pass

def _speak_system_to_file(text):
    try:
        if sys.platform == "darwin":
            # Use say directly — most reliable on macOS, no temp file needed
            subprocess.run(["say", "-v", "Daniel", "-r", "150", text], check=False, timeout=30)
            return "__spoken__"
        elif sys.platform == "linux":
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); tmp.close()
            subprocess.run(["espeak","-v","en-US","-s","150","-w",tmp.name,text], check=False, timeout=15)
            return tmp.name
    except Exception: pass
    return None

def _play_audio(filepath):
    if not filepath: return
    if filepath == "__spoken__": return
    if not os.path.exists(filepath): return
    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", filepath], check=False, timeout=60)
        elif sys.platform == "linux":
            subprocess.run(["ffplay","-nodisp","-autoexit","-loglevel","quiet",filepath], check=False, timeout=60)
        elif sys.platform == "win32":
            subprocess.run(["powershell","-c",f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"], check=False)
    except Exception: pass

# ═══════════════════════════════════════════════════════════
#  WORKERS
# ═══════════════════════════════════════════════════════════
class ModelWarmupWorker(QThread):
    warmup_complete = pyqtSignal()
    def run(self):
        if not MODEL_WARMUP_ENABLED:
            self.warmup_complete.emit(); return
        try:
            # Use the SAME num_ctx as real text requests so Ollama keeps the
            # model loaded at that context size — avoids a reload on first message.
            resp = _http().post("http://localhost:11434/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": "Hi", "stream": True,
                      "keep_alive": OLLAMA_KEEP_ALIVE,
                      "options": {
                          "num_predict": 5,
                          "num_ctx": CTX_SIZE_SMALL,   # must match first real request
                          "temperature": 0.1,
                          "num_thread": min(8, max(2, (os.cpu_count() or 4))),
                          "num_batch": 512,
                          "num_gpu": 99,
                      }},
                timeout=60, stream=True)
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("done"):
                        break
        except Exception:
            pass
        self.warmup_complete.emit()

class JarvisWorker(QThread):
    token_received = pyqtSignal(str)
    finished       = pyqtSignal(str)
    error          = pyqtSignal(str)
    def __init__(self, prompt, history, use_news=False, is_first=False, model_ready=False):
        super().__init__()
        self.prompt = prompt
        self.history = history
        self.use_news = use_news
        self.is_first = is_first
        self.model_ready = model_ready

    def run(self):
        # Fetch real-time news BEFORE starting the LLM — give it enough time to actually return.
        # News queries need real data; a 0.25s timeout means it almost always comes back empty.
        ctx = ""
        if self.use_news:
            ctx = fetch_context_quick(self.prompt, wait=4.0)  # wait up to 4s for RSS

        aug = self.prompt
        if ctx:
            aug = (f"REAL-TIME DATA (use this, do not use training data for current events):\n{ctx}"
                   f"\n\nUser question: {self.prompt}\n\nAnswer using the real-time data above.")

        # Trim history: none for first message (fastest), limited for subsequent
        if self.is_first:
            trimmed = []
        else:
            trimmed = self.history[:-1][-10:]

        history_text = "\n".join(trimmed)
        full_prompt = f"{build_system_prompt()}\n\n{history_text}\nUser: {aug}\nJarvis:"

        # Always use CTX_SIZE_SMALL for first message — must match warmup ctx
        # so Ollama doesn't reload the model.  Subsequent messages scale up.
        if self.is_first:
            ctx_size = CTX_SIZE_SMALL
        else:
            ctx_size = CTX_SIZE_SMALL if len(full_prompt) < 2000 else CTX_SIZE_LARGE
        num_predict = MAX_TOKENS_TEXT

        try:
            full, done_reason, eval_count = _stream_ollama(
                full_prompt,
                num_predict,
                ctx_size,
                self.token_received.emit,
            )

            # Only continue if genuinely cut off mid-sentence
            if _looks_cut_off(full, done_reason, eval_count, num_predict):
                cont_prompt = build_continuation_prompt(self.prompt, full)
                extra, _, _ = _stream_ollama(
                    cont_prompt,
                    768,
                    CTX_SIZE_SMALL,
                    self.token_received.emit,
                )
                full += extra

            final = full.strip()
            if final:
                self.finished.emit(final)
            else:
                self.error.emit("Empty response from model")

        except Exception as e:
            self.error.emit(str(e))

class VoiceWorker(QThread):
    text_received = pyqtSignal(str)
    error         = pyqtSignal(str)
    level_update  = pyqtSignal(int)

    RATE = 16000

    def __init__(self):
        super().__init__()
        self._stop = threading.Event()
        self._frames = []

    def stop_recording(self):
        self._stop.set()

    def _recognize(self, audio_bytes):
        import speech_recognition as sr
        rec = sr.Recognizer()
        rec.dynamic_energy_threshold = True
        aud = sr.AudioData(audio_bytes, self.RATE, 2)
        for lang in ("en-IN", "en-US", "en-GB"):
            try:
                return rec.recognize_google(aud, language=lang)
            except sr.UnknownValueError:
                continue
        raise sr.UnknownValueError()

    def run(self):
        import speech_recognition as sr
        import sounddevice as sd
        import numpy as np
        import wave
        import tempfile
        import time

        self._frames = []
        self._stop.clear()
        heard_speech = False
        last_loud = None
        start = time.time()
        silence_thresh = 120
        silence_secs = 0.55
        max_secs = 7
        min_secs = 0.25

        def cb(indata, frames, time_info, status):
            if self._stop.is_set():
                return
            chunk = indata.copy()
            self._frames.append(chunk)
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
            self.level_update.emit(min(100, int(rms / 40)))
            nonlocal heard_speech, last_loud, silence_thresh
            if rms > silence_thresh:
                heard_speech = True
                last_loud = time.time()
            elif len(self._frames) == 8:
                silence_thresh = max(80, int(rms * 2.5))

        try:
            device_info = sd.query_devices(kind="input")
            device = device_info["index"] if device_info else None
        except Exception:
            device = None

        try:
            with sd.InputStream(
                samplerate=self.RATE,
                channels=1,
                dtype="int16",
                callback=cb,
                device=device,
                blocksize=1024,
            ):
                while not self._stop.is_set():
                    elapsed = time.time() - start
                    if elapsed > max_secs:
                        break
                    if (
                        heard_speech
                        and last_loud
                        and elapsed > min_secs
                        and time.time() - last_loud > silence_secs
                    ):
                        break
                    time.sleep(0.05)
        except Exception as e:
            msg = str(e).lower()
            if "permission" in msg or "denied" in msg or "not authorized" in msg:
                self.error.emit(
                    "Microphone access denied. Enable it in "
                    "System Settings → Privacy & Security → Microphone."
                )
            else:
                self.error.emit(f"Microphone error: {e}")
            return

        if not self._frames:
            self.error.emit("No audio recorded. Check your microphone and try again.")
            return

        audio = np.concatenate(self._frames, axis=0)
        if len(audio) < self.RATE * 0.35:
            self.error.emit("Speech too short. Speak clearly, then pause.")
            return

        wav_path = None
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav_path = tmp.name
            tmp.close()
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.RATE)
                wf.writeframes(audio.tobytes())

            try:
                text = self._recognize(audio.tobytes())
            except sr.UnknownValueError:
                with sr.AudioFile(wav_path) as src:
                    rec = sr.Recognizer()
                    aud = rec.record(src)
                text = None
                for lang in ("en-IN", "en-US", "en-GB"):
                    try:
                        text = rec.recognize_google(aud, language=lang)
                        break
                    except sr.UnknownValueError:
                        continue
                if not text:
                    raise sr.UnknownValueError()

            text = text.strip()
            if not text:
                self.error.emit("Could not understand speech. Try again.")
                return
            self.text_received.emit(text)
        except ImportError as e:
            self.error.emit(f"Missing library: {e}. Run: pip install sounddevice SpeechRecognition numpy")
        except sr.UnknownValueError:
            self.error.emit("Could not understand speech. Speak louder and try again.")
        except sr.RequestError as e:
            self.error.emit(f"Speech recognition unavailable (need internet): {e}")
        except Exception as e:
            self.error.emit(f"Voice error: {e}")
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass

class TTSWorker(QThread):
    finished_speaking = pyqtSignal()
    def __init__(self, sentence_queue, stop_event, mute_event):
        super().__init__()
        self.sq = sentence_queue
        self.stop = stop_event
        self.mute = mute_event

    def run(self):
        # True pipeline: synthesis of sentence N+1 runs in background while N plays.
        # synth thread  → _aq (audio file paths) → playback loop (this thread)
        self._aq = queue.Queue(maxsize=4)   # bound so we don't over-synthesize

        def synth():
            while not self.stop.is_set():
                try:
                    s = self.sq.get(timeout=0.2)
                    if s is None:
                        self._aq.put(None)
                        break
                    if self.mute.is_set():
                        # skip synthesis but signal end-of-item so playback doesn't stall
                        self._aq.put(None)
                        continue
                    path = speak_with_piper(s) or _speak_system_to_file(s)
                    self._aq.put(path)   # blocks if queue full (back-pressure)
                except queue.Empty:
                    continue

        st = threading.Thread(target=synth, daemon=True)
        st.start()

        while not self.stop.is_set():
            try:
                p = self._aq.get(timeout=0.5)
                if p is None:
                    # Could be a muted item sentinel — check if more coming
                    # by peeking; if synth thread is still alive, keep going
                    if not st.is_alive() and self._aq.empty():
                        break
                    continue
                if not self.mute.is_set():
                    _play_audio(p)   # blocks until this clip finishes; synth runs in parallel
            except queue.Empty:
                if not st.is_alive():
                    break
                continue

        st.join(timeout=5)
        self.finished_speaking.emit()

class VoiceLLMWorker(QThread):
    sentence_ready = pyqtSignal(str)
    finished       = pyqtSignal(str)
    error          = pyqtSignal(str)
    def __init__(self, prompt, history, use_news=False):
        super().__init__()
        self.prompt = prompt
        self.history = history
        self.use_news = use_news

    def run(self):
        import re
        ctx = ""
        # Fire news fetch in background — only use if it finishes before LLM starts (very short wait)
        if self.use_news:
            ctx = fetch_context_quick(self.prompt, wait=0.10)
        aug = (f"REAL-TIME DATA:\n{ctx}\n\nQuestion: {self.prompt}" if ctx else self.prompt)

        # Very short history for voice = minimal latency
        trimmed_h = self.history[:-1][-6:]
        history_text = "\n".join(trimmed_h)
        full_prompt = f"{build_system_prompt()}\n\n{history_text}\nUser: {aug}\nJarvis:"

        # Use small context always for voice — speed > memory
        ctx_size = CTX_SIZE_SMALL

        try:
            full = ""
            buf = ""

            # Sentence boundary pattern — only split on strong boundaries
            SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

            def on_token(text):
                nonlocal full, buf
                full += text
                buf += text

                # Split on complete sentences only (ends with . ! ? followed by space + capital)
                parts = SENT_SPLIT.split(buf)
                for s in parts[:-1]:
                    s = s.strip()
                    if s:
                        self.sentence_ready.emit(s)
                buf = parts[-1]

                # Safety flush: if buffer is very long and has a natural clause break
                if len(buf) >= 120:
                    soft = max(buf.rfind(", "), buf.rfind("; "), buf.rfind(": "))
                    if soft >= 60:
                        s = buf[:soft + 1].strip()
                        if s:
                            self.sentence_ready.emit(s)
                        buf = buf[soft + 2:].lstrip()

            _, done_reason, eval_count = _stream_ollama(
                full_prompt,
                MAX_TOKENS_VOICE,
                ctx_size,
                on_token,
                for_voice=True,
            )

            if _looks_cut_off(full, done_reason, eval_count, MAX_TOKENS_VOICE):
                cont_prompt = build_continuation_prompt(self.prompt, full)
                _, _, _ = _stream_ollama(
                    cont_prompt,
                    512,
                    ctx_size,
                    on_token,
                    for_voice=True,
                )

            # Flush anything remaining in the buffer
            if buf.strip():
                self.sentence_ready.emit(buf.strip())
            self.finished.emit(full.strip())

        except Exception as e:
            self.error.emit(str(e))

# ═══════════════════════════════════════════════════════════
#  MASSIVE ARC REACTOR — IRON MAN STYLE v5.0
# ═══════════════════════════════════════════════════════════
class ArcReactor(QWidget):
    def __init__(self, size=400, parent=None):
        super().__init__(parent)
        self.setMinimumSize(size, size)
        self.setFixedSize(size, size)
        self._size = size
        self._angle1 = 0.0
        self._angle2 = 0.0
        self._angle3 = 0.0
        self._angle4 = 0.0
        self._angle5 = 0.0
        self._pulse = 0.0
        self._scan = 0.0
        self._wave = 0.0
        self._breath = 0.0
        self._state = "idle"
        self._energy = 0.3
        self._tilt_x = 0.0
        self._tilt_y = 0.0
        self._hover = False
        self._particles = []
        self._init_particles()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(1000 // ANIMATION_FPS)
        self.setMouseTracking(True)

    def _init_particles(self):
        self._particles = []
        for _ in range(30):
            self._particles.append({
                "angle": random.uniform(0, 360),
                "radius": random.uniform(0.1, 0.9),
                "speed": random.uniform(0.2, 1.5),
                "size": random.uniform(1, 3),
                "alpha": random.uniform(0.3, 1.0),
                "decay": random.uniform(0.001, 0.005),
            })

    def set_state(self, state):
        self._state = state

    def _step(self):
        speeds = {
            "idle":       (0.2, -0.15, 0.4, -0.3, 0.6, 1.0, 0.3),
            "listening":  (0.8, -0.6, 1.2, -0.8, 1.5, 2.5, 0.8),
            "processing": (1.5, -1.2, 2.0, -1.5, 2.5, 3.5, 1.0),
            "speaking":   (1.0, -0.8, 1.5, -1.0, 1.8, 2.5, 0.6),
        }
        s1, s2, s3, s4, s5, sp, se = speeds.get(self._state, speeds["idle"])
        self._angle1 = (self._angle1 + s1) % 360
        self._angle2 = (self._angle2 + s2) % 360
        self._angle3 = (self._angle3 + s3) % 360
        self._angle4 = (self._angle4 + s4) % 360
        self._angle5 = (self._angle5 + s5) % 360
        self._pulse = (self._pulse + sp) % 360
        self._scan = (self._scan + 0.8) % 360
        self._wave = (self._wave + 0.5) % 360
        self._breath = (self._breath + 0.03) % (2 * math.pi)
        if self._state in ("listening", "processing", "speaking"):
            self._energy = min(1.0, self._energy + 0.02)
        else:
            self._energy = max(0.3, self._energy - 0.01)
        self._tilt_x *= 0.95
        self._tilt_y *= 0.95
        for p in self._particles:
            p["angle"] = (p["angle"] + p["speed"]) % 360
            p["alpha"] = max(0, p["alpha"] - p["decay"])
            if p["alpha"] <= 0:
                p["angle"] = random.uniform(0, 360)
                p["radius"] = random.uniform(0.1, 0.9)
                p["alpha"] = random.uniform(0.5, 1.0)
        self.update()

    def mouseMoveEvent(self, event):
        cx, cy = self.width() / 2, self.height() / 2
        dx = (event.position().x() - cx) / cx
        dy = (event.position().y() - cy) / cy
        self._tilt_x = dy * 15
        self._tilt_y = -dx * 15
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2
            R = min(cx, cy) - 10
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.translate(cx, cy)
            p.rotate(self._tilt_x * 0.3)
            p.scale(1 + abs(self._tilt_y) * 0.002, 1 + abs(self._tilt_x) * 0.002)
            p.translate(-cx, -cy)
            state_col = (C_GREEN if self._state == "listening" else
                         QColor(0, 160, 255) if self._state == "responding" else C_CYAN)
            outer_glow = QRadialGradient(cx, cy, R * 1.4)
            outer_glow.setColorAt(0, QColor(0, 212, 255, int(30 * self._energy)))
            outer_glow.setColorAt(0.5, QColor(0, 150, 200, int(15 * self._energy)))
            outer_glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(outer_glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), R * 1.4, R * 1.4)
            bg = QRadialGradient(cx, cy, R)
            bg.setColorAt(0, QColor(0, 15, 35, 240))
            bg.setColorAt(0.6, QColor(0, 8, 22, 220))
            bg.setColorAt(0.85, QColor(0, 5, 15, 200))
            bg.setColorAt(1, QColor(0, 2, 8, 180))
            p.setBrush(QBrush(bg))
            p.drawEllipse(QPointF(cx, cy), R, R)
            p.setPen(QPen(QColor(15, 30, 45, 240), R * 0.10))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), R * 0.95, R * 0.95)
            self._draw_ring_segments(p, cx, cy, R * 0.92, self._angle1, 32, QColor(0, 180, 220, 140), R * 0.08, 3.5, True)
            self._draw_ring_dots(p, cx, cy, R * 0.80, self._angle2, 24, QColor(0, 200, 255, 180))
            self._draw_ring_bars(p, cx, cy, R * 0.68, self._angle3, 16, QColor(0, 220, 255, 160))
            self._draw_ring_arcs(p, cx, cy, R * 0.55, self._angle4, 12, QColor(0, 229, 255, 200))
            self._draw_ring_segments(p, cx, cy, R * 0.42, self._angle5, 8, QColor(0, 240, 255, 220), R * 0.04, 2.0, False)
            self._draw_chevrons(p, cx, cy, R * 0.75, self._angle1, 20)
            self._draw_ticks(p, cx, cy, R * 0.88, 48, self._angle1)
            self._draw_ticks(p, cx, cy, R * 0.72, 32, self._angle2)
            self._draw_scan_sweep(p, cx, cy, R * 0.9)
            self._draw_energy_wave(p, cx, cy, R)
            self._draw_particles(p, cx, cy, R)
            self._draw_core(p, cx, cy, R * 0.30)
            pulse_s = 0.72 + 0.28 * math.sin(math.radians(self._pulse))
            core_r = max(4, R * 0.035 * pulse_s)
            p.setBrush(QBrush(QColor(255, 255, 255, 255)))
            p.setPen(QPen(state_col, 2))
            p.drawEllipse(QPointF(cx, cy), core_r, core_r)
            if self._hover:
                hover_glow = QRadialGradient(cx, cy, R * 0.5)
                hover_glow.setColorAt(0, QColor(0, 212, 255, 20))
                hover_glow.setColorAt(1, QColor(0, 0, 0, 0))
                p.setBrush(QBrush(hover_glow))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(cx, cy), R * 0.5, R * 0.5)
        except Exception as _paint_err:
            pass

    def _draw_ring_segments(self, p, cx, cy, radius, angle, segments, color, width, has_gaps, _unused=None):
        seg_angle = 360 / segments
        gap = seg_angle * 0.25 if has_gaps else 1.5
        for i in range(segments):
            a_start = i * seg_angle + angle
            a_span = seg_angle - gap
            phase = ((i * seg_angle + angle) % 360) / 360
            alpha = int(color.alpha() * (0.4 + 0.6 * abs(math.sin(math.pi * phase + self._breath))))
            col = QColor(color.red(), color.green(), color.blue(), alpha)
            pen = QPen(col, width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2), int(a_start * 16), int(a_span * 16))

    def _draw_ring_dots(self, p, cx, cy, radius, angle, count, color):
        for i in range(count):
            a = math.radians(i * (360 / count) + angle)
            phase = ((i * (360 / count) + angle) % 360) / 360
            alpha = int(color.alpha() * (0.5 + 0.5 * math.sin(math.pi * phase * 2)))
            dot_r = 2 + 2 * math.sin(math.pi * phase + self._breath * 2)
            col = QColor(color.red(), color.green(), color.blue(), alpha)
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            x = cx + math.cos(a) * radius
            y = cy + math.sin(a) * radius
            p.drawEllipse(QPointF(x, y), dot_r, dot_r)

    def _draw_ring_bars(self, p, cx, cy, radius, angle, count, color):
        for i in range(count):
            a = math.radians(i * (360 / count) + angle)
            bar_len = 8 + 6 * math.sin(math.radians(self._pulse + i * 20))
            x1 = cx + math.cos(a) * (radius - bar_len/2)
            y1 = cy + math.sin(a) * (radius - bar_len/2)
            x2 = cx + math.cos(a) * (radius + bar_len/2)
            y2 = cy + math.sin(a) * (radius + bar_len/2)
            phase = ((i * (360 / count) + angle) % 360) / 360
            alpha = int(color.alpha() * (0.4 + 0.6 * abs(math.sin(math.pi * phase))))
            pen = QPen(QColor(color.red(), color.green(), color.blue(), alpha), 2.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_ring_arcs(self, p, cx, cy, radius, angle, count, color):
        for i in range(count):
            a_start = i * (360 / count) + angle
            a_span = 12
            phase = ((i * (360 / count) + angle) % 360) / 360
            alpha = int(color.alpha() * (0.6 + 0.4 * math.sin(math.pi * phase * 2 + self._breath)))
            pen = QPen(QColor(color.red(), color.green(), color.blue(), alpha), 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2), int(a_start * 16), int(a_span * 16))

    def _draw_chevrons(self, p, cx, cy, radius, angle, count):
        for i in range(count):
            a_start = i * (360 / count) + angle
            a_span = 8
            bright = (i % 3 == 0)
            alpha = 220 if bright else 70
            pen = QPen(QColor(200, 235, 255, alpha), 1.5 if bright else 0.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2), int(a_start * 16), int(a_span * 16))

    def _draw_ticks(self, p, cx, cy, radius, count, angle):
        for i in range(count):
            a = math.radians(i * (360 / count) + angle * 0.15)
            ca, sa = math.cos(a), math.sin(a)
            is_major = (i % 4 == 0)
            r0 = radius - (self._size * 0.065 if is_major else self._size * 0.032)
            r1 = radius
            pen = QPen(QColor(0, 200, 255, 160 if is_major else 50), 1.3 if is_major else 0.6)
            p.setPen(pen)
            p.drawLine(QPointF(cx + ca * r0, cy + sa * r0), QPointF(cx + ca * r1, cy + sa * r1))

    def _draw_scan_sweep(self, p, cx, cy, radius):
        a = math.radians(self._scan)
        pen = QPen(QColor(0, 229, 255, 80), 2)
        p.setPen(pen)
        x2 = cx + math.cos(a) * radius
        y2 = cy + math.sin(a) * radius
        p.drawLine(QPointF(cx, cy), QPointF(x2, y2))
        p.setBrush(QBrush(QColor(0, 229, 255, 60)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x2, y2), 8, 8)
        for trail in range(3):
            ta = a - math.radians((trail + 1) * 5)
            talpha = 40 - trail * 12
            tpen = QPen(QColor(0, 229, 255, talpha), 1)
            p.setPen(tpen)
            tx2 = cx + math.cos(ta) * radius * 0.9
            ty2 = cy + math.sin(ta) * radius * 0.9
            p.drawLine(QPointF(cx, cy), QPointF(tx2, ty2))

    def _draw_energy_wave(self, p, cx, cy, max_r):
        wave_r = (math.sin(math.radians(self._wave)) * 0.5 + 0.5) * max_r * 0.85
        alpha = int(100 * (1 - wave_r / (max_r * 0.85)) * self._energy)
        if alpha > 5:
            p.setPen(QPen(QColor(0, 229, 255, alpha), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), wave_r, wave_r)

    def _draw_particles(self, p, cx, cy, max_r):
        for pt in self._particles:
            a = math.radians(pt["angle"])
            r = pt["radius"] * max_r
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r
            alpha = int(200 * pt["alpha"] * self._energy)
            size = pt["size"] * (0.5 + 0.5 * self._energy)
            p.setBrush(QBrush(QColor(0, 212, 255, alpha)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), size, size)

    def _draw_core(self, p, cx, cy, radius):
        pulse_s = 0.6 + 0.4 * math.sin(math.radians(self._pulse))
        intensity = self._energy
        for i, (r_mult, alpha_mult) in enumerate([(2.0, 0.08), (1.5, 0.15), (1.2, 0.3), (1.0, 0.5), (0.7, 0.8)]):
            cg = QRadialGradient(cx, cy, radius * r_mult)
            cg.setColorAt(0, QColor(220, 245, 255, int(255 * alpha_mult * intensity)))
            cg.setColorAt(0.2, QColor(0, 229, 255, int(200 * alpha_mult * intensity)))
            cg.setColorAt(0.5, QColor(0, 180, 255, int(100 * alpha_mult * intensity)))
            cg.setColorAt(0.8, QColor(0, 100, 200, int(40 * alpha_mult * intensity)))
            cg.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(cg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), radius * r_mult * pulse_s, radius * r_mult * pulse_s)
        inner_r = radius * 0.4 * pulse_s
        inner_g = QRadialGradient(cx, cy, inner_r)
        inner_g.setColorAt(0, QColor(255, 255, 255, int(250 * intensity)))
        inner_g.setColorAt(0.5, QColor(0, 229, 255, int(200 * intensity)))
        inner_g.setColorAt(1, QColor(0, 150, 255, 0))
        p.setBrush(QBrush(inner_g))
        p.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

    def mousePressEvent(self, event):
        for p in self._particles:
            p["alpha"] = 1.0
            p["angle"] = random.uniform(0, 360)
            p["radius"] = random.uniform(0.1, 0.5)
        self.update()

# ═══════════════════════════════════════════════════════════
#  HUD PANEL STYLES & WIDGETS
# ═══════════════════════════════════════════════════════════
PANEL_STYLE = """
QFrame {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(4,14,32,220), stop:1 rgba(2,8,22,200));
    border: 1px solid rgba(0,150,200,70);
    border-top: 1px solid rgba(0,212,255,100);
    border-radius: 6px;
}
"""

def section_header(text, icon="◈"):
    f = QFrame()
    f.setStyleSheet("QFrame{background:transparent;border:none;border-bottom:1px solid rgba(0,150,200,60);padding-bottom:2px;}")
    lay = QHBoxLayout(f); lay.setContentsMargins(0,0,0,4); lay.setSpacing(6)
    dot = QLabel(icon); dot.setFont(_mono(8, True))
    dot.setStyleSheet("color:rgba(0,212,255,180);background:transparent;border:none;")
    lbl = QLabel(text); lbl.setFont(_mono(8, True))
    lbl.setStyleSheet("color:rgba(0,212,255,200);background:transparent;border:none;")
    lay.addWidget(dot); lay.addWidget(lbl); lay.addStretch()
    return f

def stat_row(label_text, value_text, val_color="#00D4FF"):
    w = QWidget(); w.setStyleSheet("background:transparent;")
    lay = QHBoxLayout(w); lay.setContentsMargins(0,1,0,1); lay.setSpacing(0)
    lbl = QLabel(label_text); lbl.setFont(_mono(8))
    lbl.setStyleSheet("color:rgba(0,170,200,160);background:transparent;border:none;")
    bar = QFrame(); bar.setFixedHeight(2)
    bar.setStyleSheet("background:rgba(0,180,220,40);border:none;")
    if isinstance(value_text, QLabel):
        val = value_text
    else:
        val = QLabel(str(value_text)); val.setFont(_mono(8, True))
        val.setStyleSheet(f"color:{val_color};background:transparent;border:none;")
    lay.addWidget(lbl); lay.addWidget(bar, 1); lay.addWidget(val)
    return w

class CircularGauge(QWidget):
    def __init__(self, value=75, label="", size=80, parent=None):
        super().__init__(parent)
        self._value = value
        self._label = label
        self._size = size
        self._angle = 0.0
        self.setFixedSize(size, size)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(50)

    def set_value(self, v):
        self._value = max(0, min(100, v))
        self.update()

    def _step(self):
        self._angle = (self._angle + 2.5) % 360
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2
            R = min(cx, cy) - 4
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(0, 40, 70, 100), 6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), R, R)
            pen = QPen(C_CYAN, 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(int(cx - R), int(cy - R), int(R * 2), int(R * 2), int(90 * 16), int(-self._value / 100 * 360 * 16))
            glow_pen = QPen(QColor(0, 212, 255, 60), 8)
            p.setPen(glow_pen)
            p.drawArc(int(cx - R), int(cy - R), int(R * 2), int(R * 2), int(90 * 16), int(-self._value / 100 * 360 * 16))
            p.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
            p.setPen(QPen(C_CYAN))
            txt = f"{int(self._value)}%"
            tw = p.fontMetrics().horizontalAdvance(txt)
            p.drawText(int(cx - tw / 2), int(cy + 5), txt)
            if self._label:
                p.setFont(_mono(6))
                p.setPen(QPen(QColor(0, 150, 200, 130)))
                lines = self._label.split('\n')
                for i, line in enumerate(lines):
                    lw = p.fontMetrics().horizontalAdvance(line)
                    p.drawText(int(cx - lw / 2), int(cy + 20 + i * 12), line)
        except Exception as _paint_err:
            pass

class VerticalBarMeter(QWidget):
    def __init__(self, value=75, parent=None):
        super().__init__(parent)
        self._value = max(0, min(100, value))
        self.setFixedWidth(18)

    def set_value(self, v):
        self._value = max(0, min(100, v))
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            segs = 20
            seg_h = (h - 2) // segs - 1
            filled = int(segs * self._value / 100)
            for i in range(segs):
                is_filled = (segs - 1 - i) < filled
                ratio = (segs - 1 - i) / segs
                if is_filled:
                    col = QColor(0, int(150 + 80 * ratio), int(200 + 55 * ratio), 180)
                else:
                    col = QColor(0, int(40 + 30 * ratio), int(60 + 40 * ratio), 50)
                p.setBrush(QBrush(col))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, 1 + i * (seg_h + 1), w - 2, seg_h)
        except Exception as _paint_err:
            pass

class WaveformDisplay(QWidget):
    def __init__(self, parent=None, height=60):
        super().__init__(parent)
        self._t = 0.0
        self._active = False
        self.setMinimumHeight(height)
        self.setFixedHeight(height)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(50)

    def set_active(self, v):
        self._active = v

    def _step(self):
        self._t = (self._t + (0.15 if self._active else 0.04)) % (math.pi * 200)
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor(0, 8, 20, 160))
            p.setPen(QPen(QColor(0, 100, 150, 30), 0.5))
            p.drawLine(0, h // 2, w, h // 2)
            p.setPen(QPen(QColor(0, 212, 255, 160 if self._active else 80), 1.5))
            n = 100
            pts = []
            for i in range(n):
                fx = i / (n - 1)
                if self._active:
                    amp = (0.5 + 0.3 * math.sin(fx * 12 + self._t * 3)) * (0.7 + 0.3 * math.sin(fx * 8 - self._t * 2))
                    fy = 0.5 + amp * 0.4 * math.sin(fx * 20 + self._t * 4)
                else:
                    fy = 0.5 + 0.1 * math.sin(fx * 6 + self._t)
                pts.append(QPointF(fx * w, fy * h))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
            p.setPen(QPen(QColor(0, 212, 255, 40), 3))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
        except Exception as _paint_err:
            pass

class Equalizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars = [random.uniform(0.1, 0.9) for _ in range(24)]
        self._targets = [random.uniform(0.1, 0.9) for _ in range(24)]
        self._active = False
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(80)

    def set_active(self, v):
        self._active = v

    def _step(self):
        for i in range(24):
            if self._active:
                if random.random() < 0.3:
                    self._targets[i] = random.uniform(0.2, 1.0)
            else:
                self._targets[i] = random.uniform(0.05, 0.25)
            diff = self._targets[i] - self._bars[i]
            self._bars[i] += diff * 0.25
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor(0, 8, 20, 160))
            p.setPen(QPen(QColor(0, 150, 200, 60), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(0, 0, w - 1, h - 1)
            n = len(self._bars)
            bar_w = (w - 40) / n
            freqs = ["20", "40", "80", "160", "320", "640", "1.2K", "2.5K", "5K", "10K", "20K"]
            for i, val in enumerate(self._bars):
                bh = int(val * (h - 24))
                bx = int(20 + i * bar_w) + 1
                by = h - 14 - bh
                ratio = val
                col = QColor(0, int(180 + 60 * ratio), int(220 + 35 * ratio), int(100 + 130 * ratio))
                p.setBrush(QBrush(col))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(bx, by, max(1, int(bar_w) - 2), bh)
                glow_col = QColor(0, int(200 + 55 * ratio), 255, int(150 * ratio))
                p.setBrush(QBrush(glow_col))
                p.drawRect(bx, by, max(1, int(bar_w) - 2), 2)
            p.setFont(_mono(6))
            p.setPen(QPen(QColor(0, 150, 200, 100)))
            for i, freq in enumerate(freqs):
                idx = int(i * n / len(freqs))
                fw = p.fontMetrics().horizontalAdvance(freq)
                p.drawText(int(20 + idx * bar_w - fw / 2), h - 2, freq)
            for level, label in [(0, "+12"), (0.5, "0"), (1.0, "-12")]:
                y = int(h * (1 - level) - 12)
                p.setPen(QPen(QColor(0, 150, 200, 80)))
                p.drawText(2, y, label)
                p.drawText(w - 20, y, label)
        except Exception as _paint_err:
            pass

class ReactorPulse(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self.setMinimumHeight(40)
        self.setFixedHeight(50)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(50)

    def _step(self):
        self._t = (self._t + 0.08) % (math.pi * 200)
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor(0, 8, 20, 160))
            p.setPen(QPen(QColor(0, 212, 255, 120), 1.5))
            n = 120
            pts = []
            for i in range(n):
                fx = i / (n - 1)
                phase = (fx * 8 + self._t * 0.5) % 1.0
                if 0.3 < phase < 0.35:
                    fy = 0.5 - 0.3 * math.sin((phase - 0.3) / 0.05 * math.pi)
                elif 0.35 <= phase < 0.4:
                    fy = 0.5 + 0.2 * math.sin((phase - 0.35) / 0.05 * math.pi)
                elif 0.4 <= phase < 0.45:
                    fy = 0.5 - 0.15 * math.sin((phase - 0.4) / 0.05 * math.pi)
                else:
                    fy = 0.5
                pts.append(QPointF(fx * w, fy * h))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
            p.setPen(QPen(QColor(0, 212, 255, 40), 3))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
        except Exception as _paint_err:
            pass

class MiniArcIcon(QWidget):
    def __init__(self, size=28, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0.0
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(50)

    def _step(self):
        self._angle = (self._angle + 3) % 360
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2
            R = min(cx, cy) - 2
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            bg = QRadialGradient(cx, cy, R)
            bg.setColorAt(0, QColor(0, 30, 60, 200))
            bg.setColorAt(1, QColor(0, 10, 25, 180))
            p.setBrush(QBrush(bg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), R, R)
            p.setPen(QPen(C_CYAN, max(1, R * 0.12)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), R * 0.85, R * 0.85)
            for i in range(8):
                deg = self._angle + i * 45
                p.setPen(QPen(QColor(0, 200, 255, 160 if i % 2 == 0 else 80), max(1, R * 0.08)))
                p.drawArc(QRectF(cx - R * 0.65, cy - R * 0.65, R * 1.3, R * 1.3), int(deg * 16), int(20 * 16))
            cg = QRadialGradient(cx, cy, R * 0.35)
            cg.setColorAt(0, QColor(220, 245, 255, 220))
            cg.setColorAt(1, QColor(0, 180, 255, 0))
            p.setBrush(QBrush(cg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), R * 0.35, R * 0.35)
        except Exception as _paint_err:
            pass

class ChatBubble(QFrame):
    def __init__(self, text, is_user=True, timestamp=None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._full = text
        self._ts = timestamp or datetime.now()
        self._build(text)

    def _build(self, text):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(10)
        ts_str = self._ts.strftime("%I:%M %p") if isinstance(self._ts, datetime) else str(self._ts)
        if self.is_user:
            outer.addStretch()
            col = QVBoxLayout()
            col.setSpacing(3)
            col.setAlignment(Qt.AlignmentFlag.AlignRight)
            meta = QHBoxLayout()
            meta.setContentsMargins(0, 0, 8, 0)
            ts = QLabel(ts_str)
            ts.setFont(_mono(7))
            ts.setStyleSheet("color:rgba(0,150,200,100);background:transparent;border:none;")
            checkmark = QLabel("✓✓")
            checkmark.setFont(_mono(7))
            checkmark.setStyleSheet("color:rgba(0,212,255,120);background:transparent;border:none;")
            meta.addWidget(ts)
            meta.addSpacing(6)
            meta.addWidget(checkmark)
            col.addLayout(meta)
            self.label = QLabel(text)
            self.label.setWordWrap(True)
            self.label.setFont(_mono(10))
            self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.label.setMaximumWidth(560)
            self.label.setStyleSheet("""
                background:rgba(0,25,60,200);
                color:#C8E8FF;
                border:1px solid rgba(0,180,220,80);
                border-top:1px solid rgba(0,212,255,120);
                border-radius:16px 16px 4px 16px;
                padding:12px 16px;
            """)
            col.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignRight)
            outer.addLayout(col)
        else:
            self._icon = MiniArcIcon(28)
            outer.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(3)
            meta = QHBoxLayout()
            meta.setContentsMargins(8, 0, 8, 0)
            copy_btn = QPushButton("⎘")
            copy_btn.setFixedSize(16, 14)
            copy_btn.setStyleSheet(
                "QPushButton{background:transparent;color:rgba(0,212,255,70);border:none;font-size:9px;}"
                "QPushButton:hover{color:#00D4FF;}")
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._full))
            ts = QLabel(ts_str)
            ts.setFont(_mono(7))
            ts.setStyleSheet("color:rgba(0,150,200,100);background:transparent;border:none;")
            meta.addWidget(copy_btn)
            meta.addStretch()
            meta.addWidget(ts)
            col.addLayout(meta)
            # Use QTextEdit instead of QLabel — QLabel clips long word-wrapped text
            # inside scroll areas; QTextEdit renders the full content correctly.
            self.label = QTextEdit()
            self.label.setReadOnly(True)
            self.label.setFont(_mono(10))
            self.label.setMaximumWidth(560)
            self.label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.label.setStyleSheet("""
                QTextEdit {
                    background:rgba(0,10,30,240);
                    color:#A8D8F0;
                    border:1px solid rgba(0,100,160,80);
                    border-top:1px solid rgba(0,160,210,100);
                    border-radius:8px;
                    padding:6px 12px;
                }
                QTextEdit QScrollBar { width:0px; height:0px; }
            """)
            # Start collapsed — will expand as text arrives
            self.label.setFixedHeight(32)
            self.label.document().setDocumentMargin(4)
            if text:
                self.label.setPlainText(text)
                QTimer.singleShot(0, self._resize_label)
            self.label.document().contentsChanged.connect(self._resize_label)
            col.addWidget(self.label)
            outer.addLayout(col, stretch=1)
            outer.addStretch()

    def _resize_label(self):
        if not self.is_user and hasattr(self, 'label') and isinstance(self.label, QTextEdit):
            # Force layout so document size is accurate
            self.label.document().adjustSize()
            doc_h = int(self.label.document().size().height())
            # Add padding: top+bottom padding (6+6) + border (2) + small buffer
            h = max(32, doc_h + 16)
            self.label.setFixedHeight(h)

    def append_text(self, t):
        self._full += t
        if isinstance(self.label, QTextEdit):
            self.label.setPlainText(self._full)
            # _resize_label fires via contentsChanged signal automatically
        else:
            self.label.setText(self._full)

class TypingDots(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._dots = [0.3, 0.3, 0.3]
        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._anim)
        self.hide()

    def start(self):
        self.show()
        self._timer.start(160)

    def stop(self):
        self._timer.stop()
        self.hide()

    def _anim(self):
        self._step = (self._step + 1) % 3
        for i in range(3):
            self._dots[i] = 1.0 if i == self._step else 0.3
        self.update()

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            r = 4
            gap = 12
            x = 22
            y = self.height() // 2
            for alpha in self._dots:
                p.setBrush(QBrush(QColor(0, 212, 255, int(200 * alpha))))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(x, y), r * alpha, r * alpha)
                x += r * 2 + gap
        except Exception as _paint_err:
            pass

class SystemStatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._bars = {}
        for label, key, val in [
            ("CPU Usage", "cpu", 23),
            ("RAM Usage", "ram", 45),
            ("Disk Usage", "disk", 68),
            ("Network", "net", 42),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(label)
            lbl.setFont(_mono(8))
            lbl.setStyleSheet("color:rgba(0,170,210,160);background:transparent;border:none;")
            lbl.setFixedWidth(75)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(val)
            bar.setFixedHeight(5)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar{background:rgba(0,50,80,100);border:none;border-radius:2px;}
                QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(0,120,180,200),stop:1 rgba(0,212,255,255));border-radius:2px;}
            """)
            pct = QLabel(f"{val}%")
            pct.setFont(_mono(8, True))
            pct.setStyleSheet("color:rgba(0,212,255,200);background:transparent;border:none;")
            pct.setFixedWidth(32)
            row.addWidget(lbl)
            row.addWidget(bar, 1)
            row.addWidget(pct)
            lay.addLayout(row)
            self._bars[key] = (bar, pct)
        t = QTimer(self)
        t.timeout.connect(self._refresh)
        t.start(3000)

    def _refresh(self):
        try:
            import psutil
            vals = {
                "cpu": int(psutil.cpu_percent()),
                "ram": int(psutil.virtual_memory().percent),
                "disk": int(psutil.disk_usage("/").percent),
                "net": min(100, int(psutil.net_io_counters().bytes_sent / 1e6) % 100),
            }
            for k, (bar, pct) in self._bars.items():
                v = vals.get(k, 0)
                bar.setValue(v)
                pct.setText(f"{v}%")
        except Exception:
            pass

class ConversationHistory(QWidget):
    item_clicked = pyqtSignal(str)
    item_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget{background:transparent;border:none;outline:none;}
            QListWidget::item{color:rgba(0,180,220,160);font-family:'Courier New';font-size:8px;
                padding:4px 6px;border-radius:3px;margin:1px;}
            QListWidget::item:selected{background:rgba(0,212,255,25);color:#00EEFF;}
            QListWidget::item:hover{background:rgba(0,212,255,12);}
        """)
        self._list.itemClicked.connect(lambda i: self.item_clicked.emit(i.data(Qt.ItemDataRole.UserRole)))
        lay.addWidget(self._list)
        link = QPushButton("VIEW ALL HISTORY")
        link.setFixedHeight(22)
        link.setStyleSheet(
            "QPushButton{background:transparent;color:rgba(0,180,220,140);"
            "border:none;font-family:'Courier New';font-size:7px;}"
            "QPushButton:hover{color:#00D4FF;}")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        lay.addWidget(link)

    def refresh(self):
        self._list.clear()
        for fname in list_saved_chats()[:6]:
            try:
                ts = fname.replace("chat_","").replace(".json","")
                dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
                try:
                    msgs = load_chat(fname)
                    for m in msgs:
                        if m.startswith("User: "):
                            label = m[6:40]
                            break
                    else:
                        label = dt.strftime("%b %d  %H:%M")
                except:
                    label = dt.strftime("%b %d  %H:%M")
                time_str = dt.strftime("%I:%M %p") if dt.date() == datetime.now().date() else "Yesterday"
            except:
                label = fname; time_str = ""

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, fname)
            self._list.addItem(item)

            # Row widget with label + delete button
            row = QWidget()
            row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(4, 0, 2, 0)
            rl.setSpacing(4)
            lbl = QLabel(f"▷  {label[:22]}")
            lbl.setFont(_mono(8))
            lbl.setStyleSheet("color:rgba(0,180,220,160);background:transparent;")
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(14, 14)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(
                "QPushButton{background:transparent;color:rgba(255,80,80,120);"
                "border:none;font-size:9px;font-weight:bold;}"
                "QPushButton:hover{color:rgba(255,80,80,255);}")
            del_btn.clicked.connect(lambda _, f=fname: self.item_deleted.emit(f))
            rl.addWidget(lbl, stretch=1)
            rl.addWidget(del_btn)
            item.setSizeHint(row.sizeHint())
            self._list.setItemWidget(item, row)

class CircularDateClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._start_time = datetime.now()
        self.setFixedHeight(88)
        t = QTimer(self); t.timeout.connect(self.update); t.start(1000)

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            now = datetime.now()
            ring_r = min(h - 8, 38)
            rcx, rcy = ring_r + 6, h // 2
            p.setPen(QPen(QColor(0, 60, 100, 120), ring_r * 0.14))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(rcx, rcy), ring_r, ring_r)
            p.setPen(QPen(C_CYAN, ring_r * 0.10))
            p.drawArc(QRectF(rcx - ring_r, rcy - ring_r, ring_r * 2, ring_r * 2), int(90 * 16), int(-270 * 16))
            p.setFont(_mono(7, True))
            p.setPen(QPen(QColor(0, 200, 255, 180)))
            dow = now.strftime("%A").upper()
            dw = p.fontMetrics().horizontalAdvance(dow)
            p.drawText(int(rcx - dw / 2), int(rcy - 10), dow)
            p.setFont(_mono(6))
            p.setPen(QPen(QColor(0, 150, 200, 140)))
            mon = now.strftime("%b").upper()
            mw = p.fontMetrics().horizontalAdvance(mon)
            p.drawText(int(rcx - mw / 2), int(rcy + 2), mon)
            p.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
            p.setPen(QPen(C_CYAN))
            day = now.strftime("%d")
            dtw = p.fontMetrics().horizontalAdvance(day)
            p.drawText(int(rcx - dtw / 2), int(rcy + 18), day)
            tx = int(rcx + ring_r + 14)
            p.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
            p.setPen(QPen(C_CYAN))
            time_str = now.strftime("%I:%M:%S %p")
            p.drawText(tx, int(h * 0.48), time_str)
            elapsed = datetime.now() - self._start_time
            s = int(elapsed.total_seconds())
            hrs, rem = divmod(s, 3600); mins, secs = divmod(rem, 60)
            p.setFont(_mono(7))
            p.setPen(QPen(QColor(0, 150, 200, 130)))
            p.drawText(tx, int(h * 0.72), "System Uptime")
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(tx, int(h * 0.88), f"{hrs}h {mins}m {secs}s")
        except Exception as _paint_err:
            pass

class RadialShortcutsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 195)
        self.setStyleSheet("background:transparent;")
        self._buttons = []
        shortcuts = list(SHORTCUT_ACTIONS.keys())
        angles = [-90, -45, 0, 45, 90, 135, 180, -135]
        cx, cy, radius = 105, 98, 72
        for i, name in enumerate(shortcuts):
            btn = QPushButton(name, self)
            btn.setFixedSize(72, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(_mono(6))
            btn.setStyleSheet(
                "QPushButton{background:rgba(0,20,45,160);color:rgba(0,180,220,170);"
                "border:1px solid rgba(0,150,200,70);border-radius:3px;}"
                "QPushButton:hover{background:rgba(0,212,255,25);color:#00EEFF;}")
            a = math.radians(angles[i])
            bx = int(cx + radius * math.cos(a) - 36)
            by = int(cy + radius * math.sin(a) - 10)
            btn.move(bx, by)
            btn.clicked.connect(SHORTCUT_ACTIONS[name])
            self._buttons.append(btn)
        self._reactor = ArcReactor(52)
        self._reactor.setFixedSize(52, 52)
        self._reactor.move(cx - 26, cy - 26)

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(0, 130, 180, 40), 1, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(105, 98), 72, 72)
        except Exception as _paint_err:
            pass

class _MiniRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(50)

    def _step(self):
        self._angle = (self._angle + 2.5) % 360
        self.update()

    def paintEvent(self, e):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        R = min(cx, cy) - 4
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(0, 60, 100, 100), 6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R, R)
        pen = QPen(C_CYAN, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(int(cx - R), int(cy - R), int(R * 2), int(R * 2), int(self._angle * 16), int(260 * 16))
        p.setFont(_mono(9, True))
        p.setPen(QPen(C_CYAN))
        txt = "100%"
        tw = p.fontMetrics().horizontalAdvance(txt)
        p.drawText(int(cx - tw / 2), int(cy + 5), txt)

class _MiniWaveform(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._active = False
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(50)

    def set_active(self, v):
        self._active = v

    def _step(self):
        self._t = (self._t + 0.08) % (math.pi * 2)
        self.update()

    def paintEvent(self, e):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(0, 212, 255, 160 if self._active else 80), 1.2))
        n = 60
        pts = []
        for i in range(n):
            fx = i / (n - 1)
            amp = (0.6 + 0.4 * math.sin(fx * 12 + self._t * 3)) if self._active else 0.2
            fy = 0.5 + amp * 0.4 * math.sin(fx * 18 + self._t * 4)
            pts.append(QPointF(fx * w, fy * h))
        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

class ChatDashboard(QWidget):
    weather_ready = pyqtSignal(dict)
    weather_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_history = []
        self.current_bubble = None
        self.worker = None
        self.current_filename = None
        self._deleted = False
        self._t0 = None
        self._weather_busy = False
        self._stream_buffer = []
        self._model_ready = False  # set True when warmup completes
        self._stream_timer = QTimer(self)
        self._stream_timer.setInterval(33)
        self._stream_timer.timeout.connect(self._flush_stream_buffer)
        self.weather_ready.connect(self._update_weather_ui)
        self.weather_error.connect(self._weather_failed)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        topbar = QWidget()
        topbar.setFixedHeight(44)
        topbar.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 rgba(0,10,30,240), stop:1 rgba(0,6,20,220));"
            "border-bottom:1px solid rgba(0,150,200,80);")
        tbl = QHBoxLayout(topbar)
        tbl.setContentsMargins(16, 0, 16, 0)
        tbl.setSpacing(12)

        logo_lay = QHBoxLayout()
        logo_lay.setSpacing(6)
        logo_icon = QLabel("◈")
        logo_icon.setFont(_mono(14, True))
        logo_icon.setStyleSheet("color:#00D4FF;background:transparent;")
        logo_lay.addWidget(logo_icon)
        logo_text = QLabel("JARVIS")
        logo_text.setFont(_orbitron(14, True))
        logo_text.setStyleSheet("color:#00D4FF;background:transparent;")
        logo_lay.addWidget(logo_text)
        tbl.addLayout(logo_lay)
        tbl.addStretch()

        # Title in true center — use a separate absolutely-positioned label
        # so it stays centered regardless of left/right widget widths
        title = QLabel("JARVIS AI ASSISTANT", topbar)
        title.setFont(_orbitron(12, True))
        title.setStyleSheet("color:rgba(0,212,255,220);background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Reposition on resize via a helper
        def _center_title():
            title.setFixedWidth(topbar.width())
            title.move(0, (topbar.height() - title.height()) // 2)
        topbar.resizeEvent = lambda e, fn=_center_title: (fn(), type(topbar).resizeEvent(topbar, e))
        QTimer.singleShot(0, _center_title)

        tbl.addStretch()

        self._status_lbl = QLabel("●  SYSTEM ONLINE")
        self._status_lbl.setFont(_mono(8, True))
        self._status_lbl.setStyleSheet("color:#00FF88;background:transparent;")
        tbl.addWidget(self._status_lbl)

        for lbl, slot, accent in [
            ("🎙  VOICE", self._open_voice, True),
            ("◉ SAVE", self._save_chat, False),
            ("⊗ CLEAR", self._clear_chat, False),
        ]:
            b = QPushButton(lbl)
            b.setFixedHeight(28)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(_mono(8))
            style_base = "font-family:'Courier New';font-size:8px;font-weight:bold;padding:0 10px;border-radius:4px;"
            if accent:
                b.setStyleSheet(
                    f"QPushButton{{background:rgba(0,212,255,25);color:#00EEFF;"
                    f"border:1px solid rgba(0,212,255,160);{style_base}}}"
                    f"QPushButton:hover{{background:rgba(0,212,255,50);}}")
            else:
                b.setStyleSheet(
                    f"QPushButton{{background:rgba(0,212,255,10);color:rgba(0,180,220,150);"
                    f"border:1px solid rgba(0,150,200,60);{style_base}}}"
                    f"QPushButton:hover{{background:rgba(0,212,255,25);color:#00D4FF;}}")
            b.clicked.connect(slot)
            tbl.addWidget(b)
        root.addWidget(topbar)

        main = QHBoxLayout()
        main.setContentsMargins(10, 8, 10, 8)
        main.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(8)

        clock_frame = QFrame()
        clock_frame.setFixedWidth(220)
        clock_frame.setStyleSheet(PANEL_STYLE)
        clf = QVBoxLayout(clock_frame)
        clf.setContentsMargins(10, 8, 10, 8)
        clf.setSpacing(0)
        self._date_clock = CircularDateClock()
        clf.addWidget(self._date_clock)
        left.addWidget(clock_frame)

        sys_frame = QFrame()
        sys_frame.setFixedWidth(220)
        sys_frame.setStyleSheet(PANEL_STYLE)
        syf = QVBoxLayout(sys_frame)
        syf.setContentsMargins(12, 10, 12, 10)
        syf.setSpacing(6)
        syf.addWidget(section_header("SYSTEM STATUS"))
        syf.addWidget(SystemStatusBar())
        left.addWidget(sys_frame)

        pwr_frame = QFrame()
        pwr_frame.setFixedWidth(220)
        pwr_frame.setStyleSheet(PANEL_STYLE)
        pwf = QVBoxLayout(pwr_frame)
        pwf.setContentsMargins(12, 10, 12, 10)
        pwf.setSpacing(6)
        pwf.addWidget(section_header("POWER STATUS"))
        pwr_row = QHBoxLayout()
        self._pwr_ring = _MiniRing()
        self._pwr_ring.setFixedSize(70, 70)
        pwr_row.addWidget(self._pwr_ring)
        pwr_info = QVBoxLayout()
        pwr_info.setSpacing(2)
        self._pwr_pct_lbl = QLabel("100%")
        self._pwr_pct_lbl.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        self._pwr_pct_lbl.setStyleSheet("color:#00D4FF;background:transparent;")
        pwr_info.addWidget(self._pwr_pct_lbl)
        pwr_info.addWidget(_label("ONLINE", 7, "color:#00FF88;"))
        pwr_row.addLayout(pwr_info)
        pwr_row.addStretch()
        pwf.addLayout(pwr_row)
        conn_lbl = _label("AC POWER CONNECTED", 7, "rgba(0,200,255,140)")
        pwf.addWidget(conn_lbl)
        mode_lbl = _label("High Performance Mode", 7, "rgba(0,150,200,110)")
        pwf.addWidget(mode_lbl)
        left.addWidget(pwr_frame)

        voice_frame = QFrame()
        voice_frame.setFixedWidth(220)
        voice_frame.setStyleSheet(PANEL_STYLE)
        vof = QVBoxLayout(voice_frame)
        vof.setContentsMargins(12, 10, 12, 10)
        vof.setSpacing(6)
        vof.addWidget(section_header("VOICE STATUS"))
        self._voice_wave = _MiniWaveform()
        self._voice_wave.setFixedHeight(40)
        vof.addWidget(self._voice_wave)
        self._voice_status_lbl = _label("Idle...", 8, "rgba(0,180,220,140)")
        self._voice_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vof.addWidget(self._voice_status_lbl)
        mic_btn = QPushButton("🎤")
        mic_btn.setFixedSize(36, 36)
        mic_btn.setStyleSheet(
            "QPushButton{background:rgba(0,212,255,20);color:#00D4FF;"
            "border:2px solid rgba(0,212,255,120);border-radius:18px;font-size:16px;}"
            "QPushButton:hover{background:rgba(0,212,255,50);}")
        mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mic_btn.clicked.connect(self._open_voice)
        vof.addWidget(mic_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        left.addWidget(voice_frame)
        left.addStretch()
        main.addLayout(left)

        center = QVBoxLayout()
        center.setSpacing(8)

        arc_container = QWidget()
        arc_container.setStyleSheet("background:transparent;")
        ac_lay = QGridLayout(arc_container)
        ac_lay.setContentsMargins(0, 0, 0, 0)
        ac_lay.setSpacing(0)

        self.arc = ArcReactor(320)
        arc_cell = QWidget()
        arc_cell_lay = QVBoxLayout(arc_cell)
        arc_cell_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arc_cell_lay.addWidget(self.arc)
        ac_lay.addWidget(arc_cell, 1, 1)

        left_labels = ["SYS", "GEO", "MED", "NET", "CPU", "DOC"]
        right_labels = ["CRM", "PWR", "COM", "VID", "AUD", "CFG"]
        lbl_col = QVBoxLayout()
        lbl_col.setSpacing(8)
        lbl_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        for txt in left_labels:
            lb = _label(txt, 7, "rgba(0,180,220,130)")
            lb.setAlignment(Qt.AlignmentFlag.AlignRight)
            lbl_col.addWidget(lb)
        rbl_col = QVBoxLayout()
        rbl_col.setSpacing(8)
        rbl_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        for txt in right_labels:
            lb = _label(txt, 7, "rgba(0,180,220,130)")
            lb.setAlignment(Qt.AlignmentFlag.AlignLeft)
            rbl_col.addWidget(lb)
        left_w = QWidget()
        left_w.setLayout(lbl_col)
        left_w.setFixedWidth(38)
        right_w = QWidget()
        right_w.setLayout(rbl_col)
        right_w.setFixedWidth(38)
        ac_lay.addWidget(left_w, 1, 0)
        ac_lay.addWidget(right_w, 1, 2)

        self._arc_time = _label(datetime.now().strftime("%I:%M %p"), 8, "rgba(0,212,255,180)", bold=True)
        self._arc_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ac_lay.addWidget(self._arc_time, 0, 1)
        online_lbl = _label("●  ONLINE", 9, "rgba(0,212,255,200)", bold=True)
        online_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ac_lay.addWidget(online_lbl, 2, 1)

        t_arc = QTimer(self)
        t_arc.timeout.connect(
            lambda: self._arc_time.setText(datetime.now().strftime("%I:%M %p")))
        t_arc.start(30000)
        center.addWidget(arc_container)

        chat_frame = QFrame()
        chat_frame.setStyleSheet("""
            QFrame{
                background:rgba(0,8,24,160);
                border:1px solid rgba(0,130,180,70);
                border-top:1px solid rgba(0,180,220,120);
                border-radius:6px;
            }""")
        cf_lay = QVBoxLayout(chat_frame)
        cf_lay.setContentsMargins(0, 0, 0, 0)
        cf_lay.setSpacing(0)

        chat_hdr = QWidget()
        chat_hdr.setFixedHeight(32)
        chat_hdr.setStyleSheet(
            "background:rgba(0,12,30,180);"
            "border-bottom:1px solid rgba(0,130,180,60);"
            "border-radius:6px 6px 0 0;")
        ch_lay = QHBoxLayout(chat_hdr)
        ch_lay.setContentsMargins(12, 0, 12, 0)
        ch_lay.addWidget(_label("CHAT WITH JARVIS", 8, "rgba(0,212,255,200)", bold=True))
        ch_lay.addStretch()
        for icon in ["⚙", "⋯"]:
            b = QPushButton(icon)
            b.setFixedSize(22, 22)
            b.setStyleSheet(
                "QPushButton{background:transparent;color:rgba(0,180,220,120);border:none;font-size:12px;}"
                "QPushButton:hover{color:#00D4FF;}")
            ch_lay.addWidget(b)
        cf_lay.addWidget(chat_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea{border:none;background:transparent;}
            QScrollBar:vertical{width:4px;background:transparent;}
            QScrollBar::handle:vertical{background:rgba(0,180,220,80);border-radius:2px;min-height:20px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}""")
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background:transparent;")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch()
        scroll.setWidget(self.chat_widget)
        self._scroll = scroll
        cf_lay.addWidget(scroll)
        self.typing = TypingDots()
        cf_lay.addWidget(self.typing)
        center.addWidget(chat_frame, stretch=1)

        inp_frame = QFrame()
        inp_frame.setStyleSheet("""
            QFrame{
                background:rgba(0,10,28,200);
                border:1px solid rgba(0,180,220,120);
                border-radius:24px;
            }""")
        inp_lay = QHBoxLayout(inp_frame)
        inp_lay.setContentsMargins(12, 6, 6, 6)
        inp_lay.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type your message...")
        self.input.setFont(_mono(10))
        self.input.setFixedHeight(40)
        self.input.setMaxLength(500)
        self.input.setStyleSheet(
            "QLineEdit{background:transparent;color:#B8F0FF;border:none;}"
            "QLineEdit::placeholder{color:rgba(0,150,180,80);}")
        self.input.returnPressed.connect(self._send)
        self.send_btn = QPushButton("SEND")
        self.send_btn.setFixedSize(80, 38)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFont(_mono(9, True))
        self.send_btn.setStyleSheet("""
            QPushButton{
                background:rgba(0,20,50,180);
                color:#00EEFF;border:2px solid rgba(0,212,255,200);
                border-radius:19px;padding:0 16px;}
            QPushButton:hover{background:rgba(0,212,255,30);border-color:#00EEFF;}
            QPushButton:disabled{background:rgba(0,30,60,100);color:rgba(0,180,220,60);
                border-color:rgba(0,150,200,80);}""")
        self.send_btn.clicked.connect(self._send)
        mic2 = QPushButton("🎤")
        mic2.setFixedSize(38, 38)
        mic2.setStyleSheet(
            "QPushButton{background:rgba(0,212,255,15);color:#00D4FF;"
            "border:2px solid rgba(0,212,255,120);border-radius:19px;font-size:16px;}"
            "QPushButton:hover{background:rgba(0,212,255,40);}")
        mic2.setCursor(Qt.CursorShape.PointingHandCursor)
        mic2.clicked.connect(self._open_voice)
        inp_lay.addWidget(self.input)
        inp_lay.addWidget(self.send_btn)
        inp_lay.addWidget(mic2)
        center.addWidget(inp_frame)
        main.addLayout(center, stretch=1)

        right = QVBoxLayout()
        right.setSpacing(8)

        sc_frame = QFrame()
        sc_frame.setFixedWidth(210)
        sc_frame.setStyleSheet(PANEL_STYLE)
        scf = QVBoxLayout(sc_frame)
        scf.setContentsMargins(8, 8, 8, 8)
        scf.setSpacing(4)
        scf.addWidget(section_header("SYSTEM SHORTCUTS"))
        scf.addWidget(RadialShortcutsPanel(), alignment=Qt.AlignmentFlag.AlignCenter)
        right.addWidget(sc_frame)

        tools_frame = QFrame()
        tools_frame.setFixedWidth(210)
        tools_frame.setStyleSheet(PANEL_STYLE)
        tf = QVBoxLayout(tools_frame)
        tf.setContentsMargins(12, 10, 12, 10)
        tf.setSpacing(4)
        tf.addWidget(section_header("TOOLS"))
        tools = [("⊞", "Open Calculator"), ("⌕", "Search the Web"),
                 ("✎", "Open Notepad"), ("⎙", "Take a Screenshot")]
        for icon, name in tools:
            btn = QPushButton(f"  {icon}  {name}")
            btn.setFixedHeight(24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{background:transparent;color:rgba(0,180,220,140);"
                "border:none;font-family:'Courier New';font-size:8px;text-align:left;}"
                "QPushButton:hover{color:#00D4FF;background:rgba(0,212,255,8);border-radius:3px;}")
            if name in TOOL_ACTIONS:
                btn.clicked.connect(TOOL_ACTIONS[name])
            tf.addWidget(btn)
        right.addWidget(tools_frame)

        hist_frame = QFrame()
        hist_frame.setFixedWidth(210)
        hist_frame.setStyleSheet(PANEL_STYLE)
        hf = QVBoxLayout(hist_frame)
        hf.setContentsMargins(12, 10, 12, 10)
        hf.setSpacing(4)
        hf.addWidget(section_header("CONVERSATION HISTORY"))
        self.hist_widget = ConversationHistory()
        self.hist_widget.item_clicked.connect(self._load_chat)
        self.hist_widget.item_deleted.connect(self._delete_history_chat)
        self.hist_widget.refresh()
        hf.addWidget(self.hist_widget)
        new_btn = QPushButton("＋  NEW CHAT")
        new_btn.setFixedHeight(24)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet(
            "QPushButton{background:rgba(0,212,255,12);color:rgba(0,212,255,180);"
            "border:1px solid rgba(0,180,220,80);border-radius:3px;"
            "font-family:'Courier New';font-size:7px;font-weight:bold;}"
            "QPushButton:hover{background:rgba(0,212,255,30);}")
        new_btn.clicked.connect(self._new_chat)
        hf.addWidget(new_btn)
        right.addWidget(hist_frame)

        wx_frame = QFrame()
        wx_frame.setFixedWidth(210)
        wx_frame.setStyleSheet(PANEL_STYLE)
        wxf = QVBoxLayout(wx_frame)
        wxf.setContentsMargins(12, 10, 12, 10)
        wxf.setSpacing(4)
        wxf.addWidget(section_header("WEATHER"))
        wx_row = QHBoxLayout()
        self._wx_icon_lbl = QLabel("🌡")
        self._wx_icon_lbl.setFont(QFont("", 28))
        self._wx_icon_lbl.setStyleSheet("color:rgba(150,200,220,160);background:transparent;")
        wx_row.addWidget(self._wx_icon_lbl)
        wx_info = QVBoxLayout()
        wx_info.setSpacing(1)
        self._wx_cond = _label("MOSTLY CLOUDY", 7, "rgba(0,200,255,180)", bold=True)
        self._wx_temp = QLabel("--°")
        self._wx_temp.setFont(QFont("Courier New", 22, QFont.Weight.Bold))
        self._wx_temp.setStyleSheet("color:#00D4FF;background:transparent;")
        wx_info.addWidget(self._wx_cond)
        wx_info.addWidget(self._wx_temp)
        wx_row.addLayout(wx_info)
        wx_row.addStretch()
        wxf.addLayout(wx_row)
        self._wx_feel = QLabel("--°")
        self._wx_feel.setFont(_mono(8, True))
        self._wx_feel.setStyleSheet("color:#00D4FF;background:transparent;border:none;")
        wxf.addWidget(stat_row("Feels like", self._wx_feel))
        self._wx_humid = QLabel("--%")
        self._wx_humid.setFont(_mono(8, True))
        self._wx_humid.setStyleSheet("color:#00D4FF;background:transparent;border:none;")
        wxf.addWidget(stat_row("Humidity", self._wx_humid))
        self._wx_wind = QLabel("-- km/h")
        self._wx_wind.setFont(_mono(8, True))
        self._wx_wind.setStyleSheet("color:#00D4FF;background:transparent;border:none;")
        wxf.addWidget(stat_row("Wind", self._wx_wind))
        right.addWidget(wx_frame)
        right.addStretch()
        main.addLayout(right)
        root.addLayout(main, stretch=1)

        footer = QWidget()
        footer.setFixedHeight(36)
        footer.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 rgba(0,6,18,240), stop:1 rgba(0,4,14,220));"
            "border-top:1px solid rgba(0,100,160,70);")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 0, 16, 0)
        fl.setSpacing(8)
        for icon, tip, slot in [
            ("⌂", "home", None),
            ("⎘", "copy", lambda: QApplication.clipboard().setText(
                self.conversation_history[-1].split(": ", 1)[1] if self.conversation_history else "")),
            ("⬇", "downloads", SHORTCUT_ACTIONS["Downloads"]),
            ("🔊", "voice", self._open_voice),
            ("📋", "history", lambda: self.hist_widget.refresh()),
        ]:
            b = QPushButton(icon)
            b.setFixedSize(32, 28)
            b.setToolTip(tip)
            b.setStyleSheet(
                "QPushButton{background:rgba(0,212,255,10);color:rgba(0,200,220,160);"
                "border:1px solid rgba(0,150,200,50);border-radius:4px;font-size:13px;}"
                "QPushButton:hover{background:rgba(0,212,255,30);}")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if slot:
                b.clicked.connect(slot)
            fl.addWidget(b)
        fl.addStretch()
        os_lbl = QLabel(f"JARVIS OS {OS_VERSION}")
        os_lbl.setFont(_mono(7))
        os_lbl.setStyleSheet("color:rgba(0,150,200,120);background:transparent;")
        fl.addWidget(os_lbl)
        root.addWidget(footer)

        self._add_bubble(f"JARVIS ONLINE. Welcome back, {USER_NAME}. All systems initialized.", is_user=False)
        QTimer.singleShot(100, self._fetch_weather)
        QTimer.singleShot(
            1200,
            lambda: threading.Thread(target=preload_piper_voice, daemon=True).start()
        )
        self._weather_timer = QTimer(self)
        self._weather_timer.timeout.connect(self._fetch_weather)
        self._weather_timer.start(WEATHER_REFRESH_MS)

    # Dynamic weather icon based on condition text
    @staticmethod
    def _weather_icon(desc: str) -> str:
        d = desc.lower()
        if any(x in d for x in ("thunder", "storm", "lightning")):
            return "⛈"
        if any(x in d for x in ("snow", "sleet", "blizzard", "hail")):
            return "🌨"
        if any(x in d for x in ("rain", "drizzle", "shower", "mist", "fog")):
            return "🌧"
        if any(x in d for x in ("partly", "partial", "overcast", "mostly cloudy")):
            return "⛅"
        if any(x in d for x in ("cloud", "cloudy")):
            return "☁"
        if any(x in d for x in ("clear", "sunny", "fair", "bright")):
            return "☀"
        return "🌡"

    # FIXED: Fetch weather for Mohali, Punjab, India specifically
    def _fetch_weather(self):
        if self._weather_busy:
            return
        self._weather_busy = True
        self._wx_cond.setText("UPDATING...")

        def _do():
            # Primary: wttr.in JSON API
            try:
                loc_encoded = urllib.parse.quote(WEATHER_LOCATION)
                url = f"https://wttr.in/{loc_encoded}?format=j1"
                r = _http().get(url, timeout=8)
                r.raise_for_status()
                d = r.json()
                cur = d["current_condition"][0]
                desc = cur.get("weatherDesc", [{}])[0].get("value", "--")
                self.weather_ready.emit({
                    "temp": cur.get("temp_C", "--"),
                    "desc": desc,
                    "feel": cur.get("FeelsLikeC", "--"),
                    "humid": cur.get("humidity", "--"),
                    "wind": cur.get("windspeedKmph", "--"),
                    "icon": self._weather_icon(desc),
                })
                return
            except Exception:
                pass

            # Fallback: open-meteo (Mohali coords: 30.7046, 76.7179)
            try:
                url2 = (
                    "https://api.open-meteo.com/v1/forecast"
                    "?latitude=30.7046&longitude=76.7179"
                    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "wind_speed_10m,weather_code&wind_speed_unit=kmh"
                )
                r2 = _http().get(url2, timeout=8)
                r2.raise_for_status()
                d2 = r2.json()["current"]
                wcode = d2.get("weather_code", 0)
                # Map WMO weather codes to simple descriptions
                _wmo = {
                    0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
                    45: "Foggy", 48: "Icy Fog", 51: "Light Drizzle", 53: "Drizzle",
                    55: "Heavy Drizzle", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
                    71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 80: "Rain Showers",
                    81: "Rain Showers", 82: "Heavy Showers", 95: "Thunderstorm",
                    96: "Thunderstorm", 99: "Thunderstorm",
                }
                desc2 = _wmo.get(wcode, "Cloudy")
                self.weather_ready.emit({
                    "temp": str(round(d2.get("temperature_2m", 0))),
                    "desc": desc2,
                    "feel": str(round(d2.get("apparent_temperature", 0))),
                    "humid": str(round(d2.get("relative_humidity_2m", 0))),
                    "wind": str(round(d2.get("wind_speed_10m", 0))),
                    "icon": self._weather_icon(desc2),
                })
            except Exception as e:
                self.weather_error.emit(str(e))

        threading.Thread(target=_do, daemon=True).start()

    def _update_weather_ui(self, data):
        self._weather_busy = False
        self._wx_temp.setText(f"{data.get('temp', '--')}°")
        self._wx_cond.setText(str(data.get("desc", "--"))[:16].upper())
        self._wx_feel.setText(f"{data.get('feel', '--')}°")
        self._wx_humid.setText(f"{data.get('humid', '--')}%")
        self._wx_wind.setText(f"{data.get('wind', '--')} km/h")
        # Update weather icon dynamically
        if hasattr(self, '_wx_icon_lbl'):
            self._wx_icon_lbl.setText(data.get("icon", "🌡"))

    def _weather_failed(self, msg):
        self._weather_busy = False
        self._wx_cond.setText("WEATHER OFFLINE")
        print(f"Weather fetch error: {msg}")

    def _add_bubble(self, text, is_user=True):
        b = ChatBubble(text, is_user=is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, b)
        self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())
        return b

    def _queue_stream_text(self, text):
        self._stream_buffer.append(text)
        if not self._stream_timer.isActive():
            self._stream_timer.start()

    def _flush_stream_buffer(self):
        if not self._stream_buffer:
            self._stream_timer.stop()
            return
        if self.current_bubble:
            chunk = "".join(self._stream_buffer)
            self._stream_buffer.clear()
            self.current_bubble.append_text(chunk)
            self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())

    def _set_thinking(self, on):
        self.send_btn.setEnabled(not on)
        self.input.setEnabled(not on)
        if on:
            self.typing.start()
            self.arc.set_state("responding")
            self._status_lbl.setText("●  PROCESSING...")
            self._status_lbl.setStyleSheet("color:#FF9500;background:transparent;")
            self._t0 = datetime.now()
        else:
            self.typing.stop()
            self.arc.set_state("idle")
            self._status_lbl.setText("●  SYSTEM ONLINE")
            self._status_lbl.setStyleSheet("color:#00FF88;background:transparent;")
            self._t0 = None

    # FIXED: Pass is_first flag for faster first response
    def _send(self):
        text = self.input.text().strip()
        if not text or (self.worker and self.worker.isRunning()):
            return
        self.input.clear()
        self._add_bubble(text, is_user=True)
        self.conversation_history.append(f"User: {text}")
        if text.lower() in ["exit", "quit", "stop"]:
            self._add_bubble("Shutting down. Until next time.", is_user=False)
            return
        self._set_thinking(True)
        use_news = needs_realtime(text.lower())
        self.current_bubble = self._add_bubble(
            "⟳ Fetching latest news..." if use_news else "", is_user=False)

        # FIXED: Pass is_first flag for faster first response
        is_first = len(self.conversation_history) <= 2

        self.worker = JarvisWorker(
            text,
            list(self.conversation_history),
            use_news=use_news,
            is_first=is_first,
            model_ready=self._model_ready,
        )
        self.worker.token_received.connect(self._queue_stream_text)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, resp):
        self._flush_stream_buffer()
        # Always set the full response on the bubble — guards against any tokens
        # that were dropped or not yet flushed from the stream buffer.
        if self.current_bubble and resp:
            if isinstance(self.current_bubble.label, QTextEdit):
                self.current_bubble.label.setPlainText(resp)
                # Defer resize so Qt has laid out the document first
                QTimer.singleShot(0, self.current_bubble._resize_label)
            else:
                self.current_bubble.label.setText(resp)
            self.current_bubble._full = resp
            QTimer.singleShot(10, lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()))
        self.conversation_history.append(f"Jarvis: {resp}")
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        if self.conversation_history and not self._deleted:
            self.current_filename = save_chat(self.conversation_history, self.current_filename)
            self.hist_widget.refresh()
        self._deleted = False
        self._set_thinking(False)
        self.input.setFocus()

    def _on_error(self, msg):
        self._flush_stream_buffer()
        if self.current_bubble:
            self.current_bubble.append_text(f"\nERROR: {msg}")
        self._set_thinking(False)

    def _save_chat(self):
        if not self.conversation_history:
            return
        self.current_filename = save_chat(self.conversation_history, self.current_filename)
        self.hist_widget.refresh()

    def _new_chat(self):
        if self.conversation_history:
            save_chat(self.conversation_history, self.current_filename)
            self.hist_widget.refresh()
        self.conversation_history.clear()
        self.current_filename = None
        self._clear_bubbles()
        self._add_bubble("New session started. How may I assist you?", is_user=False)

    def _load_chat(self, filename):
        if self.conversation_history:
            save_chat(self.conversation_history, self.current_filename)
        try:
            msgs = load_chat(filename)
            self.conversation_history = msgs
            self.current_filename = filename
            self._clear_bubbles()
            bubbles = []
            for m in msgs:
                if m.startswith("User: "):
                    bubbles.append(self._add_bubble(m[6:], is_user=True))
                elif m.startswith("Jarvis: "):
                    bubbles.append(self._add_bubble(m[8:], is_user=False))
            # Defer resize so all bubbles are laid out before sizing
            def _resize_all():
                for b in bubbles:
                    if b and not b.is_user:
                        b._resize_label()
            QTimer.singleShot(50, _resize_all)
        except Exception as e:
            self._add_bubble(f"Failed to load: {e}", is_user=False)

    def _delete_history_chat(self, filename):
        # If the deleted chat is the currently active one, clear the view
        if filename == self.current_filename:
            self.conversation_history.clear()
            self.current_filename = None
            self._deleted = True
            self._clear_bubbles()
            self._add_bubble("Chat deleted. Start a new conversation.", is_user=False)
        delete_chat(filename)
        self.hist_widget.refresh()

    def _clear_chat(self):
        self.conversation_history.clear()
        self.current_filename = None
        self._clear_bubbles()
        self._add_bubble("Memory cleared. Systems reset.", is_user=False)

    def _clear_bubbles(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _open_voice(self):
        self._voice_status_lbl.setText("Listening...")
        self._voice_wave.set_active(True)
        self._voice_overlay = VoiceInterface(self)
        self._voice_overlay.transcript_ready.connect(self._on_voice_transcript)
        self._voice_overlay.destroyed.connect(self._on_voice_closed)
        self._voice_overlay.showMaximized()

    def _on_voice_closed(self, _=None):
        self._voice_status_lbl.setText("Idle...")
        self._voice_wave.set_active(False)

    def _on_voice_transcript(self, user_text, jarvis_text):
        self.conversation_history.append(f"User: {user_text}")
        self.conversation_history.append(f"Jarvis: {jarvis_text}")
        self._add_bubble(user_text, is_user=True)
        self._add_bubble(jarvis_text, is_user=False)
        self.current_filename = save_chat(self.conversation_history, self.current_filename)
        self.hist_widget.refresh()

    def on_close(self):
        if self.conversation_history:
            save_chat(self.conversation_history, self.current_filename)

class VoiceInterface(QWidget):
    transcript_ready = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background:#02060E;")
        self._state = "idle"
        self._last_user = ""
        self._last_jarvis = ""
        self.voice_worker = None
        self.tts_worker = None
        self.llm_worker = None
        self._sq = None
        self._tts_stop = None
        self._muted = threading.Event()
        self._auto_listen = True
        self.conv_history = list(parent.conversation_history) if parent and hasattr(parent, "conversation_history") else []
        self._build()
        QTimer.singleShot(150, self._start_listening)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        topbar = QWidget()
        topbar.setFixedHeight(48)
        topbar.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 rgba(0,10,30,240), stop:1 rgba(0,6,20,220));"
            "border-bottom:1px solid rgba(0,150,200,80);")
        tbl = QHBoxLayout(topbar)
        tbl.setContentsMargins(14, 0, 14, 0)
        tbl.setSpacing(10)

        center_col = QVBoxLayout()
        center_col.setSpacing(0)
        center_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("JARVIS")
        title.setFont(_orbitron(16, True))
        title.setStyleSheet("color:#00D4FF;background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("VOICE INTERFACE")
        sub.setFont(_mono(8))
        sub.setStyleSheet("color:rgba(0,180,220,120);background:transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_col.addWidget(title)
        center_col.addWidget(sub)
        tbl.addStretch()
        tbl.addLayout(center_col)
        tbl.addStretch()

        self._top_clock = QLabel()
        self._top_clock.setFont(_mono(12, True))
        self._top_clock.setStyleSheet("color:#00D4FF;background:transparent;")
        self._top_date = QLabel()
        self._top_date.setFont(_mono(7))
        self._top_date.setStyleSheet("color:rgba(0,180,220,140);background:transparent;")
        clock_col = QVBoxLayout()
        clock_col.setSpacing(0)
        clock_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        clock_col.addWidget(self._top_clock)
        clock_col.addWidget(self._top_date)
        tbl.addLayout(clock_col)

        for lbl_txt, act in [("─", ""), ("□", ""), ("✕", "close")]:
            b = QPushButton(lbl_txt)
            b.setFixedSize(30, 30)
            b.setStyleSheet(
                "QPushButton{background:transparent;color:rgba(0,180,220,150);"
                "border:none;font-size:13px;}"
                "QPushButton:hover{color:#00D4FF;}")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if act == "close":
                b.clicked.connect(self.close)
            tbl.addWidget(b)
        root.addWidget(topbar)
        t_clock2 = QTimer(self)
        t_clock2.timeout.connect(self._tick_clock)
        t_clock2.start(1000)
        self._tick_clock()

        main = QHBoxLayout()
        main.setContentsMargins(10, 8, 10, 8)
        main.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(8)

        vc_frame = QFrame()
        vc_frame.setFixedWidth(230)
        vc_frame.setStyleSheet(PANEL_STYLE)
        vcf = QVBoxLayout(vc_frame)
        vcf.setContentsMargins(12, 10, 12, 10)
        vcf.setSpacing(6)
        vcf.addWidget(section_header("VOICE CHAT"))
        self._vc_status = _label("LISTENING...", 9, "rgba(0,212,255,200)", bold=True)
        self._vc_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vcf.addWidget(self._vc_status)

        wave_mic = QHBoxLayout()
        wave_mic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vc_wave_left = _MiniWaveform()
        self._vc_wave_left.setFixedSize(60, 30)
        self._vc_wave_left.set_active(True)
        wave_mic.addWidget(self._vc_wave_left)
        mic_icon = QLabel("🎤")
        mic_icon.setFont(QFont("", 24))
        mic_icon.setStyleSheet("color:rgba(0,212,255,180);background:transparent;")
        wave_mic.addWidget(mic_icon)
        self._vc_wave_right = _MiniWaveform()
        self._vc_wave_right.setFixedSize(60, 30)
        self._vc_wave_right.set_active(True)
        wave_mic.addWidget(self._vc_wave_right)
        vcf.addLayout(wave_mic)

        self._vc_prompt = _label("I'm listening. Go ahead.", 8, "rgba(0,180,220,150)")
        self._vc_prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vcf.addWidget(self._vc_prompt)
        left.addWidget(vc_frame)

        vi_frame = QFrame()
        vi_frame.setFixedWidth(230)
        vi_frame.setStyleSheet(PANEL_STYLE)
        vif = QVBoxLayout(vi_frame)
        vif.setContentsMargins(12, 10, 12, 10)
        vif.setSpacing(6)
        vif.addWidget(section_header("VOICE INPUT"))
        vi_row = QHBoxLayout()
        self._mic_ring = CircularGauge(78, "MIC\nLEVEL", 85)
        self._mic_ring.setFixedSize(85, 85)
        vi_row.addWidget(self._mic_ring)

        vbar = VerticalBarMeter(78)
        vbar.setFixedWidth(20)
        vi_row.addWidget(vbar)

        lvl_col = QVBoxLayout()
        lvl_col.setSpacing(2)
        for lvl in [100, 75, 50, 25, 0]:
            lvl_col.addWidget(_label(str(lvl), 6, "rgba(0,150,200,80)"))
        vi_row.addLayout(lvl_col)
        vif.addLayout(vi_row)

        noise_row = QHBoxLayout()
        noise_row.addWidget(_label("≈  Noise Reduction:", 7, "rgba(0,150,200,120)"))
        noise_row.addWidget(_label("ON", 7, "#00FF88", bold=True))
        vif.addLayout(noise_row)
        left.addWidget(vi_frame)

        vs_frame = QFrame()
        vs_frame.setFixedWidth(230)
        vs_frame.setStyleSheet(PANEL_STYLE)
        vsf = QVBoxLayout(vs_frame)
        vsf.setContentsMargins(12, 10, 12, 10)
        vsf.setSpacing(4)
        vsf.addWidget(section_header("VOICE SETTINGS"))
        for setting, val in [("Sensitivity", 75), ("Noise Filter", 60)]:
            row = QHBoxLayout()
            row.addWidget(_label(setting, 7, "rgba(0,160,200,140)"))
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(0, 100)
            sl.setValue(val)
            sl.setFixedHeight(12)
            sl.setStyleSheet("""
                QSlider::groove:horizontal{height:3px;background:rgba(0,60,100,150);border-radius:1px;}
                QSlider::handle:horizontal{width:10px;height:10px;background:#00D4FF;border-radius:5px;margin:-3px 0;}
                QSlider::sub-page:horizontal{background:rgba(0,180,220,200);border-radius:1px;}""")
            row.addWidget(sl)
            row.addWidget(_label(f"{val}%", 7, "rgba(0,212,255,180)"))
            vsf.addLayout(row)
        auto_row = QHBoxLayout()
        auto_row.addWidget(_label("Auto Gain", 7, "rgba(0,160,200,140)"))
        auto_row.addStretch()
        auto_row.addWidget(_label("ON", 7, "#00FF88", bold=True))
        vsf.addLayout(auto_row)
        left.addWidget(vs_frame)

        cmd_frame = QFrame()
        cmd_frame.setFixedWidth(230)
        cmd_frame.setStyleSheet(PANEL_STYLE)
        cmdf = QVBoxLayout(cmd_frame)
        cmdf.setContentsMargins(12, 10, 12, 10)
        cmdf.setSpacing(4)
        cmdf.addWidget(section_header("VOICE COMMANDS"))
        for icon, cmd, slot in [
            ("🎤", "Start Listening", self._start_listening),
            ("⏹", "Stop Listening", self._stop_all),
            ("⎘", "Switch to Text Chat", self.close),
            ("✕", "Exit Voice Mode", self.close),
        ]:
            btn = QPushButton(f"  {icon}  {cmd}")
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(_mono(8))
            btn.setStyleSheet(
                "QPushButton{background:transparent;color:rgba(0,160,210,150);"
                "border:none;text-align:left;}"
                "QPushButton:hover{color:#00D4FF;background:rgba(0,212,255,8);}")
            btn.clicked.connect(slot)
            cmdf.addWidget(btn)
        left.addWidget(cmd_frame)
        left.addStretch()
        main.addLayout(left)

        center = QVBoxLayout()
        center.setSpacing(8)

        self.waveform = WaveformDisplay(height=90)
        center.addWidget(self.waveform)

        arc_row = QHBoxLayout()

        listen_col = QVBoxLayout()
        listen_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._listen_lbl = _label("LISTENING", 10, "rgba(0,212,255,200)", bold=True)
        self._listen_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        listen_col.addWidget(self._listen_lbl)
        self._listen_wave = _MiniWaveform()
        self._listen_wave.setFixedSize(70, 24)
        listen_col.addWidget(self._listen_wave)
        arc_row.addLayout(listen_col)

        self.main_arc = ArcReactor(400)
        self.main_arc.setFixedSize(400, 400)
        arc_row.addWidget(self.main_arc)

        speak_col = QVBoxLayout()
        speak_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._speak_lbl = _label("SPEAKING", 10, "rgba(0,212,255,200)", bold=True)
        self._speak_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speak_col.addWidget(self._speak_lbl)
        self._speak_wave = _MiniWaveform()
        self._speak_wave.setFixedSize(70, 24)
        speak_col.addWidget(self._speak_wave)
        arc_row.addLayout(speak_col)
        center.addLayout(arc_row)

        self._proc_lbl = _label("PROCESSING", 10, "rgba(0,180,220,180)", bold=True)
        self._proc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self._proc_lbl)
        dots_lbl = _label("• • •", 9, "rgba(0,180,220,120)")
        dots_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(dots_lbl)

        self.transcript_lbl = QLabel("Tap SPEAK to begin...")
        self.transcript_lbl.setFont(_mono(9))
        self.transcript_lbl.setWordWrap(True)
        self.transcript_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transcript_lbl.setMaximumHeight(50)
        self.transcript_lbl.setStyleSheet(
            "color:rgba(0,200,240,160);background:transparent;padding:0 20px;")
        center.addWidget(self.transcript_lbl)

        eq_box = QFrame()
        eq_box.setStyleSheet(
            "QFrame{background:rgba(0,8,22,180);border:1px solid rgba(0,130,180,60);border-radius:4px;}")
        eq_lay = QVBoxLayout(eq_box)
        eq_lay.setContentsMargins(8, 6, 8, 6)
        eq_lay.setSpacing(4)
        eq_lay.addWidget(_label("EQUALIZER", 7, "rgba(0,180,220,160)", bold=True))
        self.equalizer = Equalizer()
        self.equalizer.setFixedHeight(90)
        eq_lay.addWidget(self.equalizer)
        center.addWidget(eq_box)

        rp_box = QFrame()
        rp_box.setStyleSheet(
            "QFrame{background:rgba(0,8,22,180);border:1px solid rgba(0,130,180,60);border-radius:4px;}")
        rp_lay = QVBoxLayout(rp_box)
        rp_lay.setContentsMargins(8, 4, 8, 4)
        rp_lay.setSpacing(2)
        rp_lay.addWidget(_label("REACTOR PULSE", 7, "rgba(0,180,220,160)", bold=True))
        self.reactor_pulse = ReactorPulse()
        self.reactor_pulse.setFixedHeight(50)
        rp_lay.addWidget(self.reactor_pulse)
        center.addWidget(rp_box)
        main.addLayout(center, stretch=1)

        right = QVBoxLayout()
        right.setSpacing(8)

        cs_frame = QFrame()
        cs_frame.setFixedWidth(230)
        cs_frame.setStyleSheet(PANEL_STYLE)
        csf = QVBoxLayout(cs_frame)
        csf.setContentsMargins(12, 10, 12, 10)
        csf.setSpacing(6)
        csf.addWidget(section_header("CONVERSATION STATUS"))
        cs_row = QHBoxLayout()
        mini_arc2 = ArcReactor(65)
        mini_arc2.setFixedSize(65, 65)
        cs_row.addWidget(mini_arc2)
        cs_info = QVBoxLayout()
        cs_info.setSpacing(3)
        for k, v in [("MODEL +", OLLAMA_MODEL), ("RESPONSE TIME", "0.85 sec"), ("TOKENS", "512")]:
            r2 = QHBoxLayout()
            r2.addWidget(_label(k, 7, "rgba(0,140,180,120)"))
            r2.addWidget(_label(v, 7, "rgba(0,212,255,200)"))
            cs_info.addLayout(r2)
        self._conn_lbl = _label("●  CONNECTED", 8, "#00FF88", bold=True)
        cs_info.addWidget(self._conn_lbl)
        cs_row.addLayout(cs_info)
        csf.addLayout(cs_row)
        right.addWidget(cs_frame)

        ao_frame = QFrame()
        ao_frame.setFixedWidth(230)
        ao_frame.setStyleSheet(PANEL_STYLE)
        aof = QVBoxLayout(ao_frame)
        aof.setContentsMargins(12, 10, 12, 10)
        aof.setSpacing(6)
        aof.addWidget(section_header("AUDIO OUTPUT"))
        ao_row = QHBoxLayout()
        self._spk_ring = CircularGauge(65, "SPEAKER\nLEVEL", 80)
        self._spk_ring.setFixedSize(80, 80)
        ao_row.addWidget(self._spk_ring)

        spk_bar = VerticalBarMeter(65)
        spk_bar.setFixedWidth(20)
        ao_row.addWidget(spk_bar)

        for lvl in [100, 75, 50, 25, 0]:
            ao_row.addWidget(_label(str(lvl), 6, "rgba(0,150,200,80)"))
        aof.addLayout(ao_row)
        aof.addWidget(_label("🔊  Output Device: Built-in Output", 7, "rgba(0,150,200,120)"))
        right.addWidget(ao_frame)

        state_frame = QFrame()
        state_frame.setFixedWidth(230)
        state_frame.setStyleSheet(PANEL_STYLE)
        stf = QVBoxLayout(state_frame)
        stf.setContentsMargins(12, 10, 12, 10)
        stf.setSpacing(6)
        stf.addWidget(section_header("CURRENT STATE"))
        st_row = QHBoxLayout()
        self._state_dot = QLabel("●")
        self._state_dot.setFont(QFont("", 24))
        self._state_dot.setStyleSheet("color:#00D4FF;background:transparent;")
        st_row.addWidget(self._state_dot)
        st_col = QVBoxLayout()
        st_col.setSpacing(2)
        self._state_lbl = _label("IDLE", 12, "#00D4FF", bold=True)
        self._state_sub = _label("Tap SPEAK to begin...", 7, "rgba(0,180,220,130)")
        st_col.addWidget(self._state_lbl)
        st_col.addWidget(self._state_sub)
        st_row.addLayout(st_col)
        stf.addLayout(st_row)

        dot_row = QHBoxLayout()
        dot_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._state_dots = []
        for i in range(8):
            d = QLabel("○")
            d.setFont(_mono(8))
            d.setStyleSheet("color:rgba(0,150,200,80);background:transparent;")
            dot_row.addWidget(d)
            self._state_dots.append(d)
        stf.addLayout(dot_row)
        right.addWidget(state_frame)

        ctrl_frame = QFrame()
        ctrl_frame.setFixedWidth(230)
        ctrl_frame.setStyleSheet(PANEL_STYLE)
        ctrlf = QVBoxLayout(ctrl_frame)
        ctrlf.setContentsMargins(12, 10, 12, 10)
        ctrlf.setSpacing(8)
        ctrlf.addWidget(section_header("VOICE CONTROLS"))
        ctrl_row = QHBoxLayout()
        ctrl_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_row.setSpacing(12)

        speak_col = QVBoxLayout()
        speak_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speak_col.setSpacing(4)
        self._speak_btn = QPushButton("🎤")
        self._speak_btn.setFixedSize(52, 52)
        self._speak_btn.setFont(QFont("", 18))
        self._speak_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._speak_btn.setStyleSheet(
            "QPushButton{background:rgba(0,212,255,25);color:#00D4FF;"
            "border:2px solid rgba(0,212,255,160);border-radius:26px;}"
            "QPushButton:hover{background:rgba(0,212,255,50);}"
            "QPushButton:disabled{background:rgba(0,30,60,100);color:rgba(0,180,220,60);"
            "border-color:rgba(0,150,200,80);}")
        self._speak_btn.clicked.connect(self._start_listening)
        speak_col.addWidget(self._speak_btn)
        speak_col.addWidget(_label("SPEAK", 7, "#00D4FF"))
        ctrl_row.addLayout(speak_col)

        mute_col = QVBoxLayout()
        mute_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mute_col.setSpacing(4)
        self._mute_btn = QPushButton("🔇")
        self._mute_btn.setFixedSize(52, 52)
        self._mute_btn.setFont(QFont("", 18))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.setStyleSheet(
            "QPushButton{background:rgba(0,212,255,12);color:rgba(0,200,220,160);"
            "border:2px solid rgba(0,180,220,100);border-radius:26px;}"
            "QPushButton:hover{background:rgba(0,212,255,30);}")
        self._mute_btn.clicked.connect(self._toggle_mute)
        mute_col.addWidget(self._mute_btn)
        mute_col.addWidget(_label("MUTE", 7, "rgba(0,200,220,160)"))
        ctrl_row.addLayout(mute_col)

        stop_col = QVBoxLayout()
        stop_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stop_col.setSpacing(4)
        stop_btn = QPushButton("⏹")
        stop_btn.setFixedSize(52, 52)
        stop_btn.setFont(QFont("", 18))
        stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        stop_btn.setStyleSheet(
            "QPushButton{background:rgba(255,180,0,20);color:#FFB800;"
            "border:2px solid rgba(255,180,0,120);border-radius:26px;}"
            "QPushButton:hover{background:rgba(255,180,0,50);}")
        stop_btn.clicked.connect(self._stop_all)
        stop_col.addWidget(stop_btn)
        stop_col.addWidget(_label("STOP", 7, "#FFB800"))
        ctrl_row.addLayout(stop_col)

        exit_col = QVBoxLayout()
        exit_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exit_col.setSpacing(4)
        exit_btn = QPushButton("✕")
        exit_btn.setFixedSize(52, 52)
        exit_btn.setFont(QFont("", 18))
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet(
            "QPushButton{background:rgba(255,60,60,20);color:rgba(255,120,120,200);"
            "border:2px solid rgba(255,60,60,120);border-radius:26px;}"
            "QPushButton:hover{background:rgba(255,60,60,50);}")
        exit_btn.clicked.connect(self.close)
        exit_col.addWidget(exit_btn)
        exit_col.addWidget(_label("EXIT", 7, "rgba(255,100,100,200)"))
        ctrl_row.addLayout(exit_col)

        ctrlf.addLayout(ctrl_row)
        right.addWidget(ctrl_frame)
        right.addStretch()
        main.addLayout(right)
        root.addLayout(main, stretch=1)

        bot = QWidget()
        bot.setFixedHeight(26)
        bot.setStyleSheet(
            "background:rgba(0,6,18,220);border-top:1px solid rgba(0,100,160,60);")
        bl = QHBoxLayout(bot)
        bl.setContentsMargins(14, 0, 14, 0)
        bl.addStretch()
        bl.addWidget(_label(f"JARVIS OS {OS_VERSION}", 7, "rgba(0,150,200,100)"))
        bl.addStretch()
        root.addWidget(bot)

        self._speak_timer = QTimer(self)
        self._speak_timer.timeout.connect(self._animate_speak_dots)
        self._speak_dot_idx = 0
        self._speak_timer.start(400)

    def _tick_clock(self):
        now = datetime.now()
        self._top_clock.setText(now.strftime("%I:%M:%S %p"))
        self._top_date.setText(now.strftime("%A, %B %d, %Y"))

    def _animate_speak_dots(self):
        self._speak_dot_idx = (self._speak_dot_idx + 1) % 8
        for i, d in enumerate(self._state_dots):
            if i <= self._speak_dot_idx:
                d.setText("●")
                d.setStyleSheet("color:rgba(0,212,255,200);background:transparent;")
            else:
                d.setText("○")
                d.setStyleSheet("color:rgba(0,150,200,60);background:transparent;")

    def _set_state(self, state):
        self._state = state
        self.main_arc.set_state(state)
        self._vc_wave_left.set_active(state == "listening")
        self._vc_wave_right.set_active(state == "listening")
        self.waveform.set_active(state == "listening")
        self.equalizer.set_active(state == "listening" or state == "responding")
        if state == "listening":
            self._state_lbl.setText("LISTENING")
            self._state_lbl.setStyleSheet("color:#00FF88;background:transparent;")
            self._state_dot.setStyleSheet("color:#00FF88;background:transparent;")
            self._state_sub.setText("Speak now...")
            self._proc_lbl.setText("LISTENING")
            self._listen_lbl.setStyleSheet("color:#00FF88;background:transparent;")
            self._speak_lbl.setStyleSheet("color:rgba(0,212,255,200);background:transparent;")
            self._vc_status.setText("LISTENING...")
            self._vc_prompt.setText("I'm listening. Go ahead.")
        elif state == "responding":
            self._state_lbl.setText("PROCESSING")
            self._state_lbl.setStyleSheet("color:#00D4FF;background:transparent;")
            self._state_dot.setStyleSheet("color:#00D4FF;background:transparent;")
            self._state_sub.setText("Jarvis is thinking...")
            self._proc_lbl.setText("PROCESSING")
            self._vc_status.setText("PROCESSING...")
        else:
            self._state_lbl.setText("IDLE")
            self._state_lbl.setStyleSheet("color:#00D4FF;background:transparent;")
            self._state_dot.setStyleSheet("color:#00D4FF;background:transparent;")
            self._state_sub.setText("Tap SPEAK to begin...")
            self._proc_lbl.setText("STANDBY")
            self._vc_status.setText("Idle...")
            self._listen_lbl.setStyleSheet("color:rgba(0,212,255,200);background:transparent;")
            self._speak_lbl.setStyleSheet("color:rgba(0,212,255,200);background:transparent;")

    def _toggle_mute(self):
        if self._muted.is_set():
            self._muted.clear()
            if self._mute_btn:
                self._mute_btn.setText("🔇")
                self._mute_btn.setStyleSheet(
                    "QPushButton{background:rgba(0,212,255,12);color:rgba(0,200,220,160);"
                    "border:2px solid rgba(0,180,220,100);border-radius:26px;}"
                    "QPushButton:hover{background:rgba(0,212,255,30);}")
        else:
            self._muted.set()
            if self._mute_btn:
                self._mute_btn.setText("🔊")
                self._mute_btn.setStyleSheet(
                    "QPushButton{background:rgba(255,180,0,30);color:#FFB800;"
                    "border:2px solid rgba(255,180,0,160);border-radius:26px;}"
                    "QPushButton:hover{background:rgba(255,180,0,50);}")

    def _start_listening(self):
        if self.voice_worker and self.voice_worker.isRunning():
            return
        self._auto_listen = True
        self._set_state("listening")
        if self._speak_btn:
            self._speak_btn.setEnabled(False)
        self.voice_worker = VoiceWorker()
        self.voice_worker.text_received.connect(self._on_speech)
        self.voice_worker.error.connect(self._on_err)
        self.voice_worker.level_update.connect(self._mic_ring.set_value)
        self.voice_worker.start()

    def _on_speech(self, text):
        self._last_user = text
        self.transcript_lbl.setText(f"You: {text}")
        self._set_state("responding")
        self.conv_history.append(f"User: {text}")
        self._sq = queue.Queue()
        self._tts_stop = threading.Event()
        self.tts_worker = TTSWorker(self._sq, self._tts_stop, self._muted)
        self.tts_worker.finished_speaking.connect(self._on_tts_done)
        self.tts_worker.start()
        self.llm_worker = VoiceLLMWorker(text, list(self.conv_history),
                                         use_news=needs_realtime(text.lower()))
        self.llm_worker.sentence_ready.connect(self._on_sentence)
        self.llm_worker.finished.connect(self._on_llm_done)
        self.llm_worker.error.connect(lambda e: self.transcript_lbl.setText(f"Error: {e}"))
        self.llm_worker.start()

    def _on_sentence(self, s):
        if self._sq:
            self._sq.put(s)
        cur = self.transcript_lbl.text()
        if cur.startswith("You:"):
            self.transcript_lbl.setText(f"Jarvis: {s}")
        else:
            self.transcript_lbl.setText((cur + " " + s)[-120:])

    def _on_llm_done(self, resp):
        self._last_jarvis = resp
        self.conv_history.append(f"Jarvis: {resp}")
        if self._sq:
            self._sq.put(None)
        self.transcript_ready.emit(self._last_user, resp)

    def _on_tts_done(self):
        self._set_state("idle")
        if self._speak_btn:
            self._speak_btn.setEnabled(True)
        if self._auto_listen and self.isVisible():
            QTimer.singleShot(250, self._start_listening)

    def _on_err(self, err):
        self.transcript_lbl.setText(f"Error: {err}")
        self._set_state("idle")
        if self._speak_btn:
            self._speak_btn.setEnabled(True)
        if self._auto_listen and self.isVisible():
            QTimer.singleShot(2000, self._start_listening)

    def _stop_all(self):
        self._auto_listen = False
        if self.voice_worker and self.voice_worker.isRunning():
            self.voice_worker.stop_recording()
        if self._tts_stop:
            self._tts_stop.set()
        self._set_state("idle")
        if self._speak_btn:
            self._speak_btn.setEnabled(True)

    def closeEvent(self, event):
        self._auto_listen = False
        self._stop_all()
        event.accept()

# ═══════════════════════════════════════════════════════════
#  STARTUP SCREEN
# ═══════════════════════════════════════════════════════════
BOOT_ITEMS = [
    "Initializing JARVIS OS",
    "Loading Core Modules",
    "Establishing Connections",
    "Calibrating Systems",
    "Launching Interface",
    "System Ready",
]

SYSTEM_CHECKS = [
    "POWER SYSTEMS",
    "MEMORY MODULES",
    "NETWORK CONNECTION",
    "AUDIO SYSTEMS",
    "VISUAL INTERFACE",
    "AI CORE",
    "DATABASE",
    "SECURITY PROTOCOLS",
]

class StartupScreen(QWidget):
    boot_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color:#02060E;")
        import time as _time
        self._t = 0.0
        self._last_ts = _time.perf_counter()
        self._arc_angle = 0.0
        self._arc_angle2 = 0.0
        self._arc_pulse = 0.0
        self._boot_idx = 0
        self._boot_pct = 0.0
        self._boot_done = [False] * len(BOOT_ITEMS)
        self._checks_done = [False] * len(SYSTEM_CHECKS)
        self._overall_pct = 0.0
        self._show_welcome = False
        self._welcome_alpha = 0.0
        self._finishing = False
        self._fade_out = 0.0
        self._spoken = False
        self._mem_pct = 0.0
        self._cpu_pct = 0.0
        self._net_pct = 0.0
        self._pwr_pct = 0.0
        self._model_ready = False   # set by JarvisMainWindow when warmup completes
        self._anim_done = False     # set when animation wants to finish

        self._hb_noise = [0.0] * 80
        self._dot_brightness = [i % 3 == 0 for i in range(24)]
        self._world_dots = [
            (0.12, 0.4), (0.18, 0.35), (0.14, 0.55), (0.22, 0.6), (0.30, 0.5), (0.28, 0.35),
            (0.38, 0.38), (0.42, 0.5), (0.48, 0.4), (0.50, 0.55), (0.55, 0.45), (0.58, 0.35),
            (0.62, 0.5), (0.65, 0.40), (0.70, 0.45), (0.72, 0.35), (0.78, 0.5), (0.82, 0.42),
            (0.85, 0.55), (0.90, 0.48), (0.92, 0.38), (0.45, 0.70), (0.48, 0.75), (0.52, 0.72),
        ]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(1000 // 30)

    def _step(self):
        import time as _time
        now_ts = _time.perf_counter()
        dt = min(now_ts - self._last_ts, 0.05)
        self._last_ts = now_ts
        self._t += dt
        t = self._t
        self._arc_angle = (self._arc_angle + 60 * dt) % 360
        self._arc_angle2 = (self._arc_angle2 - 38 * dt) % 360
        self._arc_pulse = (self._arc_pulse + 180 * dt) % 360
        self._mem_pct = min(72, self._mem_pct + 80 * dt)
        self._cpu_pct = min(63, self._cpu_pct + 70 * dt)
        self._net_pct = min(100, self._net_pct + 110 * dt)
        self._pwr_pct = min(100, self._pwr_pct + 120 * dt)
        total_items = len(BOOT_ITEMS)
        total_duration = total_items * 0.55
        elapsed_for_boot = max(0, t - 0.3)
        item_t = elapsed_for_boot / 0.55
        new_boot_idx = min(int(item_t), total_items)
        for i in range(new_boot_idx):
            if not self._boot_done[i]:
                self._boot_done[i] = True
                check_idx = min(i, len(SYSTEM_CHECKS) - 1)
                self._checks_done[check_idx] = True
        if new_boot_idx < total_items:
            frac = item_t - int(item_t)
            self._boot_pct = frac * 100
        else:
            self._boot_pct = 100
        if new_boot_idx >= total_items:
            for i in range(len(SYSTEM_CHECKS)):
                self._checks_done[i] = True
        self._overall_pct = min(100, (elapsed_for_boot / total_duration) * 100)
        all_done = all(self._boot_done)
        if all_done and not self._show_welcome:
            self._show_welcome = True
        if self._show_welcome:
            self._welcome_alpha = min(1.0, self._welcome_alpha + 1.5 * dt)
        if self._show_welcome and not self._spoken and self._welcome_alpha > 0.8:
            self._spoken = True
            def _speak():
                path = speak_with_piper(f"Welcome back, {USER_NAME}. All systems are online.") or \
                       _speak_system_to_file(f"Welcome back, {USER_NAME}. All systems are online.")
                if path:
                    _play_audio(path)
            threading.Thread(target=_speak, daemon=True).start()
            QTimer.singleShot(800, self._begin_finish)
        if self._finishing:
            self._fade_out = min(1.0, self._fade_out + 2.5 * dt)
        self.update()

    def notify_model_ready(self):
        """Called by JarvisMainWindow when the warmup completes."""
        self._model_ready = True
        # If the animation already finished waiting, fire boot_complete now
        if self._anim_done:
            self.boot_complete.emit()

    def _begin_finish(self):
        self._finishing = True
        self._anim_done = True
        if self._model_ready:
            QTimer.singleShot(500, self.boot_complete.emit)
        else:
            # Poll every 200ms until model is ready, then fire
            self._wait_for_model()

    def _wait_for_model(self):
        if self._model_ready:
            QTimer.singleShot(300, self.boot_complete.emit)
        else:
            QTimer.singleShot(200, self._wait_for_model)

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), C_BG)
            p.setPen(QPen(QColor(0, 212, 255, 160), 1))
            p.drawLine(0, 34, w, 34)
            p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QPen(QColor(0, 212, 255, 220)))
            title = "JARVIS SYSTEM STARTUP"
            tw = p.fontMetrics().horizontalAdvance(title)
            p.drawText(int(cx - tw / 2), 24, title)
            p.setPen(QPen(QColor(0, 100, 150, 100), 1))
            p.drawLine(0, h - 28, w, h - 28)
            p.setFont(_mono(7))
            p.setPen(QPen(QColor(0, 150, 200, 120)))
            p.drawText(14, h - 12, f"JARVIS OS {OS_VERSION}")
            ver = f"BUILD {datetime.now().strftime('%Y.%m.%d')}"
            vw = p.fontMetrics().horizontalAdvance(ver)
            p.drawText(int(cx - vw / 2), h - 12, ver)
            if self._anim_done and not self._model_ready:
                status = "LOADING AI MODEL..."
                p.setPen(QPen(QColor(255, 180, 0, 200)))
            elif self._show_welcome:
                status = "ONLINE"
                p.setPen(QPen(QColor(0, 150, 200, 120)))
            else:
                status = "INITIALIZING"
                p.setPen(QPen(QColor(0, 150, 200, 120)))
            p.drawText(w - 200, h - 12, f"STATUS: {status}")
            lx, ly = 24, 50
            lw = 260
            p.setFont(QFont("Courier New", 22, QFont.Weight.Bold))
            p.setPen(QPen(QColor(0, 212, 255, 230)))
            p.drawText(lx, ly + 28, "J.A.R.V.I.S")
            p.setFont(_mono(7))
            p.setPen(QPen(QColor(0, 150, 200, 160)))
            p.drawText(lx, ly + 44, "JUST A RATHER VERY")
            p.drawText(lx, ly + 57, "INTELLIGENT SYSTEM")
            box_y = ly + 70
            self._draw_panel_box(p, lx - 4, box_y, lw, 230)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(lx + 4, box_y + 18, "SYSTEM STATUS")
            p.setPen(QPen(QColor(0, 150, 200, 80), 0.5))
            p.drawLine(lx, box_y + 24, lx + lw - 8, box_y + 24)
            for i, chk in enumerate(SYSTEM_CHECKS):
                iy = box_y + 36 + i * 23
                done = self._checks_done[i]
                p.setFont(_mono(8))
                p.setPen(QPen(QColor(0, 170, 200, 170 if done else 80)))
                p.drawText(lx + 4, iy, chk)
                status = "OK"
                sc = QColor(0, 255, 136, 200) if done else QColor(0, 150, 200, 80)
                p.setPen(QPen(sc))
                p.setFont(_mono(8, True))
                sw = p.fontMetrics().horizontalAdvance(status)
                p.drawText(lx + lw - sw - 10, iy, status)
            diag_y = box_y + 240
            self._draw_panel_box(p, lx - 4, diag_y, lw, 120)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(lx + 4, diag_y + 18, "DIAGNOSTICS")
            self._draw_heartbeat(p, lx + 4, diag_y + 30, lw - 14, 28)
            p.setFont(_mono(7))
            p.setPen(QPen(QColor(0, 255, 136, 180)))
            p.drawText(lx + 4, diag_y + 72, "All systems operational  ✓")
            p.setPen(QPen(QColor(0, 150, 200, 120)))
            p.drawText(lx + 4, diag_y + 87, "Diagnostics complete")
            pbar_x = lx + 4
            pbar_y = diag_y + 95
            pbar_w = lw - 14
            p.setBrush(QBrush(QColor(0, 50, 80, 80)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(pbar_x, pbar_y, pbar_w, 10)
            filled = int(pbar_w * self._overall_pct / 100)
            if filled > 0:
                g = QLinearGradient(pbar_x, 0, pbar_x + pbar_w, 0)
                g.setColorAt(0, QColor(0, 140, 200, 200))
                g.setColorAt(1, QColor(0, 212, 255, 255))
                p.setBrush(QBrush(g))
                p.drawRect(pbar_x, pbar_y, filled, 10)
            p.setFont(_mono(7, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(pbar_x + pbar_w - 28, pbar_y + 9, f"{int(self._overall_pct)}%")
            boot_y = diag_y + 128
            self._draw_panel_box(p, lx - 4, boot_y, lw, 30 + len(BOOT_ITEMS) * 22)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(lx + 4, boot_y + 18, "BOOT SEQUENCE")
            for i, item in enumerate(BOOT_ITEMS):
                iy = boot_y + 32 + i * 22
                done = self._boot_done[i]
                p.setFont(_mono(8))
                p.setPen(QPen(QColor(0, 150, 200, 120)))
                p.drawText(lx + 4, iy, ">")
                p.setPen(QPen(QColor(0, 190, 220, 170 if done else 80)))
                p.drawText(lx + 16, iy, item)
                if done:
                    p.setPen(QPen(QColor(0, 255, 136, 200)))
                    p.setFont(_mono(8, True))
                    p.drawText(lx + lw - 68, iy, "COMPLETE")
            rw = 230
            rx = w - rw - 24
            info_y = 50
            self._draw_panel_box(p, rx, info_y, rw, 155)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(rx + 8, info_y + 18, "SYSTEM INFORMATION")
            info_rows = [
                ("VERSION", OS_VERSION),
                ("BUILD", datetime.now().strftime("%Y.%m.%d")),
                ("UPTIME", "00:00:08"),
                ("USER", USER_NAME),
                ("STATUS", "ONLINE" if self._show_welcome else "BOOT"),
            ]
            for i, (k, v) in enumerate(info_rows):
                iy = info_y + 34 + i * 22
                p.setFont(_mono(8))
                p.setPen(QPen(QColor(0, 150, 200, 140)))
                p.drawText(rx + 8, iy, k)
                col = QColor(0, 255, 136, 220) if k == "STATUS" and self._show_welcome else QColor(0, 212, 255, 200)
                p.setPen(QPen(col))
                p.setFont(_mono(8, True))
                vw2 = p.fontMetrics().horizontalAdvance(v)
                p.drawText(rx + rw - vw2 - 10, iy, v)
            mem_y = info_y + 165
            self._draw_panel_box(p, rx, mem_y, rw, 105)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(rx + 8, mem_y + 18, "MEMORY USAGE")
            mcc_x = rx + rw // 2
            mcc_y = mem_y + 65
            self._draw_donut(p, mcc_x, mcc_y, 32, self._mem_pct / 100, C_CYAN)
            p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
            p.setPen(QPen(C_CYAN))
            txt = f"{int(self._mem_pct)}%"
            tw2 = p.fontMetrics().horizontalAdvance(txt)
            p.drawText(int(mcc_x - tw2 / 2), mcc_y + 5, txt)
            p.setFont(_mono(7))
            p.setPen(QPen(QColor(0, 150, 200, 130)))
            sub = f"{self._mem_pct * 0.08:.1f} GB / 8.0 GB"
            sw2 = p.fontMetrics().horizontalAdvance(sub)
            p.drawText(int(mcc_x - sw2 / 2), mcc_y + 20, sub)
            proc_y = mem_y + 115
            self._draw_panel_box(p, rx, proc_y, rw, 70)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(rx + 8, proc_y + 18, "PROCESSOR")
            self._draw_sparkline(p, rx + 8, proc_y + 26, rw - 16, 28)
            pct_str = f"{int(self._cpu_pct)}%"
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 200)))
            pw = p.fontMetrics().horizontalAdvance(pct_str)
            p.drawText(rx + rw - pw - 10, proc_y + 18, pct_str)
            net_y = proc_y + 80
            self._draw_panel_box(p, rx, net_y, rw, 80)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(rx + 8, net_y + 18, "NETWORK")
            self._draw_world_dots(p, rx + 8, net_y + 24, rw - 16, 38)
            p.setFont(_mono(7))
            p.setPen(QPen(QColor(0, 150, 200, 130)))
            p.drawText(rx + 8, net_y + 68, "GLOBAL CONNECTIVITY")
            p.setFont(_mono(7, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(rx + rw - 36, net_y + 68, f"{int(self._net_pct)}%")
            pwr_y = net_y + 90
            self._draw_panel_box(p, rx, pwr_y, rw, 70)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 180)))
            p.drawText(rx + 8, pwr_y + 18, "POWER LEVEL")
            seg_count = 20
            seg_filled = int(seg_count * self._pwr_pct / 100)
            seg_x = rx + 8
            seg_y = pwr_y + 26
            seg_w = (rw - 20) // seg_count - 1
            for s in range(seg_count):
                col2 = QColor(0, 212, 255, 200) if s < seg_filled else QColor(0, 60, 100, 60)
                p.setBrush(QBrush(col2))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(seg_x + s * (seg_w + 1), seg_y, seg_w, 14)
            p.setFont(_mono(8, True))
            p.setPen(QPen(QColor(0, 212, 255, 200)))
            p.drawText(rx + rw - 60, pwr_y + 56, f"{int(self._pwr_pct)}%  OPTIMAL")
            arc_size = min(w - lw - rw - 80, h - 160)
            arc_size = max(arc_size, 200)
            self._draw_arc_reactor_custom(p, cx, cy, arc_size / 2 - 10)
            if self._show_welcome and self._welcome_alpha > 0:
                a = int(255 * self._welcome_alpha)
                box_x2 = int(cx - 280)
                box_y2 = int(h - 170)
                p.setBrush(QBrush(QColor(0, 10, 24, 180)))
                p.setPen(QPen(QColor(0, 212, 255, int(a * 0.5)), 1))
                p.drawRect(box_x2, box_y2, 560, 90)
                p.setFont(_mono(9))
                p.setPen(QPen(QColor(0, 170, 200, int(a * 0.7))))
                line1 = "SYSTEM INITIALIZATION COMPLETE"
                lw2 = p.fontMetrics().horizontalAdvance(line1)
                p.drawText(int(cx - lw2 / 2), box_y2 + 22, line1)
                p.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
                p.setPen(QPen(QColor(0, 212, 255, a)))
                line2 = f"WELCOME BACK, {USER_NAME}."
                lw3 = p.fontMetrics().horizontalAdvance(line2)
                p.drawText(int(cx - lw3 / 2), box_y2 + 52, line2)
                p.setFont(_mono(8))
                p.setPen(QPen(QColor(0, 150, 200, int(a * 0.6))))
                line3 = "JARVIS IS ONLINE AND AT YOUR SERVICE"
                lw4 = p.fontMetrics().horizontalAdvance(line3)
                p.drawText(int(cx - lw4 / 2), box_y2 + 70, line3)
                self._draw_waveform(p, box_x2, box_y2 + 78, 560, 14)
            if self._fade_out > 0:
                p.fillRect(self.rect(), QColor(2, 6, 14, int(255 * self._fade_out)))
        except Exception as _paint_err:
            pass

    def _draw_panel_box(self, p, x, y, w, h):
        p.setBrush(QBrush(QColor(0, 8, 22, 180)))
        p.setPen(QPen(QColor(0, 150, 200, 60), 0.8))
        p.drawRect(x, y, w, h)
        p.setPen(QPen(QColor(0, 212, 255, 90), 1.2))
        p.drawLine(x, y, x + w, y)

    def _draw_arc_reactor_custom(self, p, cx, cy, R):
        t = self._t
        bg = QRadialGradient(cx, cy, R)
        bg.setColorAt(0, QColor(0, 25, 50, 230))
        bg.setColorAt(0.7, QColor(0, 12, 28, 210))
        bg.setColorAt(1, QColor(0, 5, 15, 180))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), R, R)
        p.setPen(QPen(QColor(15, 30, 45, 240), R * 0.10))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R * 0.95, R * 0.95)
        n_segs = 32
        for i in range(n_segs):
            a_start = i * (360 / n_segs) + self._arc_angle * 0.2
            a_span = (360 / n_segs) - 3.5
            phase = ((i * (360 / n_segs) + self._arc_angle) % 360) / 360
            alpha = int(50 + 160 * abs(math.sin(math.pi * phase)))
            pen = QPen(QColor(0, alpha // 2, alpha, alpha), R * 0.065)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(QRectF(cx - R * 0.88, cy - R * 0.88, R * 1.76, R * 1.76), int(a_start * 16), int(a_span * 16))
        R3 = R * 0.70
        for gw, ga in [(R * 0.10, 10), (R * 0.06, 25), (R * 0.025, 80), (R * 0.012, 200)]:
            p.setPen(QPen(QColor(0, 180, 255, ga), gw))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), R3, R3)
        n_ch = 20
        for i in range(n_ch):
            a_start = i * (360 / n_ch) + self._arc_angle
            a_span = 7
            bright = (i % 3 == 0)
            pen = QPen(QColor(200, 235, 255, 220 if bright else 70), R * 0.020 if bright else R * 0.010)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(QRectF(cx - R3, cy - R3, R3 * 2, R3 * 2), int(a_start * 16), int(a_span * 16))
        R2 = R * 0.82
        for i in range(48):
            a = math.radians(i * 7.5 + self._arc_angle2 * 0.15)
            ca, sa = math.cos(a), math.sin(a)
            is_major = (i % 4 == 0)
            r0 = R2 - R * (0.065 if is_major else 0.032)
            r1 = R2
            pen = QPen(QColor(0, 200, 255, 160 if is_major else 50), 1.3 if is_major else 0.6)
            p.setPen(pen)
            p.drawLine(QPointF(cx + ca * r0, cy + sa * r0), QPointF(cx + ca * r1, cy + sa * r1))
        for rf, ao, pw_f, ns, ss in [
            (0.54, self._arc_angle, 0.020, 10, 16),
            (0.38, self._arc_angle2, 0.014, 8, 22),
        ]:
            ri = R * rf
            for i in range(ns):
                deg = ao + i * (360 / ns)
                pen = QPen(C_CYAN, R * pw_f)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawArc(QRectF(cx - ri, cy - ri, ri * 2, ri * 2), int(deg * 16), int(ss * 16))
        for rf, a in [(0.48, 40), (0.33, 25)]:
            ri = R * rf
            p.setPen(QPen(QColor(0, 160, 210, a), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), ri, ri)
        pulse_s = 0.72 + 0.28 * math.sin(math.radians(self._arc_pulse))
        cg = QRadialGradient(cx, cy, R * 0.28 * pulse_s)
        cg.setColorAt(0, QColor(220, 245, 255, int(210 * pulse_s)))
        cg.setColorAt(0.18, QColor(0, 200, 255, int(180 * pulse_s)))
        cg.setColorAt(0.5, QColor(0, 140, 220, int(70 * pulse_s)))
        cg.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(cg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), R * 0.28 * pulse_s, R * 0.28 * pulse_s)
        p.setBrush(QBrush(QColor(240, 250, 255, 255)))
        p.setPen(QPen(C_CYAN, 1.5))
        p.drawEllipse(QPointF(cx, cy), max(3, R * 0.035), max(3, R * 0.035))

    def _draw_donut(self, p, cx, cy, R, frac, color):
        p.setPen(QPen(QColor(0, 40, 70, 120), R * 0.35))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R, R)
        p.setPen(QPen(color, R * 0.32))
        p.drawArc(QRectF(cx - R, cy - R, R * 2, R * 2), int(90 * 16), int(-frac * 360 * 16))

    def _draw_heartbeat(self, p, x, y, w, h):
        p.setPen(QPen(C_CYAN, 1.2))
        t = self._t
        pts = []
        n = 80
        for i in range(n):
            fx = i / (n - 1)
            phase = (fx * 4 + t * 1.5) % 1.0
            if 0.3 < phase < 0.5:
                fy = 0.5 + math.sin((phase - 0.3) / 0.2 * math.pi) * 0.9
            else:
                fy = 0.5 + self._hb_noise[i]
            pts.append(QPointF(x + fx * w, y + (1 - fy) * h))
        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

    def _draw_sparkline(self, p, x, y, w, h):
        p.setPen(QPen(C_CYAN2, 1))
        t = self._t
        pts = []
        n = 50
        for i in range(n):
            fx = i / (n - 1)
            fy = 0.5 + 0.4 * math.sin((fx * 6 + t * 0.8) * math.pi) * math.cos(fx * 3.14)
            pts.append(QPointF(x + fx * w, y + (1 - fy) * h))
        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

    def _draw_world_dots(self, p, x, y, w, h):
        p.setPen(Qt.PenStyle.NoPen)
        for i, (fx, fy) in enumerate(self._world_dots):
            bright = self._dot_brightness[i % len(self._dot_brightness)]
            col = QColor(0, 212, 255, 160 if bright else 60)
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(x + fx * w, y + fy * h), 1.5, 1.5)

    def _draw_waveform(self, p, x, y, w, h):
        t = self._t
        p.setPen(QPen(QColor(0, 212, 255, 120), 1))
        n = 100
        pts = []
        for i in range(n):
            fx = i / (n - 1)
            amp = 0.5 * math.sin(fx * 20 + t * 3) * math.sin(fx * 7 - t)
            pts.append(QPointF(x + fx * w, y + h / 2 + amp * h / 2))
        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

# ═══════════════════════════════════════════════════════════
#  HOLOGRAPHIC BACKGROUND
# ═══════════════════════════════════════════════════════════
class HoloBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._off = 0
        self._pt = 0
        self._sweep = 0.0
        self._particles = []
        for _ in range(PARTICLE_COUNT):
            self._particles.append({
                "x": random.uniform(0, 1),
                "y": random.uniform(0, 1),
                "vx": random.uniform(-0.0002, 0.0002),
                "vy": random.uniform(-0.0005, -0.0001),
                "life": random.uniform(0.3, 1.0),
                "decay": random.uniform(0.001, 0.003),
                "size": random.uniform(1, 2),
            })
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(1000 // 20)

    def _step(self):
        self._off = (self._off + 1) % 100
        self._pt = (self._pt + 1) % 360
        self._sweep = (self._sweep + 0.4) % 360
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] = max(0, p["life"] - p["decay"])
        self._particles = [p for p in self._particles if p["life"] > 0]
        while len(self._particles) < PARTICLE_COUNT:
            self._particles.append({
                "x": random.uniform(0, 1),
                "y": 1.0,
                "vx": random.uniform(-0.0002, 0.0002),
                "vy": random.uniform(-0.0005, -0.0001),
                "life": 1.0,
                "decay": random.uniform(0.001, 0.003),
                "size": random.uniform(1, 2),
            })
        self.update()

    def paintEvent(self, event):
        try:
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            step = 80
            pen = QPen()
            for gx in range(-(self._off % step), w + step, step):
                alpha = max(3, int(10 + 4 * math.sin(math.radians(self._pt + gx / 5))))
                pen.setColor(QColor(0, 160, 220, max(2, alpha)))
                pen.setWidthF(0.4)
                p.setPen(pen)
                p.drawLine(gx, 0, gx, h)
            for gy in range(0, h + step, step):
                alpha = max(3, int(10 + 4 * math.sin(math.radians(self._pt + gy / 5))))
                pen.setColor(QColor(0, 160, 220, max(2, alpha)))
                pen.setWidthF(0.4)
                p.setPen(pen)
                p.drawLine(0, gy, w, gy)
            vg = QRadialGradient(cx, cy, max(w, h) * 0.7)
            vg.setColorAt(0, QColor(0, 0, 0, 0))
            vg.setColorAt(0.65, QColor(0, 0, 0, 0))
            vg.setColorAt(1, QColor(0, 0, 12, 220))
            p.setBrush(QBrush(vg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(self.rect())
            p.setPen(Qt.PenStyle.NoPen)
            for pt in self._particles:
                a = int(120 * pt["life"])
                p.setBrush(QBrush(QColor(0, 180, 220, a)))
                p.drawEllipse(QPointF(pt["x"] * w, pt["y"] * h), pt["size"], pt["size"])
        except Exception as _paint_err:
            pass

# ═══════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════
class JarvisMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S  —  HOLOGRAPHIC INTERFACE  v5.1")
        self.setMinimumSize(1280, 820)
        self.resize(1540, 900)
        self.setStyleSheet("background-color:#02060E;")

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._bg = HoloBackground(self)
        self._bg.lower()
        self._bg.resize(self.size())

        self._startup = StartupScreen()
        self._startup.boot_complete.connect(self._on_boot_done)
        self._stack.addWidget(self._startup)

        self._dashboard = ChatDashboard()
        self._stack.addWidget(self._dashboard)
        self._stack.setCurrentWidget(self._startup)

        # Warm the model after boot without blocking the dashboard.
        self._warmup = ModelWarmupWorker()
        self._warmup.warmup_complete.connect(self._on_warmup_done)
        if MODEL_WARMUP_ENABLED:
            self._warmup.start()
        self._boot_done = False

    def _on_warmup_done(self):
        # Tell the startup screen the model is loaded — it will proceed to dashboard
        self._startup.notify_model_ready()
        # Also mark dashboard so it knows model is warm
        if hasattr(self, '_dashboard'):
            self._dashboard._model_ready = True

    def _on_boot_done(self):
        self._boot_done = True
        self._show_dashboard()

    def _show_dashboard(self):
        self._stack.setCurrentWidget(self._dashboard)
        self._dashboard.input.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg.resize(self.size())

    def closeEvent(self, event):
        self._dashboard.on_close()
        event.accept()

# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(2, 6, 14))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 212, 255))
    app.setPalette(palette)
    window = JarvisMainWindow()
    window.show()
    sys.exit(app.exec())
