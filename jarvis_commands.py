"""
JARVIS v3 - Commands Module
===========================
All voice commands: PC control, web features, CSE student tools,
notes system, fun commands, and daily assistant features.
Import from jarvis_core: voice, speak, listener, brain, memory, etc.
"""

import os
import sys
import time
import random
import subprocess
import webbrowser
import threading
import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Callable

import pyautogui
import psutil
import pyperclip
import requests
import pyjokes

from jarvis_core import (
    voice, speak, listener, brain, memory,
    OWNER_NAME, CITY, NOTES_DIR, SCREENSHOTS_DIR, LOGS_DIR,
    get_timestamp
)

# Suppress pyautogui failsafe for voice control
pyautogui.FAILSAFE = False


# ============================================================
# PC CONTROL
# ============================================================

# Dictionary of 20+ apps with their Windows paths
APP_PATHS: Dict[str, List[str]] = {
    "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
    "brave": [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"],
    "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"],
    "edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
    "vscode": [r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe"],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "spotify": [r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe"],
    "discord": [r"C:\Users\%USERNAME%\AppData\Local\Discord\app-1.0.9005\Discord.exe"],
    "telegram": [r"C:\Users\%USERNAME%\AppData\Roaming\Telegram Desktop\Telegram.exe"],
    "whatsapp": [r"C:\Users\%USERNAME%\AppData\Local\WhatsApp\WhatsApp.exe"],
    "obs": [r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"],
    "vlc": [r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"],
    "task manager": ["taskmgr.exe"],
    "file explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe"],
    "command prompt": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "paint": ["mspaint.exe"],
    "word": [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
    "excel": [r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
    "winrar": [r"C:\Program Files\WinRAR\WinRAR.exe"],
    "notepad++": [r"C:\Program Files\Notepad++\notepad++.exe"],
    "teams": [r"C:\Users\%USERNAME%\AppData\Local\Microsoft\Teams\current\Teams.exe"],
}

# Apps safe to close via taskkill
SAFE_CLOSE_LIST = [
    "notepad.exe", "mspaint.exe", "calc.exe", "vlc.exe",
    "chrome.exe", "brave.exe", "firefox.exe", "msedge.exe",
    "code.exe", "spotify.exe", "obs64.exe", "winword.exe",
    "excel.exe", "powerpnt.exe", "notepad++.exe",
]


def open_app(name: str) -> str:
    """Open an application by name. Returns status message."""
    name_lower = name.lower().strip()

    # Direct match
    if name_lower in APP_PATHS:
        paths = APP_PATHS[name_lower]
        for path in paths:
            expanded = os.path.expandvars(path)
            if os.path.exists(expanded):
                try:
                    os.startfile(expanded)
                    return f"Opening {name}."
                except Exception as e:
                    return f"Could not open {name}: {e}"
        # Try subprocess fallback
        try:
            subprocess.Popen([os.path.expandvars(paths[0])], shell=False)
            return f"Opening {name}."
        except Exception as e:
            return f"Failed to open {name}: {e}"

    # Partial match
    for app_name, paths in APP_PATHS.items():
        if name_lower in app_name or app_name in name_lower:
            for path in paths:
                expanded = os.path.expandvars(path)
                if os.path.exists(expanded):
                    try:
                        os.startfile(expanded)
                        return f"Opening {app_name}."
                    except Exception:
                        pass
            try:
                subprocess.Popen([os.path.expandvars(paths[0])], shell=False)
                return f"Opening {app_name}."
            except Exception as e:
                return f"Failed to open {app_name}: {e}"

    return f"I don't know how to open {name}. Try adding it to jarvis_config.py."


def close_app(name: str) -> str:
    """Close an application safely using taskkill."""
    name_lower = name.lower().strip()

    # Map common names to executable names
    name_map = {
        "chrome": "chrome.exe", "brave": "brave.exe",
        "firefox": "firefox.exe", "edge": "msedge.exe",
        "vscode": "code.exe", "notepad": "notepad.exe",
        "calculator": "calc.exe", "spotify": "spotify.exe",
        "vlc": "vlc.exe", "paint": "mspaint.exe",
        "word": "winword.exe", "excel": "excel.exe",
        "discord": "discord.exe", "telegram": "telegram.exe",
        "whatsapp": "whatsapp.exe", "obs": "obs64.exe",
    }

    exe_name = name_map.get(name_lower, name_lower)
    if not exe_name.endswith('.exe'):
        exe_name += '.exe'

    if exe_name.lower() not in [s.lower() for s in SAFE_CLOSE_LIST]:
        return f"{name} is not in the safe close list. Close it manually to be safe."

    try:
        result = subprocess.run(
            ["taskkill", "/IM", exe_name, "/F"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return f"Closed {name}."
        else:
            return f"{name} doesn't seem to be running."
    except Exception as e:
        return f"Error closing {name}: {e}"


def volume_control(action: str) -> str:
    """Control system volume: up, down, mute, or set to X percent."""
    action_lower = action.lower().strip()

    if action_lower in ["up", "increase", "higher", "louder"]:
        pyautogui.press('volumeup', presses=5)
        return "Volume increased."
    elif action_lower in ["down", "decrease", "lower", "quieter"]:
        pyautogui.press('volumedown', presses=5)
        return "Volume decreased."
    elif action_lower in ["mute", "unmute", "silent"]:
        pyautogui.press('volumemute')
        return "Volume muted."
    elif "percent" in action_lower or "%" in action_lower:
        # Extract number
        numbers = re.findall(r'\d+', action_lower)
        if numbers:
            target = int(numbers[0])
            target = max(0, min(100, target))
            # Mute then unmute to reset, then press volume up appropriate times
            pyautogui.press('volumemute')
            time.sleep(0.1)
            pyautogui.press('volumemute')
            # Each volumeup is ~2%, so press accordingly
            presses = target // 2
            pyautogui.press('volumeup', presses=presses)
            return f"Volume set to approximately {target} percent."

    return "Volume commands: up, down, mute, or set to X percent."


def brightness_control(action: str) -> str:
    """Control screen brightness: up, down, or set to X percent."""
    try:
        import screen_brightness_control as sbc

        action_lower = action.lower().strip()
        current = sbc.get_brightness()[0] if isinstance(sbc.get_brightness(), list) else sbc.get_brightness()

        if action_lower in ["up", "increase", "higher", "brighter"]:
            new_val = min(100, current + 20)
            sbc.set_brightness(new_val)
            return f"Brightness increased to {new_val} percent."
        elif action_lower in ["down", "decrease", "lower", "dimmer"]:
            new_val = max(0, current - 20)
            sbc.set_brightness(new_val)
            return f"Brightness decreased to {new_val} percent."
        elif "percent" in action_lower or "%" in action_lower:
            numbers = re.findall(r'\d+', action_lower)
            if numbers:
                target = max(0, min(100, int(numbers[0])))
                sbc.set_brightness(target)
                return f"Brightness set to {target} percent."

        return "Brightness commands: up, down, or set to X percent."
    except Exception as e:
        return f"Brightness control not available: {e}"


def take_screenshot() -> str:
    """Take a screenshot and save to Desktop/JarvisScreenshots/."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename

        screenshot = pyautogui.screenshot()
        screenshot.save(str(filepath))

        return f"Screenshot saved as {filename}."
    except Exception as e:
        return f"Screenshot failed: {e}"


def get_system_info() -> str:
    """Get and speak full system information summary."""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        freq_mhz = cpu_freq.current if cpu_freq else 0

        # RAM
        ram = psutil.virtual_memory()
        ram_used_gb = ram.used / (1024**3)
        ram_total_gb = ram.total / (1024**3)

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            bat_percent = battery.percent
            charging = "plugged in" if battery.power_plugged else "on battery"
            bat_str = f"Battery at {bat_percent} percent, {charging}."
        else:
            bat_str = "No battery detected."

        # Disk
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = int(uptime_seconds // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)

        summary = (
            f"CPU usage is {cpu_percent} percent at {freq_mhz:.0f} megahertz. "
            f"RAM usage is {ram_used_gb:.1f} out of {ram_total_gb:.1f} gigabytes. "
            f"{bat_str} "
            f"Disk usage is {disk_percent} percent. "
            f"System uptime is {uptime_hours} hours and {uptime_minutes} minutes."
        )

        return summary
    except Exception as e:
        return f"Could not get system info: {e}"


def pc_sleep() -> str:
    """Put PC to sleep after confirmation."""
    speak("Are you sure you want to put the computer to sleep? Say yes to confirm.")
    response = listener.listen(timeout=5)
    if response and "yes" in response:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Putting computer to sleep."
    return "Sleep cancelled."


def pc_restart() -> str:
    """Restart PC after confirmation."""
    speak("Are you sure you want to restart? Say yes to confirm.")
    response = listener.listen(timeout=5)
    if response and "yes" in response:
        os.system("shutdown /r /t 10")
        return "Restarting in 10 seconds."
    return "Restart cancelled."


# ============================================================
# CLIPBOARD CONTROL
# ============================================================

def copy_to_clipboard(text: str) -> str:
    """Copy text to clipboard."""
    try:
        pyperclip.copy(text)
        return "Copied to clipboard."
    except Exception as e:
        return f"Clipboard error: {e}"


def read_clipboard() -> str:
    """Read clipboard contents and speak them."""
    try:
        text = pyperclip.paste()
        if text:
            # Truncate if too long
            if len(text) > 200:
                return f"Clipboard contains: {text[:200]}... (truncated)"
            return f"Clipboard says: {text}"
        return "Clipboard is empty."
    except Exception as e:
        return f"Could not read clipboard: {e}"


def clear_clipboard() -> str:
    """Clear clipboard contents."""
    try:
        pyperclip.copy("")
        return "Clipboard cleared."
    except Exception as e:
        return f"Could not clear clipboard: {e}"


# ============================================================
# TYPING ASSISTANT
# ============================================================

def type_text(text: str) -> str:
    """Type text using pyautogui at the current cursor position."""
    try:
        # Small delay to let user switch windows
        speak("Typing in 2 seconds. Switch to your target window.")
        time.sleep(2)
        pyautogui.typewrite(text, interval=0.01)
        return "Text typed."
    except Exception as e:
        return f"Typing failed: {e}"


# ============================================================
# WEB FEATURES
# ============================================================

# Dictionary of 40+ websites
WEBSITE_URLS: Dict[str, str] = {
    "github": "https://github.com",
    "leetcode": "https://leetcode.com",
    "codeforces": "https://codeforces.com",
    "hackerrank": "https://www.hackerrank.com",
    "codechef": "https://www.codechef.com",
    "atcoder": "https://atcoder.jp",
    "geeksforgeeks": "https://www.geeksforgeeks.org",
    "stackoverflow": "https://stackoverflow.com",
    "w3schools": "https://www.w3schools.com",
    "mdn": "https://developer.mozilla.org",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "gmail": "https://mail.google.com",
    "drive": "https://drive.google.com",
    "classroom": "https://classroom.google.com",
    "meet": "https://meet.google.com",
    "youtube": "https://youtube.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://netflix.com",
    "prime": "https://www.primevideo.com",
    "twitter": "https://x.com",
    "instagram": "https://instagram.com",
    "linkedin": "https://linkedin.com",
    "reddit": "https://reddit.com",
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "telegram web": "https://web.telegram.org",
    "discord": "https://discord.com/app",
    "notion": "https://notion.so",
    "obsidian": "https://obsidian.md",
    "figma": "https://figma.com",
    "canva": "https://canva.com",
    "coursera": "https://coursera.org",
    "udemy": "https://udemy.com",
    "nptel": "https://nptel.ac.in",
    "mit": "https://ocw.mit.edu",
    "google": "https://google.com",
    "bing": "https://bing.com",
    "duckduckgo": "https://duckduckgo.com",
}

# Search engines
SEARCH_ENGINES: Dict[str, str] = {
    "google": "https://www.google.com/search?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
    "github": "https://github.com/search?q={}",
    "stackoverflow": "https://stackoverflow.com/search?q={}",
    "leetcode": "https://leetcode.com/search/?q={}",
    "geeksforgeeks": "https://www.geeksforgeeks.org/search/?q={}",
    "bing": "https://www.bing.com/search?q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
}


def open_website(name: str) -> str:
    """Open a website by name."""
    name_lower = name.lower().strip()

    # Direct match
    if name_lower in WEBSITE_URLS:
        webbrowser.open(WEBSITE_URLS[name_lower])
        return f"Opening {name}."

    # Partial match
    for site_name, url in WEBSITE_URLS.items():
        if name_lower in site_name or site_name in name_lower:
            webbrowser.open(url)
            return f"Opening {site_name}."

    # Try as direct URL
    if "." in name_lower:
        url = name_lower if name_lower.startswith("http") else f"https://{name_lower}"
        webbrowser.open(url)
        return f"Opening {url}."

    return f"I don't have {name} in my website list. Try adding it to jarvis_config.py."


def search_web(engine: str, query: str) -> str:
    """Search the web using specified engine."""
    engine_lower = engine.lower().strip()

    if engine_lower not in SEARCH_ENGINES:
        # Default to google
        engine_lower = "google"

    search_url = SEARCH_ENGINES[engine_lower].format(query.replace(" ", "+"))
    webbrowser.open(search_url)
    return f"Searching {engine} for {query}."


def get_weather() -> str:
    """Get weather for the configured city using wttr.in."""
    try:
        url = f"https://wttr.in/{CITY}?format=%C+%t+%w+%h"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            weather = response.text.strip()
            return f"Weather in {CITY}: {weather}."
        else:
            return f"Could not fetch weather for {CITY}."
    except Exception as e:
        return f"Weather fetch failed: {e}"


# ============================================================
# CSE STUDENT FEATURES
# ============================================================

def explain_concept(topic: str) -> str:
    """Explain a CS concept using Groq AI."""
    if not topic.strip():
        return "What concept should I explain?"
    response = brain.ask_explanation(topic)
    return response


def debug_assistant() -> str:
    """Interactive debugging assistant."""
    speak("Describe the error you're facing.")
    error_desc = listener.listen(timeout=10, phrase_time_limit=10)
    if not error_desc:
        return "I didn't catch that. Please describe your error again."

    speak("Is it a runtime error or a logic error?")
    error_type = listener.listen(timeout=5)
    if not error_type:
        error_type = "unknown"

    return brain.debug_code(error_desc, error_type)


def code_complexity(description: str) -> str:
    """Analyze time and space complexity of an algorithm."""
    if not description.strip():
        return "Please describe the algorithm."
    return brain.get_complexity(description)


def generate_code(description: str) -> str:
    """Generate code from description and type it or save to file."""
    if not description.strip():
        return "What code should I generate?"

    speak("Generating code. This may take a moment.")
    code = brain.ask_code(description)

    speak("Should I type it into the current window, or save it to a file?")
    choice = listener.listen(timeout=5)

    if choice and "file" in choice:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_code_{timestamp}.py"
        filepath = NOTES_DIR / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            return f"Code saved to {filename}."
        except Exception as e:
            return f"Failed to save file: {e}"
    else:
        # Type it
        speak("Switch to your target window. Typing in 3 seconds.")
        time.sleep(3)
        try:
            # Extract code from markdown code blocks if present
            clean_code = re.sub(r'```python\n?', '', code)
            clean_code = re.sub(r'```\n?', '', clean_code)
            pyautogui.typewrite(clean_code, interval=0.01)
            return "Code typed into the active window."
        except Exception as e:
            return f"Failed to type code: {e}"


def interview_prep(topic: str) -> str:
    """Get interview questions on a topic using Groq AI."""
    if not topic.strip():
        return "What topic should I prepare interview questions for?"

    prompt = (
        f"Generate 3 technical interview questions about {topic} "
        f"for a computer science interview. Make them progressively harder. "
        f"Format as a numbered list with brief answers."
    )
    return brain.ask_jarvis(prompt)


def explain_error(error_text: str) -> str:
    """Explain a programming error message."""
    if not error_text.strip():
        return "What error message should I explain?"

    prompt = (
        f"Explain this programming error message in simple terms: '{error_text}'. "
        f"Provide 3 possible fixes. Keep it concise."
    )
    return brain.ask_jarvis(prompt)


# ============================================================
# NOTES SYSTEM
# ============================================================

def create_note() -> str:
    """Create a note by listening to user dictation."""
    speak("What should I note down?")
    content = listener.listen(timeout=10, phrase_time_limit=15)
    if not content:
        return "I didn't catch that. Note cancelled."

    speak("What topic is this note about?")
    topic = listener.listen(timeout=5)
    if not topic:
        topic = "general"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{topic.replace(' ', '_')}_{timestamp}.txt"
    filepath = NOTES_DIR / filename

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Topic: {topic}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Content:\n{content}\n")

        memory.save_note_ref(filename, topic)
        return f"Note saved as {filename}."
    except Exception as e:
        return f"Failed to save note: {e}"


def read_last_note() -> str:
    """Read the most recent note file."""
    try:
        notes = sorted(NOTES_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not notes:
            return "No notes found."

        with open(notes[0], 'r', encoding='utf-8') as f:
            content = f.read()
        return f"Last note: {content[:500]}"
    except Exception as e:
        return f"Could not read note: {e}"


def list_notes() -> str:
    """List the last 5 note filenames."""
    try:
        notes = sorted(NOTES_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not notes:
            return "No notes found."

        note_list = [f"{i+1}. {n.name}" for i, n in enumerate(notes[:5])]
        return "Recent notes:\n" + "\n".join(note_list)
    except Exception as e:
        return f"Could not list notes: {e}"


# ============================================================
# FUN AND PERSONALITY
# ============================================================

MOTIVATIONAL_QUOTES: List[str] = [
    "The best way to predict the future is to implement it. Keep coding!",
    "Every expert was once a beginner. Every pro was once an amateur.",
    "It's not a bug, it's an undocumented feature.",
    "First, solve the problem. Then, write the code.",
    "Code is like humor. When you have to explain it, it's bad.",
    "The only way to learn a new programming language is by writing programs in it.",
    "Simplicity is the soul of efficiency.",
    "Make it work, make it right, make it fast.",
    "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.",
    "Don't worry if it doesn't work right. If everything did, you'd be out of a job.",
    "Programming isn't about what you know; it's about what you can figure out.",
    "The most damaging phrase in the language is: It's always been done this way.",
    "Talk is cheap. Show me the code.",
    "A good programmer is someone who always looks both ways before crossing a one-way street.",
    "The code you write today will be the legacy you leave tomorrow.",
]


def tell_joke() -> str:
    """Tell a programming joke."""
    try:
        return pyjokes.get_joke(category='neutral')
    except Exception:
        return "Why do programmers prefer dark mode? Because light attracts bugs."


def motivate() -> str:
    """Return a random motivational CS-themed quote."""
    return random.choice(MOTIVATIONAL_QUOTES)


def roast_me() -> str:
    """Get a tech roast from Groq AI."""
    prompt = (
        "Give a lighthearted, funny tech/programming roast. "
        "Keep it under 2 sentences. Be clever but not mean."
    )
    return brain.ask_jarvis(prompt)


def fun_fact() -> str:
    """Get a CS fun fact from Groq AI."""
    prompt = "Tell me an interesting and surprising computer science fun fact. Keep it under 2 sentences."
    return brain.ask_jarvis(prompt)


def flip_coin() -> str:
    """Flip a coin."""
    return f"It's {'Heads' if random.choice([True, False]) else 'Tails'}."


def roll_dice(sides: int = 6) -> str:
    """Roll a dice with given number of sides (default 6)."""
    try:
        sides = int(sides)
        if sides < 2:
            sides = 6
    except (ValueError, TypeError):
        sides = 6
    result = random.randint(1, sides)
    return f"Rolled a {result} on a {sides}-sided dice."


def calculate(expression: str) -> str:
    """Safely evaluate a math expression."""
    if not expression or not expression.strip():
        return "What should I calculate?"

    try:
        # Normalize input
        expr = expression.lower().strip()

        # Handle natural language
        expr = expr.replace("percent", "/100")
        expr = expr.replace("percentage", "/100")
        expr = expr.replace("modulo", "%")
        expr = expr.replace("mod", "%")
        expr = expr.replace("to the power", "**")
        expr = expr.replace("power", "**")
        expr = expr.replace("squared", "**2")
        expr = expr.replace("cubed", "**3")
        expr = expr.replace("square root of", "math.sqrt")
        expr = expr.replace("sqrt of", "math.sqrt")
        expr = expr.replace("cube root of", "(lambda x: x**(1/3))")
        expr = expr.replace("of", "*")
        expr = expr.replace("times", "*")
        expr = expr.replace("x", "*")
        expr = expr.replace("divided by", "/")
        expr = expr.replace("divide by", "/")
        expr = expr.replace("over", "/")
        expr = expr.replace("plus", "+")
        expr = expr.replace("minus", "-")
        expr = expr.replace("subtracted by", "-")

        # Extract just the math expression using regex
        # Allow: digits, operators, parentheses, math functions, decimal points
        allowed_pattern = r'[\d\+\-\*\/\%\(\)\.\,\s\*\*]+|math\.\w+|lambda\s+x\s*:\s*x\*\*\(1/3\)'
        matches = re.findall(allowed_pattern, expr)
        clean_expr = ''.join(matches).strip()

        if not clean_expr:
            return "I couldn't understand that math expression."

        # Safe eval with limited globals
        safe_globals = {"__builtins__": {}, "math": math}
        result = eval(clean_expr, safe_globals)

        # Format result
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 4)

        return f"The answer is {result}."

    except ZeroDivisionError:
        return "Cannot divide by zero."
    except Exception:
        return "I couldn't calculate that. Try something like '15 percent of 3400' or '2 to the power 10'."


# ============================================================
# DAILY ASSISTANT
# ============================================================

# Active reminders storage
_active_reminders: List[threading.Thread] = []


def set_reminder(time_str: str, message: str) -> str:
    """Set a reminder that speaks after given time."""
    try:
        # Parse time string like "5 minutes", "1 hour", "30 seconds"
        time_lower = time_str.lower().strip()
        total_seconds = 0

        # Extract all number+unit pairs
        patterns = [
            (r'(\d+)\s*hour', 3600),
            (r'(\d+)\s*hr', 3600),
            (r'(\d+)\s*minute', 60),
            (r'(\d+)\s*min', 60),
            (r'(\d+)\s*second', 1),
            (r'(\d+)\s*sec', 1),
        ]

        for pattern, multiplier in patterns:
            matches = re.findall(pattern, time_lower)
            for match in matches:
                total_seconds += int(match) * multiplier

        if total_seconds <= 0:
            # Try plain number as minutes
            numbers = re.findall(r'\d+', time_lower)
            if numbers:
                total_seconds = int(numbers[0]) * 60
            else:
                return "I didn't understand the time. Say something like '5 minutes' or '1 hour'."

        if total_seconds > 86400:  # Max 24 hours
            return "I can only set reminders up to 24 hours."

        def reminder_thread(seconds: int, msg: str):
            time.sleep(seconds)
            speak(f"Reminder: {msg}")

        t = threading.Thread(target=reminder_thread, args=(total_seconds, message), daemon=True)
        t.start()
        _active_reminders.append(t)

        # Format human-readable time
        mins, secs = divmod(total_seconds, 60)
        hrs, mins = divmod(mins, 60)
        time_parts = []
        if hrs > 0:
            time_parts.append(f"{hrs} hour{'s' if hrs > 1 else ''}")
        if mins > 0:
            time_parts.append(f"{mins} minute{'s' if mins > 1 else ''}")
        if secs > 0 and hrs == 0:
            time_parts.append(f"{secs} second{'s' if secs > 1 else ''}")
        time_readable = " ".join(time_parts)

        return f"Reminder set for {time_readable}: {message}."

    except Exception as e:
        return f"Could not set reminder: {e}"


def morning_briefing() -> str:
    """Provide a morning briefing with time, weather, and motivation."""
    # Current time and date
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")

    # Weather
    weather = get_weather()

    # Motivational quote
    quote = motivate()

    briefing = (
        f"Good morning, {OWNER_NAME}. It's {time_str} on {date_str}. "
        f"{weather} "
        f"Here's your motivation: {quote}"
    )

    return briefing


# ============================================================
# POMODORO TIMER
# ============================================================

_pomodoro_active = False


def pomodoro_timer(minutes: int = 25) -> str:
    """Run a Pomodoro timer with voice checkpoints."""
    global _pomodoro_active

    try:
        minutes = int(minutes)
        if minutes < 1:
            minutes = 25
        if minutes > 120:
            minutes = 120
    except (ValueError, TypeError):
        minutes = 25

    _pomodoro_active = True

    def pomodoro_thread(mins: int):
        global _pomodoro_active
        speak(f"Pomodoro started for {mins} minutes. Focus!")

        total_seconds = mins * 60
        checkpoint_interval = 300  # 5 minutes
        elapsed = 0

        while elapsed < total_seconds and _pomodoro_active:
            time.sleep(min(checkpoint_interval, total_seconds - elapsed))
            elapsed += checkpoint_interval

            if not _pomodoro_active:
                return

            remaining = total_seconds - elapsed
            if remaining > 0:
                mins_left = remaining // 60
                speak(f"{mins_left} minutes remaining. Stay focused!")

        if _pomodoro_active:
            speak("Pomodoro complete! Time for a break. Stretch and rest your eyes.")
            _pomodoro_active = False

    t = threading.Thread(target=pomodoro_thread, args=(minutes,), daemon=True)
    t.start()

    return f"Pomodoro timer started for {minutes} minutes."


def stop_pomodoro() -> str:
    """Stop the active pomodoro timer."""
    global _pomodoro_active
    if _pomodoro_active:
        _pomodoro_active = False
        return "Pomodoro stopped."
    return "No active pomodoro timer."


# ============================================================
# UTILITY COMMANDS
# ============================================================

def get_time() -> str:
    """Return current time."""
    return f"It's {datetime.now().strftime('%I:%M %p')}."


def get_date() -> str:
    """Return current date."""
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."


def shutdown_jarvis() -> str:
    """Graceful shutdown message."""
    return "Shutting down. Goodbye!"


# Export all command functions
__all__ = [
    # PC Control
    'open_app', 'close_app', 'volume_control', 'brightness_control',
    'take_screenshot', 'get_system_info', 'pc_sleep', 'pc_restart',
    # Clipboard
    'copy_to_clipboard', 'read_clipboard', 'clear_clipboard',
    # Typing
    'type_text',
    # Web
    'open_website', 'search_web', 'get_weather',
    # CSE Features
    'explain_concept', 'debug_assistant', 'code_complexity',
    'generate_code', 'interview_prep', 'explain_error',
    # Notes
    'create_note', 'read_last_note', 'list_notes',
    # Fun
    'tell_joke', 'motivate', 'roast_me', 'fun_fact',
    'flip_coin', 'roll_dice', 'calculate',
    # Daily
    'set_reminder', 'morning_briefing',
    # Pomodoro
    'pomodoro_timer', 'stop_pomodoro',
    # Utility
    'get_time', 'get_date', 'shutdown_jarvis',
    # Dictionaries
    'APP_PATHS', 'WEBSITE_URLS', 'SEARCH_ENGINES',
]
