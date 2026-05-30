"""
J.A.R.V.I.S  —  HOLOGRAPHIC AI INTERFACE  v3.0
Startup boot animation  →  HUD Chat Dashboard
All original logic (news, voice, TTS pipeline, warmup) preserved.
"""

import sys, os, json, requests, urllib.parse, threading, multiprocessing
import queue, subprocess, math, hashlib, random
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFrame, QSizePolicy,
    QListWidget, QListWidgetItem, QScrollArea, QStackedWidget,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPointF, QRectF,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QLinearGradient, QPalette,
    QPen, QRadialGradient, QConicalGradient, QFontDatabase
)

# ═══════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════
PARTICLE_COUNT   = 40
ANIMATION_FPS    = 60
MODEL_WARMUP_ENABLED = True
HISTORY_DIR  = os.path.expanduser("~/.jarvis_chats")
VOICE_CACHE  = os.path.expanduser("~/piper_voices/cache/")
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(VOICE_CACHE, exist_ok=True)
PIPER_VOICE_MODEL = os.path.expanduser(
    "~/piper_voices/en_GB-northern_english_male-medium.onnx")

C_CYAN   = QColor(0, 212, 255)
C_CYAN2  = QColor(0, 180, 220)
C_GOLD   = QColor(255, 180, 0)
C_GREEN  = QColor(0, 255, 136)
C_RED    = QColor(255, 59, 48)
C_BG     = QColor(1, 8, 16)
C_PANEL  = QColor(4, 18, 38)

# ═══════════════════════════════════════════════════════════
#  CHAT HISTORY STORAGE
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
#  SYSTEM PROMPT  (with live date/time injection)
# ═══════════════════════════════════════════════════════════
_PROMPT_CACHE = {"text": "", "ts": 0}

def build_system_prompt():
    """Rebuild at most once per 60 s to avoid datetime formatting overhead."""
    import time
    now_ts = time.time()
    if now_ts - _PROMPT_CACHE["ts"] < 60 and _PROMPT_CACHE["text"]:
        return _PROMPT_CACHE["text"]
    now = datetime.now()
    prompt = (
        f"You are Jarvis, a highly intelligent AI assistant. "
        f"Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}. "
        f"Always use this when asked about the date or time. "
        f"Be concise, confident, and slightly witty — keep answers SHORT unless detail is needed. "
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}
import xml.etree.ElementTree as ET
import re as _re

def _parse_rss(content, max_results=10):
    try:
        root = ET.fromstring(content)
        for elem in root.iter():
            if "}" in elem.tag: elem.tag = elem.tag.split("}", 1)[1]
        items = root.findall(".//item") or root.findall(".//entry")
        out = []
        for item in items[:max_results]:
            title = (item.findtext("title") or "").strip()
            title = title.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&#39;","'").replace("&quot;",'"')
            pubdate = (item.findtext("pubDate") or item.findtext("updated") or "").strip()
            desc = _re.sub(r"<[^>]+>", "", (item.findtext("description") or "").strip())[:150]
            if title: out.append((title, pubdate[:22], desc))
        return out
    except Exception: return []

def fetch_google_news_rss(query, max_results=10):
    encoded = urllib.parse.quote(query)
    for url in [
        f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en",
        f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en",
    ]:
        try:
            r = requests.get(url, headers=_HEADERS, timeout=7)
            if r.status_code == 200:
                items = _parse_rss(r.content, max_results)
                if items:
                    qwords = [w for w in query.lower().split() if len(w) > 2]
                    filtered = [i for i in items if any(w in i[0].lower() for w in qwords)] or items
                    lines = [f"REAL-TIME NEWS — '{query}':"]
                    for n,(t,d,desc) in enumerate(filtered,1):
                        lines.append(f"{n}. {t}" + (f"  [{d}]" if d else "") + (f"\n   → {desc}" if desc else ""))
                    return "\n".join(lines)
        except Exception: continue
    return ""

def fetch_bing_news_rss(query, max_results=8):
    try:
        r = requests.get(f"https://www.bing.com/news/search?q={urllib.parse.quote(query)}&format=rss",
                         headers=_HEADERS, timeout=7)
        if r.status_code == 200:
            items = _parse_rss(r.content, max_results)
            if items:
                qwords = [w for w in query.lower().split() if len(w) > 2]
                filtered = [i for i in items if any(w in i[0].lower() for w in qwords)] or items
                lines = [f"BING NEWS — '{query}':"]
                for n,(t,d,desc) in enumerate(filtered,1):
                    lines.append(f"{n}. {t}" + (f"  [{d}]" if d else ""))
                return "\n".join(lines)
    except Exception: pass
    return ""

def fetch_wikipedia_summary(query):
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ','_'))}",
            headers=_HEADERS, timeout=5)
        if r.status_code == 200:
            d = r.json(); extract = d.get("extract","")
            if extract and len(extract) > 80:
                return f"[Wikipedia — {d.get('title','')}] {extract[:500]}"
    except Exception: pass
    return ""

def fetch_context(query):
    results = {}
    def _g(): results["g"] = fetch_google_news_rss(query)
    def _b(): results["b"] = fetch_bing_news_rss(query)
    def _w(): results["w"] = fetch_wikipedia_summary(query)
    ts = [threading.Thread(target=f, daemon=True) for f in (_g,_b,_w)]
    for t in ts: t.start()
    for t in ts: t.join(timeout=6)
    return results.get("g") or results.get("b") or results.get("w") or ""

def needs_realtime(text):
    triggers = [
        "will there be","will it be","will there","going to be","will it rain","will it snow",
        "second season","season 2","season 3","new season","next season","renewed","cancelled","canceled",
        "upcoming games","new games","new releases","release date","any new","any upcoming",
        "when is","when will","latest on","recently","just released","just announced","new update",
        "coming out","come out","out yet","news","latest news","what's happening","what is happening",
        "current events","today in","update on","tell me about","what happened","recent","breaking",
        "fetch","search","find news","get news",
    ]
    return any(t in text.lower() for t in triggers)

# ═══════════════════════════════════════════════════════════
#  VOICE / TTS
# ═══════════════════════════════════════════════════════════
def _cache_key(text):
    return os.path.join(VOICE_CACHE, hashlib.md5(text.encode()).hexdigest() + ".wav")

def speak_with_piper(text):
    cache_file = _cache_key(text)
    if os.path.exists(cache_file): return cache_file
    try:
        import io, piper, wave
        if not os.path.exists(PIPER_VOICE_MODEL): return None
        voice = piper.PiperVoice.load(PIPER_VOICE_MODEL)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf: voice.synthesize_wav(text, wf)
        buf.seek(0)
        with open(cache_file, "wb") as f: f.write(buf.getvalue())
        return cache_file
    except Exception: return None

def _speak_system_to_file(text):
    try:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); tmp.close()
        if sys.platform == "linux":
            subprocess.run(["espeak","-v","en-US","-s","150","-w",tmp.name,text], check=False, timeout=15)
            return tmp.name
        elif sys.platform == "darwin":
            subprocess.run(["say","-v","Daniel","-r","150","-o",tmp.name,"--data-format=LEF32@22050",text], check=False, timeout=15)
            return tmp.name
    except Exception: pass
    return None

def _play_audio(filepath):
    if not filepath or not os.path.exists(filepath): return
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
        def _ollama():
            try:
                resp = requests.post("http://localhost:11434/api/generate",
                    json={"model":"llama3.2:3b","prompt":f"{build_system_prompt()}\n\nUser: Hello\nJarvis:",
                          "stream":True,"options":{"num_predict":20,"num_ctx":1024,"num_thread":4}},
                    timeout=60, stream=True)
                for line in resp.iter_lines():
                    if line and json.loads(line).get("done"): break
            except Exception: pass
        def _ping():
            try: requests.get("http://localhost:11434/api/tags", timeout=5)
            except Exception: pass
        t1=threading.Thread(target=_ollama,daemon=True); t2=threading.Thread(target=_ping,daemon=True)
        t1.start(); t2.start(); t1.join(); t2.join(timeout=5)
        self.warmup_complete.emit()

class JarvisWorker(QThread):
    token_received = pyqtSignal(str)
    finished       = pyqtSignal(str)
    error          = pyqtSignal(str)
    def __init__(self, prompt, history, use_news=False):
        super().__init__(); self.prompt=prompt; self.history=history; self.use_news=use_news
    def run(self):
        if not self.use_news:
            self._run_llm(self.prompt); return
        ctx_holder={}
        def _fetch(): ctx_holder["c"] = fetch_context(self.prompt)
        t=threading.Thread(target=_fetch,daemon=True); t.start(); t.join(timeout=6)
        ctx = ctx_holder.get("c","")
        if ctx:
            aug = (f"REAL-TIME DATA fetched right now:\n{ctx}\n\n"
                   f"User question: {self.prompt}\n\n"
                   f"Answer using ONLY the data above. Quote specific headlines. "
                   f"Do NOT use training data or guess. If data doesn't cover it, say so.")
        else:
            aug = (f"The user asked: {self.prompt}\n\n"
                   f"A live news search returned NO results. "
                   f"Tell the user honestly you couldn't find current info and suggest checking a news site.")
        self._run_llm(aug)
    def _run_llm(self, aug):
        # Keep only last 6 exchanges (12 lines) to minimise prompt tokens
        trimmed = self.history[:-1]
        if len(trimmed) > 12:
            trimmed = trimmed[-12:]
        history_text = "\n".join(trimmed)
        full_prompt = f"{build_system_prompt()}\n\n{history_text}\nUser: {aug}\nJarvis:"
        try:
            resp = requests.post("http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {
                        "num_ctx":     1024,   # smaller context = faster TTFT
                        "num_predict": 400,    # cap output length — prevents rambling
                        "temperature": 0.7,
                        "top_p":       0.9,
                        "top_k":       40,
                        "repeat_penalty": 1.1,
                        "num_thread":  4,      # pin to 4 threads — avoids core thrashing
                    }
                }, timeout=120, stream=True)
            full=""
            for line in resp.iter_lines():
                if line:
                    chunk=json.loads(line); text=chunk.get("response","")
                    if text: self.token_received.emit(text); full+=text
                    if chunk.get("done"): break
            self.finished.emit(full.strip())
        except Exception as e: self.error.emit(str(e))

class VoiceWorker(QThread):
    text_received = pyqtSignal(str)
    error         = pyqtSignal(str)
    def __init__(self):
        super().__init__(); self._stop=threading.Event(); self._frames=[]; self.RATE=16000
    def stop_recording(self): self._stop.set()
    def run(self):
        try:
            import sounddevice as sd, speech_recognition as sr, numpy as np, io, wave
            self._frames=[]; self._stop.clear()
            def cb(indata,frames,time,status):
                if not self._stop.is_set(): self._frames.append(indata.copy())
            with sd.InputStream(samplerate=self.RATE,channels=1,dtype='int16',callback=cb):
                self._stop.wait(timeout=30)
            if not self._frames: self.error.emit("No audio recorded."); return
            audio=np.concatenate(self._frames,axis=0)
            buf=io.BytesIO()
            with wave.open(buf,'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(self.RATE); wf.writeframes(audio.tobytes())
            buf.seek(0)
            rec=sr.Recognizer()
            with sr.AudioFile(buf) as src: aud=rec.record(src)
            self.text_received.emit(rec.recognize_google(aud))
        except ImportError as e: self.error.emit(f"Missing library: {e}")
        except Exception as e:   self.error.emit(str(e))

class TTSWorker(QThread):
    finished_speaking = pyqtSignal()
    def __init__(self, sentence_queue, stop_event):
        super().__init__(); self.sq=sentence_queue; self.stop=stop_event; self._aq=queue.Queue()
    def run(self):
        def synth():
            while not self.stop.is_set():
                try:
                    s=self.sq.get(timeout=0.2)
                    if s is None: self._aq.put(None); break
                    path=speak_with_piper(s) or _speak_system_to_file(s)
                    if path: self._aq.put(path)
                except queue.Empty: continue
        st=threading.Thread(target=synth,daemon=True); st.start()
        while not self.stop.is_set():
            try:
                p=self._aq.get(timeout=0.3)
                if p is None: break
                _play_audio(p)
            except queue.Empty: continue
        st.join(timeout=5); self.finished_speaking.emit()

class VoiceLLMWorker(QThread):
    sentence_ready = pyqtSignal(str)
    finished       = pyqtSignal(str)
    error          = pyqtSignal(str)
    def __init__(self, prompt, history, use_news=False):
        super().__init__(); self.prompt=prompt; self.history=history; self.use_news=use_news
    def run(self):
        import re
        ctx=""
        if self.use_news:
            h={}
            def _f(): h["c"]=fetch_context(self.prompt)
            t=threading.Thread(target=_f,daemon=True); t.start(); t.join(timeout=6)
            ctx=h.get("c","")
        aug = (f"REAL-TIME DATA:\n{ctx}\n\nQuestion: {self.prompt}\n\nAnswer using only the data above." if ctx
               else f"The user asked: {self.prompt}\nA live search returned no results. Be honest about it.")
        trimmed_h = self.history[:-1]
        if len(trimmed_h) > 12: trimmed_h = trimmed_h[-12:]
        history_text="\n".join(trimmed_h)
        full_prompt=f"{build_system_prompt()}\n\n{history_text}\nUser: {aug}\nJarvis:"
        try:
            resp=requests.post("http://localhost:11434/api/generate",
                json={"model":"llama3.2:3b","prompt":full_prompt,"stream":True,
                      "options":{"num_ctx":1024,"num_predict":300,"temperature":0.7,
                                 "top_p":0.9,"top_k":40,"repeat_penalty":1.1,"num_thread":4}},
                timeout=120, stream=True)
            full=""; buf=""
            for line in resp.iter_lines():
                if line:
                    chunk=json.loads(line); text=chunk.get("response","")
                    if text:
                        full+=text; buf+=text
                        parts=re.split(r'(?<=[.!?])\s+',buf)
                        for s in parts[:-1]:
                            s=s.strip()
                            if s: self.sentence_ready.emit(s)
                        buf=parts[-1]
                    if chunk.get("done"): break
            if buf.strip(): self.sentence_ready.emit(buf.strip())
            self.finished.emit(full.strip())
        except Exception as e: self.error.emit(str(e))

# ═══════════════════════════════════════════════════════════
#  SHARED PAINT HELPERS
# ═══════════════════════════════════════════════════════════
def draw_glowing_text(painter, text, x, y, font, color, glow_radius=8):
    """Draw text with a soft cyan glow halo."""
    painter.setFont(font)
    for r in range(glow_radius, 0, -2):
        alpha = int(30 * (glow_radius - r + 1) / glow_radius)
        gc = QColor(color.red(), color.green(), color.blue(), alpha)
        painter.setPen(QPen(gc))
        painter.drawText(x - r//2, y - r//2, text)
        painter.drawText(x + r//2, y - r//2, text)
        painter.drawText(x - r//2, y + r//2, text)
        painter.drawText(x + r//2, y + r//2, text)
    painter.setPen(QPen(color))
    painter.drawText(x, y, text)

# ═══════════════════════════════════════════════════════════
#  STARTUP SCREEN
# ═══════════════════════════════════════════════════════════
class StartupScreen(QWidget):
    """
    Full-screen JARVIS boot animation:
      - 3 concentric rotating rings (cyan + gold accent)
      - Radial tick marks like the reference image
      - Scanning sweep line
      - Boot text sequence
      - Particle burst
    Emits `boot_complete` after ~7 seconds.
    """
    boot_complete = pyqtSignal()

    BOOT_LINES = [
        "INITIALIZING CORE SYSTEMS...",
        "LOADING NEURAL MODULES...",
        "CALIBRATING SENSORS...",
        "ESTABLISHING SECURE LINK...",
        "RUNNING DIAGNOSTICS...",
        "ALL SYSTEMS NOMINAL",
        "J.A.R.V.I.S  ONLINE",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #010810;")
        self._angle      = 0.0
        self._angle2     = 0.0
        self._angle3     = 0.0
        self._sweep      = 0.0
        self._pulse      = 0.0
        self._progress   = 0.0
        self._tick       = 0
        self._boot_idx   = 0
        self._boot_alpha = [0.0] * len(self.BOOT_LINES)
        self._particles  = []
        self._done       = False
        self._fade_out   = 0.0

        # Spawn background particles
        self._spawn_particles(60)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(1000 // ANIMATION_FPS)

        # After 7.5 s emit boot_complete
        QTimer.singleShot(7500, self._finish)

    def _spawn_particles(self, n):
        for _ in range(n):
            self._particles.append({
                "x": random.uniform(0, 1),
                "y": random.uniform(0, 1),
                "vx": random.uniform(-0.0003, 0.0003),
                "vy": random.uniform(-0.0006, -0.0001),
                "life": random.uniform(0.3, 1.0),
                "decay": random.uniform(0.003, 0.008),
                "size": random.uniform(1, 3),
            })

    def _step(self):
        dt = 1.0 / ANIMATION_FPS
        self._angle  = (self._angle  + 60  * dt) % 360
        self._angle2 = (self._angle2 - 40  * dt) % 360
        self._angle3 = (self._angle3 + 25  * dt) % 360
        self._sweep  = (self._sweep  + 120 * dt) % 360
        self._pulse  = (self._pulse  + 180 * dt) % 360
        self._progress = min(1.0, self._progress + dt / 6.0)
        self._tick += 1

        # Advance boot text every ~0.9 s
        idx = int(self._tick / (ANIMATION_FPS * 0.9))
        if idx < len(self.BOOT_LINES):
            self._boot_idx = idx
            for i in range(idx + 1):
                self._boot_alpha[i] = min(1.0, self._boot_alpha[i] + 0.06)

        # Particles
        for p in self._particles:
            p["x"] += p["vx"]; p["y"] += p["vy"]
            p["life"] = max(0, p["life"] - p["decay"])
        self._particles = [p for p in self._particles if p["life"] > 0]
        while len(self._particles) < 60:
            self._particles.append({
                "x": random.uniform(0, 1), "y": 1.0,
                "vx": random.uniform(-0.0003, 0.0003),
                "vy": random.uniform(-0.0006, -0.0001),
                "life": 1.0, "decay": random.uniform(0.003, 0.008),
                "size": random.uniform(1, 3),
            })

        if self._done:
            self._fade_out = min(1.0, self._fade_out + 0.04)

        self.update()

    def _finish(self):
        self._done = True
        QTimer.singleShot(1200, self.boot_complete.emit)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), C_BG)

        # Grid
        pen = QPen(QColor(0, 212, 255, 8), 0.5)
        painter.setPen(pen)
        for gx in range(0, w, 50):
            painter.drawLine(gx, 0, gx, h)
        for gy in range(0, h, 50):
            painter.drawLine(0, gy, w, gy)

        # Particles
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            alpha = int(180 * p["life"])
            painter.setBrush(QBrush(QColor(0, 212, 255, alpha)))
            px, py = p["x"] * w, p["y"] * h
            painter.drawEllipse(QPointF(px, py), p["size"], p["size"])

        # Ring radii
        R1, R2, R3 = min(cx, cy) * 0.78, min(cx, cy) * 0.62, min(cx, cy) * 0.46

        # Outer glow rings (blurred by layering)
        for glow_r, radius in [(R1, R1), (R2, R2), (R3, R3)]:
            for width, alpha in [(12, 15), (6, 30), (2, 180)]:
                pen = QPen(QColor(0, 212, 255, alpha), width)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Ring 1 — outer, rotating arc segments (cyan)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(12):
            start_deg = self._angle + i * 30
            pen = QPen(C_CYAN, 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(
                int(cx - R1), int(cy - R1), int(R1 * 2), int(R1 * 2),
                int((start_deg) * 16), int(18 * 16)
            )

        # Ring 2 — middle, counter-rotating, gold accent arc
        for i in range(8):
            start_deg = self._angle2 + i * 45
            color = C_GOLD if i % 4 == 0 else C_CYAN2
            pen = QPen(color, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(
                int(cx - R2), int(cy - R2), int(R2 * 2), int(R2 * 2),
                int(start_deg * 16), int(30 * 16)
            )

        # Ring 3 — inner, slow rotation
        for i in range(6):
            start_deg = self._angle3 + i * 60
            pen = QPen(QColor(0, 212, 255, 200), 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(
                int(cx - R3), int(cy - R3), int(R3 * 2), int(R3 * 2),
                int(start_deg * 16), int(45 * 16)
            )

        # Radial tick marks (like the reference image)
        for i in range(72):
            angle_rad = math.radians(i * 5)
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            is_major = (i % 6 == 0)
            tick_len = 14 if is_major else 6
            r_start = R1 + 6
            r_end   = r_start + tick_len
            alpha   = 200 if is_major else 80
            pen = QPen(QColor(0, 212, 255, alpha), 1.5 if is_major else 0.8)
            painter.setPen(pen)
            painter.drawLine(
                QPointF(cx + cos_a * r_start, cy + sin_a * r_start),
                QPointF(cx + cos_a * r_end,   cy + sin_a * r_end)
            )

        # Sweep radar line
        sweep_rad = math.radians(self._sweep)
        grad = QConicalGradient(cx, cy, -self._sweep)
        grad.setColorAt(0.0, QColor(0, 212, 255, 0))
        grad.setColorAt(0.08, QColor(0, 212, 255, 80))
        grad.setColorAt(0.15, QColor(0, 212, 255, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), R1, R1)

        # Inner dark fill
        painter.setBrush(QBrush(QColor(1, 8, 20, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), R3 - 4, R3 - 4)

        # Pulsing core glow
        pulse = 0.7 + 0.3 * math.sin(math.radians(self._pulse))
        core_r = R3 * 0.35 * pulse
        core_grad = QRadialGradient(cx, cy, core_r * 3)
        core_grad.setColorAt(0,   QColor(0, 212, 255, int(120 * pulse)))
        core_grad.setColorAt(0.5, QColor(0, 212, 255, int(40  * pulse)))
        core_grad.setColorAt(1,   QColor(0, 212, 255, 0))
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r * 3, core_r * 3)

        # J.A.R.V.I.S  title
        font_big = QFont("Courier New", 26, QFont.Weight.Bold)
        fm = painter.fontMetrics()
        title = "J.A.R.V.I.S"
        painter.setFont(font_big)
        tw = painter.fontMetrics().horizontalAdvance(title)
        draw_glowing_text(painter, title, int(cx - tw/2), int(cy + 10), font_big, C_CYAN, glow_radius=12)

        # Progress arc (bottom of outer ring)
        prog_pen = QPen(C_GOLD, 4)
        prog_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(prog_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        span = int(self._progress * 270 * 16)
        painter.drawArc(
            int(cx - R1 - 20), int(cy - R1 - 20),
            int((R1 + 20) * 2), int((R1 + 20) * 2),
            int(225 * 16), -span
        )

        # Boot text — bottom area
        font_small = QFont("Courier New", 10)
        painter.setFont(font_small)
        line_h = 22
        text_y_start = int(cy + R1 + 40)
        for i, line in enumerate(self.BOOT_LINES):
            alpha = int(255 * self._boot_alpha[i])
            if alpha <= 0: continue
            color = C_GREEN if i == len(self.BOOT_LINES) - 1 else QColor(0, 212, 255, alpha)
            painter.setPen(QPen(color))
            lw = painter.fontMetrics().horizontalAdvance(line)
            painter.drawText(int(cx - lw / 2), text_y_start + i * line_h, line)

        # Fade-out overlay
        if self._fade_out > 0:
            painter.fillRect(self.rect(), QColor(1, 8, 16, int(255 * self._fade_out)))

# ═══════════════════════════════════════════════════════════
#  HUD WIDGETS
# ═══════════════════════════════════════════════════════════
class HUDArcReactor(QWidget):
    """Center arc reactor — bigger, more detailed, state-aware."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self._angle = 0.0; self._angle2 = 0.0; self._pulse = 0.0
        self._state = "idle"; self._energy = 0.0
        self._timer = QTimer(self); self._timer.timeout.connect(self._step)
        self._timer.start(1000 // ANIMATION_FPS)

    def set_state(self, state):
        self._state = state

    def _step(self):
        speed = 3.0 if self._state == "responding" else 1.5
        self._angle  = (self._angle  + speed * 1.0) % 360
        self._angle2 = (self._angle2 - speed * 0.7) % 360
        self._pulse  = (self._pulse  + 4.0) % 360
        if self._state == "responding":
            self._energy = min(1.0, self._energy + 0.05)
        else:
            self._energy = max(0.0, self._energy - 0.02)
        self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        R = min(cx, cy) - 10
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0,0,0,0))

        if self._state == "listening":
            core_c = C_GREEN
        elif self._state == "responding":
            core_c = QColor(0, 180, 255)
        else:
            core_c = C_CYAN

        # Glow rings
        for width, alpha in [(20, 8), (10, 20), (3, 100)]:
            pen = QPen(QColor(core_c.red(), core_c.green(), core_c.blue(), alpha), width)
            painter.setPen(pen); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), R * 0.9, R * 0.9)

        # Rotating arc segments — 3 rings
        rings = [
            (R * 0.88, self._angle,   3,  12, 20),
            (R * 0.70, self._angle2,  2,   8, 35),
            (R * 0.54, self._angle,   1.5, 6, 45),
        ]
        for radius, angle_start, pen_w, n_segs, seg_span in rings:
            for i in range(n_segs):
                deg = angle_start + i * (360 / n_segs)
                pen = QPen(core_c, pen_w)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen); painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawArc(
                    int(cx-radius), int(cy-radius), int(radius*2), int(radius*2),
                    int(deg*16), int(seg_span*16)
                )

        # Tick marks
        for i in range(48):
            a = math.radians(i * 7.5)
            ca, sa = math.cos(a), math.sin(a)
            is_m = (i % 4 == 0)
            r0 = R * 0.88 + 3; r1 = r0 + (10 if is_m else 5)
            pen = QPen(QColor(core_c.red(), core_c.green(), core_c.blue(), 180 if is_m else 70), 1)
            painter.setPen(pen)
            painter.drawLine(QPointF(cx+ca*r0, cy+sa*r0), QPointF(cx+ca*r1, cy+sa*r1))

        # Energy fill ring (responds to state)
        if self._energy > 0:
            pen = QPen(QColor(core_c.red(), core_c.green(), core_c.blue(), int(60 * self._energy)), 8)
            painter.setPen(pen); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), R * 0.70, R * 0.70)

        # Core pulse
        pulse_scale = 0.6 + 0.4 * math.sin(math.radians(self._pulse))
        core_r = R * 0.28 * pulse_scale
        cg = QRadialGradient(cx, cy, core_r * 3)
        cg.setColorAt(0,   QColor(core_c.red(), core_c.green(), core_c.blue(), int(140 * pulse_scale)))
        cg.setColorAt(0.5, QColor(core_c.red(), core_c.green(), core_c.blue(), int(50  * pulse_scale)))
        cg.setColorAt(1,   QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(cg)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), core_r * 3, core_r * 3)

        # Center dot
        painter.setBrush(QBrush(core_c)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 5, 5)


class HUDStatusBar(QWidget):
    """Top status bar: live clock, date, status indicator."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self._status = "SYSTEM ONLINE"
        self._status_color = "#00FF88"
        self._build()
        t = QTimer(self); t.timeout.connect(self._tick); t.start(1000)
        self._tick()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)

        self.time_label = QLabel()
        self.time_label.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #00D4FF; letter-spacing: 2px;")

        self.date_label = QLabel()
        self.date_label.setFont(QFont("Courier New", 9))
        self.date_label.setStyleSheet("color: rgba(0,212,255,160);")

        self.status_label = QLabel()
        self.status_label.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self.status_label.setStyleSheet(f"color: {self._status_color}; letter-spacing: 2px;")

        lay.addWidget(self.time_label)
        lay.addSpacing(12)
        lay.addWidget(self.date_label)
        lay.addStretch()
        lay.addWidget(self.status_label)

    def _tick(self):
        now = datetime.now()
        self.time_label.setText(now.strftime("%I:%M:%S %p"))
        self.date_label.setText(now.strftime("%A  ·  %B %d, %Y"))

    def set_status(self, text, color="#00FF88"):
        self._status_color = color
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(f"color: {color}; letter-spacing: 2px; font-weight: bold;")


class HUDTypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self._dots = [0.3, 0.3, 0.3]; self._step = 0
        self._timer = QTimer(self); self._timer.timeout.connect(self._anim)
        self.hide()
    def start(self): self.show(); self._timer.start(140)
    def stop(self):  self._timer.stop(); self.hide()
    def _anim(self):
        self._step = (self._step + 1) % 3
        for i in range(3): self._dots[i] = 1.0 if i == self._step else 0.3
        self.update()
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 4; gap = 14; x = 20; y = self.height() // 2
        for alpha in self._dots:
            p.setBrush(QBrush(QColor(0, 212, 255, int(200 * alpha))))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), r * alpha, r * alpha)
            x += r * 2 + gap


class HUDChatBubble(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.is_user = is_user; self._full = text; self._build(text)
    def _build(self, text):
        lay = QVBoxLayout(self); lay.setContentsMargins(4, 2, 4, 2); lay.setSpacing(2)
        meta = QHBoxLayout(); meta.setContentsMargins(10, 0, 10, 0)
        ts = QLabel(datetime.now().strftime("%H:%M"))
        ts.setFont(QFont("Courier New", 7))
        ts.setStyleSheet("color: rgba(0,212,255,70);")
        copy = QPushButton("⎘"); copy.setFixedSize(18, 14)
        copy.setStyleSheet("QPushButton{background:transparent;color:rgba(0,212,255,90);border:none;font-size:10px;}"
                           "QPushButton:hover{color:#00D4FF;}")
        copy.setCursor(Qt.CursorShape.PointingHandCursor)
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self._full))
        if self.is_user:
            meta.addStretch(); meta.addWidget(copy); meta.addWidget(ts)
        else:
            who = QLabel("JARVIS"); who.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            who.setStyleSheet("color: rgba(0,212,255,120); letter-spacing: 1px;")
            meta.addWidget(who); meta.addWidget(ts); meta.addWidget(copy); meta.addStretch()
        lay.addLayout(meta)
        row = QHBoxLayout(); row.setContentsMargins(0,0,0,0)
        self.label = QLabel(text); self.label.setWordWrap(True)
        self.label.setFont(QFont("Courier New", 10))
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.label.setMaximumWidth(680)
        if self.is_user:
            self.label.setStyleSheet("""
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(0,80,200,100), stop:1 rgba(0,30,140,140));
                color: #FFFFFF; border: 1.5px solid rgba(0,212,255,200);
                border-radius: 16px; padding: 10px 16px;""")
            row.addStretch(); row.addWidget(self.label)
        else:
            self.label.setStyleSheet("""
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(0,15,50,180), stop:1 rgba(0,30,80,140));
                color: #00D4FF; border: 1.5px solid rgba(0,212,255,130);
                border-radius: 16px; padding: 10px 16px;""")
            row.addWidget(self.label); row.addStretch()
        lay.addLayout(row)
    def append_text(self, t):
        self._full += t; self.label.setText(self._full)


class HUDSessionPanel(QWidget):
    """Left panel — collapsible chat session history."""
    chat_selected = pyqtSignal(str)
    chat_deleted  = pyqtSignal(str)
    new_chat      = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent); self._collapsed=False; self._all=[]
        self.setMaximumWidth(220); self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(4,4,4,4); lay.setSpacing(6)

        self.toggle = QPushButton("◀  SESSIONS")
        self.toggle.setFixedHeight(36)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setStyleSheet(self._btn_style(False))
        self.toggle.clicked.connect(self._toggle)
        lay.addWidget(self.toggle)

        self.panel = QWidget()
        self.panel.setStyleSheet("background:rgba(4,18,38,180); border:1px solid rgba(0,212,255,70); border-radius:6px;")
        pl = QVBoxLayout(self.panel); pl.setContentsMargins(8,8,8,8); pl.setSpacing(6)

        hdr = QLabel("SESSIONS"); hdr.setFont(QFont("Courier New",8,QFont.Weight.Bold))
        hdr.setStyleSheet("color:rgba(0,212,255,160); letter-spacing:2px; background:transparent; border:none;")
        pl.addWidget(hdr)

        self.search = QLineEdit(); self.search.setPlaceholderText("SEARCH...")
        self.search.setFixedHeight(26); self.search.setFont(QFont("Courier New",8))
        self.search.setStyleSheet("""QLineEdit{background:rgba(0,212,255,10);color:#00D4FF;
            border:1px solid rgba(0,212,255,70);border-radius:4px;padding:0 6px;}
            QLineEdit:focus{border-color:rgba(0,212,255,160);}""")
        self.search.textChanged.connect(self._filter)
        pl.addWidget(self.search)

        self.list = QListWidget()
        self.list.setStyleSheet("""QListWidget{background:rgba(0,8,22,120);border:1px solid rgba(0,212,255,40);border-radius:4px;outline:none;}
            QListWidget::item{color:rgba(0,212,255,160);font-family:'Courier New';font-size:9px;padding:5px 7px;border-radius:3px;margin:1px;}
            QListWidget::item:selected{background:rgba(0,212,255,30);color:#00D4FF;border:1px solid rgba(0,212,255,100);}
            QListWidget::item:hover{background:rgba(0,212,255,12);}""")
        self.list.itemClicked.connect(lambda i: self.chat_selected.emit(i.data(Qt.ItemDataRole.UserRole)))
        pl.addWidget(self.list)

        for label, sig, style in [
            ("＋  NEW",    self.new_chat,    "rgba(0,212,255,25);color:#00D4FF;border:1px solid rgba(0,212,255,80);"),
            ("⌫  DELETE", self._do_delete,  "rgba(255,59,48,15);color:#FF6B6B;border:1px solid rgba(255,59,48,60);"),
        ]:
            btn = QPushButton(label); btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton{{background:{style}border-radius:4px;font-size:9px;font-weight:bold;"
                              f"font-family:'Courier New';}}")
            if callable(sig): btn.clicked.connect(sig)
            else: btn.clicked.connect(sig.emit)
            pl.addWidget(btn)

        self.panel.hide()
        lay.addWidget(self.panel); lay.addStretch()

    def _btn_style(self, expanded):
        arrow = "◀" if expanded else "▶"
        return (f"QPushButton{{background:rgba(0,212,255,30);color:#00D4FF;"
                f"border:1.5px solid rgba(0,212,255,150);border-radius:6px;"
                f"font-family:'Courier New';font-size:10px;font-weight:bold;letter-spacing:2px;}}"
                f"QPushButton:hover{{background:rgba(0,212,255,55);}}")

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.panel.setVisible(not self._collapsed)
        self.toggle.setText("▶  SESSIONS" if self._collapsed else "◀  SESSIONS")

    def refresh(self):
        self.list.clear(); self._all=[]
        for fname in list_saved_chats():
            try:
                ts=fname.replace("chat_","").replace(".json","")
                dt=datetime.strptime(ts,"%Y%m%d_%H%M%S"); label=dt.strftime("%b %d  %H:%M")
            except: label=fname
            item=QListWidgetItem(label); item.setData(Qt.ItemDataRole.UserRole,fname)
            self._all.append((label.lower(),item)); self.list.addItem(item)

    def _filter(self, text):
        self.list.clear()
        for label,item in self._all:
            if text.lower() in label: self.list.addItem(item)

    def _do_delete(self):
        item=self.list.currentItem()
        if item: self.chat_deleted.emit(item.data(Qt.ItemDataRole.UserRole))


class HUDInfoPanel(QWidget):
    """Right panel — system status + quick actions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(200)
        self._build()
        t=QTimer(self); t.timeout.connect(self._refresh); t.start(2000)
        self._refresh()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(4,4,4,4); lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        hdr = QLabel("◈  SYSTEM"); hdr.setFont(QFont("Courier New",9,QFont.Weight.Bold))
        hdr.setStyleSheet("color:rgba(0,212,255,180); letter-spacing:2px;")
        lay.addWidget(hdr)

        frame = QFrame()
        frame.setStyleSheet("background:rgba(4,18,38,180); border:1px solid rgba(0,212,255,60); border-radius:6px;")
        fl = QVBoxLayout(frame); fl.setContentsMargins(10,10,10,10); fl.setSpacing(6)

        self.ollama_lbl = self._stat_label("● OLLAMA", "#00FF88")
        self.model_lbl  = self._stat_label("MODEL: llama3.2:3b", "rgba(0,212,255,150)")
        self.resp_lbl   = self._stat_label("RESPONSE: --", "rgba(0,212,255,120)")

        fl.addWidget(self.ollama_lbl)
        fl.addWidget(self.model_lbl)
        fl.addWidget(self.resp_lbl)
        lay.addWidget(frame)

        hdr2 = QLabel("◈  QUICK TIPS"); hdr2.setFont(QFont("Courier New",9,QFont.Weight.Bold))
        hdr2.setStyleSheet("color:rgba(0,212,255,180); letter-spacing:2px;")
        lay.addWidget(hdr2)

        tips_frame = QFrame()
        tips_frame.setStyleSheet("background:rgba(4,18,38,180); border:1px solid rgba(0,212,255,60); border-radius:6px;")
        tf = QVBoxLayout(tips_frame); tf.setContentsMargins(10,10,10,10); tf.setSpacing(4)
        for tip in ["↵  Send message", "🎙  Voice mode", "[ SAVE ]  Save chat", "[ CLEAR ]  Clear chat"]:
            l=QLabel(tip); l.setFont(QFont("Courier New",8))
            l.setStyleSheet("color:rgba(0,212,255,120); background:transparent; border:none;")
            l.setWordWrap(True); tf.addWidget(l)
        lay.addWidget(tips_frame)
        lay.addStretch()

    def _stat_label(self, text, color):
        l = QLabel(text); l.setFont(QFont("Courier New",8,QFont.Weight.Bold))
        l.setStyleSheet(f"color:{color}; background:transparent; border:none;")
        return l

    def _refresh(self):
        try:
            r=requests.get("http://localhost:11434/api/tags",timeout=2)
            if r.status_code==200:
                self.ollama_lbl.setText("● OLLAMA  ONLINE")
                self.ollama_lbl.setStyleSheet("color:#00FF88; background:transparent; border:none; font-weight:bold; font-family:'Courier New'; font-size:8pt;")
            else: raise Exception()
        except:
            self.ollama_lbl.setText("● OLLAMA  OFFLINE")
            self.ollama_lbl.setStyleSheet("color:#FF6B6B; background:transparent; border:none; font-weight:bold; font-family:'Courier New'; font-size:8pt;")

    def set_response_time(self, ms):
        self.resp_lbl.setText(f"RESPONSE: {ms}ms")


# ═══════════════════════════════════════════════════════════
#  VOICE CHAT OVERLAY  (same as before, polished)
# ═══════════════════════════════════════════════════════════
class VoiceChatOverlay(QWidget):
    transcript_ready = pyqtSignal(str, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showFullScreen()
        self._state="idle"; self._last_user=""; self._last_jarvis=""
        self.voice_worker=None; self.tts_worker=None; self.llm_worker=None
        self.conv_history=[]; self._sq=None; self._tts_stop=None
        self._build()

    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        bg=QWidget(); bg.setStyleSheet("background-color:rgba(1,6,16,245);")
        bgl=QVBoxLayout(bg); bgl.setContentsMargins(50,40,50,40); bgl.setSpacing(20)

        top=QHBoxLayout()
        title=QLabel("J.A.R.V.I.S  ///  VOICE MODE")
        title.setFont(QFont("Courier New",16,QFont.Weight.Bold))
        title.setStyleSheet("color:#00D4FF; letter-spacing:4px;")
        close=QPushButton("✕  EXIT"); close.setFixedSize(110,34)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet("QPushButton{background:rgba(255,59,48,30);color:#FF6B6B;"
                            "border:2px solid rgba(255,59,48,130);border-radius:6px;"
                            "font-family:'Courier New';font-size:11px;font-weight:bold;}"
                            "QPushButton:hover{background:rgba(255,59,48,60);color:#FF3B30;}")
        close.clicked.connect(self.close)
        top.addWidget(title); top.addStretch(); top.addWidget(close)
        bgl.addLayout(top)

        arc_box=QWidget(); abl=QVBoxLayout(arc_box); abl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arc=HUDArcReactor(); self.arc.setFixedSize(320,320)
        abl.addWidget(self.arc); bgl.addWidget(arc_box)

        self.state_lbl=QLabel("TAP TO SPEAK")
        self.state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_lbl.setFont(QFont("Courier New",14,QFont.Weight.Bold))
        self.state_lbl.setStyleSheet("color:rgba(0,212,255,180); letter-spacing:3px;")
        bgl.addWidget(self.state_lbl)

        self.transcript_lbl=QLabel(""); self.transcript_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transcript_lbl.setWordWrap(True); self.transcript_lbl.setFont(QFont("Courier New",11))
        self.transcript_lbl.setStyleSheet("color:rgba(224,247,255,160); padding:0 80px;")
        self.transcript_lbl.setMaximumHeight(100); bgl.addWidget(self.transcript_lbl)
        bgl.addStretch()

        btn_row=QHBoxLayout(); btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speak_btn=QPushButton("🎤  SPEAK"); self.speak_btn.setFixedSize(180,60)
        self.speak_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.speak_btn.setFont(QFont("Courier New",13,QFont.Weight.Bold))
        self.speak_btn.setStyleSheet(self._btn_style())
        self.speak_btn.clicked.connect(self._on_btn)
        btn_row.addWidget(self.speak_btn); bgl.addLayout(btn_row); bgl.addSpacing(30)
        root.addWidget(bg)

    def _btn_style(self, active=False):
        if active:
            return ("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                    "stop:0 rgba(255,59,48,150),stop:1 rgba(255,80,60,120));"
                    "color:#FFF;border:2px solid rgba(255,59,48,230);border-radius:30px;font-weight:bold;}")
        return ("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "stop:0 rgba(0,100,220,130),stop:1 rgba(0,60,170,100));"
                "color:#FFF;border:2px solid rgba(0,212,255,230);border-radius:30px;font-weight:bold;}")

    def _set_state(self, state):
        self._state=state; self.arc.set_state(state)
        if state=="listening":
            self.state_lbl.setText("●●  LISTENING  ●●")
            self.state_lbl.setStyleSheet("color:#00FF88; letter-spacing:3px; font-weight:bold;")
            self.speak_btn.setText("⏹  STOP"); self.speak_btn.setStyleSheet(self._btn_style(True))
        elif state=="responding":
            self.state_lbl.setText("●●  PROCESSING  ●●")
            self.state_lbl.setStyleSheet("color:#00D4FF; letter-spacing:3px; font-weight:bold;")
            self.speak_btn.setText("🎤  SPEAK"); self.speak_btn.setStyleSheet(self._btn_style())
            self.speak_btn.setEnabled(False)
        else:
            self.state_lbl.setText("TAP TO SPEAK")
            self.state_lbl.setStyleSheet("color:rgba(0,212,255,180); letter-spacing:3px;")
            self.speak_btn.setText("🎤  SPEAK"); self.speak_btn.setStyleSheet(self._btn_style())
            self.speak_btn.setEnabled(True)

    def _on_btn(self):
        if self._state=="listening":
            if self.voice_worker and self.voice_worker.isRunning(): self.voice_worker.stop_recording()
        elif self._state=="idle": self._start_listening()

    def _start_listening(self):
        self._set_state("listening")
        self.voice_worker=VoiceWorker()
        self.voice_worker.text_received.connect(self._on_speech)
        self.voice_worker.error.connect(self._on_voice_err)
        self.voice_worker.start()

    def _on_speech(self, text):
        self._last_user=text; self.transcript_lbl.setText(f"You: {text}")
        self._set_state("responding"); self.conv_history.append(f"User: {text}")
        self._sq=queue.Queue(); self._tts_stop=threading.Event()
        self.tts_worker=TTSWorker(self._sq,self._tts_stop)
        self.tts_worker.finished_speaking.connect(lambda: self._set_state("idle"))
        self.tts_worker.start()
        use_news=needs_realtime(text.lower())
        self.llm_worker=VoiceLLMWorker(text,list(self.conv_history),use_news=use_news)
        self.llm_worker.sentence_ready.connect(self._on_sentence)
        self.llm_worker.finished.connect(self._on_llm_done)
        self.llm_worker.error.connect(lambda e: self.transcript_lbl.setText("Connection error."))
        self.llm_worker.start()

    def _on_sentence(self, s):
        if self._sq: self._sq.put(s)
        cur=self.transcript_lbl.text()
        if cur.startswith("You:"): self.transcript_lbl.setText(f"Jarvis: {s}")
        else: self.transcript_lbl.setText((cur+" "+s)[-160:])

    def _on_llm_done(self, resp):
        self._last_jarvis=resp; self.conv_history.append(f"Jarvis: {resp}")
        if self._sq: self._sq.put(None)
        self.transcript_ready.emit(self._last_user, resp)

    def _on_voice_err(self, err):
        self.transcript_lbl.setText(f"Error: {err}")
        if self._tts_stop: self._tts_stop.set()
        self._set_state("idle")


# ═══════════════════════════════════════════════════════════
#  CHAT DASHBOARD  (HUD layout)
# ═══════════════════════════════════════════════════════════
class ChatDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_history = []
        self.current_bubble = None
        self.worker = None
        self.current_filename = None
        self._deleted = False
        self._t0 = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top status bar ──────────────────────────────────
        self.status_bar = HUDStatusBar()
        self.status_bar.setStyleSheet(
            "background:rgba(4,18,38,200); border-bottom:1px solid rgba(0,212,255,60);")
        root.addWidget(self.status_bar)

        # ── Main 3-column area ──────────────────────────────
        cols = QHBoxLayout(); cols.setContentsMargins(8,8,8,8); cols.setSpacing(8)

        # Left — sessions
        self.session_panel = HUDSessionPanel()
        self.session_panel.new_chat.connect(self._new_chat)
        self.session_panel.chat_selected.connect(self._load_chat)
        self.session_panel.chat_deleted.connect(self._delete_chat)
        self.session_panel.refresh()
        cols.addWidget(self.session_panel)

        # Center — reactor + chat
        center = QWidget()
        cl = QVBoxLayout(center); cl.setContentsMargins(4,4,4,4); cl.setSpacing(6)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("J.A.R.V.I.S"); title.setFont(QFont("Courier New",22,QFont.Weight.Bold))
        title.setStyleSheet("color:#00D4FF; letter-spacing:5px;")
        title_row.addWidget(title); title_row.addStretch()

        voice_btn = self._hdr_btn("🎙  VOICE", self._open_voice)
        save_btn  = self._hdr_btn("[ SAVE ]",  self._save_chat)
        clear_btn = self._hdr_btn("[ CLEAR ]", self._clear_chat)
        for b in (voice_btn, save_btn, clear_btn):
            title_row.addWidget(b)
            title_row.addSpacing(4)
        cl.addLayout(title_row)

        # Arc reactor (center, compact)
        arc_box = QWidget(); abl = QHBoxLayout(arc_box)
        abl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arc = HUDArcReactor(); self.arc.setFixedSize(200, 200)
        abl.addWidget(self.arc); cl.addWidget(arc_box)

        # Chat scroll area
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""QScrollArea{border:none;background:transparent;}
            QScrollBar:vertical{width:4px;background:transparent;}
            QScrollBar::handle:vertical{background:rgba(0,212,255,100);border-radius:2px;min-height:20px;}""")
        self.chat_widget = QWidget(); self.chat_widget.setStyleSheet("background:transparent;")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(8,8,8,8); self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch()
        scroll.setWidget(self.chat_widget)
        self._scroll = scroll

        self.typing = HUDTypingIndicator()
        cl.addWidget(scroll); cl.addWidget(self.typing)

        # Char count
        self.char_lbl = QLabel("0 / 500")
        self.char_lbl.setFont(QFont("Courier New",7))
        self.char_lbl.setStyleSheet("color:rgba(0,212,255,60);")
        self.char_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        cl.addWidget(self.char_lbl)

        # Input row
        inp_frame = QFrame()
        inp_frame.setStyleSheet("""background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba(0,25,70,180),stop:1 rgba(0,15,50,160));
            border:1.5px solid rgba(0,212,255,150); border-radius:10px;""")
        inp_lay = QHBoxLayout(inp_frame); inp_lay.setContentsMargins(12,6,6,6); inp_lay.setSpacing(6)
        prompt_lbl = QLabel(">_"); prompt_lbl.setFont(QFont("Courier New",13,QFont.Weight.Bold))
        prompt_lbl.setStyleSheet("color:#00D4FF;")
        self.input = QLineEdit(); self.input.setPlaceholderText("ENTER COMMAND...")
        self.input.setFont(QFont("Courier New",11,QFont.Weight.Bold)); self.input.setFixedHeight(40)
        self.input.setMaxLength(500)
        self.input.setStyleSheet("""QLineEdit{background:transparent;color:#00D4FF;border:none;padding:0 6px;}
            QLineEdit:focus{outline:none;}""")
        self.input.returnPressed.connect(self._send)
        self.input.textChanged.connect(self._char_count)
        self.send_btn = QPushButton("SEND ▶"); self.send_btn.setFixedSize(100,40)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba(0,130,255,150),stop:1 rgba(0,80,210,130));
            color:#FFF;border:1px solid rgba(0,212,255,190);border-radius:8px;
            font-family:'Courier New';font-size:10px;font-weight:bold;}
            QPushButton:hover{background:rgba(0,160,255,180);}
            QPushButton:disabled{background:rgba(0,212,255,20);color:rgba(0,212,255,50);}""")
        self.send_btn.clicked.connect(self._send)
        inp_lay.addWidget(prompt_lbl); inp_lay.addWidget(self.input); inp_lay.addWidget(self.send_btn)
        cl.addWidget(inp_frame)

        cols.addWidget(center, stretch=1)

        # Right — info panel
        self.info_panel = HUDInfoPanel()
        cols.addWidget(self.info_panel)

        root.addLayout(cols, stretch=1)

        # Greet
        self._add_bubble("JARVIS ONLINE. All systems initialized. How may I assist you?", is_user=False)

    def _hdr_btn(self, label, slot):
        b = QPushButton(label); b.setFixedHeight(30)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet("""QPushButton{background:transparent;color:rgba(0,212,255,140);
            border:1px solid rgba(0,212,255,60);border-radius:4px;
            font-family:'Courier New';font-size:9px;font-weight:bold;padding:0 8px;}
            QPushButton:hover{background:rgba(0,212,255,20);color:#00D4FF;border-color:#00D4FF;}""")
        b.clicked.connect(slot); return b

    def _add_bubble(self, text, is_user=True):
        b = HUDChatBubble(text, is_user=is_user)
        self.chat_layout.insertWidget(self.chat_layout.count()-1, b)
        QApplication.processEvents()
        self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())
        return b

    def _char_count(self, text):
        n=len(text); self.char_lbl.setText(f"{n} / 500")
        self.char_lbl.setStyleSheet(
            f"color:{'rgba(255,59,48,150)' if n>400 else 'rgba(255,159,0,150)' if n>300 else 'rgba(0,212,255,60)'};")

    def _set_thinking(self, on):
        self.send_btn.setEnabled(not on); self.input.setEnabled(not on)
        if on:
            self.typing.start(); self.arc.set_state("responding")
            self.status_bar.set_status("PROCESSING...", "#FF9500")
            self._t0 = datetime.now()
        else:
            self.typing.stop(); self.arc.set_state("idle")
            self.status_bar.set_status("SYSTEM ONLINE", "#00FF88")
            if self._t0:
                ms = int((datetime.now()-self._t0).total_seconds()*1000)
                self.info_panel.set_response_time(ms); self._t0=None

    def _send(self):
        text=self.input.text().strip()
        if not text or (self.worker and self.worker.isRunning()): return
        self.input.clear(); self._add_bubble(text, is_user=True)
        self.conversation_history.append(f"User: {text}")
        if text.lower() in ["exit","quit","stop"]:
            self._add_bubble("Shutting down. Until next time.", is_user=False); return
        self._set_thinking(True)
        self.current_bubble = self._add_bubble("", is_user=False)
        self.worker = JarvisWorker(text, list(self.conversation_history), use_news=needs_realtime(text.lower()))
        self.worker.token_received.connect(lambda t: (self.current_bubble.append_text(t), QApplication.processEvents()))
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, resp):
        self.conversation_history.append(f"Jarvis: {resp}")
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        if self.conversation_history and not self._deleted:
            self.current_filename = save_chat(self.conversation_history, self.current_filename)
            self.session_panel.refresh()
        self._deleted=False; self._set_thinking(False); self.input.setFocus()

    def _on_error(self, msg):
        if self.current_bubble: self.current_bubble.append_text(f"\nERROR: {msg}")
        self._set_thinking(False)

    def _save_chat(self):
        if not self.conversation_history: return
        self.current_filename = save_chat(self.conversation_history, self.current_filename)
        self.session_panel.refresh()

    def _new_chat(self):
        if self.conversation_history:
            save_chat(self.conversation_history, self.current_filename)
            self.session_panel.refresh()
        self.conversation_history.clear(); self.current_filename=None
        self._clear_bubbles()
        self._add_bubble("New session started. How may I assist you?", is_user=False)

    def _load_chat(self, filename):
        if self.conversation_history:
            save_chat(self.conversation_history, self.current_filename)
        try:
            msgs=load_chat(filename); self.conversation_history=msgs; self.current_filename=filename
            self._clear_bubbles()
            for m in msgs:
                if m.startswith("User: "):    self._add_bubble(m[6:], is_user=True)
                elif m.startswith("Jarvis: "): self._add_bubble(m[8:], is_user=False)
        except Exception as e:
            self._add_bubble(f"Failed to load: {e}", is_user=False)

    def _delete_chat(self, filename):
        delete_chat(filename)
        if self.current_filename==filename:
            self._deleted=True; self.current_filename=None; self.conversation_history.clear()
            self._clear_bubbles()
            self._add_bubble("Session deleted. Starting fresh.", is_user=False)
        self.session_panel.refresh()

    def _clear_chat(self):
        self.conversation_history.clear(); self.current_filename=None
        self._clear_bubbles()
        self._add_bubble("MEMORY WIPED. Systems reset.", is_user=False)

    def _clear_bubbles(self):
        while self.chat_layout.count() > 1:
            item=self.chat_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _open_voice(self):
        self._voice_overlay = VoiceChatOverlay(self)
        self._voice_overlay.transcript_ready.connect(self._on_voice_transcript)
        self._voice_overlay.show()

    def _on_voice_transcript(self, user_text, jarvis_text):
        self.conversation_history.append(f"User: {user_text}")
        self.conversation_history.append(f"Jarvis: {jarvis_text}")
        self._add_bubble(user_text, is_user=True)
        self._add_bubble(jarvis_text, is_user=False)
        self.current_filename = save_chat(self.conversation_history, self.current_filename)
        self.session_panel.refresh()

    def on_close(self):
        if self.conversation_history:
            save_chat(self.conversation_history, self.current_filename)


# ═══════════════════════════════════════════════════════════
#  HOLOGRAPHIC BACKGROUND (persistent across screens)
# ═══════════════════════════════════════════════════════════
class HoloBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._off=0; self._pt=0; self._gl=0
        self._particles=[]
        for _ in range(PARTICLE_COUNT):
            self._particles.append({
                "x":random.uniform(0,1),"y":random.uniform(0,1),
                "vx":random.uniform(-0.0002,0.0002),"vy":random.uniform(-0.0005,-0.0001),
                "life":random.uniform(0.3,1.0),"decay":random.uniform(0.002,0.006),
                "size":random.uniform(1,2.5),
            })
        t=QTimer(self); t.timeout.connect(self._step); t.start(1000//ANIMATION_FPS)

    def _step(self):
        self._off=(self._off+1)%60; self._pt=(self._pt+1)%360; self._gl=(self._gl+1)%100
        for p in self._particles:
            p["x"]+=p["vx"]; p["y"]+=p["vy"]; p["life"]=max(0,p["life"]-p["decay"])
        self._particles=[p for p in self._particles if p["life"]>0]
        while len(self._particles)<PARTICLE_COUNT:
            self._particles.append({"x":random.uniform(0,1),"y":1.0,
                "vx":random.uniform(-0.0002,0.0002),"vy":random.uniform(-0.0005,-0.0001),
                "life":1.0,"decay":random.uniform(0.002,0.006),"size":random.uniform(1,2.5)})
        self.update()

    def paintEvent(self, event):
        w,h=self.width(),self.height()
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Grid
        step=50; pen=QPen()
        for gx in range(-(self._off%step),w,step):
            alpha=int(8+4*math.sin(math.radians(self._pt+gx/3)))
            pen.setColor(QColor(0,212,255,max(3,alpha))); pen.setWidthF(0.5); p.setPen(pen)
            p.drawLine(gx,0,gx,h)
        for gy in range(-(self._off%step),h,step):
            alpha=int(8+4*math.sin(math.radians(self._pt+gy/3)))
            pen.setColor(QColor(0,212,255,max(3,alpha))); pen.setWidthF(0.5); p.setPen(pen)
            p.drawLine(0,gy,w,gy)
        # Particles
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self._particles:
            a=int(160*pt["life"]); p.setBrush(QBrush(QColor(0,212,255,a)))
            p.drawEllipse(QPointF(pt["x"]*w,pt["y"]*h),pt["size"],pt["size"])
        # Scanlines
        for sy in range(0,h,3):
            fl=10 if (self._gl+sy)%20<10 else 4
            p.setPen(QPen(QColor(0,0,0,fl))); p.drawLine(0,sy,w,sy)


# ═══════════════════════════════════════════════════════════
#  MAIN WINDOW  (manages startup → dashboard transition)
# ═══════════════════════════════════════════════════════════
class JarvisMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S  —  HOLOGRAPHIC INTERFACE  v3.0")
        self.setMinimumSize(1280, 820)
        self.resize(1540, 900)
        self.setStyleSheet("background-color:#010810;")

        # Root stacked widget
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Holographic background lives behind everything
        self._bg = HoloBackground(self)
        self._bg.lower()
        self._bg.resize(self.size())

        # Startup screen
        self._startup = StartupScreen()
        self._startup.boot_complete.connect(self._show_dashboard)
        self._stack.addWidget(self._startup)

        # Dashboard (created but hidden until boot completes)
        self._dashboard = ChatDashboard()
        self._stack.addWidget(self._dashboard)

        self._stack.setCurrentWidget(self._startup)

        # Warmup fires immediately alongside startup animation
        self._warmup = ModelWarmupWorker()
        self._warmup.start()

    def _show_dashboard(self):
        self._stack.setCurrentWidget(self._dashboard)
        self._dashboard.input.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg.resize(self.size())

    def closeEvent(self, event):
        self._dashboard.on_close(); event.accept()


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,     QColor(1, 8, 16))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 212, 255))
    app.setPalette(palette)
    window = JarvisMainWindow()
    window.show()
    sys.exit(app.exec())
