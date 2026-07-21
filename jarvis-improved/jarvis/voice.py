"""
Voice engine — TTS (text-to-speech) and STT (speech-to-text).
Gracefully falls back to stdout if audio hardware is missing.
"""

from __future__ import annotations

import logging
import threading

from jarvis.config import VOICE_SPEED, VOICE_ENABLED

logger = logging.getLogger(__name__)


class VoiceEngine:
    """TTS wrapper. Falls back to print if pyttsx3 unavailable."""

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()
        self.enabled = VOICE_ENABLED
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", VOICE_SPEED)
            self._engine.setProperty("volume", 1.0)
            # Prefer a nice voice
            for v in self._engine.getProperty("voices"):
                if any(p in v.name.lower() for p in ["zira", "david", "hazel"]):
                    self._engine.setProperty("voice", v.id)
                    break
        except Exception as e:
            logger.warning("TTS unavailable (%s) — printing instead.", e)

    def speak(self, text: str) -> None:
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                    return
                except Exception:
                    pass
            print(f"[JARVIS] {text}")


class Listener:
    """Microphone-based STT. Returns None when unavailable."""

    def __init__(self) -> None:
        self._recognizer = None
        self._mic = None
        if not VOICE_ENABLED:
            return
        try:
            import speech_recognition as sr  # type: ignore
            self._recognizer = sr.Recognizer()
            self._mic = sr.Microphone()
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
            logger.info("Microphone ready.")
        except Exception as e:
            logger.warning("Microphone unavailable (%s).", e)

    def listen(self, timeout: float = 5.0) -> str | None:
        if self._recognizer is None or self._mic is None:
            return None
        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self._recognizer.listen(source, timeout=timeout)
            return self._recognizer.recognize_google(audio).strip()
        except Exception:
            return None

    @property
    def available(self) -> bool:
        return self._recognizer is not None


# Module-level singletons
voice = VoiceEngine()
listener = Listener()

def speak(text: str) -> None:
    voice.speak(text)
