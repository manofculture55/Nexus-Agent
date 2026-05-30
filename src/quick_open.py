"""
quick_open.py — NEXUS Quick Open Overlay
A lightweight, always-on-top floating overlay window toggled with Ctrl+Alt+N.
Uses Tkinter for the GUI and pynput for global hotkey detection.
Runs independently of the main CLI agent.

Phase 21 of the NEXUS implementation plan.

Launch with:  pythonw src/quick_open.py   (no console window)
    or:       python  src/quick_open.py   (with console for debugging)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext

# Add src/ to the path so local imports work correctly
sys.path.insert(0, os.path.dirname(__file__))

from pynput.keyboard import GlobalHotKeys


# ---------------------------------------------------------------------------
# Theme colours (Catppuccin Mocha inspired — matches TODO spec)
# ---------------------------------------------------------------------------
BG_DARK      = "#0A1931"      # Main background (from project palette)
BG_MEDIUM    = "#1A3D63"      # Input / title bar background
BG_CHAT      = "#0D2137"      # Chat area background (slightly lighter)
FG_TEXT      = "#F6FAFD"      # Primary text (from project palette)
FG_DIM       = "#B3CFE5"      # Secondary / dim text (from project palette)
ACCENT       = "#4A7FA7"      # Accent colour — buttons, borders (from project palette)
ACCENT_HOVER = "#5E9CC7"      # Button hover state
ERROR_RED    = "#f38ba8"      # Error messages
SUCCESS_GRN  = "#a6e3a1"      # Success messages
THINKING_YLW = "#f9e2af"      # "Thinking..." indicator

# Fonts
FONT_TITLE   = ("Segoe UI", 11, "bold")
FONT_CHAT    = ("Consolas", 10)
FONT_INPUT   = ("Segoe UI", 10)
FONT_BTN     = ("Segoe UI", 9)
FONT_QBTN    = ("Segoe UI", 9)

# Window dimensions
WIN_WIDTH    = 420
WIN_HEIGHT   = 540


# ---------------------------------------------------------------------------
# Quick Open Application
# ---------------------------------------------------------------------------
class QuickOpenApp:
    """The main Quick Open overlay application."""

    def __init__(self):
        self.root = tk.Tk()
        self._visible = True
        self._model_loaded = False
        self._processing = False

        self._setup_window()
        self._build_ui()
        self._setup_hotkey()
        self._load_model_async()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------
    def _setup_window(self):
        """Configure the main overlay window."""
        self.root.title("NEXUS Quick Open")
        self.root.overrideredirect(True)  # Remove default title bar
        self.root.attributes("-topmost", True)  # Always on top
        self.root.configure(bg=BG_DARK)

        # Try to make semi-transparent (Windows-specific)
        try:
            self.root.attributes("-alpha", 0.95)
        except tk.TclError:
            pass  # Not supported on this platform

        # Position on the right edge of the screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - WIN_WIDTH - 20
        y = (screen_h - WIN_HEIGHT) // 2
        self.root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}+{x}+{y}")

        # Allow window dragging via the custom title bar
        self._drag_x = 0
        self._drag_y = 0

        # Handle window close cleanly
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Build UI widgets
    # ------------------------------------------------------------------
    def _build_ui(self):
        """Construct all UI elements."""

        # === Custom title bar ===
        title_bar = tk.Frame(self.root, bg=BG_MEDIUM, height=36)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)

        # Make title bar draggable
        title_bar.bind("<Button-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._do_drag)

        # Title label
        title_label = tk.Label(
            title_bar, text="  ⚡ NEXUS Quick Open", font=FONT_TITLE,
            bg=BG_MEDIUM, fg=FG_TEXT, anchor="w"
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._do_drag)

        # Minimize button
        min_btn = tk.Label(
            title_bar, text=" — ", font=FONT_TITLE,
            bg=BG_MEDIUM, fg=FG_DIM, cursor="hand2"
        )
        min_btn.pack(side=tk.RIGHT, padx=(0, 2))
        min_btn.bind("<Button-1>", lambda e: self._toggle_window())

        # Close button
        close_btn = tk.Label(
            title_bar, text=" ✕ ", font=FONT_TITLE,
            bg=BG_MEDIUM, fg=ERROR_RED, cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT, padx=(0, 2))
        close_btn.bind("<Button-1>", lambda e: self._on_close())

        # === Status bar (under title) ===
        self._status_label = tk.Label(
            self.root, text="Loading model...", font=("Segoe UI", 8),
            bg=BG_DARK, fg=THINKING_YLW, anchor="w"
        )
        self._status_label.pack(fill=tk.X, padx=10, pady=(2, 0))

        # === Chat area ===
        chat_frame = tk.Frame(self.root, bg=BG_DARK)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 4))

        self.chat_area = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=FONT_CHAT,
            bg=BG_CHAT, fg=FG_TEXT, insertbackground=FG_TEXT,
            relief=tk.FLAT, borderwidth=0, padx=10, pady=8,
            state=tk.DISABLED, cursor="arrow",
            selectbackground=ACCENT, selectforeground=FG_TEXT,
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for styling
        self.chat_area.tag_configure("user", foreground=SUCCESS_GRN, font=("Consolas", 10, "bold"))
        self.chat_area.tag_configure("nexus", foreground=ACCENT_HOVER, font=("Consolas", 10, "bold"))
        self.chat_area.tag_configure("thinking", foreground=THINKING_YLW, font=("Consolas", 10, "italic"))
        self.chat_area.tag_configure("error", foreground=ERROR_RED)
        self.chat_area.tag_configure("info", foreground=FG_DIM)
        self.chat_area.tag_configure("response", foreground=FG_TEXT)

        # Show welcome message
        self._append_chat("NEXUS Quick Open ready.\n", "info")
        self._append_chat("Press Ctrl+Alt+N to show/hide this window.\n", "info")
        self._append_chat("Type a command below or use the quick action buttons.\n\n", "info")

        # === Quick action buttons ===
        btn_frame = tk.Frame(self.root, bg=BG_DARK)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 4))

        buttons = [
            ("🔋 Battery", self._quick_battery),
            ("📊 Processes", self._quick_processes),
            ("❓ Help", self._quick_help),
            ("🗑 Clear", self._quick_clear),
        ]

        for text, cmd in buttons:
            btn = tk.Button(
                btn_frame, text=text, font=FONT_QBTN,
                bg=BG_MEDIUM, fg=FG_TEXT, activebackground=ACCENT,
                activeforeground=FG_TEXT, relief=tk.FLAT,
                cursor="hand2", command=cmd, padx=8, pady=3
            )
            btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=ACCENT))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG_MEDIUM))

        # === Input area ===
        input_frame = tk.Frame(self.root, bg=BG_DARK)
        input_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.input_field = tk.Entry(
            input_frame, font=FONT_INPUT,
            bg=BG_MEDIUM, fg=FG_TEXT, insertbackground=FG_TEXT,
            relief=tk.FLAT, borderwidth=0,
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 4))
        self.input_field.insert(0, "Type a command...")
        self.input_field.config(fg=FG_DIM)

        # Placeholder behavior
        self.input_field.bind("<FocusIn>", self._on_focus_in)
        self.input_field.bind("<FocusOut>", self._on_focus_out)
        self.input_field.bind("<Return>", lambda e: self._send_command())

        # Send button
        send_btn = tk.Button(
            input_frame, text="Send", font=FONT_BTN,
            bg=ACCENT, fg=FG_TEXT, activebackground=ACCENT_HOVER,
            activeforeground=FG_TEXT, relief=tk.FLAT,
            cursor="hand2", command=self._send_command,
            padx=14, pady=5
        )
        send_btn.pack(side=tk.RIGHT)
        send_btn.bind("<Enter>", lambda e: send_btn.config(bg=ACCENT_HOVER))
        send_btn.bind("<Leave>", lambda e: send_btn.config(bg=ACCENT))

        # === Bottom border accent ===
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------------------
    # Chat area helpers
    # ------------------------------------------------------------------
    def _append_chat(self, text, tag=None):
        """Append text to the chat area (thread-safe via root.after if needed)."""
        self.chat_area.config(state=tk.NORMAL)
        if tag:
            self.chat_area.insert(tk.END, text, tag)
        else:
            self.chat_area.insert(tk.END, text)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def _append_chat_safe(self, text, tag=None):
        """Thread-safe version of _append_chat — schedules on the main thread."""
        self.root.after(0, self._append_chat, text, tag)

    # ------------------------------------------------------------------
    # Input field placeholder
    # ------------------------------------------------------------------
    def _on_focus_in(self, event):
        if self.input_field.get() == "Type a command...":
            self.input_field.delete(0, tk.END)
            self.input_field.config(fg=FG_TEXT)

    def _on_focus_out(self, event):
        if not self.input_field.get():
            self.input_field.insert(0, "Type a command...")
            self.input_field.config(fg=FG_DIM)

    # ------------------------------------------------------------------
    # Window dragging
    # ------------------------------------------------------------------
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Global hotkey (Ctrl+Alt+N)
    # ------------------------------------------------------------------
    def _setup_hotkey(self):
        """Register Ctrl+Alt+N as a global hotkey using pynput."""
        hotkeys = GlobalHotKeys({
            "<ctrl>+<alt>+n": self._on_hotkey_pressed,
        })
        hotkeys.daemon = True
        hotkeys.start()

    def _on_hotkey_pressed(self):
        """Called from the hotkey thread — schedule toggle on main thread."""
        self.root.after(0, self._toggle_window)

    def _toggle_window(self):
        """Show/hide the overlay window."""
        if self._visible:
            self.root.withdraw()
            self._visible = False
        else:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.input_field.focus_set()
            # Clear placeholder and get ready for input
            if self.input_field.get() == "Type a command...":
                self.input_field.delete(0, tk.END)
                self.input_field.config(fg=FG_TEXT)
            self._visible = True

    # ------------------------------------------------------------------
    # Model loading (async at startup)
    # ------------------------------------------------------------------
    def _load_model_async(self):
        """Load the NEXUS model in a background thread."""
        def _load():
            try:
                from model_loader import load_model
                load_model()
                self._model_loaded = True
                self.root.after(0, self._set_status, "Ready — model loaded", SUCCESS_GRN)
            except Exception as e:
                self.root.after(0, self._set_status, f"Model load failed: {e}", ERROR_RED)

        t = threading.Thread(target=_load, daemon=True)
        t.start()

    def _set_status(self, text, color=FG_DIM):
        """Update the status bar text and color."""
        self._status_label.config(text=text, fg=color)

    # ------------------------------------------------------------------
    # Send command
    # ------------------------------------------------------------------
    def _send_command(self):
        """Read input, route it, and display the response."""
        user_input = self.input_field.get().strip()

        if not user_input or user_input == "Type a command...":
            return

        if self._processing:
            return  # Don't allow concurrent requests

        # Clear input field
        self.input_field.delete(0, tk.END)

        # Display user message
        self._append_chat(f"You: ", "user")
        self._append_chat(f"{user_input}\n", "response")

        # Check if model is loaded
        if not self._model_loaded:
            self._append_chat("NEXUS: ", "nexus")
            self._append_chat("Model is still loading. Please wait...\n\n", "thinking")
            return

        # Show thinking indicator
        self._append_chat("NEXUS: ", "nexus")
        self._append_chat("Thinking...\n", "thinking")
        self._set_status("Processing...", THINKING_YLW)
        self._processing = True

        # Run the route in a separate thread
        def _process():
            try:
                from router import route
                result = route(user_input)
                self.root.after(0, self._show_response, result)
            except Exception as e:
                self.root.after(0, self._show_error, str(e))

        t = threading.Thread(target=_process, daemon=True)
        t.start()

    def _show_response(self, result):
        """Display the response from NEXUS (called on main thread)."""
        # Remove the "Thinking..." line by replacing the last bit
        self.chat_area.config(state=tk.NORMAL)
        # Find and remove the last "Thinking..." text
        content = self.chat_area.get("1.0", tk.END)
        thinking_idx = content.rfind("Thinking...\n")
        if thinking_idx >= 0:
            # Calculate line/col position
            before = content[:thinking_idx]
            line = before.count("\n") + 1
            col = len(before.split("\n")[-1])
            start_pos = f"{line}.{col}"
            end_pos = f"{line}.{col + len('Thinking...') + 1}"
            self.chat_area.delete(start_pos, end_pos)
        self.chat_area.config(state=tk.DISABLED)

        # Show the actual response
        self._append_chat(f"{result}\n\n", "response")
        self._set_status("Ready", SUCCESS_GRN)
        self._processing = False

    def _show_error(self, error_msg):
        """Display an error message (called on main thread)."""
        # Remove "Thinking..."
        self.chat_area.config(state=tk.NORMAL)
        content = self.chat_area.get("1.0", tk.END)
        thinking_idx = content.rfind("Thinking...\n")
        if thinking_idx >= 0:
            before = content[:thinking_idx]
            line = before.count("\n") + 1
            col = len(before.split("\n")[-1])
            start_pos = f"{line}.{col}"
            end_pos = f"{line}.{col + len('Thinking...') + 1}"
            self.chat_area.delete(start_pos, end_pos)
        self.chat_area.config(state=tk.DISABLED)

        self._append_chat(f"Error: {error_msg}\n\n", "error")
        self._set_status("Error occurred", ERROR_RED)
        self._processing = False

    # ------------------------------------------------------------------
    # Quick action buttons
    # ------------------------------------------------------------------
    def _quick_battery(self):
        """Quick action: show battery status."""
        if not self._model_loaded:
            self._append_chat("Model is still loading...\n\n", "thinking")
            return
        try:
            import system_tasks
            result = system_tasks.get_battery()
            self._append_chat("NEXUS: ", "nexus")
            self._append_chat(f"{result}\n\n", "response")
        except Exception as e:
            self._append_chat(f"Error: {e}\n\n", "error")

    def _quick_processes(self):
        """Quick action: show running processes."""
        if not self._model_loaded:
            self._append_chat("Model is still loading...\n\n", "thinking")
            return
        try:
            import system_tasks
            result = system_tasks.get_processes()
            self._append_chat("NEXUS: ", "nexus")
            self._append_chat(f"{result}\n\n", "response")
        except Exception as e:
            self._append_chat(f"Error: {e}\n\n", "error")

    def _quick_help(self):
        """Quick action: show available commands."""
        help_text = (
            "━━━ Available Commands ━━━\n"
            "• Summarise a file:      summarise notes.txt\n"
            "• Summarise a folder:    summarise all files in C:\\docs\n"
            "• Ask a question:        what is machine learning?\n"
            "• Battery status:        battery / what is my battery?\n"
            "• Running processes:     show processes\n"
            "• Model info:            model info\n"
            "• Reset training:        reset my training\n"
            "• Rename file:           rename notes.txt to old.txt\n"
            "• Copy file:             copy report.pdf to D:\\backup\n"
            "• Move file:             move data.csv to D:\\archive\n"
            "• Delete file:           delete file temp.txt\n"
            "• List files:            list files in C:\\docs\n"
            "• Search docs (RAG):     what do my files say about X?\n"
            "• Reindex files:         reindex my files\n"
            "• Shutdown:              shut down my computer\n"
            "• Restart:               restart the computer\n"
            "• Sleep:                 put the computer to sleep\n"
        )
        self._append_chat(help_text + "\n", "info")

    def _quick_clear(self):
        """Quick action: clear the chat area."""
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.config(state=tk.DISABLED)
        self._append_chat("Chat cleared.\n\n", "info")

    # ------------------------------------------------------------------
    # Close / cleanup
    # ------------------------------------------------------------------
    def _on_close(self):
        """Clean shutdown."""
        self.root.destroy()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def run(self):
        """Start the Tkinter main loop."""
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = QuickOpenApp()
    app.run()
