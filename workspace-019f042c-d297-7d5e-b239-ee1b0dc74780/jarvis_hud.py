"""
JARVIS v4 - Modern HUD (CustomTkinter)
======================================
Professional dark-themed GUI with sidebar navigation,
chat history panel, document upload, RAG Q&A, settings,
and real-time status indicators.

Features:
- Modern dark theme with accent colors
- Sidebar with navigation tabs
- Chat history with searchable conversations
- Document upload & RAG document management
- Settings panel with configurable options
- Voice activity visualization
- Real-time system stats
"""

import os
import threading
import time
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict

try:
    import customtkinter as ctk
    CUSTOMTKINTER_AVAILABLE = True
except ImportError:
    CUSTOMTKINTER_AVAILABLE = False
    print("[WARNING] customtkinter not installed. Falling back to tkinter.")

if CUSTOMTKINTER_AVAILABLE:
    import tkinter as tk
    from tkinter import messagebox, filedialog, simpledialog
else:
    import tkinter as tk
    from tkinter import messagebox, filedialog, simpledialog

# Import JARVIS core components
try:
    from jarvis_core import (
        voice, speak, listener, brain, memory,
        OWNER_NAME, WAKE_WORD, VOICE_SPEED, MAX_MEMORY,
        get_time_greeting, get_timestamp, BASE_DIR
    )
except ImportError:
    # Placeholder for testing UI standalone
    OWNER_NAME = "Boss"
    WAKE_WORD = "jarvis"
    VOICE_SPEED = 172
    MAX_MEMORY = 30
    def get_timestamp(): return datetime.now().strftime("%H:%M:%S")
    def speak(text): print(f"[SPEAK] {text}")


# ============================================================
# THEME CONFIGURATION
# ============================================================

THEME = {
    "bg_primary": "#0d1117",      # Main background
    "bg_secondary": "#161b22",     # Sidebar, panels
    "bg_tertiary": "#21262d",      # Cards, inputs
    "accent": "#58a6ff",           # Primary accent (blue)
    "accent_hover": "#79b8ff",
    "accent_secondary": "#238636", # Success green
    "text_primary": "#e6edf3",     # Main text
    "text_secondary": "#8b949e",   # Secondary text
    "text_muted": "#484f58",       # Muted text
    "border": "#30363d",           # Borders
    "error": "#f85149",            # Error red
    "warning": "#d29922",          # Warning yellow
    "success": "#3fb950",          # Success green
    "status_listening": "#3fb950",
    "status_speaking": "#f85149",
    "status_thinking": "#d29922",
    "status_idle": "#484f58",
}

# Configure CustomTkinter appearance
if CUSTOMTKINTER_AVAILABLE:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


# ============================================================
# MODERN HUD CLASS
# ============================================================

class JarvisHUD:
    """Modern CustomTkinter HUD for JARVIS v4."""

    def __init__(self):
        self.root = None
        self._thread = None
        self._running = False
        self._command_queue = queue.Queue()

        # Callbacks for integration with main JARVIS
        self.on_send_message: Optional[Callable[[str], None]] = None
        self.on_voice_toggle: Optional[Callable[[], bool]] = None
        self.on_wake_word_change: Optional[Callable[[str], None]] = None

        # State
        self.current_tab = "chat"
        self.conversations: List[Dict] = []
        self.current_conversation_id = None
        self.voice_enabled = True
        self.is_listening = False
        self.is_thinking = False

    # ==================== WINDOW SETUP ====================

    def _create_window(self):
        """Create the main application window."""
        if CUSTOMTKINTER_AVAILABLE:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("JARVIS v4")
        self.root.geometry("1100x700+100+50")
        self.root.configure(fg_color=THEME["bg_primary"])

        # Minimum window size
        self.root.minsize(900, 600)

        # Window icon (if available)
        try:
            self.root.iconbitmap(str(BASE_DIR / "jarvis_icon.ico"))
        except:
            pass

        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Build UI sections
        self._create_sidebar()
        self._create_main_content()
        self._create_status_bar()

        # Start update loops
        self._running = True
        self._update_clock()
        self._process_queue()

    # ==================== SIDEBAR ====================

    def _create_sidebar(self):
        """Create the left sidebar with navigation."""
        if CUSTOMTKINTER_AVAILABLE:
            sidebar = ctk.CTkFrame(
                self.root, width=220, fg_color=THEME["bg_secondary"],
                corner_radius=0
            )
        else:
            sidebar = tk.Frame(self.root, width=220, bg=THEME["bg_secondary"])

        sidebar.grid(row=0, column=0, sticky="nsew", rowspan=2)
        sidebar.grid_propagate(False)

        # App title
        if CUSTOMTKINTER_AVAILABLE:
            title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
            title_frame.pack(fill="x", padx=15, pady=(20, 10))

            ctk.CTkLabel(
                title_frame, text="JARVIS",
                font=("Segoe UI", 24, "bold"),
                text_color=THEME["accent"]
            ).pack(side="left")

            ctk.CTkLabel(
                title_frame, text=" v4",
                font=("Segoe UI", 12),
                text_color=THEME["text_muted"]
            ).pack(side="left", pady=5)
        else:
            tk.Label(
                sidebar, text="JARVIS v4",
                font=("Segoe UI", 20, "bold"),
                bg=THEME["bg_secondary"], fg=THEME["accent"]
            ).pack(fill="x", padx=15, pady=(20, 10))

        # Separator
        if CUSTOMTKINTER_AVAILABLE:
            ctk.CTkFrame(sidebar, height=1, fg_color=THEME["border"]).pack(
                fill="x", padx=15, pady=5
            )
        else:
            tk.Frame(sidebar, height=1, bg=THEME["border"]).pack(
                fill="x", padx=15, pady=5
            )

        # Navigation buttons
        nav_items = [
            ("chat", "Chat", lambda: self._switch_tab("chat")),
            ("history", "History", lambda: self._switch_tab("history")),
            ("documents", "Documents", lambda: self._switch_tab("documents")),
            ("rag", "Document Q&A", lambda: self._switch_tab("rag")),
            ("tools", "Agent Tools", lambda: self._switch_tab("tools")),
            ("settings", "Settings", lambda: self._switch_tab("settings")),
        ]

        self.nav_buttons = {}
        for tab_id, label, command in nav_items:
            btn = self._create_nav_button(sidebar, label, command, tab_id == "chat")
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[tab_id] = btn

        # Bottom section - Voice toggle & Status
        if CUSTOMTKINTER_AVAILABLE:
            ctk.CTkFrame(sidebar, height=1, fg_color=THEME["border"]).pack(
                fill="x", padx=15, pady=10
            )

            bottom_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
            bottom_frame.pack(fill="x", padx=15, pady=10, side="bottom")

            # Voice toggle
            self.voice_switch = ctk.CTkSwitch(
                bottom_frame, text="Voice",
                command=self._toggle_voice,
                fg_color=THEME["bg_tertiary"],
                progress_color=THEME["accent_secondary"],
            )
            self.voice_switch.pack(fill="x", pady=5)
            self.voice_switch.select()  # On by default

            # Status indicator
            self.status_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
            self.status_frame.pack(fill="x", pady=5)

            self.status_dot = ctk.CTkLabel(
                self.status_frame, text="●",
                font=("Segoe UI", 14),
                text_color=THEME["status_idle"]
            )
            self.status_dot.pack(side="left")

            self.status_label = ctk.CTkLabel(
                self.status_frame, text="Idle",
                font=("Segoe UI", 11),
                text_color=THEME["text_secondary"]
            )
            self.status_label.pack(side="left", padx=5)

            # Owner name
            ctk.CTkLabel(
                bottom_frame,
                text=f"Hello, {OWNER_NAME}",
                font=("Segoe UI", 11),
                text_color=THEME["text_muted"]
            ).pack(fill="x", pady=5)
        else:
            tk.Frame(sidebar, height=1, bg=THEME["border"]).pack(
                fill="x", padx=15, pady=10
            )

            bottom_frame = tk.Frame(sidebar, bg=THEME["bg_secondary"])
            bottom_frame.pack(fill="x", padx=15, pady=10, side="bottom")

            self.status_label = tk.Label(
                bottom_frame, text="Status: Idle",
                font=("Segoe UI", 10),
                bg=THEME["bg_secondary"], fg=THEME["text_secondary"]
            )
            self.status_label.pack(fill="x", pady=5)

    def _create_nav_button(self, parent, text, command, is_active=False):
        """Create a navigation button."""
        fg = THEME["accent"] if is_active else THEME["bg_tertiary"]
        text_c = THEME["bg_primary"] if is_active else THEME["text_primary"]
        hover = THEME["accent_hover"] if is_active else THEME["bg_tertiary"]

        if CUSTOMTKINTER_AVAILABLE:
            btn = ctk.CTkButton(
                parent, text=text, command=command,
                fg_color=fg, text_color=text_c,
                hover_color=hover,
                font=("Segoe UI", 13),
                height=38, corner_radius=8,
                anchor="w"
            )
        else:
            btn = tk.Button(
                parent, text=text, command=command,
                bg=fg, fg=text_c,
                font=("Segoe UI", 12),
                height=2, bd=0, padx=15,
                activebackground=hover,
                activeforeground=text_c,
                relief="flat", anchor="w"
            )
        return btn

    def _switch_tab(self, tab_name: str):
        """Switch between main content tabs."""
        self.current_tab = tab_name

        # Update nav button styles
        for tid, btn in self.nav_buttons.items():
            is_active = tid == tab_name
            if CUSTOMTKINTER_AVAILABLE:
                btn.configure(
                    fg_color=THEME["accent"] if is_active else "transparent",
                    text_color=THEME["bg_primary"] if is_active else THEME["text_primary"],
                )
            else:
                btn.configure(
                    bg=THEME["accent"] if is_active else THEME["bg_secondary"],
                    fg=THEME["bg_primary"] if is_active else THEME["text_primary"],
                )

        # Show/hide tab frames
        for name, frame in self.tab_frames.items():
            if name == tab_name:
                frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
            else:
                frame.grid_forget()

    # ==================== MAIN CONTENT ====================

    def _create_main_content(self):
        """Create the main content area with tab frames."""
        if CUSTOMTKINTER_AVAILABLE:
            self.content_frame = ctk.CTkFrame(
                self.root, fg_color=THEME["bg_primary"], corner_radius=0
            )
        else:
            self.content_frame = tk.Frame(self.root, bg=THEME["bg_primary"])

        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Create all tab frames
        self.tab_frames = {}
        self._create_chat_tab()
        self._create_history_tab()
        self._create_documents_tab()
        self._create_rag_tab()
        self._create_tools_tab()
        self._create_settings_tab()

        # Show default tab
        self._switch_tab("chat")

    # ==================== CHAT TAB ====================

    def _create_chat_tab(self):
        """Create the main chat interface tab."""
        if CUSTOMTKINTER_AVAILABLE:
            frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_secondary"])
        else:
            frame = tk.Frame(self.content_frame, bg=THEME["bg_secondary"])

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Chat display area
        if CUSTOMTKINTER_AVAILABLE:
            self.chat_display = ctk.CTkTextbox(
                frame, fg_color=THEME["bg_primary"],
                text_color=THEME["text_primary"],
                font=("Consolas", 12),
                wrap="word", state="disabled",
                corner_radius=10, padx=10, pady=10,
            )
        else:
            self.chat_display = tk.Text(
                frame, bg=THEME["bg_primary"],
                fg=THEME["text_primary"],
                font=("Consolas", 12),
                wrap="word", state="disabled",
                padx=10, pady=10,
            )

        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 5))

        # Input frame
        if CUSTOMTKINTER_AVAILABLE:
            input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        else:
            input_frame = tk.Frame(frame, bg=THEME["bg_secondary"])

        input_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        input_frame.grid_columnconfigure(0, weight=1)

        # Message entry
        if CUSTOMTKINTER_AVAILABLE:
            self.message_entry = ctk.CTkEntry(
                input_frame,
                placeholder_text="Type a message or command...",
                font=("Segoe UI", 12),
                fg_color=THEME["bg_tertiary"],
                text_color=THEME["text_primary"],
                border_color=THEME["border"],
                height=40, corner_radius=8,
            )
        else:
            self.message_entry = tk.Entry(
                input_frame,
                font=("Segoe UI", 12),
                bg=THEME["bg_tertiary"],
                fg=THEME["text_primary"],
                insertbackground=THEME["text_primary"],
                relief="flat", bd=8,
            )

        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.message_entry.bind("<Return>", lambda e: self._send_message())

        # Send button
        if CUSTOMTKINTER_AVAILABLE:
            send_btn = ctk.CTkButton(
                input_frame, text="Send",
                command=self._send_message,
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                font=("Segoe UI", 12, "bold"),
                width=80, height=40, corner_radius=8,
            )
        else:
            send_btn = tk.Button(
                input_frame, text="Send",
                command=self._send_message,
                bg=THEME["accent"], fg=THEME["bg_primary"],
                font=("Segoe UI", 11, "bold"),
                relief="flat", bd=0, padx=15,
                activebackground=THEME["accent_hover"],
            )

        send_btn.grid(row=0, column=1)

        # Voice button
        if CUSTOMTKINTER_AVAILABLE:
            voice_btn = ctk.CTkButton(
                input_frame, text="🎤",
                command=self._trigger_voice_listen,
                fg_color=THEME["bg_tertiary"],
                hover_color=THEME["accent"],
                font=("Segoe UI", 16),
                width=40, height=40, corner_radius=8,
            )
        else:
            voice_btn = tk.Button(
                input_frame, text="Mic",
                command=self._trigger_voice_listen,
                bg=THEME["bg_tertiary"], fg=THEME["text_primary"],
                font=("Segoe UI", 10),
                relief="flat", bd=0, padx=10,
            )

        voice_btn.grid(row=0, column=2, padx=(8, 0))

        self.tab_frames["chat"] = frame

    def _send_message(self):
        """Send a message from the input field."""
        text = self.message_entry.get().strip()
        if not text:
            return

        self.message_entry.delete(0, "end")
        self.add_chat_message("You", text, is_user=True)

        if self.on_send_message:
            threading.Thread(
                target=self.on_send_message, args=(text,), daemon=True
            ).start()

    def add_chat_message(self, sender: str, text: str, is_user: bool = False):
        """Add a message to the chat display."""
        timestamp = datetime.now().strftime("%H:%M")

        color = THEME["accent"] if is_user else THEME["text_secondary"]
        prefix = ">>" if is_user else "<<"

        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"[{timestamp}] {prefix} ", "")
        self.chat_display.insert("end", f"{sender}: ", "")

        # Configure tag for sender color
        tag_name = f"sender_{timestamp}_{sender}"
        if CUSTOMTKINTER_AVAILABLE:
            self.chat_display.tag_config(tag_name, foreground=color, font=("Segoe UI", 11, "bold"))
        else:
            self.chat_display.tag_config(tag_name, foreground=color, font=("Segoe UI", 10, "bold"))

        # Apply tag to the sender line
        last_idx = self.chat_display.index("end-1c")
        line_start = f"{last_idx} linestart"
        self.chat_display.delete(line_start, "end")
        self.chat_display.insert("end", f"[{timestamp}] {prefix} {sender}: ", tag_name)
        self.chat_display.insert("end", f"{text}\n\n", "")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _trigger_voice_listen(self):
        """Trigger voice listening mode."""
        if self.on_voice_toggle:
            result = self.on_voice_toggle()
            speak("Listening..." if result else "Voice disabled.")

    # ==================== HISTORY TAB ====================

    def _create_history_tab(self):
        """Create the chat history management tab."""
        if CUSTOMTKINTER_AVAILABLE:
            frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_secondary"])
        else:
            frame = tk.Frame(self.content_frame, bg=THEME["bg_secondary"])

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Header
        if CUSTOMTKINTER_AVAILABLE:
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            ctk.CTkLabel(
                header, text="Chat History",
                font=("Segoe UI", 18, "bold"),
                text_color=THEME["text_primary"]
            ).pack(side="left")

            # Search
            self.history_search = ctk.CTkEntry(
                header, placeholder_text="Search conversations...",
                font=("Segoe UI", 11),
                fg_color=THEME["bg_tertiary"],
                width=250, height=32,
            )
            self.history_search.pack(side="right", padx=(10, 0))
            self.history_search.bind("<Return>", lambda e: self._refresh_history())

            # New chat button
            new_chat_btn = ctk.CTkButton(
                header, text="+ New Chat",
                command=self._create_new_conversation,
                fg_color=THEME["accent_secondary"],
                hover_color="#2ea043",
                font=("Segoe UI", 11),
                height=32, width=100,
            )
            new_chat_btn.pack(side="right", padx=(10, 0))
        else:
            header = tk.Frame(frame, bg=THEME["bg_secondary"])
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            tk.Label(
                header, text="Chat History",
                font=("Segoe UI", 16, "bold"),
                bg=THEME["bg_secondary"], fg=THEME["text_primary"]
            ).pack(side="left")

        # Conversations list
        if CUSTOMTKINTER_AVAILABLE:
            self.history_list = ctk.CTkScrollableFrame(
                frame, fg_color=THEME["bg_primary"],
                corner_radius=10,
            )
        else:
            self.history_list = tk.Frame(frame, bg=THEME["bg_primary"])

        self.history_list.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)

        self.tab_frames["history"] = frame

    def _create_new_conversation(self):
        """Create a new conversation."""
        try:
            from jarvis_chat_db import create_conversation
            conv_id = create_conversation()
            self.current_conversation_id = conv_id
            self._refresh_history()
            self._switch_tab("chat")
            self.add_chat_message("JARVIS", "Started a new conversation. How can I help?", is_user=False)
        except ImportError:
            self.add_chat_message("JARVIS", "Chat database not available.", is_user=False)

    def _refresh_history(self):
        """Refresh the conversation list."""
        try:
            from jarvis_chat_db import chat_db
            search = getattr(self, 'history_search', None)
            search_text = search.get().strip() if search and hasattr(search, 'get') else None

            conversations = chat_db.list_conversations(
                search=search_text if search_text else None,
                limit=50
            )

            # Clear list
            for widget in self.history_list.winfo_children():
                widget.destroy()

            for conv in conversations:
                self._add_history_item(conv)

        except ImportError:
            if CUSTOMTKINTER_AVAILABLE:
                ctk.CTkLabel(
                    self.history_list,
                    text="Chat database not available.",
                    text_color=THEME["text_muted"]
                ).pack(pady=20)

    def _add_history_item(self, conv: Dict):
        """Add a conversation item to the history list."""
        if CUSTOMTKINTER_AVAILABLE:
            item = ctk.CTkFrame(self.history_list, fg_color=THEME["bg_tertiary"], corner_radius=8)
            item.pack(fill="x", pady=2, padx=5)

            title = ctk.CTkLabel(
                item, text=conv.get("title", "Untitled"),
                font=("Segoe UI", 12),
                text_color=THEME["text_primary"],
                anchor="w"
            )
            title.pack(fill="x", padx=10, pady=(5, 0))

            meta = ctk.CTkLabel(
                item,
                text=f"{conv.get('message_count', 0)} messages · {conv.get('updated_at', '')}",
                font=("Segoe UI", 10),
                text_color=THEME["text_muted"],
                anchor="w"
            )
            meta.pack(fill="x", padx=10, pady=(0, 5))
        else:
            item = tk.Frame(self.history_list, bg=THEME["bg_tertiary"], padx=10, pady=5)
            item.pack(fill="x", pady=2)

            tk.Label(
                item, text=conv.get("title", "Untitled"),
                font=("Segoe UI", 11),
                bg=THEME["bg_tertiary"], fg=THEME["text_primary"],
                anchor="w"
            ).pack(fill="x")

    # ==================== DOCUMENTS TAB ====================

    def _create_documents_tab(self):
        """Create the document upload and management tab."""
        if CUSTOMTKINTER_AVAILABLE:
            frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_secondary"])
        else:
            frame = tk.Frame(self.content_frame, bg=THEME["bg_secondary"])

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Header
        if CUSTOMTKINTER_AVAILABLE:
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            ctk.CTkLabel(
                header, text="Documents",
                font=("Segoe UI", 18, "bold"),
                text_color=THEME["text_primary"]
            ).pack(side="left")

            upload_btn = ctk.CTkButton(
                header, text="+ Upload Document",
                command=self._upload_document,
                fg_color=THEME["accent_secondary"],
                hover_color="#2ea043",
                font=("Segoe UI", 11),
                height=32,
            )
            upload_btn.pack(side="right")
        else:
            header = tk.Frame(frame, bg=THEME["bg_secondary"])
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            tk.Label(
                header, text="Documents",
                font=("Segoe UI", 16, "bold"),
                bg=THEME["bg_secondary"], fg=THEME["text_primary"]
            ).pack(side="left")

            tk.Button(
                header, text="Upload Document",
                command=self._upload_document,
                bg=THEME["accent_secondary"], fg="white"
            ).pack(side="right")

        # Documents list
        if CUSTOMTKINTER_AVAILABLE:
            self.docs_list = ctk.CTkScrollableFrame(
                frame, fg_color=THEME["bg_primary"], corner_radius=10
            )
        else:
            self.docs_list = tk.Frame(frame, bg=THEME["bg_primary"])

        self.docs_list.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)

        # Stats label
        if CUSTOMTKINTER_AVAILABLE:
            self.docs_stats = ctk.CTkLabel(
                frame, text="No documents indexed.",
                font=("Segoe UI", 11),
                text_color=THEME["text_muted"]
            )
            self.docs_stats.grid(row=2, column=0, padx=15, pady=(0, 15))
        else:
            self.docs_stats = tk.Label(
                frame, text="No documents indexed.",
                font=("Segoe UI", 10),
                bg=THEME["bg_secondary"], fg=THEME["text_muted"]
            )
            self.docs_stats.grid(row=2, column=0, padx=15, pady=(0, 15))

        self.tab_frames["documents"] = frame
        self._refresh_documents()

    def _upload_document(self):
        """Open file dialog to upload a document."""
        filetypes = [
            ("All supported", "*.pdf *.txt *.md *.docx *.py *.js *.html *.css *.json *.csv"),
            ("PDF files", "*.pdf"),
            ("Text files", "*.txt *.md"),
            ("Word files", "*.docx"),
            ("Code files", "*.py *.js *.html *.css"),
            ("Data files", "*.json *.csv"),
            ("All files", "*.*"),
        ]

        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=filetypes
        )

        if file_path:
            threading.Thread(target=self._index_document, args=(file_path,), daemon=True).start()

    def _index_document(self, file_path: str):
        """Index a document in the RAG system."""
        try:
            from jarvis_rag import rag_engine
            result = rag_engine.upload_document(Path(file_path))

            if result["success"]:
                self.add_chat_message(
                    "JARVIS",
                    f"Document uploaded: {result['filename']} ({result['chunks_added']} chunks indexed)",
                    is_user=False
                )
            else:
                self.add_chat_message(
                    "JARVIS",
                    f"Upload failed: {result.get('error', 'Unknown error')}",
                    is_user=False
                )
        except ImportError:
            self.add_chat_message("JARVIS", "RAG system not available.", is_user=False)

        self._refresh_documents()

    def _refresh_documents(self):
        """Refresh the documents list."""
        try:
            from jarvis_rag import rag_engine
            docs = rag_engine.list_documents()
            stats = rag_engine.get_stats()

            # Clear list
            for widget in self.docs_list.winfo_children():
                widget.destroy()

            if not docs:
                if CUSTOMTKINTER_AVAILABLE:
                    ctk.CTkLabel(
                        self.docs_list,
                        text="No documents uploaded yet.",
                        text_color=THEME["text_muted"]
                    ).pack(pady=20)
                self.docs_stats.configure(text="No documents indexed.")
                return

            for doc in docs:
                self._add_document_item(doc)

            self.docs_stats.configure(
                text=f"{stats.get('total_documents', 0)} documents · {stats.get('total_chunks', 0)} chunks"
            )

        except ImportError:
            if CUSTOMTKINTER_AVAILABLE:
                ctk.CTkLabel(
                    self.docs_list,
                    text="RAG system not available.",
                    text_color=THEME["text_muted"]
                ).pack(pady=20)

    def _add_document_item(self, doc: Dict):
        """Add a document item to the list."""
        if CUSTOMTKINTER_AVAILABLE:
            item = ctk.CTkFrame(self.docs_list, fg_color=THEME["bg_tertiary"], corner_radius=8)
            item.pack(fill="x", pady=2, padx=5)

            name = ctk.CTkLabel(
                item, text=doc.get("filename", "Unknown"),
                font=("Segoe UI", 12),
                text_color=THEME["text_primary"],
                anchor="w"
            )
            name.pack(fill="x", padx=10, pady=(5, 0))

            meta = ctk.CTkLabel(
                item,
                text=f"{doc.get('total_chunks', 0)} chunks · ID: {doc.get('doc_id', '?')[:8]}",
                font=("Segoe UI", 10),
                text_color=THEME["text_muted"],
                anchor="w"
            )
            meta.pack(fill="x", padx=10, pady=(0, 5))
        else:
            item = tk.Frame(self.docs_list, bg=THEME["bg_tertiary"], padx=10, pady=5)
            item.pack(fill="x", pady=2)

            tk.Label(
                item, text=doc.get("filename", "Unknown"),
                font=("Segoe UI", 11),
                bg=THEME["bg_tertiary"], fg=THEME["text_primary"],
                anchor="w"
            ).pack(fill="x")

    # ==================== RAG Q&A TAB ====================

    def _create_rag_tab(self):
        """Create the RAG Q&A interface."""
        if CUSTOMTKINTER_AVAILABLE:
            frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_secondary"])
        else:
            frame = tk.Frame(self.content_frame, bg=THEME["bg_secondary"])

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Header
        if CUSTOMTKINTER_AVAILABLE:
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            ctk.CTkLabel(
                header, text="Document Q&A (RAG)",
                font=("Segoe UI", 18, "bold"),
                text_color=THEME["text_primary"]
            ).pack(side="left")

            refresh_btn = ctk.CTkButton(
                header, text="Refresh",
                command=self._refresh_rag,
                fg_color=THEME["bg_tertiary"],
                hover_color=THEME["border"],
                font=("Segoe UI", 11),
                height=32, width=80,
            )
            refresh_btn.pack(side="right")
        else:
            header = tk.Frame(frame, bg=THEME["bg_secondary"])
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            tk.Label(
                header, text="Document Q&A (RAG)",
                font=("Segoe UI", 16, "bold"),
                bg=THEME["bg_secondary"], fg=THEME["text_primary"]
            ).pack(side="left")

        # Content split
        content = ctk.CTkFrame(frame, fg_color="transparent") if CUSTOMTKINTER_AVAILABLE \
            else tk.Frame(frame, bg=THEME["bg_secondary"])
        content.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        # Question & Answer area
        qa_frame = ctk.CTkFrame(content, fg_color=THEME["bg_primary"], corner_radius=10) \
            if CUSTOMTKINTER_AVAILABLE \
            else tk.Frame(content, bg=THEME["bg_primary"], padx=10, pady=10)
        qa_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        qa_frame.grid_columnconfigure(0, weight=1)
        qa_frame.grid_rowconfigure(1, weight=1)

        # Question input
        if CUSTOMTKINTER_AVAILABLE:
            self.rag_question = ctk.CTkEntry(
                qa_frame, placeholder_text="Ask about your documents...",
                font=("Segoe UI", 12),
                fg_color=THEME["bg_tertiary"],
                height=40,
            )
        else:
            self.rag_question = tk.Entry(
                qa_frame, font=("Segoe UI", 12),
                bg=THEME["bg_tertiary"], fg=THEME["text_primary"],
                insertbackground=THEME["text_primary"], relief="flat", bd=8,
            )

        self.rag_question.grid(row=0, column=0, sticky="ew", pady=(10, 5), padx=10)
        self.rag_question.bind("<Return>", lambda e: self._ask_rag())

        # Ask button
        if CUSTOMTKINTER_AVAILABLE:
            ask_btn = ctk.CTkButton(
                qa_frame, text="Ask Documents",
                command=self._ask_rag,
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                font=("Segoe UI", 12, "bold"),
                height=40,
            )
        else:
            ask_btn = tk.Button(
                qa_frame, text="Ask Documents",
                command=self._ask_rag,
                bg=THEME["accent"], fg=THEME["bg_primary"],
                font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
            )

        ask_btn.grid(row=0, column=1, pady=(10, 5), padx=10)

        # Answer display
        if CUSTOMTKINTER_AVAILABLE:
            self.rag_answer = ctk.CTkTextbox(
                qa_frame,
                fg_color=THEME["bg_secondary"],
                text_color=THEME["text_primary"],
                font=("Consolas", 11),
                wrap="word", state="disabled",
            )
        else:
            self.rag_answer = tk.Text(
                qa_frame,
                bg=THEME["bg_secondary"], fg=THEME["text_primary"],
                font=("Consolas", 11),
                wrap="word", state="disabled",
            )

        self.rag_answer.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(5, 10))

        # Sources panel
        sources_frame = ctk.CTkFrame(content, fg_color=THEME["bg_primary"], corner_radius=10) \
            if CUSTOMTKINTER_AVAILABLE \
            else tk.Frame(content, bg=THEME["bg_primary"], padx=10, pady=10)
        sources_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        if CUSTOMTKINTER_AVAILABLE:
            ctk.CTkLabel(
                sources_frame, text="Sources",
                font=("Segoe UI", 14, "bold"),
                text_color=THEME["text_primary"]
            ).pack(anchor="w", padx=10, pady=10)

            self.rag_sources = ctk.CTkScrollableFrame(
                sources_frame, fg_color="transparent"
            )
        else:
            tk.Label(
                sources_frame, text="Sources",
                font=("Segoe UI", 13, "bold"),
                bg=THEME["bg_primary"], fg=THEME["text_primary"]
            ).pack(anchor="w", padx=5, pady=5)

            self.rag_sources = tk.Frame(sources_frame, bg=THEME["bg_primary"])

        self.rag_sources.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_frames["rag"] = frame

    def _ask_rag(self):
        """Ask a question using RAG."""
        question = self.rag_question.get().strip()
        if not question:
            return

        self.rag_question.delete(0, "end")

        # Update answer display
        self.rag_answer.configure(state="normal")
        self.rag_answer.delete("1.0", "end")
        self.rag_answer.insert("1.0", f"Searching documents for: {question}\n\n")
        self.rag_answer.configure(state="disabled")

        threading.Thread(target=self._process_rag_query, args=(question,), daemon=True).start()

    def _process_rag_query(self, question: str):
        """Process RAG query in background."""
        try:
            from jarvis_rag import rag_engine
            result = rag_engine.ask_document(question)

            # Update answer
            self.rag_answer.configure(state="normal")
            self.rag_answer.delete("1.0", "end")

            if result["context"]:
                self.rag_answer.insert("1.0", f"Q: {question}\n\n")
                self.rag_answer.insert("end", f"Found {len(result['sources'])} relevant sources:\n\n")

                for i, source in enumerate(result["sources"], 1):
                    self.rag_answer.insert("end", f"[{i}] {source['filename']} (relevance: {source['similarity']}%)\n")
                    self.rag_answer.insert("end", f"    {source['text_preview']}\n\n")

                # Use AI to generate answer
                context = result["context"]
                prompt = (
                    f"Based on the following document excerpts, answer this question:\n"
                    f"Question: {question}\n\n"
                    f"Document context:\n{context[:3000]}\n\n"
                    f"Provide a concise, accurate answer based only on the provided context."
                )

                ai_response = brain.ask_jarvis(prompt)
                self.rag_answer.insert("end", f"---\n\nAnswer:\n{ai_response}\n")
            else:
                self.rag_answer.insert("1.0", f"No relevant documents found for: {question}\n\n")
                self.rag_answer.insert("end", "Try uploading documents first or rephrasing your question.")

            self.rag_answer.configure(state="disabled")

            # Update sources panel
            for widget in self.rag_sources.winfo_children():
                widget.destroy()

            for i, source in enumerate(result["sources"], 1):
                if CUSTOMTKINTER_AVAILABLE:
                    src = ctk.CTkFrame(self.rag_sources, fg_color=THEME["bg_tertiary"], corner_radius=6)
                    src.pack(fill="x", pady=2, padx=5)

                    ctk.CTkLabel(
                        src, text=f"[{i}] {source['filename']}",
                        font=("Segoe UI", 10),
                        text_color=THEME["text_primary"],
                        anchor="w"
                    ).pack(fill="x", padx=8, pady=(4, 0))

                    ctk.CTkLabel(
                        src, text=f"Relevance: {source['similarity']}%",
                        font=("Segoe UI", 9),
                        text_color=THEME["accent"],
                        anchor="w"
                    ).pack(fill="x", padx=8, pady=(0, 4))

        except ImportError:
            self.rag_answer.configure(state="normal")
            self.rag_answer.delete("1.0", "end")
            self.rag_answer.insert("1.0", "RAG system not available.")
            self.rag_answer.configure(state="disabled")

    def _refresh_rag(self):
        """Refresh RAG tab."""
        self._refresh_documents()

    # ==================== TOOLS TAB ====================

    def _create_tools_tab(self):
        """Create the agent tools showcase tab."""
        if CUSTOMTKINTER_AVAILABLE:
            frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_secondary"])
        else:
            frame = tk.Frame(self.content_frame, bg=THEME["bg_secondary"])

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Header
        if CUSTOMTKINTER_AVAILABLE:
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            ctk.CTkLabel(
                header, text="Agent Tools",
                font=("Segoe UI", 18, "bold"),
                text_color=THEME["text_primary"]
            ).pack(side="left")

            run_btn = ctk.CTkButton(
                header, text="Run Tool",
                command=self._run_tool,
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                font=("Segoe UI", 11),
                height=32, width=100,
            )
            run_btn.pack(side="right")
        else:
            header = tk.Frame(frame, bg=THEME["bg_secondary"])
            header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

            tk.Label(
                header, text="Agent Tools",
                font=("Segoe UI", 16, "bold"),
                bg=THEME["bg_secondary"], fg=THEME["text_primary"]
            ).pack(side="left")

        # Tools list
        if CUSTOMTKINTER_AVAILABLE:
            self.tools_list = ctk.CTkScrollableFrame(
                frame, fg_color=THEME["bg_primary"], corner_radius=10
            )
        else:
            self.tools_list = tk.Frame(frame, bg=THEME["bg_primary"])

        self.tools_list.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)

        # Add tool cards
        tools_info = [
            ("web_search", "Web Search", "Search the web using DuckDuckGo for current information."),
            ("run_python", "Python Executor", "Execute Python code safely in a sandboxed environment."),
            ("calculator", "Calculator", "Advanced math: algebra, trig, logarithms, and more."),
            ("file_operations", "File Manager", "Read, write, list, and search files."),
            ("system_info", "System Info", "Get CPU, RAM, disk, battery, and process information."),
            ("datetime_tool", "DateTime", "Current time, date calculations, and timezone info."),
            ("shell_command", "Shell", "Run safe, non-destructive shell commands."),
        ]

        for tool_id, name, desc in tools_info:
            self._add_tool_card(tool_id, name, desc)

        self.tab_frames["tools"] = frame

    def _add_tool_card(self, tool_id: str, name: str, desc: str):
        """Add a tool info card."""
        if CUSTOMTKINTER_AVAILABLE:
            card = ctk.CTkFrame(self.tools_list, fg_color=THEME["bg_tertiary"], corner_radius=8)
            card.pack(fill="x", pady=3, padx=5)

            ctk.CTkLabel(
                card, text=name,
                font=("Segoe UI", 13, "bold"),
                text_color=THEME["accent"],
                anchor="w"
            ).pack(fill="x", padx=10, pady=(8, 2))

            ctk.CTkLabel(
                card, text=desc,
                font=("Segoe UI", 11),
                text_color=THEME["text_secondary"],
                anchor="w", wraplength=500
            ).pack(fill="x", padx=10, pady=(2, 8))
        else:
            card = tk.Frame(self.tools_list, bg=THEME["bg_tertiary"], padx=10, pady=8)
            card.pack(fill="x", pady=3)

            tk.Label(
                card, text=name,
                font=("Segoe UI", 12, "bold"),
                bg=THEME["bg_tertiary"], fg=THEME["accent"],
                anchor="w"
            ).pack(fill="x")

            tk.Label(
                card, text=desc,
                font=("Segoe UI", 10),
                bg=THEME["bg_tertiary"], fg=THEME["text_secondary"],
                anchor="w", wraplength=500, justify="left"
            ).pack(fill="x")

    def _run_tool(self):
        """Open dialog to run a specific tool."""
        tool = simpledialog.askstring(
            "Run Tool",
            "Enter tool name (web_search, calculator, etc.):"
        )
        if tool:
            param = simpledialog.askstring("Parameters", "Enter parameters (JSON format):")
            try:
                import json
                params = json.loads(param or "{}")
                from jarvis_agent_tools import agent
                result = agent.executor.execute(tool, params)
                self.add_chat_message("Tool", f"{tool}: {result[:200]}", is_user=False)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ==================== SETTINGS TAB ====================

    def _create_settings_tab(self):
        """Create the settings configuration tab."""
        if CUSTOMTKINTER_AVAILABLE:
            frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_secondary"])
        else:
            frame = tk.Frame(self.content_frame, bg=THEME["bg_secondary"])

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        if CUSTOMTKINTER_AVAILABLE:
            scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        else:
            scroll = tk.Frame(frame, bg=THEME["bg_secondary"])

        scroll.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        # Title
        if CUSTOMTKINTER_AVAILABLE:
            ctk.CTkLabel(
                scroll, text="Settings",
                font=("Segoe UI", 22, "bold"),
                text_color=THEME["text_primary"]
            ).pack(anchor="w", pady=(0, 15))

            # API Key
            api_frame = ctk.CTkFrame(scroll, fg_color=THEME["bg_primary"], corner_radius=10)
            api_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                api_frame, text="Groq API Key",
                font=("Segoe UI", 14, "bold"),
                text_color=THEME["text_primary"]
            ).pack(anchor="w", padx=15, pady=(10, 5))

            self.api_key_entry = ctk.CTkEntry(
                api_frame, show="*",
                font=("Consolas", 12),
                fg_color=THEME["bg_tertiary"],
                height=36,
            )
            self.api_key_entry.pack(fill="x", padx=15, pady=(0, 5))

            save_api_btn = ctk.CTkButton(
                api_frame, text="Save API Key",
                command=self._save_api_key,
                fg_color=THEME["accent_secondary"],
                hover_color="#2ea043",
                height=32,
            )
            save_api_btn.pack(anchor="w", padx=15, pady=(0, 10))

            # Voice Settings
            voice_frame = ctk.CTkFrame(scroll, fg_color=THEME["bg_primary"], corner_radius=10)
            voice_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                voice_frame, text="Voice Settings",
                font=("Segoe UI", 14, "bold"),
                text_color=THEME["text_primary"]
            ).pack(anchor="w", padx=15, pady=(10, 5))

            # Voice speed slider
            ctk.CTkLabel(
                voice_frame, text="Voice Speed (WPM)",
                font=("Segoe UI", 12),
                text_color=THEME["text_secondary"]
            ).pack(anchor="w", padx=15)

            self.speed_slider = ctk.CTkSlider(
                voice_frame, from_=100, to=250,
                number_of_steps=150,
                command=self._update_voice_speed,
            )
            self.speed_slider.set(172)
            self.speed_slider.pack(fill="x", padx=15, pady=5)

            self.speed_label = ctk.CTkLabel(
                voice_frame, text="172 WPM",
                font=("Segoe UI", 11),
                text_color=THEME["text_muted"]
            )
            self.speed_label.pack(anchor="w", padx=15, pady=(0, 10))

            # Wake Word
            ctk.CTkLabel(
                voice_frame, text="Wake Word",
                font=("Segoe UI", 12),
                text_color=THEME["text_secondary"]
            ).pack(anchor="w", padx=15, pady=(5, 0))

            self.wake_word_entry = ctk.CTkEntry(
                voice_frame,
                font=("Segoe UI", 12),
                fg_color=THEME["bg_tertiary"],
                height=36,
            )
            self.wake_word_entry.insert(0, WAKE_WORD)
            self.wake_word_entry.pack(fill="x", padx=15, pady=5)

            save_wake_btn = ctk.CTkButton(
                voice_frame, text="Save Wake Word",
                command=self._save_wake_word,
                fg_color=THEME["accent_secondary"],
                hover_color="#2ea043",
                height=32,
            )
            save_wake_btn.pack(anchor="w", padx=15, pady=(0, 10))

            # Appearance
            appearance_frame = ctk.CTkFrame(scroll, fg_color=THEME["bg_primary"], corner_radius=10)
            appearance_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                appearance_frame, text="Appearance",
                font=("Segoe UI", 14, "bold"),
                text_color=THEME["text_primary"]
            ).pack(anchor="w", padx=15, pady=(10, 5))

            self.theme_menu = ctk.CTkOptionMenu(
                appearance_frame,
                values=["Dark", "Light", "System"],
                command=self._change_theme,
            )
            self.theme_menu.set("Dark")
            self.theme_menu.pack(anchor="w", padx=15, pady=(0, 10))

            # About
            about_frame = ctk.CTkFrame(scroll, fg_color=THEME["bg_primary"], corner_radius=10)
            about_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                about_frame, text="About JARVIS v4",
                font=("Segoe UI", 14, "bold"),
                text_color=THEME["text_primary"]
            ).pack(anchor="w", padx=15, pady=(10, 5))

            about_text = (
                "JARVIS v4 - AI Voice Assistant\n"
                "Built for CSE Students & Developers\n\n"
                "Features:\n"
                "- Voice & text control\n"
                "- Persistent chat history (SQLite)\n"
                "- Document Q&A with RAG\n"
                "- Multi-agent tool calling\n"
                "- Modern CustomTkinter UI\n\n"
                "Powered by Groq API (Llama 3)"
            )

            ctk.CTkLabel(
                about_frame, text=about_text,
                font=("Segoe UI", 11),
                text_color=THEME["text_secondary"],
                anchor="w", justify="left"
            ).pack(anchor="w", padx=15, pady=(0, 10))
        else:
            tk.Label(
                scroll, text="Settings",
                font=("Segoe UI", 18, "bold"),
                bg=THEME["bg_secondary"], fg=THEME["text_primary"]
            ).pack(anchor="w", pady=(0, 10))

            tk.Label(
                scroll,
                text="Settings require CustomTkinter. Install: pip install customtkinter",
                font=("Segoe UI", 11),
                bg=THEME["bg_secondary"], fg=THEME["text_secondary"]
            ).pack(anchor="w", pady=5)

        self.tab_frames["settings"] = frame

    def _save_api_key(self):
        """Save the Groq API key."""
        key = self.api_key_entry.get().strip()
        if key:
            try:
                env_path = BASE_DIR / ".env"
                lines = []
                if env_path.exists():
                    lines = env_path.read_text().splitlines()

                # Update or add GROQ_API_KEY
                key_found = False
                for i, line in enumerate(lines):
                    if line.startswith("GROQ_API_KEY="):
                        lines[i] = f"GROQ_API_KEY={key}"
                        key_found = True
                        break

                if not key_found:
                    lines.append(f"GROQ_API_KEY={key}")

                env_path.write_text("\n".join(lines) + "\n")
                messagebox.showinfo("Success", "API Key saved! Restart JARVIS to apply.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _update_voice_speed(self, value):
        """Update voice speed from slider."""
        if hasattr(self, 'speed_label'):
            self.speed_label.configure(text=f"{int(value)} WPM")

    def _save_wake_word(self):
        """Save wake word setting."""
        word = self.wake_word_entry.get().strip().lower()
        if word:
            try:
                env_path = BASE_DIR / ".env"
                lines = []
                if env_path.exists():
                    lines = env_path.read_text().splitlines()

                key_found = False
                for i, line in enumerate(lines):
                    if line.startswith("WAKE_WORD="):
                        lines[i] = f"WAKE_WORD={word}"
                        key_found = True
                        break

                if not key_found:
                    lines.append(f"WAKE_WORD={word}")

                env_path.write_text("\n".join(lines) + "\n")

                if self.on_wake_word_change:
                    self.on_wake_word_change(word)

                messagebox.showinfo("Success", f"Wake word set to '{word}'! Restart to apply.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _change_theme(self, theme_name: str):
        """Change the UI theme."""
        if CUSTOMTKINTER_AVAILABLE:
            ctk.set_appearance_mode(theme_name.lower())

    # ==================== STATUS BAR ====================

    def _create_status_bar(self):
        """Create the bottom status bar."""
        if CUSTOMTKINTER_AVAILABLE:
            status_bar = ctk.CTkFrame(
                self.root, height=28, fg_color=THEME["bg_secondary"],
                corner_radius=0
            )
        else:
            status_bar = tk.Frame(self.root, height=28, bg=THEME["bg_secondary"])

        status_bar.grid(row=1, column=1, sticky="ew")

        if CUSTOMTKINTER_AVAILABLE:
            self.clock_label = ctk.CTkLabel(
                status_bar, text="00:00:00",
                font=("Consolas", 11),
                text_color=THEME["text_muted"]
            )
            self.clock_label.pack(side="right", padx=10)

            self.stats_label = ctk.CTkLabel(
                status_bar, text="JARVIS v4 Ready",
                font=("Segoe UI", 10),
                text_color=THEME["text_muted"]
            )
            self.stats_label.pack(side="left", padx=10)
        else:
            self.clock_label = tk.Label(
                status_bar, text="00:00:00",
                font=("Consolas", 10),
                bg=THEME["bg_secondary"], fg=THEME["text_muted"]
            )
            self.clock_label.pack(side="right", padx=10)

            self.stats_label = tk.Label(
                status_bar, text="JARVIS v4 Ready",
                font=("Segoe UI", 9),
                bg=THEME["bg_secondary"], fg=THEME["text_muted"]
            )
            self.stats_label.pack(side="left", padx=10)

    # ==================== UPDATE LOOPS ====================

    def _update_clock(self):
        """Update the clock display every second."""
        if not self._running:
            return

        try:
            now = datetime.now().strftime("%H:%M:%S")
            self.clock_label.configure(text=now)
        except Exception:
            pass

        if self.root and self._running:
            self.root.after(1000, self._update_clock)

    def _process_queue(self):
        """Process queued UI updates."""
        if not self._running:
            return

        try:
            while True:
                task = self._command_queue.get_nowait()
                if task["type"] == "status":
                    self._update_status(task["status"])
                elif task["type"] == "message":
                    self.add_chat_message(
                        task.get("sender", "JARVIS"),
                        task["text"],
                        task.get("is_user", False)
                    )
        except queue.Empty:
            pass

        if self.root and self._running:
            self.root.after(100, self._process_queue)

    def _update_status(self, status: str):
        """Update the status indicator."""
        color_map = {
            "idle": THEME["status_idle"],
            "listening": THEME["status_listening"],
            "speaking": THEME["status_speaking"],
            "thinking": THEME["status_thinking"],
        }
        color = color_map.get(status, THEME["status_idle"])
        label = status.capitalize()

        try:
            if hasattr(self, 'status_dot'):
                self.status_dot.configure(text_color=color)
            if hasattr(self, 'status_label'):
                self.status_label.configure(text=label)

            # Update stats
            mem_count = len(getattr(brain, 'conversation_memory', [])) if 'brain' in globals() else 0
            self.stats_label.configure(
                text=f"Status: {label} | Memory: {mem_count}"
            )
        except Exception:
            pass

    def _toggle_voice(self):
        """Toggle voice on/off."""
        self.voice_enabled = not self.voice_enabled

    # ==================== PUBLIC API ====================

    def start(self):
        """Start the HUD in a background thread."""
        if self._running:
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(1)

    def _run(self):
        """Run the tkinter main loop."""
        try:
            self._create_window()
            if self.root:
                self.root.mainloop()
        except Exception as e:
            print(f"[HUD ERROR] {e}")
        finally:
            self._running = False
            self.root = None

    def stop(self):
        """Stop the HUD."""
        self._running = False
        if self.root:
            try:
                self.root.after(10, self.root.destroy)
            except Exception:
                pass

    def update(self, status: str = None, command: str = None,
               response: str = None, memory_count: int = None):
        """Update HUD state from external sources."""
        if status:
            self._command_queue.put({
                "type": "status",
                "status": status
            })

        if command:
            self._command_queue.put({
                "type": "message",
                "sender": "You",
                "text": command,
                "is_user": True
            })

        if response:
            self._command_queue.put({
                "type": "message",
                "sender": "JARVIS",
                "text": response,
                "is_user": False
            })

    def add_user_message(self, text: str):
        """Add a user message to the chat."""
        self._command_queue.put({
            "type": "message",
            "sender": "You",
            "text": text,
            "is_user": True
        })

    def add_ai_message(self, text: str):
        """Add an AI message to the chat."""
        self._command_queue.put({
            "type": "message",
            "sender": "JARVIS",
            "text": text,
            "is_user": False
        })


# ============================================================
# GLOBAL INSTANCE & HELPERS
# ============================================================

hud = JarvisHUD()


def update_hud(status: str = None, command: str = None,
               response: str = None, memory_count: int = None):
    """Convenience function to update the global HUD."""
    hud.update(status=status, command=command, response=response,
               memory_count=memory_count)


__all__ = ['JarvisHUD', 'hud', 'update_hud']
