"""
JARVIS v4 - Multi-Agent Tool Calling System
===========================================
Structured tool/function calling with Groq API.

Tools:
- web_search: Search the web using DuckDuckGo
- run_python: Execute Python code safely
- calculator: Advanced math calculations
- file_operations: Read, write, list files
- system_info: Get system information
- datetime_tool: Get current date/time info
- shell_command: Run safe shell commands
"""

import os
import re
import math
import json
import subprocess
import tempfile
import traceback
import ast
import logging
import shlex
import socket
import getpass
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from typing import get_type_hints

import requests
import psutil

from jarvis_core import (
    brain, speak, OWNER_NAME, BASE_DIR,
    SCREENSHOTS_DIR, NOTES_DIR
)

logger = logging.getLogger(__name__)
READABLE_DIRS: List[str] = ["notes", "documents", "logs"]

# ============================================================
# TOOL DEFINITIONS (JSON Schema for Groq)
# ============================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo for current information, facts, news, or any topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results (1-5)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute Python code safely in a sandboxed environment. Use for calculations, data processing, file manipulation, or any programming task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform mathematical calculations including arithmetic, algebra, trigonometry, logarithms, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_operations",
            "description": "Read, write, list, or search files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "list", "search", "delete"],
                        "description": "File operation to perform"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content for write operation"
                    }
                },
                "required": ["action", "path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Get detailed system information including CPU, RAM, disk, battery, and running processes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "enum": ["basic", "detailed", "processes"],
                        "default": "basic",
                        "description": "Level of detail"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "datetime_tool",
            "description": "Get current date, time, day of week, or perform date calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to get: 'time', 'date', 'day', 'datetime', or a date calculation like 'days until 2024-12-25'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shell_command",
            "description": "Run safe shell commands. Only non-destructive commands are allowed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
]


# ============================================================
# TOOL IMPLEMENTATIONS
# ============================================================

class ToolExecutor:
    """Executes tool calls with safety checks and error handling."""

    def __init__(self) -> None:
        self.tools: Dict[str, Callable[..., Any]] = {
            "web_search": self.web_search,
            "run_python": self.run_python,
            "calculator": self.calculator,
            "file_operations": self.file_operations,
            "system_info": self.system_info,
            "datetime_tool": self.datetime_tool,
            "shell_command": self.shell_command,
        }

    # --------------------------------------------------------
    # Web Search
    # --------------------------------------------------------

    @staticmethod
    def web_search(query: str, max_results: int = 3) -> str:
        """Search the web using DuckDuckGo."""
        try:
            max_results = min(max(max_results, 1), 5)

            # Use DuckDuckGo HTML interface
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
            }
            data = {"q": query}

            response = requests.post(url, headers=headers, data=data, timeout=10)

            if response.status_code != 200:
                return f"Search failed with status {response.status_code}."

            # Parse results
            from html.parser import HTMLParser

            class ResultParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.results = []
                    self.in_result = False
                    self.in_title = False
                    self.in_snippet = False
                    self.current = {}
                    self._buffer = ""

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    cls = attrs_dict.get('class', '')

                    if 'result__a' in cls:
                        self.in_title = True
                        self._buffer = ""
                        self.current['url'] = attrs_dict.get('href', '')
                    elif 'result__snippet' in cls:
                        self.in_snippet = True
                        self._buffer = ""

                def handle_endtag(self, tag):
                    if self.in_title:
                        self.in_title = False
                        self.current['title'] = self._buffer.strip()
                    elif self.in_snippet:
                        self.in_snippet = False
                        self.current['snippet'] = self._buffer.strip()
                        if self.current.get('title'):
                            self.results.append(self.current)
                            self.current = {}

                def handle_data(self, data):
                    if self.in_title or self.in_snippet:
                        self._buffer += data

            parser = ResultParser()
            parser.feed(response.text)

            if not parser.results:
                return f"No web results found for '{query}'."

            output = f"Web search results for '{query}':\n\n"
            for i, r in enumerate(parser.results[:max_results], 1):
                title = r.get('title', 'No title')
                snippet = r.get('snippet', '')
                output += f"{i}. {title}\n   {snippet}\n\n"

            return output.strip()

        except Exception as e:
            return f"Web search error: {str(e)}"

    # --------------------------------------------------------
    # Run Python
    # --------------------------------------------------------

    @staticmethod
    def is_safe_code(code: str) -> bool:
        """Validate Python code safety using AST parsing."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Security violation: AST syntax error: {e}")
            return False

        dangerous_names: set[str] = {'__import__', 'getattr', 'eval', 'exec', 'os', 'subprocess'}

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                logger.warning("Security violation: Unauthorized import statement detected in AST.")
                return False
            if isinstance(node, ast.Name) and node.id in dangerous_names:
                logger.warning(f"Security violation: Unauthorized identifier '{node.id}' detected in AST.")
                return False
            if isinstance(node, ast.Attribute) and (node.attr in dangerous_names or node.attr.startswith('__')):
                logger.warning(f"Security violation: Unauthorized attribute '{node.attr}' detected in AST.")
                return False
        return True

    @staticmethod
    def run_python(code: str) -> str:
        """Execute Python code in a restricted environment."""
        if not ToolExecutor.is_safe_code(code):
            return "Security error: AST validation failed. Unauthorized imports, modules, or attributes detected."

        # Create restricted globals
        safe_builtins: Dict[str, Any] = {
            'abs': abs, 'all': all, 'ascii': ascii,
            'bin': bin, 'bool': bool, 'bytearray': bytearray,
            'bytes': bytes, 'chr': chr, 'complex': complex,
            'dict': dict, 'dir': dir, 'divmod': divmod,
            'enumerate': enumerate, 'filter': filter, 'float': float,
            'format': format, 'frozenset': frozenset, 'hash': hash,
            'hex': hex, 'int': int, 'isinstance': isinstance,
            'issubclass': issubclass, 'iter': iter, 'len': len,
            'list': list, 'map': map, 'max': max, 'min': min,
            'next': next, 'oct': oct, 'ord': ord, 'pow': pow,
            'print': print, 'range': range, 'repr': repr,
            'reversed': reversed, 'round': round, 'set': set,
            'slice': slice, 'sorted': sorted, 'str': str,
            'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
        }

        safe_globals: Dict[str, Any] = {
            "__builtins__": safe_builtins,
            "math": math,
            "json": json,
            "re": re,
            "datetime": datetime,
            "timedelta": timedelta,
        }

        # Capture output
        import io
        import contextlib

        output_buffer = io.StringIO()

        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, dir=str(tempfile.gettempdir())
            ) as f:
                f.write(code)
                temp_path = f.name

            # Execute with output capture
            with contextlib.redirect_stdout(output_buffer), \
                 contextlib.redirect_stderr(output_buffer):
                exec(code, safe_globals)

            output = output_buffer.getvalue()

            # Clean up
            try:
                os.unlink(temp_path)
            except:
                pass

            if not output.strip():
                # Try to get the last expression value
                last_line = code.strip().split('\n')[-1]
                if not last_line.startswith(('import', 'from', 'def', 'class', 'print')):
                    try:
                        result = eval(last_line, safe_globals)
                        if result is not None:
                            return f"Result: {repr(result)}"
                    except:
                        pass
                return "Code executed successfully. No output."

            return f"Output:\n{output}"

        except Exception as e:
            error_msg = f"Python execution error: {type(e).__name__}: {str(e)}"
            # Add line number info
            tb = traceback.format_exc()
            line_match = re.search(r'line (\d+)', tb)
            if line_match:
                error_msg += f" (Line {line_match.group(1)})"
            return error_msg

    # --------------------------------------------------------
    # Calculator
    # --------------------------------------------------------

    @staticmethod
    def calculator(expression: str) -> str:
        """Evaluate mathematical expressions safely."""
        try:
            # Clean and normalize expression
            expr = expression.lower().strip()

            # Replace natural language
            replacements = {
                'percent': '/100', 'percentage': '/100',
                'modulo': '%', 'mod': '%',
                'to the power': '**', 'power': '**',
                'squared': '**2', 'cubed': '**3',
                'square root of': 'math.sqrt',
                'sqrt of': 'math.sqrt',
                'cube root of': '(lambda x: x**(1/3))',
                'pi': 'math.pi', 'e': 'math.e',
                'sin': 'math.sin', 'cos': 'math.cos',
                'tan': 'math.tan', 'log': 'math.log10',
                'ln': 'math.log', 'factorial': 'math.factorial',
                'abs': 'abs', 'floor': 'math.floor',
                'ceil': 'math.ceil', 'round': 'round',
            }

            for old, new in replacements.items():
                expr = expr.replace(old, new)

            # Allow: digits, operators, parentheses, math functions
            allowed = set('0123456789+-*/%().,** mathsqrtlogcosintanfloealbcdriumpxjkw()')
            expr_filtered = ''.join(c for c in expr if c in allowed)

            if not expr_filtered:
                return "Invalid math expression."

            # Safe eval
            safe_globals = {"__builtins__": {}, "math": math}
            result = eval(expr_filtered, safe_globals)

            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 6)

            return f"Result: {result}"

        except ZeroDivisionError:
            return "Error: Division by zero."
        except Exception as e:
            return f"Calculation error: {str(e)}"

    # --------------------------------------------------------
    # File Operations
    # --------------------------------------------------------

    @staticmethod
    def file_operations(action: str, path: str, content: Optional[str] = None) -> str:
        """Read, write, list, or search files."""
        try:
            base: Path = Path(BASE_DIR).resolve()
            target: Path = (Path(BASE_DIR) / path).resolve()

            # Security: Ensure path is within project directory
            try:
                rel_target = target.relative_to(base)
            except ValueError:
                return "Security error: Path must be within the project directory."

            # Block queries accessing .env files
            if ".env" in target.name or ".env" in str(target):
                return "Security error: Accessing .env files is blocked."

            if action == "read":
                is_allowed: bool = False
                if len(rel_target.parts) > 0 and rel_target.parts[0] in READABLE_DIRS:
                    is_allowed = True
                if not is_allowed:
                    return f"Security error: Reading files outside allowed directories ({', '.join(READABLE_DIRS)}) is blocked."

                if not target.exists():
                    return f"File not found: {path}"
                if target.is_dir():
                    return f"'{path}' is a directory. Use 'list' to see contents."
                text: str = target.read_text(encoding='utf-8', errors='ignore')
                if len(text) > 5000:
                    text = text[:5000] + "\n... (truncated, file too large)"
                return f"Contents of {path}:\n```\n{text}\n```"

            elif action == "write":
                if content is None:
                    return "No content provided for write operation."
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8')
                return f"Written {len(content)} characters to {path}."

            elif action == "list":
                if not target.exists():
                    return f"Directory not found: {path}"
                if not target.is_dir():
                    return f"'{path}' is not a directory."

                items = []
                for item in sorted(target.iterdir()):
                    prefix = "[DIR]" if item.is_dir() else "[FILE]"
                    size = ""
                    if item.is_file():
                        kb = item.stat().st_size / 1024
                        size = f" ({kb:.1f} KB)"
                    items.append(f"  {prefix} {item.name}{size}")

                return f"Contents of {path}:\n" + "\n".join(items)

            elif action == "search":
                if not target.exists():
                    return f"Path not found: {path}"

                matches = []
                search_term = content or ""
                if target.is_file():
                    files = [target]
                else:
                    files = list(target.rglob("*.py")) + list(target.rglob("*.txt")) + \
                            list(target.rglob("*.md")) + list(target.rglob("*.json"))

                for f in files:
                    try:
                        text = f.read_text(encoding='utf-8', errors='ignore')
                        if search_term.lower() in text.lower():
                            lines = [
                                i+1 for i, line in enumerate(text.split('\n'))
                                if search_term.lower() in line.lower()
                            ]
                            matches.append(f"  {f.relative_to(base)}: lines {lines}")
                    except:
                        pass

                if not matches:
                    return f"No files found containing '{search_term}'."
                return f"Search results for '{search_term}':\n" + "\n".join(matches[:20])

            elif action == "delete":
                if not target.exists():
                    return f"File not found: {path}"
                if target.is_dir():
                    return "Use shell_command with 'rmdir' to delete directories."
                target.unlink()
                return f"Deleted: {path}"

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"File operation error: {str(e)}"

    # --------------------------------------------------------
    # System Info
    # --------------------------------------------------------

    @staticmethod
    def system_info(detail: str = "basic") -> str:
        """Get system information."""
        try:
            info = []

            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            info.append(f"CPU: {cpu_count} cores, {cpu_percent:.1f}% usage")
            if cpu_freq:
                info.append(f"  Frequency: {cpu_freq.current:.0f} MHz")

            # RAM
            ram = psutil.virtual_memory()
            ram_used = ram.used / (1024**3)
            ram_total = ram.total / (1024**3)
            info.append(f"RAM: {ram_used:.1f} / {ram_total:.1f} GB ({ram.percent}% used)")

            # Disk
            disk = psutil.disk_usage('/')
            disk_used = disk.used / (1024**3)
            disk_total = disk.total / (1024**3)
            info.append(f"Disk: {disk_used:.1f} / {disk_total:.1f} GB ({disk.percent}% used)")

            # Battery
            battery = psutil.sensors_battery()
            if battery:
                status = "Charging" if battery.power_plugged else "On battery"
                info.append(f"Battery: {battery.percent}% ({status})")

            # Boot time
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes = remainder // 60
            info.append(f"Uptime: {hours}h {minutes}m")

            if detail == "detailed":
                # Network
                net_io = psutil.net_io_counters()
                info.append(f"Network: Sent {net_io.bytes_sent/1024**2:.1f} MB, "
                           f"Recv {net_io.bytes_recv/1024**2:.1f} MB")

                # Swap
                swap = psutil.swap_memory()
                info.append(f"Swap: {swap.percent}% used")

            if detail == "processes":
                procs = []
                for p in sorted(
                    psutil.process_iter(['pid', 'name', 'memory_percent']),
                    key=lambda x: x.info['memory_percent'] or 0,
                    reverse=True
                )[:10]:
                    proc = p.info
                    procs.append(f"  PID {proc['pid']}: {proc['name']} "
                               f"({proc['memory_percent']:.1f}% RAM)")
                info.append("Top processes by memory:")
                info.extend(procs)

            return "\n".join(info)

        except Exception as e:
            return f"System info error: {str(e)}"

    # --------------------------------------------------------
    # DateTime Tool
    # --------------------------------------------------------

    @staticmethod
    def datetime_tool(query: str) -> str:
        """Handle date and time queries."""
        query_lower = query.lower().strip()
        now = datetime.now()

        if query_lower in ["time", "current time"]:
            return f"Current time: {now.strftime('%I:%M:%S %p')}"

        elif query_lower in ["date", "current date"]:
            return f"Today: {now.strftime('%A, %B %d, %Y')}"

        elif query_lower in ["day", "current day"]:
            return f"Today is {now.strftime('%A')}."

        elif query_lower in ["datetime", "current datetime"]:
            return f"Current: {now.strftime('%A, %B %d, %Y %I:%M:%S %p')}"

        elif "days until" in query_lower or "days to" in query_lower:
            # Extract date
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
            if date_match:
                try:
                    target = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                    delta = target - now
                    if delta.days < 0:
                        return f"That date was {abs(delta.days)} days ago."
                    return f"{delta.days} days until {date_match.group(1)}."
                except:
                    pass
            return "Please provide date in YYYY-MM-DD format."

        elif "timezone" in query_lower:
            import time
            tz = time.tzname
            return f"Local timezone: {', '.join(tz)} (UTC{time.timezone // -3600:+d})"

        else:
            return f"DateTime info: {now.strftime('%A, %B %d, %Y %I:%M:%S %p')}"

    # --------------------------------------------------------
    # Shell Command
    # --------------------------------------------------------

    @staticmethod
    def shell_command(command: str) -> str:
        """Run safe shell commands."""
        chaining_tokens: List[str] = ['&&', '||', '|', ';', '&', '>', '<', '`', '$(']
        if any(token in command for token in chaining_tokens):
            return "Security error: Command chaining or redirection is blocked."

        dangerous: List[str] = [
            'rm -rf', 'mkfs', 'dd if=', ':(){:|:&};:',
            'del /f', 'format ', 'rd /s', 'shutdown', 'reboot', 'poweroff', 'init 0',
        ]

        cmd_lower: str = command.lower().strip()
        for d in dangerous:
            if d in cmd_lower:
                return f"Security error: Dangerous command blocked: {d}"

        posix_flag: bool = (os.name != 'nt')
        try:
            args: List[str] = shlex.split(command, posix=posix_flag)
        except ValueError:
            args = command.split()

        if not args:
            return "No command provided."

        cmd_name: str = args[0].lower()

        if cmd_name in ('dir', 'ls'):
            target_dir: Path = Path(BASE_DIR)
            recursive: bool = False
            for arg in args[1:]:
                if arg.lower() in ('/s', '-r', '-la', '-l', '-a', '/b'):
                    if arg.lower() in ('/s', '-r'):
                        recursive = True
                elif not arg.startswith('-') and not arg.startswith('/'):
                    target_dir = Path(BASE_DIR) / arg

            if not target_dir.exists():
                return f"Directory not found: {target_dir}"
            if not target_dir.is_dir():
                return f"Not a directory: {target_dir}"

            try:
                items: List[str] = []
                if recursive:
                    for p in target_dir.rglob('*'):
                        items.append(str(p.relative_to(target_dir)))
                else:
                    for p in sorted(target_dir.iterdir()):
                        prefix = "[DIR]" if p.is_dir() else "[FILE]"
                        items.append(f"{prefix} {p.name}")
                output: str = "\n".join(items[:100])
                if len(items) > 100:
                    output += "\n... (output truncated)"
                return f"Output:\n```\n{output}\n```"
            except Exception as e:
                return f"Error listing directory: {e}"

        elif cmd_name == 'pwd':
            return f"Output:\n```\n{Path.cwd()}\n```"

        elif cmd_name == 'cd':
            if len(args) > 1:
                try:
                    os.chdir(args[1])
                    return f"Changed directory to: {os.getcwd()}"
                except Exception as e:
                    return f"Error changing directory: {e}"
            return f"Current directory: {os.getcwd()}"

        elif cmd_name == 'echo':
            return f"Output:\n```\n{' '.join(args[1:])}\n```"

        elif cmd_name in ('cat', 'type'):
            if len(args) < 2:
                return "No file specified."
            file_path = Path(BASE_DIR) / args[1]
            if not file_path.exists():
                return f"File not found: {args[1]}"
            try:
                content: str = file_path.read_text(encoding='utf-8', errors='replace')
                if len(content) > 3000:
                    content = content[:3000] + "\n... (output truncated)"
                return f"Output:\n```\n{content}\n```"
            except Exception as e:
                return f"Error reading file: {e}"

        elif cmd_name == 'whoami':
            return f"Output:\n```\n{getpass.getuser()}\n```"

        elif cmd_name == 'hostname':
            return f"Output:\n```\n{socket.gethostname()}\n```"

        elif cmd_name == 'date':
            return f"Output:\n```\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n```"

        allowed_externals: List[str] = ['find', 'grep', 'wc', 'head', 'tail', 'python', 'pip']
        if not any(cmd_name == ext or cmd_name.endswith(ext) for ext in allowed_externals):
            return (f"Command not in allowed list. Allowed: dir/ls, cd, pwd, echo, "
                    f"cat/type, head, tail, find, grep, wc, date, whoami, hostname, python, pip")

        try:
            result = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(BASE_DIR),
            )

            output = result.stdout.strip()
            if result.stderr:
                output += f"\n[STDERR]: {result.stderr.strip()}"

            if not output:
                return f"Command executed (exit code: {result.returncode}). No output."

            if len(output) > 3000:
                output = output[:3000] + "\n... (output truncated)"

            return f"Output:\n```\n{output}\n```"

        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Command error: {str(e)}"

    # ============================================================
    # MAIN EXECUTION
    # ============================================================

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        if tool_name not in self.tools:
            return f"Unknown tool: {tool_name}"

        try:
            result = self.tools[tool_name](**arguments)
            return str(result)
        except TypeError as e:
            return f"Tool argument error: {str(e)}"
        except Exception as e:
            return f"Tool execution error: {str(e)}"


# ============================================================
# AGENT INTERFACE
# ============================================================

class AgentInterface:
    """
    High-level interface for tool calling with Groq.
    Handles tool use loops and response streaming.
    """

    def __init__(self) -> None:
        self.executor = ToolExecutor()

    def process_with_tools(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message with potential tool calls.
        Returns: {"response": str, "tool_calls": list}
        """
        if not brain.client:
            return {
                "response": "AI brain is offline. Check your GROQ_API_KEY.",
                "tool_calls": []
            }

        tool_calls_log: List[Dict[str, Any]] = []
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": brain.SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        max_iterations = 5
        for iteration in range(max_iterations):
            if not brain.check_rate_limit():
                msg: str = "Rate limit exceeded. Maximum 10 requests per minute allowed. Please wait for a cooldown period."
                speak(msg)
                return {
                    "response": msg,
                    "tool_calls": tool_calls_log,
                }
            try:
                response = brain.client.chat.completions.create(
                    messages=messages,
                    model="llama3-8b-8192",
                    max_tokens=1024,
                    temperature=0.7,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                )

                message = response.choices[0].message

                # Check for tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Add assistant message to conversation
                    messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    })

                    # Execute each tool call
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {}

                        # Execute tool
                        result = self.executor.execute(tool_name, arguments)

                        tool_calls_log.append({
                            "tool": tool_name,
                            "arguments": arguments,
                            "result_preview": result[:200] if len(result) > 200 else result,
                        })

                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        })

                    # Continue loop to get final response
                    continue

                else:
                    # No tool calls - we have the final response
                    return {
                        "response": message.content or "I processed your request.",
                        "tool_calls": tool_calls_log,
                    }

            except Exception as e:
                error_str: str = str(e).lower()
                if any(sub in error_str for sub in ["authentication", "401", "api_key"]):
                    return {
                        "response": "Authentication failed. Verify your GROQ_API_KEY environment variable configuration.",
                        "tool_calls": tool_calls_log,
                    }
                return {
                    "response": f"Error processing request: {str(e)}",
                    "tool_calls": tool_calls_log,
                }

        # Max iterations reached
        return {
            "response": "I performed multiple tool operations. Here's what I found:\n\n" + \
                       "\n".join([f"- Used {t['tool']}: {t['result_preview']}" for t in tool_calls_log]),
            "tool_calls": tool_calls_log,
        }


# ============================================================
# GLOBAL INSTANCE
# ============================================================

agent = AgentInterface()


def ask_with_tools(question: str) -> Dict[str, Any]:
    """Convenience function to ask JARVIS with tool calling."""
    return agent.process_with_tools(question)


__all__ = [
    'AgentInterface', 'agent', 'ask_with_tools',
    'ToolExecutor', 'TOOL_DEFINITIONS',
]
