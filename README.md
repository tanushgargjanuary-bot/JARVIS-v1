# JARVIS v3 - AI Voice Assistant for Windows

A fully-featured, free-to-use AI voice assistant for Windows built in Python. JARVIS can control your PC, browse the web, help with coding, manage notes, and hold conversations — all through voice commands.

---

## Features

| Category | Features |
|----------|----------|
| **PC Control** | Open/close apps, volume, brightness, screenshots, system info, sleep/restart |
| **Web** | Open 40+ websites, search Google/YouTube/GitHub/StackOverflow, weather |
| **CSE Student Tools** | Code explanations, debugging assistant, complexity analysis, code generation, interview prep |
| **Notes** | Voice dictation to text files, read back notes, list all notes |
| **Fun** | Jokes, motivational quotes, roasts, fun facts, coin flip, dice roll |
| **Daily Assistant** | Reminders, morning briefing, Pomodoro timer, calculator |
| **HUD Overlay** | Floating status window with real-time indicators |

---

## Quick Start (5 Steps)

### Step 1: Download and Extract
```
Download the JARVIS v3 folder to your Windows PC
```

### Step 2: Install Dependencies
```cmd
cd jarvis_v3
install.bat
```
This installs all Python packages and creates required folders.

### Step 3: Get Your Free Groq API Key
1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Create a free account
3. Generate an API key
4. Copy the key

### Step 4: Configure
```cmd
notepad .env
```
Paste your API key and set your name:
```env
GROQ_API_KEY=gsk_your_actual_key_here
OWNER_NAME=YourName
CITY=YourCity
WAKE_WORD=jarvis
VOICE_SPEED=172
MAX_MEMORY=30
```

### Step 5: Launch
```cmd
run.bat
```

Or for text-only mode (no microphone):
```cmd
run_text_mode.bat
```

---

## Complete Voice Command List

### Basic
| Say This | What Happens |
|----------|-------------|
| "Jarvis" | Activates listening mode |
| "Hello" / "Hey" | Greeting |
| "Goodbye" / "Shutdown" | Closes JARVIS |
| "What time is it" | Tells current time |
| "What day is it" | Tells date |

### PC Control
| Say This | What Happens |
|----------|-------------|
| "Open Chrome" | Launches Google Chrome |
| "Open VS Code" | Launches Visual Studio Code |
| "Close Notepad" | Closes Notepad safely |
| "Volume up" / "Volume down" | Adjusts system volume |
| "Volume mute" | Toggles mute |
| "Set volume to 50 percent" | Sets exact volume level |
| "Brightness up" / "Brightness down" | Adjusts screen brightness |
| "Set brightness to 30 percent" | Sets exact brightness |
| "Take screenshot" | Saves screenshot to screenshots/ folder |
| "System info" | Reports CPU, RAM, battery, disk, uptime |

### Web
| Say This | What Happens |
|----------|-------------|
| "Open YouTube" | Opens youtube.com |
| "Open GitHub" | Opens github.com |
| "Open LeetCode" | Opens leetcode.com |
| "Search for Python tutorials" | Opens Google search |
| "Search YouTube for lofi music" | Opens YouTube search |
| "Weather" | Reports weather for your city |

### Coding Help
| Say This | What Happens |
|----------|-------------|
| "Explain recursion" | 3-sentence explanation |
| "Debug my code" | Interactive debugging session |
| "Generate code for binary search" | Types or saves code |
| "Interview prep on linked lists" | 3 questions with answers |
| "What is the complexity of quicksort" | Big O analysis |

### Notes
| Say This | What Happens |
|----------|-------------|
| "Create note" | Dictates and saves a text file |
| "Read my last note" | Reads most recent note |
| "List my notes" | Shows last 5 notes |

### Productivity
| Say This | What Happens |
|----------|-------------|
| "Pomodoro timer" | Starts 25-min focus timer |
| "Pomodoro 45 minutes" | Custom Pomodoro duration |
| "Remind me in 5 minutes drink water" | Sets voice reminder |
| "Morning briefing" | Time, weather, motivation |
| "Calculate 15 percent of 3400" | Math solver |

### Fun
| Say This | What Happens |
|----------|-------------|
| "Tell me a joke" | Programming joke |
| "Motivate me" | CS-themed motivational quote |
| "Roast me" | AI-generated tech roast |
| "Fun fact" | CS fun fact |
| "Flip a coin" | Heads or tails |
| "Roll a dice" | Random 1-6 |
| "Roll a 20-sided dice" | Random 1-20 |

### Other
| Say This | What Happens |
|----------|-------------|
| "Type this [text]" | Types text at cursor |
| "Read clipboard" | Reads clipboard aloud |
| "Copy to clipboard [text]" | Copies text to clipboard |
| "Session info" | Shows session stats |
| "Morning briefing" | Time + weather + quote |

---

## File Overview

| File | Purpose |
|------|---------|
| `jarvis_main.py` | Main entry point - startup, wake word, command loop |
| `jarvis_core.py` | Voice engine, AI brain (Groq), memory system |
| `jarvis_commands.py` | All 30+ voice commands |
| `jarvis_hud.py` | Floating status overlay |
| `jarvis_config.py` | Easy customization file |
| `test_jarvis.py` | Component test suite |
| `run.bat` | Normal launcher (voice mode) |
| `run_text_mode.bat` | Text-only launcher |
| `install.bat` | One-click dependency installer |
| `requirements.txt` | Python package list |
| `.env` | Your private API keys (not in git) |
| `.env.example` | Template for .env |

---

## Troubleshooting

### "Python not found"
- Install Python 3.10+ from [python.org](https://python.org)
- Check "Add Python to PATH" during installation

### "No module named X"
```cmd
pip install -r requirements.txt
```

### "Groq API error"
- Check your API key in `.env` file
- Get a new key at [console.groq.com/keys](https://console.groq.com/keys)

### "Microphone not working"
- Windows Settings > Privacy > Microphone > Allow apps to access microphone
- Try text mode: `run_text_mode.bat`

### "No voice output"
- Install Windows Media Features
- Go to Windows Settings > Time & Language > Speech
- Install a voice pack (e.g., Microsoft Zira, David)

### "Brightness control not working"
- Some laptops need proprietary drivers
- Install `screen-brightness-control`: `pip install screen-brightness-control`

### "PyAudio install fails"
```cmd
pip install pipwin
pipwin install pyaudio
```

### HUD doesn't appear
- Make sure you're on Windows (HUD uses Windows-specific tkinter)
- Try running without other always-on-top apps

### Commands not recognized
- Speak clearly and at normal pace
- Background noise can interfere
- Try shorter, clearer phrases

### "Access denied" when closing apps
- Some system apps require admin privileges
- Only pre-approved apps can be safely closed

### General fix
```cmd
# Reinstall everything
install.bat
# Test all components
python test_jarvis.py
```

---

## How to Add New Commands

### 1. Add a new app shortcut
Edit `jarvis_config.py`:
```python
CUSTOM_APPS = {
    "myapp": [r"C:\Path\To\MyApp.exe"],
}
```

### 2. Add a new website
Edit `jarvis_config.py`:
```python
CUSTOM_WEBSITES = {
    "mysite": "https://example.com",
}
```

### 3. Add a new voice command
Edit `jarvis_commands.py` and add your function:
```python
def my_new_command(param: str) -> str:
    """Description of what it does."""
    return "Result message"
```

Then add it to `process_command()` in `jarvis_main.py`:
```python
if "my trigger phrase" in text_lower:
    speak(my_new_command(text))
    return True
```

---

## Tech Stack

| Service | Used For | Cost |
|---------|----------|------|
| **Groq API** (llama3-8b-8192) | AI brain, conversations | **Free tier** |
| **Google Speech Recognition** | Voice input (speech-to-text) | **Free** |
| **pyttsx3** | Voice output (text-to-speech) | **Free** (local) |
| **wttr.in** | Weather data | **Free** (no key) |

---

## System Requirements

- Windows 10 or 11
- Python 3.8+
- Microphone (for voice mode)
- Internet connection (for AI and speech recognition)

---

## Project Structure

```
jarvis_v3/
|-- requirements.txt          # Dependencies
|-- .env                      # API keys (private)
|-- .env.example              # Template
|-- install.bat               # Installer
|-- run.bat                   # Voice mode launcher
|-- run_text_mode.bat         # Text mode launcher
|
|-- jarvis_core.py            # Voice, AI, memory
|-- jarvis_commands.py        # All commands
|-- jarvis_hud.py             # Status overlay
|-- jarvis_main.py            # Main controller
|-- jarvis_config.py          # Customization
|-- test_jarvis.py            # Tests
|
|-- memory/                   # Saved data
|-- notes/                    # Voice notes
|-- screenshots/              # Screenshots
|-- logs/                     # Session logs
|
|-- README.md                 # This file
```

---

## License

MIT License - Free to use and modify.

**Note**: Keep your `.env` file private — it contains your API key!
