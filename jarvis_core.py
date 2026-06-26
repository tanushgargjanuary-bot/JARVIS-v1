"""
JARVIS v4 - Core Engine
=======================
Voice engine, AI brain, memory system, and config loader.
This is the heart of JARVIS. All other modules import from here.

v4 Changes:
- Supports chat database, RAG, and agent tools
- Enhanced system prompt with tool awareness
- Improved error handling and rate limiting
"""

import os
import sys
import json
import time
import random
import re
import threading
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import speech_recognition as sr
import pyttsx3
import psutil
import requests
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# SECTION A — CONFIG LOADER
# ============================================================

# Load .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = BASE_DIR / "memory"
NOTES_DIR = BASE_DIR / "notes"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
LOGS_DIR = BASE_DIR / "logs"
RAG_DIR = BASE_DIR / "rag"

# Ensure directories exist
for d in [MEMORY_DIR, NOTES_DIR, SCREENSHOTS_DIR, LOGS_DIR, RAG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OWNER_NAME = os.getenv("OWNER_NAME", "Boss")
CITY = os.getenv("CITY", "New York")
WAKE_WORD = os.getenv("WAKE_WORD", "jarvis").lower()
VOICE_SPEED = int(os.getenv("VOICE_SPEED", "172"))
MAX_MEMORY = int(os.getenv("MAX_MEMORY", "30"))
AGENT_TOOLS_ENABLED = os.getenv("AGENT_TOOLS_ENABLED", "true").lower() == "true"
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"

# Validate Groq API key
if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_key_here":
    print("[WARNING] GROQ_API_KEY not set. AI features will not work.")
    print("[INFO] Create a .env file or set the GROQ_API_KEY environment variable.")

# File paths
MEMORY_FILE = MEMORY_DIR / "jarvis_memory.json"
SESSION_LOG = LOGS_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


# ============================================================
# SECTION B — VOICE ENGINE
# ============================================================

class VoiceEngine:
    """Handles text-to-speech using pyttsx3 with Windows voice selection."""

    def __init__(self):
        self.engine = None
        self.voice_enabled = True
        self._lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        """Initialize the TTS engine with best available voice."""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', VOICE_SPEED)
            self.engine.setProperty('volume', 1.0)

            # Select best Windows voice (prefer Zira or David)
            voices = self.engine.getProperty('voices')
            preferred = ['zira', 'david', 'hazel', 'susan', 'anna']
            selected = None

            for pref in preferred:
                for v in voices:
                    if pref in v.name.lower():
                        selected = v.id
                        break
                if selected:
                    break

            if selected:
                self.engine.setProperty('voice', selected)
            elif voices:
                self.engine.setProperty('voice', voices[0].id)

        except Exception as e:
            print(f"[WARNING] TTS engine init failed: {e}")
            self.voice_enabled = False

    def _clean_text(self, text: str) -> str:
        """Remove emojis and special characters that TTS can't speak."""
        if not text:
            return ""
        # Remove emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0000200D"              # zero width joiner
            "]+", flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
        # Remove markdown-style characters
        text = text.replace('*', '').replace('_', '').replace('`', '')
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        return text.strip()

    def speak(self, text: str):
        """Speak the given text with timestamp print."""
        clean = self._clean_text(text)
        timestamp = datetime.now().strftime("%H:%M:%S")

        if not clean:
            return

        print(f"[{timestamp}] JARVIS: {clean}")

        if not self.voice_enabled or not self.engine:
            return

        try:
            with self._lock:
                self.engine.say(clean)
                self.engine.runAndWait()
        except Exception as e:
            print(f"[WARNING] TTS error: {e}")
            # Try to reinitialize
            try:
                self._init_engine()
            except Exception:
                self.voice_enabled = False

    def toggle_voice(self) -> bool:
        """Toggle voice on/off. Returns new state."""
        self.voice_enabled = not self.voice_enabled
        state = "ON" if self.voice_enabled else "OFF"
        print(f"[INFO] Voice {state}")
        return self.voice_enabled


# Global voice engine instance
voice = VoiceEngine()


def speak(text: str):
    """Convenience function to speak text."""
    voice.speak(text)


# ============================================================
# SECTION C — LISTEN ENGINE
# ============================================================

class ListenEngine:
    """Handles speech-to-text using Google Speech Recognition."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self._available = False
        self._init_microphone()

    def _init_microphone(self):
        """Initialize microphone with noise calibration."""
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                print("[INFO] Calibrating for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.recognizer.dynamic_energy_threshold = True
            self._available = True
            print("[OK] Microphone ready.")
        except Exception as e:
            print(f"[WARNING] Microphone not available: {e}")
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def listen(self, timeout: int = 5, phrase_time_limit: int = 5) -> Optional[str]:
        """
        Listen for speech and return recognized text (lowercase) or None.
        """
        if not self._available or not self.microphone:
            return None

        try:
            with self.microphone as source:
                print("[LISTENING...]")
                audio = self.recognizer.listen(source, timeout=timeout,
                                                phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print(f"[WARNING] Listen error: {e}")
            return None

        try:
            print("[PROCESSING...]")
            text = self.recognizer.recognize_google(audio).lower().strip()
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] YOU: {text}")
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[ERROR] Speech recognition service unavailable: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected recognition error: {e}")
            return None

    def listen_for_wake_word(self, timeout: int = 2) -> Optional[str]:
        """
        Short listen optimized for wake word detection.
        Returns recognized text or None.
        """
        if not self._available or not self.microphone:
            return None

        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=timeout,
                                                phrase_time_limit=2)
        except sr.WaitTimeoutError:
            return None
        except Exception:
            return None

        try:
            return self.recognizer.recognize_google(audio).lower().strip()
        except (sr.UnknownValueError, sr.RequestError):
            return None


# Global listen engine instance
listener = ListenEngine()


# ============================================================
# SECTION D — GROQ AI BRAIN
# ============================================================

class GroqBrain:
    """Handles all AI interactions via Groq API with tool awareness."""

    SYSTEM_PROMPT = (
        "You are JARVIS v4, a witty and highly capable AI assistant inspired by Tony Stark's JARVIS. "
        "You are an expert in Python programming, Data Structures & Algorithms, Web Development, and system automation. "
        "You assist with coding, debugging, system control, document analysis, and general knowledge. "
        "You have access to tools: web_search, run_python, calculator, file_operations, system_info, datetime_tool. "
        "Keep responses concise (2-3 sentences) since they may be spoken aloud. "
        "Be clever, slightly sarcastic, but always helpful. "
        "When users ask about uploaded documents, use the document context provided. "
        f"The user's name is {OWNER_NAME}."
    )

    def __init__(self) -> None:
        self.client: Optional[Groq] = None
        self.conversation_memory: List[Dict[str, str]] = []
        self.rate_limit_queue: deque[float] = deque()
        self._init_client()
        self._setup_memory()

    def check_rate_limit(self) -> bool:
        """Check rolling window rate limit (max 10 executions per minute)."""
        now: float = time.time()
        while self.rate_limit_queue and now - self.rate_limit_queue[0] >= 60.0:
            self.rate_limit_queue.popleft()
        if len(self.rate_limit_queue) >= 10:
            return False
        self.rate_limit_queue.append(now)
        return True

    def _init_client(self) -> None:
        """Initialize Groq client with API key."""
        if GROQ_API_KEY and GROQ_API_KEY != "your_groq_key_here":
            try:
                self.client = Groq(api_key=GROQ_API_KEY)
                print("[OK] Groq AI brain connected.")
            except Exception as e:
                err_str: str = str(e).lower()
                if any(sub in err_str for sub in ["authentication", "401", "api_key"]):
                    print("Authentication failed. Verify your GROQ_API_KEY environment variable configuration.")
                else:
                    print(f"[ERROR] Groq client init failed: {e}")
                self.client = None
        else:
            print("[WARNING] No valid GROQ_API_KEY. AI responses will be unavailable.")
            self.client = None

    def _setup_memory(self) -> None:
        """Initialize conversation memory with system prompt."""
        self.conversation_memory = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]

    def add_to_memory(self, role: str, content: str) -> None:
        """Add a message to conversation memory."""
        self.conversation_memory.append({"role": role, "content": content})
        self.trim_memory()

    def trim_memory(self) -> None:
        """Keep only the last MAX_MEMORY messages (preserving system prompt)."""
        if len(self.conversation_memory) <= MAX_MEMORY + 1:
            return
        # Always keep system prompt at index 0
        system_msg = self.conversation_memory[0]
        recent = self.conversation_memory[-MAX_MEMORY:]
        self.conversation_memory = [system_msg] + recent

    def ask_jarvis(self, prompt: str, model: Optional[str] = None, max_tokens: int = 512) -> str:
        """
        Send prompt to Groq and return AI response.
        Handles rate limits, auth errors, and network issues.
        """
        if not self.client:
            return "AI brain is offline. Check your GROQ_API_KEY in the .env file."

        if not self.check_rate_limit():
            msg: str = "Rate limit exceeded. Maximum 10 requests per minute allowed. Please wait for a cooldown period."
            speak(msg)
            return msg

        self.add_to_memory("user", prompt)

        try:
            chat_completion = self.client.chat.completions.create(
                messages=self.conversation_memory,
                model=model or "llama3-8b-8192",
                max_tokens=max_tokens,
                temperature=0.7,
            )
            response: str = chat_completion.choices[0].message.content or ""
            self.add_to_memory("assistant", response)
            return response

        except Exception as e:
            error_str: str = str(e).lower()
            if any(sub in error_str for sub in ["authentication", "401", "api_key", "auth"]):
                return "Authentication failed. Verify your GROQ_API_KEY environment variable configuration."
            elif "rate limit" in error_str:
                return "I'm getting too many requests. Please wait a moment and try again."
            elif "connection" in error_str or "network" in error_str:
                return "Network issue. Please check your internet connection."
            else:
                return f"AI brain hiccupped: {str(e)[:100]}. Try again?"

    def ask_with_tools(self, prompt: str) -> Dict[str, Any]:
        """Ask JARVIS with potential tool calling (requires agent_tools module)."""
        if not AGENT_TOOLS_ENABLED:
            return {"response": self.ask_jarvis(prompt), "tool_calls": []}

        try:
            from jarvis_agent_tools import agent
            return agent.process_with_tools(prompt)
        except ImportError:
            return {"response": self.ask_jarvis(prompt), "tool_calls": []}

    def ask_code(self, prompt: str) -> str:
        """Specialized prompt for code generation with explicit instructions."""
        code_prompt = (
            f"Write clean, well-commented Python code for: {prompt}\n\n"
            "Requirements:\n"
            "- Use only standard library + common packages\n"
            "- Include docstrings and comments\n"
            "- Handle edge cases\n"
            "- Return ONLY the code block, no explanations before or after"
        )
        return self.ask_jarvis(code_prompt, max_tokens=1024)

    def ask_explanation(self, topic: str) -> str:
        """Get a concise explanation of a topic."""
        exp_prompt = f"Explain {topic} in exactly 3 sentences. Be clear and concise."
        return self.ask_jarvis(exp_prompt)

    def debug_code(self, error_description: str, error_type: str = "unknown") -> str:
        """Get debugging help for an error."""
        debug_prompt = (
            f"A programmer encountered this error: '{error_description}'. "
            f"Error type: {error_type}. "
            "What is the most likely cause and the fix? Respond in 2-3 sentences."
        )
        return self.ask_jarvis(debug_prompt)

    def get_complexity(self, description: str) -> str:
        """Get time and space complexity analysis."""
        comp_prompt = (
            f"Analyze the time and space complexity of this algorithm: {description}. "
            "Provide Big O notation with a brief explanation. Keep it short."
        )
        return self.ask_jarvis(comp_prompt)

    def ask_with_context(self, prompt: str, context: str) -> str:
        """Ask JARVIS with additional document context (for RAG)."""
        contextual_prompt = (
            f"Use the following document context to answer the question. "
            f"If the answer isn't in the context, say so.\n\n"
            f"Context:\n{context[:4000]}\n\n"
            f"Question: {prompt}"
        )
        return self.ask_jarvis(contextual_prompt, max_tokens=1024)


# Global brain instance
brain = GroqBrain()


# ============================================================
# SECTION E — SESSION + PERSISTENT MEMORY
# ============================================================

class MemoryManager:
    """Manages both session memory and persistent memory storage."""

    def __init__(self):
        self.session_start = datetime.now()
        self.request_count = 0
        self.persistent_memory: Dict[str, Any] = {}
        self._load_memory()

    def _load_memory(self):
        """Load persistent memory from disk."""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    self.persistent_memory = json.load(f)
            except (json.JSONDecodeError, Exception):
                self.persistent_memory = {"facts": [], "notes": [], "preferences": {}}
        else:
            self.persistent_memory = {"facts": [], "notes": [], "preferences": {}}

    def _save_memory(self):
        """Save persistent memory to disk."""
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.persistent_memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARNING] Failed to save memory: {e}")

    def save_fact(self, key: str, value: str, category: str = "general"):
        """Save a fact to persistent memory."""
        entry = {
            "key": key,
            "value": value,
            "category": category,
            "timestamp": datetime.now().isoformat()
        }
        # Remove old entry with same key if exists
        self.persistent_memory["facts"] = [
            f for f in self.persistent_memory.get("facts", [])
            if f.get("key") != key
        ]
        self.persistent_memory.setdefault("facts", []).append(entry)
        self._save_memory()

    def save_note_ref(self, filename: str, topic: str) -> None:
        """Save a note reference to memory."""
        entry = {
            "filename": filename,
            "topic": topic,
            "created": datetime.now().isoformat()
        }
        self.persistent_memory.setdefault("notes", []).append(entry)
        self._save_memory()

    def search_memory(self, keyword: str) -> List[Dict[str, Any]]:
        """Search persistent memory for matching entries."""
        results = []
        keyword_lower = keyword.lower()

        for fact in self.persistent_memory.get("facts", []):
            if (keyword_lower in fact.get("key", "").lower() or
                keyword_lower in fact.get("value", "").lower() or
                keyword_lower in fact.get("category", "").lower()):
                results.append(fact)

        for note in self.persistent_memory.get("notes", []):
            if keyword_lower in note.get("topic", "").lower():
                results.append(note)

        return results

    def get_session_summary(self) -> str:
        """Get summary of current session."""
        duration = datetime.now() - self.session_start
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        duration_str = " ".join(parts)
        return (
            f"Session running for {duration_str}. "
            f"AI requests: {self.request_count}. "
            f"Memory entries: {len(brain.conversation_memory)}."
        )

    def clear_session(self):
        """Clear session memory but keep persistent facts."""
        brain._setup_memory()
        self.request_count = 0
        print("[INFO] Session memory cleared. Permanent facts preserved.")

    def log_session_event(self, event: str):
        """Log an event to the session log file."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(SESSION_LOG, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {event}\n")
        except Exception:
            pass


# Global memory manager instance
memory = MemoryManager()


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_time_greeting() -> str:
    """Return appropriate greeting based on time of day."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return f"Good morning, {OWNER_NAME}."
    elif 12 <= hour < 17:
        return f"Good afternoon, {OWNER_NAME}."
    elif 17 <= hour < 22:
        return f"Good evening, {OWNER_NAME}."
    else:
        return f"Working late, {OWNER_NAME}?"


def get_timestamp() -> str:
    """Return current timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Export all key components
__all__ = [
    'voice', 'speak', 'listener', 'brain', 'memory',
    'GROQ_API_KEY', 'OWNER_NAME', 'CITY', 'WAKE_WORD',
    'VOICE_SPEED', 'MAX_MEMORY', 'AGENT_TOOLS_ENABLED', 'RAG_ENABLED',
    'BASE_DIR', 'MEMORY_DIR', 'NOTES_DIR', 'SCREENSHOTS_DIR', 'LOGS_DIR', 'RAG_DIR',
    'get_time_greeting', 'get_timestamp',
    'VoiceEngine', 'ListenEngine', 'GroqBrain', 'MemoryManager',
]
