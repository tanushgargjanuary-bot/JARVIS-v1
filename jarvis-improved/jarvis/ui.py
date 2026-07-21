"""
GUI — CustomTkinter dark-themed interface.
Falls back to terminal if customtkinter is unavailable.
"""

from __future__ import annotations

import logging
import queue

from jarvis.config import OWNER_NAME

logger = logging.getLogger(__name__)

try:
    import customtkinter as ctk
    _OK = True
except ImportError:
    _OK = False

# Theme
_BG = "#0d1117"
_BG2 = "#161b22"
_BG3 = "#21262d"
_ACCENT = "#58a6ff"
_TEXT = "#e6edf3"
_MUTED = "#484f58"


def is_available() -> bool:
    return _OK


class JarvisApp:
    """Main GUI window."""

    def __init__(self):
        if not _OK:
            raise RuntimeError("customtkinter not installed")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title("JARVIS v2")
        self.root.geometry("950x620")
        self.root.configure(fg_color=_BG)
        self.root.minsize(800, 500)
        self._q: queue.Queue = queue.Queue()
        self._build()

    def _build(self):
        # Sidebar
        side = ctk.CTkFrame(self.root, width=180, fg_color=_BG2, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="JARVIS", font=("Segoe UI", 22, "bold"), text_color=_ACCENT).pack(pady=(20, 5))
        ctk.CTkLabel(side, text="AI Assistant", font=("Segoe UI", 11), text_color=_MUTED).pack()
        ctk.CTkFrame(side, height=1, fg_color=_BG3).pack(fill="x", padx=15, pady=10)
        for label in ["Chat", "History", "Settings"]:
            ctk.CTkButton(side, text=label, fg_color="transparent",
                          text_color=_TEXT, hover_color=_BG3, anchor="w").pack(fill="x", padx=10, pady=2)
        # Status
        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(fill="x", padx=15, side="bottom", pady=10)
        self.status = ctk.CTkLabel(bottom, text="● Ready", font=("Segoe UI", 11), text_color="#3fb950")
        self.status.pack()
        ctk.CTkLabel(bottom, text=f"Hello, {OWNER_NAME}", font=("Segoe UI", 10), text_color=_MUTED).pack(pady=(5, 0))

        # Main content
        main = ctk.CTkFrame(self.root, fg_color=_BG)
        main.grid(row=0, column=1, sticky="nsew")
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Chat display
        self.chat = ctk.CTkTextbox(main, fg_color=_BG2, text_color=_TEXT,
                                    font=("Consolas", 13), wrap="word", corner_radius=8)
        self.chat.pack(fill="both", expand=True, padx=15, pady=(15, 5))
        self.chat.insert("end", "JARVIS v2 — Ready.\n\n")
        self.chat.configure(state="disabled")

        # Input
        inp_frame = ctk.CTkFrame(main, fg_color="transparent")
        inp_frame.pack(fill="x", padx=15, pady=(5, 15))
        self.input = ctk.CTkTextbox(inp_frame, height=50, fg_color=_BG3, text_color=_TEXT, font=("Consolas", 13))
        self.input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input.bind("<Return>", self._on_enter)
        ctk.CTkButton(inp_frame, text="Send", width=80, command=self._send,
                      fg_color=_ACCENT, hover_color="#79b8ff").pack(side="right")

    def _on_enter(self, event) -> str | None:
        if not (hasattr(event, "state") and event.state & 0x1):
            self._send(); return "break"
        return None

    def _send(self):
        text = self.input.get("1.0", "end").strip()
        if not text: return
        self.input.delete("1.0", "end")
        self._append("You", text)
        self._q.put(("user", text))

    def _append(self, who: str, text: str):
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{who}: {text}\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def append_response(self, text: str):
        self._append("JARVIS", text)

    def set_status(self, text: str, color: str = ""):
        self.status.configure(text=f"● {text}")
        if color: self.status.configure(text_color=color)

    def get_queue(self) -> queue.Queue:
        return self._q

    def run(self):
        self.root.mainloop()
