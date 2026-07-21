"""
All voice/text commands — PC control, web, notes, daily, fun, CSE tools.
Each command self-registers via @register; the router matches input patterns.
"""

from __future__ import annotations

import dataclasses
import logging
import random
import re
import subprocess
import threading
import time
import webbrowser
from datetime import datetime

import psutil
import requests

from jarvis.config import (
    OWNER_NAME, CITY, NOTES_DIR, SCREENSHOTS_DIR, find_exe, is_windows,
)

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# COMMAND REGISTRY
# ════════════════════════════════════════════════════════════════════════════

@dataclasses.dataclass
class Command:
    pattern: re.Pattern
    handler: callable
    description: str = ""
    category: str = "general"

_registry: list[Command] = []

def register(pattern: str, category: str = "general", description: str = ""):
    compiled = re.compile(pattern, re.IGNORECASE)
    def decorator(func):
        _registry.append(Command(compiled, func, description or func.__doc__ or "", category))
        return func
    return decorator

def match_command(text: str):
    for cmd in _registry:
        m = cmd.pattern.match(text.strip())
        if m:
            return cmd, m.groupdict()
    return None

# ════════════════════════════════════════════════════════════════════════════
# PC CONTROL
# ════════════════════════════════════════════════════════════════════════════
_APP_ALIASES = {
    "chrome": ["google-chrome", "google-chrome-stable", "chrome"],
    "firefox": ["firefox"], "brave": ["brave-browser", "brave"],
    "edge": ["microsoft-edge", "msedge"], "vscode": ["code", "cursor"],
    "notepad": ["notepad", "gedit", "gnome-text-editor"],
    "calculator": ["calc", "gnome-calculator", "kcalc"],
    "terminal": ["wt", "gnome-terminal", "konsole", "xterm"],
    "vlc": ["vlc"], "spotify": ["spotify"], "discord": ["discord"],
}
_SAFE_CLOSE = {"chrome", "firefox", "brave", "edge", "code", "vlc", "spotify", "notepad", "discord"}

@register(r"^open (?P<name>.+)", category="pc", description="Open an app")
def open_app(name: str) -> str:
    name_l = name.lower().strip()
    for alias, bins in _APP_ALIASES.items():
        if alias in name_l or name_l in alias:
            for b in bins:
                if find_exe(b):
                    subprocess.Popen([find_exe(b)]); return f"Opening {alias}."
    if find_exe(name_l):
        subprocess.Popen([find_exe(name_l)]); return f"Opening {name_l}."
    if is_windows():
        try: subprocess.Popen(f"start {name_l}", shell=True); return f"Opening {name_l}."
        except Exception: pass
    return f"I don't know how to open '{name}'."

@register(r"^(?:close|kill|quit) (?P<name>.+)", category="pc", description="Close an app")
def close_app(name: str) -> str:
    n = name.lower().strip()
    if n not in _SAFE_CLOSE:
        return f"'{n}' not in safe-close list. Close manually."
    try:
        if is_windows(): subprocess.run(["taskkill", "/IM", f"{n}.exe", "/F"], capture_output=True, timeout=10)
        else: subprocess.run(["pkill", "-f", n], capture_output=True, timeout=10)
        return f"Closed {n}."
    except Exception as e:
        return f"Error closing {n}: {e}"

@register(r"^volume (?P<action>up|down|mute)", category="pc", description="Volume control")
def volume_control(action: str) -> str:
    try:
        import pyautogui  # type: ignore
        if action == "up": pyautogui.press("volumeup", presses=5); return "Volume up."
        if action == "down": pyautogui.press("volumedown", presses=5); return "Volume down."
        if action == "mute": pyautogui.press("volumemute"); return "Volume toggled."
    except ImportError:
        return "Volume control needs pyautogui. pip install jarvis-assistant[gui]"
    return ""

@register(r"^screenshot|take a screenshot", category="pc", description="Take a screenshot")
def take_screenshot() -> str:
    try:
        import pyautogui  # type: ignore
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOTS_DIR / f"screenshot_{ts}.png"
        pyautogui.screenshot().save(str(path))
        return f"Screenshot saved: {path.name}"
    except ImportError:
        return "Screenshots need pyautogui. pip install jarvis-assistant[gui]"
    except Exception as e:
        return f"Screenshot failed: {e}"

@register(r"^system info|sysinfo", category="pc", description="System info")
def system_info() -> str:
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    bat = psutil.sensors_battery()
    info = f"CPU: {cpu}% | RAM: {mem.percent}% | Disk: {disk.percent}%"
    if bat: info += f" | Battery: {bat.percent}%"
    return info

# ════════════════════════════════════════════════════════════════════════════
# WEB
# ════════════════════════════════════════════════════════════════════════════
_WEBSITES = {
    "google": "https://google.com", "youtube": "https://youtube.com",
    "github": "https://github.com", "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://reddit.com", "twitter": "https://x.com",
    "linkedin": "https://linkedin.com", "gmail": "https://mail.google.com",
    "chatgpt": "https://chat.openai.com", "leetcode": "https://leetcode.com",
    "wikipedia": "https://wikipedia.org", "amazon": "https://amazon.com",
}
_ENGINES = {
    "google": "https://google.com/search?q={}",
    "youtube": "https://youtube.com/results?search_query={}",
    "github": "https://github.com/search?q={}",
}

@register(r"^go to (?P<site>.+)", category="web", description="Open a website")
def open_website(site: str) -> str:
    s = site.lower().strip()
    if s.startswith("http"): webbrowser.open(s); return f"Opening {s}"
    if s in _WEBSITES: webbrowser.open(_WEBSITES[s]); return f"Opening {s}."
    for name, url in _WEBSITES.items():
        if name in s: webbrowser.open(url); return f"Opening {name}."
    if "." in s: webbrowser.open(f"https://{s}"); return f"Opening https://{s}"
    return f"I don't know '{site}'."

@register(r"^search (?P<engine>\w+) (?:for )?(?P<query>.+)", category="web", description="Search engine")
def search_engine(engine: str, query: str) -> str:
    e = engine.lower()
    if e in _ENGINES:
        webbrowser.open(_ENGINES[e].format(query)); return f"Searching {e} for: {query}"
    webbrowser.open(_ENGINES["google"].format(query)); return f"Searching Google for: {query}"

@register(r"^search (?:for )?(?P<query>.+)", category="web", description="Google search")
def search_google(query: str) -> str:
    webbrowser.open(_ENGINES["google"].format(query)); return f"Searching Google for: {query}"

@register(r"^(?:what(?:'s| is) the )?weather(?: in (?P<city>.+))?", category="web", description="Weather")
def get_weather(city: str = "") -> str:
    c = city.strip() or CITY
    try:
        r = requests.get(f"https://wttr.in/{c}?format=%l:+%C+%t+%h+%w", timeout=10)
        return r.text.strip() if r.status_code == 200 else f"Weather unavailable for {c}."
    except Exception as e:
        return f"Weather error: {e}"

# ════════════════════════════════════════════════════════════════════════════
# NOTES
# ════════════════════════════════════════════════════════════════════════════
@register(r"^create note", category="notes", description="Create a note")
def create_note() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = NOTES_DIR / f"note_{ts}.txt"
    path.write_text("", encoding="utf-8")
    return f"Note created: {path.name}"

def save_note(text: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = NOTES_DIR / f"note_{ts}.txt"
    path.write_text(text, encoding="utf-8")
    return f"Note saved: {path.name}"

@register(r"^read (?:my )?(?:last |latest )?note", category="notes", description="Read last note")
def read_last_note() -> str:
    notes = sorted(NOTES_DIR.glob("note_*.txt"), key=lambda p: p.stat().st_mtime)
    if not notes: return "No notes yet."
    content = notes[-1].read_text(encoding="utf-8").strip()
    return f"From {notes[-1].name}: {content}" if content else f"{notes[-1].name} is empty."

@register(r"^list (?:my )?notes", category="notes", description="List notes")
def list_notes() -> str:
    notes = sorted(NOTES_DIR.glob("note_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not notes: return "No notes."
    return f"{len(notes)} note(s). Latest: {', '.join(n.name for n in notes[:5])}"

# ════════════════════════════════════════════════════════════════════════════
# DAILY
# ════════════════════════════════════════════════════════════════════════════
@register(r"^(?:what(?:'s| is) the )?time|what time is it", category="daily", description="Current time")
def get_time() -> str:
    return f"It's {datetime.now().strftime('%I:%M %p')}."

@register(r"^(?:what(?:'s| is) the )?date|what day is (?:it|today)", category="daily", description="Current date")
def get_date() -> str:
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

@register(r"^set (?:a )?reminder (?:in )?(?P<minutes>\d+) (?:minutes?|mins?) (?P<msg>.+)", category="daily", description="Reminder")
def set_reminder(minutes: str, msg: str) -> str:
    from jarvis.voice import speak as _speak
    def _wait():
        time.sleep(int(minutes) * 60); _speak(f"Reminder: {msg}")
    threading.Thread(target=_wait, daemon=True).start()
    return f"Reminder set for {minutes} min: {msg}"

@register(r"^morning briefing|good morning", category="daily", description="Morning briefing")
def morning_briefing() -> str:
    h = datetime.now().hour
    greet = "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"
    weather = get_weather()
    return f"{greet}, {OWNER_NAME}! Weather: {weather}"

# ════════════════════════════════════════════════════════════════════════════
# FUN
# ════════════════════════════════════════════════════════════════════════════
_FALLBACK_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar and asks: 'Can I join you?'",
]

@register(r"^(?:tell (?:me )?a )?joke", category="fun", description="Joke")
def tell_joke() -> str:
    try:
        import pyjokes  # type: ignore
        return pyjokes.get_joke()
    except ImportError:
        return random.choice(_FALLBACK_JOKES)

@register(r"^(?:motivate me|give me a quote)", category="fun", description="Motivational quote")
def motivate() -> str:
    quotes = [
        "The only way to do great work is to love what you do. — Steve Jobs",
        "Talk is cheap. Show me the code. — Linus Torvalds",
        "First, solve the problem. Then, write the code. — John Johnson",
    ]
    return random.choice(quotes)

@register(r"^(?:flip (?:a )?coin)", category="fun", description="Coin flip")
def flip_coin() -> str:
    return f"It's {random.choice(['heads', 'tails'])}!"

@register(r"^roll (?:a )?(?P<sides>\d+)?-?sided? dice|^roll (?:a )?dice", category="fun", description="Roll dice")
def roll_dice(sides: str = "6") -> str:
    n = int(sides) if sides else 6
    return f"You rolled a {random.randint(1, n)} on a {n}-sided die."

@register(r"^(?:calculate|calc|what(?:'s| is)) (?P<expr>.+)", category="fun", description="Calculator")
def calculate(expr: str) -> str:
    t = expr.lower().replace("percent of", "/ 100 *").replace("percent", "/ 100")
    t = t.replace("times", "*").replace("x", "*").replace("plus", "+").replace("minus", "-").replace("divided by", "/")
    if not re.match(r'^[\d\s\+\-\*\/\.\(\)%]+$', t):
        return f"Cannot evaluate: {expr}"
    try:
        result = eval(t, {"__builtins__": {}}, {})  # noqa: S307
        return f"{expr} = {int(result) if isinstance(result, float) and result == int(result) else result}"
    except Exception:
        return f"Could not calculate: {expr}"

# ════════════════════════════════════════════════════════════════════════════
# CSE TOOLS
# ════════════════════════════════════════════════════════════════════════════
@register(r"^explain (?P<topic>.+)", category="cse", description="Explain a concept")
def explain_concept(topic: str) -> str:
    from jarvis.brain import brain
    return brain.ask(f"Explain '{topic}' simply for a CS student. 3-4 sentences max.")

@register(r"^complexity (?:of )?(?P<algo>.+)", category="cse", description="Algorithm complexity")
def code_complexity(algo: str) -> str:
    from jarvis.brain import brain
    return brain.ask(f"Analyze time/space complexity of '{algo}'. Big-O for best/avg/worst. Be concise.")

@register(r"^interview (?:prep )?(?:for |on )?(?P<topic>.+)", category="cse", description="Interview prep")
def interview_prep(topic: str) -> str:
    from jarvis.brain import brain
    return brain.ask(f"Give 5 interview questions about '{topic}' with brief model answers.")
