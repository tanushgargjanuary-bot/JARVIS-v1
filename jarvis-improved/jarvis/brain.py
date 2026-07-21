"""
AI brain — Groq API chat with conversation memory and tool calling.
"""

from __future__ import annotations

import json
import logging
from collections import deque

from jarvis.config import (
    GROQ_API_KEY, OWNER_NAME, AI_MODEL, MAX_TOKENS, TEMPERATURE, MAX_MEMORY,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    f"You are JARVIS, a helpful AI voice assistant running on the user's desktop. "
    f"Be concise (1-3 sentences for voice). Address the user as '{OWNER_NAME}'. "
    f"If you don't know something, say so honestly."
)


class Memory:
    """Sliding-window conversation memory."""

    def __init__(self, max_size: int = MAX_MEMORY) -> None:
        self._buf: deque[dict[str, str]] = deque(maxlen=max_size)

    def add(self, role: str, content: str) -> None:
        self._buf.append({"role": role, "content": content})

    def messages(self) -> list[dict[str, str]]:
        return list(self._buf)

    def clear(self) -> None:
        self._buf.clear()

    def __len__(self) -> int:
        return len(self._buf)


memory = Memory()


class Brain:
    """Groq LLM wrapper with memory and optional tool calling."""

    def __init__(self) -> None:
        self._client = None
        if GROQ_API_KEY and GROQ_API_KEY != "your_groq_key_here":
            try:
                from groq import Groq  # type: ignore
                self._client = Groq(api_key=GROQ_API_KEY)
            except Exception as e:
                logger.error("Groq init failed: %s", e)

    @property
    def online(self) -> bool:
        return self._client is not None

    def ask(self, user_msg: str, extra: list[dict] | None = None) -> str:
        if not self.online:
            return "[Brain offline] Set GROQ_API_KEY in .env"
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.extend(memory.messages())
        if extra:
            msgs.extend(extra)
        msgs.append({"role": "user", "content": user_msg})
        try:
            resp = self._client.chat.completions.create(
                model=AI_MODEL, messages=msgs,
                max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
            )
            reply = resp.choices[0].message.content or ""
            memory.add("user", user_msg)
            memory.add("assistant", reply)
            return reply
        except Exception as e:
            logger.error("Groq error: %s", e)
            return f"[Error] {e}"

    def ask_with_tools(self, user_msg: str, tools: list[dict], executor) -> dict:
        """Chat with function/tool calling. Returns {"response": str, "tool_calls": list}."""
        if not self.online:
            return {"response": "[Brain offline]", "tool_calls": []}
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.extend(memory.messages())
        msgs.append({"role": "user", "content": user_msg})
        log: list[dict] = []
        for _ in range(5):  # max tool iterations
            try:
                resp = self._client.chat.completions.create(
                    model=AI_MODEL, messages=msgs, tools=tools,
                    tool_choice="auto", max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
                )
            except Exception as e:
                return {"response": f"[Error] {e}", "tool_calls": log}
            msg = resp.choices[0].message
            msgs.append(msg.model_dump())
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = executor.execute(tc.function.name, args)
                    log.append({"tool": tc.function.name, "args": args, "result": result[:200]})
                    msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            else:
                reply = msg.content or "Done."
                memory.add("user", user_msg)
                memory.add("assistant", reply)
                return {"response": reply, "tool_calls": log}
        return {"response": "Max tool iterations reached.", "tool_calls": log}


brain = Brain()
