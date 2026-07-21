"""
JARVIS entry point — `python -m jarvis` or `jarvis` CLI.
Starts GUI, voice, or terminal mode.
"""

from __future__ import annotations

import logging
import sys
import threading

from jarvis.config import (
    WAKE_WORD, AGENT_TOOLS_ENABLED, LOGS_DIR, validate,
)
from jarvis.voice import listener, speak
from jarvis.brain import brain
from jarvis.commands import match_command
from jarvis.tools import ToolExecutor
from jarvis.chat_db import chat_db

logger = logging.getLogger(__name__)


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(LOGS_DIR / "jarvis.log"), encoding="utf-8"),
        ],
    )


def _process(text: str, executor: ToolExecutor, cid: str) -> str:
    # 1. Local command match
    result = match_command(text)
    if result:
        cmd, groups = result
        resp = cmd.handler(**groups)
        chat_db.add_msg(cid, "user", text)
        chat_db.add_msg(cid, "assistant", resp)
        return resp
    # 2. AI brain
    if AGENT_TOOLS_ENABLED and brain.online:
        r = brain.ask_with_tools(text, executor.schemas(), executor)
        resp = r["response"]
    elif brain.online:
        resp = brain.ask(text)
    else:
        resp = "Not sure how to help. (Brain offline — set GROQ_API_KEY.)"
    chat_db.add_msg(cid, "user", text)
    chat_db.add_msg(cid, "assistant", resp)
    return resp


def _terminal(executor: ToolExecutor, cid: str):
    print(f"\n{'='*50}\n  JARVIS v2 — Terminal Mode\n  Type 'quit' to exit\n{'='*50}\n")
    while True:
        try:
            text = input(f"[{'> '}] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!"); break
        if not text: continue
        if text.lower() in ("quit", "exit", "bye"):
            speak("Goodbye!"); break
        resp = _process(text, executor, cid)
        print(f"\n[JARVIS] {resp}\n")
        speak(resp)


def _voice_mode(executor: ToolExecutor, cid: str):
    if not listener.available:
        print("Mic not available. Falling back to terminal.")
        _terminal(executor, cid); return
    print(f"\n[Voice Mode] Listening for '{WAKE_WORD}'\n")
    speak(f"JARVIS online. Say '{WAKE_WORD}' to activate.")
    while True:
        heard = listener.listen(timeout=3.0)
        if not heard or WAKE_WORD not in heard.lower(): continue
        speak("Yes?")
        cmd = listener.listen(timeout=6.0)
        if not cmd: speak("Didn't catch that."); continue
        resp = _process(cmd, executor, cid)
        speak(resp)


def _gui(executor: ToolExecutor, cid: str):
    from jarvis.ui import JarvisApp
    app = JarvisApp()
    q = app.get_queue()

    def _worker():
        while True:
            try:
                _, text = q.get(timeout=0.5)
                resp = _process(text, executor, cid)
                app.append_response(resp)
                speak(resp)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()
    app.run()


def main():
    _setup_logging()
    for w in validate():
        print(f"[WARNING] {w}")

    executor = ToolExecutor()
    cid = chat_db.create("Session")
    logger.info("JARVIS v2 starting.")

    if "--terminal" in sys.argv or "--text" in sys.argv:
        _terminal(executor, cid)
    elif "--voice" in sys.argv:
        _voice_mode(executor, cid)
    elif "--gui" in sys.argv:
        _gui(executor, cid)
    else:
        # Auto: GUI if available, else terminal
        try:
            from jarvis.ui import is_available
            if is_available():
                _gui(executor, cid)
            else:
                _terminal(executor, cid)
        except ImportError:
            _terminal(executor, cid)


if __name__ == "__main__":
    main()
