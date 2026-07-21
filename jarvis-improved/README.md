# JARVIS v2 — AI Voice Assistant

A lightweight, cross-platform AI voice assistant powered by **Groq API** (Llama 3). Voice or text control, persistent chat history, document Q&A (RAG), and agent tool calling.

> Forked from [JARVIS-v0](https://github.com/talibmakhdum/JARVIS-v0) by talibmakhdum. Rewritten with proper packaging, cross-platform support, tests, and security fixes.

## Quick Start

```bash
git clone <this repo> && cd jarvis-improved
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[all]"
cp .env.example .env  # → add your GROQ_API_KEY
jarvis                 # auto-detects GUI / terminal
jarvis --terminal      # force terminal
jarvis --voice         # force voice mode
jarvis --gui           # force GUI
```

Get a **free** Groq key at [console.groq.com/keys](https://console.groq.com/keys).

## Commands

| Say / Type | Action |
|---|---|
| `open firefox` | Launch app (cross-platform) |
| `close chrome` | Close app |
| `volume up/down/mute` | Volume control |
| `screenshot` | Take a screenshot |
| `system info` | CPU, RAM, disk, battery |
| `go to github` | Open a website |
| `search for python tutorials` | Google search |
| `weather in Delhi` | Current weather |
| `create note` / `read my note` / `list notes` | Voice notes |
| `what time is it` / `what's the date` | Time & date |
| `set reminder 5 mins drink water` | Timed reminder |
| `morning briefing` | Time + weather + greeting |
| `tell me a joke` / `motivate me` / `flip a coin` | Fun |
| `calculate 15 percent of 3000` | Calculator |
| `explain quicksort` / `complexity of binary search` | CS tools (via AI) |
| Anything else | Sent to AI brain (Llama 3) |

## Project Structure

```
jarvis-improved/
├── jarvis/
│   ├── __init__.py      # Package version
│   ├── __main__.py      # CLI entry point
│   ├── config.py        # Settings, platform utils, security
│   ├── voice.py         # TTS + STT (graceful fallback)
│   ├── brain.py         # Groq API + conversation memory
│   ├── commands.py      # All commands (PC, web, notes, daily, fun, CSE)
│   ├── tools.py         # Agent tools (search, calc, files, system, datetime)
│   ├── chat_db.py       # SQLite chat history
│   ├── rag.py           # Document Q&A (ChromaDB + embeddings)
│   └── ui.py            # CustomTkinter dark GUI
├── pyproject.toml       # Packaging + dependencies
├── README.md
├── LICENSE              # MIT
└── .env.example
```

**13 files. 1 package. No bloat.**

## Optional Dependencies

Install only what you need:

```bash
pip install -e ".[voice]"  # Microphone + TTS
pip install -e ".[gui]"    # Volume, brightness, screenshots
pip install -e ".[ui]"     # Dark-themed GUI
pip install -e ".[rag]"    # Document Q&A (~500MB model)
pip install -e ".[fun]"    # Jokes
pip install -e ".[all]"    # Everything
```

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Free at [console.groq.com](https://console.groq.com/keys) |
| `OWNER_NAME` | `Boss` | How JARVIS addresses you |
| `CITY` | `New Delhi` | Default weather city |
| `WAKE_WORD` | `jarvis` | Voice activation word |
| `AI_MODEL` | `llama-3.1-8b-instant` | Groq model |
| `AGENT_TOOLS_ENABLED` | `true` | Tool calling |
| `RAG_ENABLED` | `true` | Document Q&A |

## Known Limitations

- Voice input needs a working mic + `pyaudio`
- Brightness control requires supported display drivers
- RAG downloads ~500MB embedding model on first use
- Groq free tier has rate limits
- App discovery uses `PATH` — apps not on PATH may not be found
- Security checks are heuristic — not a true sandbox

## License

[MIT](LICENSE) — originally forked from [JARVIS-v0](https://github.com/talibmakhdum/JARVIS-v0).
