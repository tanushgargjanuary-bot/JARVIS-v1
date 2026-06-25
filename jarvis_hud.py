"""
JARVIS v3 - HUD Overlay
=======================
Floating tkinter window showing real-time JARVIS status.
Always-on-top, transparent dark background, draggable.
Shows: time, status indicator, last command, last response,
memory count, and session duration.
"""

import tkinter as tk
from tkinter import Menu
import threading
import time
from datetime import datetime


class JarvisHUD:
    """Floating HUD overlay for JARVIS status display."""

    # Status colors
    STATUS_IDLE = "#666666"       # Grey
    STATUS_LISTENING = "#00FF00"  # Green
    STATUS_SPEAKING = "#FF4444"   # Red
    STATUS_THINKING = "#FFAA00"   # Yellow/Orange

    def __init__(self):
        self.root = None
        self._thread = None
        self._running = False

        # HUD data
        self._status = "idle"           # idle, listening, speaking, thinking
        self._last_command = "Waiting..."
        self._last_response = "JARVIS ready."
        self._memory_count = 0
        self._session_start = datetime.now()

        # UI elements (set after creation)
        self.status_canvas = None
        self.status_dot = None
        self.lbl_time = None
        self.lbl_command = None
        self.lbl_response = None
        self.lbl_memory = None
        self.lbl_duration = None

        # Pulsing animation
        self._pulse_direction = 1
        self._pulse_size = 6
        self._status_color = self.STATUS_IDLE

    def _create_window(self):
        """Create the tkinter HUD window."""
        self.root = tk.Tk()
        self.root.title("JARVIS v3")

        # Window properties
        self.root.geometry("320x180+1050+550")  # Bottom-right corner
        self.root.overrideredirect(True)         # No borders
        self.root.attributes('-topmost', True)   # Always on top
        self.root.attributes('-alpha', 0.88)     # Slight transparency
        self.root.configure(bg='#0a0a0a')

        # Make draggable
        self.root.bind('<Button-1>', self._start_drag)
        self.root.bind('<B1-Motion>', self._on_drag)
        self.root.bind('<Button-3>', self._show_context_menu)

        # --- Build UI ---
        padding = 6
        bg_color = '#0a0a0a'
        fg_color = '#00FFFF'       # Cyan title
        text_color = '#E0E0E0'     # Light grey text
        accent = '#0088AA'

        # Title frame
        title_frame = tk.Frame(self.root, bg=bg_color)
        title_frame.pack(fill='x', padx=padding, pady=(padding, 2))

        # Status indicator dot (canvas for pulsing effect)
        self.status_canvas = tk.Canvas(title_frame, width=14, height=14,
                                        bg=bg_color, highlightthickness=0)
        self.status_canvas.pack(side='left', padx=(0, 6))
        self.status_dot = self.status_canvas.create_oval(
            2, 2, 12, 12, fill=self.STATUS_IDLE, outline=''
        )

        lbl_title = tk.Label(title_frame, text="JARVIS v3",
                             font=('Consolas', 12, 'bold'),
                             fg=fg_color, bg=bg_color)
        lbl_title.pack(side='left')

        # Time label
        self.lbl_time = tk.Label(self.root, text="00:00:00",
                                  font=('Consolas', 9),
                                  fg='#888888', bg=bg_color)
        self.lbl_time.pack(anchor='e', padx=padding)

        # Separator
        sep = tk.Frame(self.root, height=1, bg=accent)
        sep.pack(fill='x', padx=padding, pady=2)

        # Last command
        tk.Label(self.root, text="CMD:", font=('Consolas', 7),
                 fg='#555555', bg=bg_color).pack(anchor='w', padx=padding)
        self.lbl_command = tk.Label(self.root, text="Waiting...",
                                     font=('Consolas', 8),
                                     fg=text_color, bg=bg_color,
                                     wraplength=300, justify='left')
        self.lbl_command.pack(anchor='w', padx=padding)

        # Last response
        tk.Label(self.root, text="RSP:", font=('Consolas', 7),
                 fg='#555555', bg=bg_color).pack(anchor='w', padx=padding)
        self.lbl_response = tk.Label(self.root, text="JARVIS ready.",
                                      font=('Consolas', 8),
                                      fg='#AAAAAA', bg=bg_color,
                                      wraplength=300, justify='left')
        self.lbl_response.pack(anchor='w', padx=padding)

        # Separator
        sep2 = tk.Frame(self.root, height=1, bg=accent)
        sep2.pack(fill='x', padx=padding, pady=2)

        # Bottom info bar
        info_frame = tk.Frame(self.root, bg=bg_color)
        info_frame.pack(fill='x', padx=padding, pady=(0, padding))

        self.lbl_memory = tk.Label(info_frame, text="Mem: 0",
                                    font=('Consolas', 7),
                                    fg='#666666', bg=bg_color)
        self.lbl_memory.pack(side='left')

        self.lbl_duration = tk.Label(info_frame, text="00:00:00",
                                      font=('Consolas', 7),
                                      fg='#666666', bg=bg_color)
        self.lbl_duration.pack(side='right')

        # Start update loops
        self._update_time()
        self._update_duration()
        self._pulse_animation()

    def _start_drag(self, event):
        """Start window drag."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        """Handle window drag motion."""
        x = self.root.winfo_x() + event.x - self._drag_start_x
        y = self.root.winfo_y() + event.y - self._drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def _show_context_menu(self, event):
        """Show right-click context menu."""
        menu = Menu(self.root, tearoff=0, bg='#1a1a1a', fg='#E0E0E0',
                    activebackground='#0088AA', activeforeground='#FFFFFF')
        menu.add_command(label="Toggle Always on Top",
                         command=self._toggle_topmost)
        menu.add_command(label="Toggle Transparency",
                         command=self._toggle_transparency)
        menu.add_separator()
        menu.add_command(label="Minimize to Taskbar",
                         command=self._minimize)
        menu.add_separator()
        menu.add_command(label="Exit HUD",
                         command=self.stop, foreground='#FF4444')
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_topmost(self):
        """Toggle always-on-top state."""
        current = self.root.attributes('-topmost')
        self.root.attributes('-topmost', not current)

    def _toggle_transparency(self):
        """Toggle window transparency."""
        current = self.root.attributes('-alpha')
        new_alpha = 0.5 if current > 0.7 else 0.88
        self.root.attributes('-alpha', new_alpha)

    def _minimize(self):
        """Minimize window to taskbar."""
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.after(100, lambda: self.root.overrideredirect(True))

    def _update_time(self):
        """Update the time display every second."""
        if not self._running or not self.root:
            return
        try:
            now = datetime.now().strftime("%H:%M:%S")
            self.lbl_time.config(text=now)
        except Exception:
            pass
        if self.root:
            self.root.after(1000, self._update_time)

    def _update_duration(self):
        """Update session duration every second."""
        if not self._running or not self.root:
            return
        try:
            elapsed = datetime.now() - self._session_start
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.lbl_duration.config(
                text=f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            )
        except Exception:
            pass
        if self.root:
            self.root.after(1000, self._update_duration)

    def _pulse_animation(self):
        """Animate the status dot with pulsing effect."""
        if not self._running or not self.root or not self.status_canvas:
            return

        try:
            # Pulse size
            self._pulse_size += 0.3 * self._pulse_direction
            if self._pulse_size >= 8:
                self._pulse_direction = -1
            elif self._pulse_size <= 4:
                self._pulse_direction = 1

            center = 7
            offset = self._pulse_size
            x1 = center - offset
            y1 = center - offset
            x2 = center + offset
            y2 = center + offset

            self.status_canvas.coords(self.status_dot, x1, y1, x2, y2)
            self.status_canvas.itemconfig(self.status_dot, fill=self._status_color)
        except Exception:
            pass

        if self.root:
            self.root.after(150, self._pulse_animation)

    def _run(self):
        """Run the tkinter main loop in a thread."""
        try:
            self._create_window()
            self._running = True
            self.root.mainloop()
        except Exception as e:
            print(f"[HUD ERROR] {e}")
        finally:
            self._running = False
            self.root = None

    # ==================== PUBLIC API ====================

    def start(self):
        """Start the HUD in a background thread."""
        if self._running:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # Wait briefly for window to initialize
        time.sleep(0.5)

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
        """
        Update HUD display elements.
        status: 'idle', 'listening', 'speaking', 'thinking'
        command: last user command text
        response: last JARVIS response text
        memory_count: current conversation memory count
        """
        if not self._running or not self.root:
            return

        try:
            # Update status dot color
            if status:
                self._status = status
                color_map = {
                    'idle': self.STATUS_IDLE,
                    'listening': self.STATUS_LISTENING,
                    'speaking': self.STATUS_SPEAKING,
                    'thinking': self.STATUS_THINKING,
                }
                self._status_color = color_map.get(status, self.STATUS_IDLE)

            # Update command label
            if command is not None:
                display_cmd = command[:45] + "..." if len(command) > 45 else command
                self.lbl_command.config(text=display_cmd)

            # Update response label
            if response is not None:
                display_rsp = response[:45] + "..." if len(response) > 45 else response
                self.lbl_response.config(text=display_rsp)

            # Update memory count
            if memory_count is not None:
                self.lbl_memory.config(text=f"Mem: {memory_count}")

        except Exception:
            pass  # HUD might be closing


# Global HUD instance
hud = JarvisHUD()


def update_hud(status: str = None, command: str = None,
               response: str = None, memory_count: int = None):
    """Convenience function to update the global HUD."""
    hud.update(status=status, command=command, response=response,
               memory_count=memory_count)


# Export
__all__ = ['JarvisHUD', 'hud', 'update_hud']
