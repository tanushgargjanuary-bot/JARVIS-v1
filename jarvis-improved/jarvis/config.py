"""
JARVIS configuration — settings loader + platform utilities.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path.cwd()
MEMORY_DIR = BASE_DIR / "memory"
NOTES_DIR = BASE_DIR / "notes"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
LOGS_DIR = BASE_DIR / "logs"
RAG_DIR = BASE_DIR / "rag"
for _d in [MEMORY_DIR, NOTES_DIR, SCREENSHOTS_DIR, LOGS_DIR, RAG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# ── Env helpers ──────────────────────────────────────────────────────────
def _e(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def _eb(key: str, default: bool = False) -> bool:
    return _e(key, str(default)).strip().lower() in ("true", "1", "yes")

def _ei(key: str, default: int = 0) -> int:
    try: return int(_e(key, str(default)))
    except ValueError: return default

def _ef(key: str, default: float = 0.0) -> float:
    try: return float(_e(key, str(default)))
    except ValueError: return default

# ── Settings ─────────────────────────────────────────────────────────────
GROQ_API_KEY: str = _e("GROQ_API_KEY", "")
OWNER_NAME: str = _e("OWNER_NAME", "Boss")
CITY: str = _e("CITY", "New Delhi")
WAKE_WORD: str = _e("WAKE_WORD", "jarvis").lower()
VOICE_SPEED: int = _ei("VOICE_SPEED", 172)
VOICE_ENABLED: bool = _eb("VOICE_ENABLED", True)
AI_MODEL: str = _e("AI_MODEL", "llama-3.1-8b-instant")
MAX_TOKENS: int = _ei("MAX_TOKENS", 512)
TEMPERATURE: float = _ef("TEMPERATURE", 0.7)
MAX_MEMORY: int = _ei("MAX_MEMORY", 30)
AGENT_TOOLS_ENABLED: bool = _eb("AGENT_TOOLS_ENABLED", True)
RAG_ENABLED: bool = _eb("RAG_ENABLED", True)

def validate() -> list[str]:
    warnings: list[str] = []
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_key_here":
        warnings.append(
            "GROQ_API_KEY not set. AI features won't work. "
            "Get a free key at https://console.groq.com/keys"
        )
    return warnings

# ── Platform helpers ─────────────────────────────────────────────────────
def is_windows() -> bool: return platform.system().lower() == "windows"
def is_macos() -> bool: return platform.system().lower() == "darwin"

def find_exe(name: str) -> str | None:
    return shutil.which(name)

def safe_resolve(base: Path, user_path: str) -> Path | None:
    """Resolve user_path under base; return None if it escapes."""
    resolved = (base / user_path).resolve()
    return resolved if resolved.is_relative_to(base.resolve()) else None

# ── Security ─────────────────────────────────────────────────────────────
_BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "ctypes", "socket", "http",
    "urllib", "requests", "webbrowser", "signal", "threading",
    "multiprocessing", "pickle", "marshal", "importlib", "builtins",
}
_BLOCKED_CMDS = {"rm -rf /", "mkfs", "format", "del /", "shutdown", "reboot"}

def validate_python(code: str) -> tuple[bool, str]:
    import ast
    try: tree = ast.parse(code)
    except SyntaxError as e: return False, f"Syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = ([a.name.split(".")[0] for a in node.names]
                     if isinstance(node, ast.Import)
                     else [node.module.split(".")[0]] if node.module else [])
            for n in names:
                if n in _BLOCKED_IMPORTS:
                    return False, f"Blocked import: {n}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"exec", "eval", "compile", "__import__"}:
                return False, f"Blocked call: {node.func.id}()"
    return True, "OK"

def redact_key(text: str) -> str:
    return re.sub(r"(sk-[A-Za-z0-9]{16,}|gsk_[A-Za-z0-9]{16,})", "****", text)
