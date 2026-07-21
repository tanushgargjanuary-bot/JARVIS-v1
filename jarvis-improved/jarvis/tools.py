"""
Agent tools — web search, calculator, file ops, system info, datetime.
These are used by Groq's function-calling when the AI needs live data.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

import psutil
import requests

from jarvis.config import NOTES_DIR

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ════════════════════════════════════════════════════════════════════════════
_REGISTRY: dict[str, dict] = {}

def tool(name: str, description: str, params: dict):
    def decorator(func):
        _REGISTRY[name] = {
            "schema": {"type": "function", "function": {
                "name": name, "description": description,
                "parameters": {"type": "object", "properties": params},
            }},
            "handler": func,
        }
        return func
    return decorator

class ToolExecutor:
    def execute(self, name: str, args: dict) -> str:
        entry = _REGISTRY.get(name)
        if not entry: return f"Unknown tool: {name}"
        try: return entry["handler"](**args)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return f"Tool '{name}' failed: {e}"

    def schemas(self) -> list[dict]:
        return [e["schema"] for e in _REGISTRY.values()]

# ════════════════════════════════════════════════════════════════════════════
# TOOLS
# ════════════════════════════════════════════════════════════════════════════
@tool("web_search", "Search DuckDuckGo for current info.",
      {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 3}})
def web_search(query: str, max_results: int = 3) -> str:
    try:
        r = requests.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1}, timeout=10)
        data = r.json()
        results = []
        if data.get("AbstractText"): results.append(data["AbstractText"])
        for t in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(t, dict) and "Text" in t: results.append(f"- {t['Text']}")
        return "\n".join(results) if results else f"No results for '{query}'."
    except Exception as e:
        return f"Search error: {e}"

@tool("calculator", "Evaluate math expressions (arithmetic, trig, logs).",
      {"expression": {"type": "string"}})
def calculator(expression: str) -> str:
    import math
    expr = expression.lower().replace("percent of", "/ 100 *").replace("times", "*")
    expr = expr.replace("plus", "+").replace("minus", "-").replace("divided by", "/")
    if not re.match(r'^[\d\s\+\-\*\/\.\(\)%a-z_]+$', expr):
        return f"Cannot evaluate: {expression}"
    safe = {"sqrt": math.sqrt, "log": math.log, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "pi": math.pi, "e": math.e, "abs": abs, "pow": pow}
    try:
        result = eval(expr, {"__builtins__": {}}, safe)  # noqa: S307
        if isinstance(result, float) and result == int(result): result = int(result)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Calculator error: {e}"

@tool("file_operations", "Read, write, or list files in the notes directory.",
      {"action": {"type": "string", "enum": ["read", "write", "list"]},
       "path": {"type": "string"}, "content": {"type": "string"}})
def file_operations(action: str, path: str = ".", content: str = "") -> str:
    base = NOTES_DIR
    target = (base / path).resolve()
    if not target.is_relative_to(base.resolve()):
        return "Path escapes the notes directory — blocked."
    try:
        if action == "list":
            return json.dumps([f.name for f in (target if target.is_dir() else base).iterdir()][:30])
        if action == "read":
            return target.read_text(encoding="utf-8", errors="replace")[:5000] if target.is_file() else "Not found."
        if action == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} chars to {path}"
        return f"Unknown action: {action}"
    except Exception as e:
        return f"File error: {e}"

@tool("system_info", "CPU, RAM, disk, battery stats.",
      {"detail": {"type": "string", "enum": ["basic", "detailed"], "default": "basic"}})
def system_info(detail: str = "basic") -> str:
    info = {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        "disk_percent": psutil.disk_usage("/").percent,
    }
    bat = psutil.sensors_battery()
    if bat: info["battery_percent"] = bat.percent
    if detail == "detailed":
        info["uptime"] = str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split(".")[0]
    return json.dumps(info)

@tool("datetime_tool", "Current date/time or date calculations.",
      {"query": {"type": "string", "enum": ["now", "today", "weekday"], "default": "now"}})
def datetime_tool(query: str = "now") -> str:
    now = datetime.now()
    if query == "now": return now.strftime("%Y-%m-%d %H:%M:%S (%A)")
    if query == "today": return now.strftime("%A, %B %d, %Y")
    if query == "weekday": return now.strftime("%A")
    return f"Unknown: {query}"
