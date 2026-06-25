"""
JARVIS v3 - Central Configuration
=================================
Customize JARVIS without touching the main code.
Edit this file to add apps, websites, or change behavior.
"""

# ============================================================
# VOICE SETTINGS
# ============================================================

# Preferred Windows TTS voices (in order of preference)
PREFERRED_VOICES = ["zira", "david", "hazel", "susan", "anna"]

# Default voice speed (words per minute)
DEFAULT_VOICE_SPEED = 172

# ============================================================
# WAKE WORD
# ============================================================

WAKE_WORD = "jarvis"  # Say this to activate JARVIS

# How long JARVIS stays active after wake word (seconds)
ACTIVATION_TIMEOUT = 8

# ============================================================
# MEMORY SETTINGS
# ============================================================

# Maximum conversation history messages (excluding system prompt)
MAX_CONVERSATION_MEMORY = 30

# ============================================================
# PATHS
# ============================================================

# These are relative to the jarvis_main.py location
MEMORY_FOLDER = "memory"
NOTES_FOLDER = "notes"
SCREENSHOTS_FOLDER = "screenshots"
LOGS_FOLDER = "logs"

# ============================================================
# APPLICATION SHORTCUTS
# ============================================================
# Add your own apps here. Format:
# "app name": ["path/to/executable.exe", "fallback_path.exe"]

CUSTOM_APPS = {
    # Examples (uncomment and modify for your system):
    # "cursor": [r"C:\Users\%USERNAME%\AppData\Local\Programs\cursor\Cursor.exe"],
    # "postman": [r"C:\Users\%USERNAME%\AppData\Local\Postman\Postman.exe"],
    # "docker": [r"C:\Program Files\Docker\Docker\Docker Desktop.exe"],
    # "steam": [r"C:\Program Files (x86)\Steam\Steam.exe"],
    # "epic": [r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe"],
}

# Apps safe to force-close via taskkill
SAFE_TO_CLOSE = [
    "notepad.exe", "mspaint.exe", "calc.exe", "vlc.exe",
    "chrome.exe", "brave.exe", "firefox.exe", "msedge.exe",
    "code.exe", "spotify.exe", "obs64.exe", "winword.exe",
    "excel.exe", "powerpnt.exe", "notepad++.exe",
]

# ============================================================
# WEBSITE SHORTCUTS
# ============================================================
# Add your own websites here. Format:
# "site name": "https://url.com"

CUSTOM_WEBSITES = {
    # Examples (uncomment and add your own):
    # "myportfolio": "https://yourname.github.io",
    # "chat": "https://chat.openai.com",
    # "localhost": "http://localhost:3000",
}

# ============================================================
# SEARCH ENGINES
# ============================================================

SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
    "github": "https://github.com/search?q={}",
    "stackoverflow": "https://stackoverflow.com/search?q={}",
    "leetcode": "https://leetcode.com/search/?q={}",
    "geeksforgeeks": "https://www.geeksforgeeks.org/search/?q={}",
    "bing": "https://www.bing.com/search?q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
}

# ============================================================
# GROQ AI SETTINGS
# ============================================================

# AI model to use (free tier on Groq)
AI_MODEL = "llama3-8b-8192"

# Maximum tokens per response
MAX_TOKENS = 512

# Temperature (creativity): 0.0 = deterministic, 1.0 = very creative
TEMPERATURE = 0.7

# ============================================================
# POMODORO DEFAULTS
# ============================================================

DEFAULT_POMODORO_MINUTES = 25
MAX_POMODORO_MINUTES = 120
POMODORO_CHECKPOINT_MINUTES = 5

# ============================================================
# HUD SETTINGS
# ============================================================

HUD_WIDTH = 320
HUD_HEIGHT = 180
HUD_OPACITY = 0.88  # 0.0 = fully transparent, 1.0 = opaque
HUD_POSITION = "bottom-right"  # Options: bottom-right, bottom-left, top-right, top-left

# ============================================================
# MOTIVATIONAL QUOTES
# ============================================================
# Add your own quotes here

EXTRA_QUOTES = [
    # "Your custom quote here.",
    # "Another inspiring quote.",
]

# ============================================================
# TROUBLESHOOTING
# ============================================================

# Common fixes for common problems:
# - Mic not working: Check Windows Privacy settings > Microphone
# - Groq errors: Verify your API key at console.groq.com
# - TTS not working: Install Windows Media Features
# - Import errors: Run install.bat again
# - pyautogui fails: Don't move mouse to screen corners during typing
