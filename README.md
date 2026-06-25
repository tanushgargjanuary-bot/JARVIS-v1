# JARVIS v4 - Upgraded AI Voice Assistant

A fully-featured, free-to-use AI voice assistant for Windows built in Python. JARVIS can control your PC, browse the web, help with coding, manage notes, hold conversations with persistent history, answer questions about your documents (RAG), and execute multi-agent tool calls — all through voice or text commands.

## What's New in v4

### Major Upgrades from v3

| Feature | v3 | v4 |
|---------|-----|-----|
| **UI** | Basic Tkinter HUD | Modern CustomTkinter with sidebar, tabs, dark theme |
| **Chat History** | In-memory only (lost on restart) | Persistent SQLite database with search |
| **Document Q&A** | Not available | Full RAG with ChromaDB + embeddings |
| **AI Tools** | Basic text responses | Multi-agent tool calling (web search, Python, calculator, files) |
| **System Prompt** | Generic assistant | Tool-aware, RAG-aware, document-aware |

### v4 New Features

- **Modern CustomTkinter HUD** — Professional dark theme with sidebar navigation, multiple tabs (Chat, History, Documents, Document Q&A, Agent Tools, Settings)
- **Persistent Chat History** — SQLite database stores all conversations, searchable, with conversation management
- **RAG Document Q&A** — Upload PDFs, TXT, DOCX, code files and ask questions about them. Uses ChromaDB vector search + sentence-transformer embeddings
- **Multi-Agent Tool Calling** — AI can use tools: web search, Python execution, calculator, file operations, system info, datetime, shell commands
- **Document Upload Interface** — Drag-and-drop style file upload with indexing progress
- **Conversation Management** — Create, search, pin, and delete conversations
- **Settings Panel** — Configure API key, voice speed, wake word, theme (Dark/Light/System)

## Feature Overview

### PC Control
- Open/close 25+ applications (Chrome, VS Code, Discord, Spotify, etc.)
- Volume control (up/down/mute/set percentage)
- Screen brightness control
- Take screenshots
- System info (CPU, RAM, battery, disk, uptime)
- Sleep and restart commands

### Web
- Open 40+ websites by name
- Search Google, YouTube, GitHub, StackOverflow, and more
- Weather for your configured city
- **NEW**: Web search via DuckDuckGo (agent tool)

### CSE Student Tools
- Code explanations
- Debugging assistant
- Time/space complexity analysis
- Code generation with auto-typing
- Interview preparation questions
- Error message explanations

### Notes
- Voice dictation to text files
- Read back notes
- List all notes

### Fun & Personality
- Programming jokes
- Motivational quotes
- Tech roasts
- Fun facts
- Coin flip and dice roll

### Daily Assistant
- Morning briefing (time + weather + motivation)
- Reminders with voice alerts
- Pomodoro timer with voice checkpoints
- Calculator (natural language math)

### NEW: Chat History & Memory
- All conversations saved to SQLite database
- Search through past conversations
- Create multiple chat sessions
- Pin important conversations
- View chat statistics

### NEW: RAG Document Q&A
- Upload PDF, TXT, DOCX, MD, Python, JS, HTML, CSS, JSON, CSV files
- Automatic text chunking and embedding
- Vector search with similarity scores
- AI answers based on your document content
- Document management dashboard

### NEW: Multi-Agent Tools
The AI can autonomously use these tools when needed:
- `web_search` — Search DuckDuckGo for current info
- `run_python` — Execute Python code safely
- `calculator` — Advanced math (algebra, trig, logs)
- `file_operations` — Read/write/list/search files
- `system_info` — Detailed system statistics
- `datetime_tool` — Date/time queries and calculations
- `shell_command` — Safe shell command execution

## Quick Start (5 Steps)

### Step 1: Download and Extract
Download the JARVIS v4 folder to your Windows PC.

### Step 2: Install Dependencies
```batch
cd jarvis_v4
install.bat
```
This installs all Python packages and creates required folders.

**For v4 upgrade specifically:**
```batch
pip install -r requirements.txt
```

### Step 3: Get Your Free Groq API Key
1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Create a free account
3. Generate an API key
4. Copy the key

### Step 4: Configure
```batch
notepad .env
```
Paste your key:
```env
GROQ_API_KEY=gsk_your_actual_key_here
OWNER_NAME=YourName
CITY=YourCity
WAKE_WORD=jarvis
```

### Step 5: Run JARVIS
```batch
run.bat
```
Or for text-only mode:
```batch
run_text_mode.bat
```

## File Structure

```
jarvis_v4/
|-- .env                  # Your API keys and settings (create this)
|-- .env.example          # Template for .env
|-- jarvis_main.py        # Entry point - main controller
|-- jarvis_core.py        # Voice engine, AI brain, memory
|-- jarvis_commands.py    # All voice commands
|-- jarvis_hud.py         # Modern CustomTkinter GUI
|-- jarvis_chat_db.py     # SQLite chat history database
|-- jarvis_rag.py         # RAG document Q&A system
|-- jarvis_agent_tools.py # Multi-agent tool calling
|-- jarvis_config.py      # Central configuration
|-- requirements.txt      # Python dependencies
|-- install.bat           # One-click installer
|-- run.bat               # Launch JARVIS
|-- run_text_mode.bat     # Text-only mode
|-- memory/               # Auto-created (chat DB, facts)
|-- notes/                # Auto-created (voice notes)
|-- screenshots/          # Auto-created
|-- logs/                 # Auto-created (session logs)
|-- rag/                  # Auto-created (documents + vector DB)
|   |-- documents/        # Uploaded files
|   |-- chroma_db/        # Vector database
```

## System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.9+ (3.11 recommended)
- **RAM**: 4GB minimum (8GB recommended for RAG)
- **Disk**: 2GB free space (for models and vector DB)
- **Microphone**: For voice control (optional - text mode available)
- **Internet**: Required for Groq API and web search

## Voice Commands Reference

### Wake Word Detection
Say **"Jarvis"** (or your configured wake word) to activate.

### Command Categories

**PC Control:**
- "Open Chrome" / "Launch VS Code" / "Start Spotify"
- "Close Chrome" / "Kill Discord"
- "Volume up" / "Volume down" / "Volume mute"
- "Brightness up" / "Set brightness to 50 percent"
- "Take a screenshot"
- "System info"
- "Put PC to sleep" / "Restart PC"

**Web:**
- "Go to GitHub" / "Open YouTube"
- "Search for Python tutorials"
- "Search YouTube for lo-fi music"
- "What's the weather"

**CSE Tools:**
- "Explain quicksort"
- "Debug my code" (interactive)
- "Analyze complexity of binary search"
- "Generate code for a web scraper"
- "Prep me for interview on linked lists"
- "Explain this error: [paste error]"

**Notes:**
- "Create note" (voice dictation)
- "Read my last note"
- "List my notes"

**NEW: Document Q&A:**
- "Ask my document about [topic]"
- "What does my document say about [topic]"
- "Search document for [query]"

**General:**
- "Tell me a joke"
- "Motivate me"
- "Calculate 15 percent of 3400"
- "Set reminder in 5 minutes drink water"
- "Start pomodoro for 25 minutes"
- "Morning briefing"
- "What time is it"

## Configuration

Edit `.env` file to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key | (required) |
| `OWNER_NAME` | How JARVIS addresses you | Boss |
| `CITY` | Your city for weather | New York |
| `WAKE_WORD` | Voice activation word | jarvis |
| `VOICE_SPEED` | TTS speed (words/min) | 172 |
| `MAX_MEMORY` | Conversation memory limit | 30 |
| `AGENT_TOOLS_ENABLED` | Enable multi-agent tools | true |
| `RAG_ENABLED` | Enable document Q&A | true |

## API Key Sources

| Service | Cost | Speed | Link |
|---------|------|-------|------|
| Groq | Free tier (generous) | Ultra-fast | [console.groq.com](https://console.groq.com) |

## Troubleshooting

### Microphone Issues
- Check Windows Privacy settings → Microphone → Allow apps
- Ensure Python has microphone permission
- Try text mode: `run_text_mode.bat`

### Import Errors
```batch
pip install -r requirements.txt
```

### CustomTkinter not found
```batch
pip install customtkinter Pillow
```

### ChromaDB / RAG Issues
- Requires ~500MB for first download of embedding model
- The model downloads automatically on first use
- Ensure you have disk space in the project folder

### Groq API Errors
- Verify your API key is correct in `.env`
- Check internet connection
- Free tier has rate limits (wait a moment and retry)

### pyautogui fails
- Don't move mouse to screen corners during typing
- Run as administrator if needed for some controls

## Architecture

```
User Input (Voice/Text)
    |
    v
[jarvis_main.py] Command Processor
    |
    +---> PC Commands [jarvis_commands.py]
    +---> Web Commands [jarvis_commands.py]
    +---> CSE Tools [jarvis_commands.py]
    +---> RAG Q&A [jarvis_rag.py] -----> ChromaDB + Embeddings
    +---> Agent Tools [jarvis_agent_tools.py] -----> Groq Function Calling
    +---> Basic AI [jarvis_core.py] -----> Groq API
    |
    v
[jarvis_chat_db.py] SQLite Persistence
    |
    v
[jarvis_hud.py] CustomTkinter UI Display
```

## License

Free to use for personal and educational purposes. Built for CSE students and developers.

## Credits

- **AI Brain**: Groq API (Llama 3)
- **Voice**: pyttsx3 + SpeechRecognition
- **UI**: CustomTkinter
- **Vector DB**: ChromaDB
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Built by**: Students, for students

---

**JARVIS v4** - Your AI assistant just got a major upgrade.
