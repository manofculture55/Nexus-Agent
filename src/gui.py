"""
gui.py — NEXUS Graphical User Interface
A full-featured chat GUI built with Tkinter so non-technical users
don't need to use the command line. Connects to the same backend
(router, model_loader) as the CLI agent and Quick Open overlay.

Phase 22 of the NEXUS implementation plan.

Launch with:  python src/gui.py      (from nexus-agent root)
         or:  gui.bat                (double-click)
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, filedialog

# Add src/ to the path so local imports work correctly
sys.path.insert(0, os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# Theme colours — matches project colour palette & quick_open.py
# ---------------------------------------------------------------------------
BG_DARK      = "#0A1931"      # Main background (from project palette)
BG_MEDIUM    = "#1A3D63"      # Sidebar / input / menu background
BG_CHAT      = "#0D2137"      # Chat area background
BG_MENU      = "#0F2A47"      # Menu bar background
FG_TEXT      = "#F6FAFD"      # Primary text
FG_DIM       = "#B3CFE5"      # Secondary / dim text
ACCENT       = "#4A7FA7"      # Accent colour — buttons, borders, highlights
ACCENT_HOVER = "#5E9CC7"      # Button hover state
ERROR_RED    = "#f38ba8"      # Error messages
SUCCESS_GRN  = "#a6e3a1"      # Success messages
THINKING_YLW = "#f9e2af"      # "Thinking..." indicator
SEPARATOR    = "#1A3D63"      # Separator lines

# Fonts
FONT_TITLE   = ("Segoe UI", 13, "bold")
FONT_CHAT    = ("Consolas", 10)
FONT_INPUT   = ("Segoe UI", 11)
FONT_BTN     = ("Segoe UI", 10, "bold")
FONT_STATUS  = ("Segoe UI", 9)
FONT_MENU    = ("Segoe UI", 10)

# Window dimensions
WIN_WIDTH    = 820
WIN_HEIGHT   = 640
MIN_WIDTH    = 600
MIN_HEIGHT   = 450

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "config", "settings.json")


# ---------------------------------------------------------------------------
# NEXUS GUI Application
# ---------------------------------------------------------------------------
class NexusGUI:
    """The main NEXUS graphical user interface."""

    def __init__(self):
        self.root = tk.Tk()
        self._model_loaded = False
        self._processing = False
        self._memory = None  # ConversationMemory instance

        self._setup_window()
        self._build_menu_bar()
        self._build_ui()
        self._load_model_async()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------
    def _setup_window(self):
        """Configure the main application window."""
        self.root.title("NEXUS — Offline AI Agent")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)

        # Centre the window on screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - WIN_WIDTH) // 2
        y = (screen_h - WIN_HEIGHT) // 2
        self.root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}+{x}+{y}")

        # Window icon — use default if no .ico available
        try:
            self.root.iconbitmap(default="")
        except tk.TclError:
            pass

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------
    def _build_menu_bar(self):
        """Build the menu bar with File, Settings, Help menus."""
        menu_bar = tk.Menu(self.root, bg=BG_MENU, fg=FG_TEXT,
                           activebackground=ACCENT, activeforeground=FG_TEXT,
                           font=FONT_MENU, relief=tk.FLAT, borderwidth=0)

        # --- File menu ---
        file_menu = tk.Menu(menu_bar, tearoff=0, bg=BG_MEDIUM, fg=FG_TEXT,
                            activebackground=ACCENT, activeforeground=FG_TEXT,
                            font=FONT_MENU)
        file_menu.add_command(label="New Chat", command=self._new_chat,
                              accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close,
                              accelerator="Alt+F4")
        menu_bar.add_cascade(label="File", menu=file_menu)

        # --- Settings menu ---
        settings_menu = tk.Menu(menu_bar, tearoff=0, bg=BG_MEDIUM, fg=FG_TEXT,
                                activebackground=ACCENT, activeforeground=FG_TEXT,
                                font=FONT_MENU)
        settings_menu.add_command(label="Model Info", command=self._show_model_info)
        settings_menu.add_command(label="Manage Permissions", command=self._manage_permissions)
        menu_bar.add_cascade(label="Settings", menu=settings_menu)

        # --- Help menu ---
        help_menu = tk.Menu(menu_bar, tearoff=0, bg=BG_MEDIUM, fg=FG_TEXT,
                            activebackground=ACCENT, activeforeground=FG_TEXT,
                            font=FONT_MENU)
        help_menu.add_command(label="Available Commands", command=self._show_commands)
        help_menu.add_separator()
        help_menu.add_command(label="About NEXUS", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self._new_chat())

    # ------------------------------------------------------------------
    # Build UI widgets
    # ------------------------------------------------------------------
    def _build_ui(self):
        """Construct all UI elements."""

        # === Header bar ===
        header = tk.Frame(self.root, bg=BG_MEDIUM, height=52)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Logo / title
        title_label = tk.Label(
            header, text="  ⚡ N E X U S", font=FONT_TITLE,
            bg=BG_MEDIUM, fg=FG_TEXT, anchor="w"
        )
        title_label.pack(side=tk.LEFT, padx=(16, 0), fill=tk.Y)

        subtitle_label = tk.Label(
            header, text="Offline AI Agent v2.0  ", font=FONT_STATUS,
            bg=BG_MEDIUM, fg=FG_DIM, anchor="e"
        )
        subtitle_label.pack(side=tk.RIGHT, padx=(0, 16), fill=tk.Y)

        # Accent line under header
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill=tk.X)

        # === Status bar (under header) ===
        status_frame = tk.Frame(self.root, bg=BG_DARK)
        status_frame.pack(fill=tk.X)

        self._status_label = tk.Label(
            status_frame, text="⏳ Loading model — please wait...",
            font=FONT_STATUS, bg=BG_DARK, fg=THINKING_YLW, anchor="w"
        )
        self._status_label.pack(fill=tk.X, padx=16, pady=(6, 2))

        # === Chat area ===
        chat_frame = tk.Frame(self.root, bg=BG_DARK)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 4))

        self.chat_area = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=FONT_CHAT,
            bg=BG_CHAT, fg=FG_TEXT, insertbackground=FG_TEXT,
            relief=tk.FLAT, borderwidth=0, padx=14, pady=10,
            state=tk.DISABLED, cursor="arrow",
            selectbackground=ACCENT, selectforeground=FG_TEXT,
            spacing1=2, spacing3=2,
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for styling
        self.chat_area.tag_configure("user_label", foreground=SUCCESS_GRN,
                                     font=("Consolas", 10, "bold"))
        self.chat_area.tag_configure("nexus_label", foreground=ACCENT_HOVER,
                                     font=("Consolas", 10, "bold"))
        self.chat_area.tag_configure("thinking", foreground=THINKING_YLW,
                                     font=("Consolas", 10, "italic"))
        self.chat_area.tag_configure("error", foreground=ERROR_RED)
        self.chat_area.tag_configure("info", foreground=FG_DIM)
        self.chat_area.tag_configure("response", foreground=FG_TEXT)
        self.chat_area.tag_configure("separator", foreground=SEPARATOR,
                                     font=("Consolas", 8))
        self.chat_area.tag_configure("timestamp", foreground="#6B7F99",
                                     font=("Consolas", 8))

        # Welcome message
        self._append_chat("Welcome to NEXUS — your offline AI assistant.\n", "info")
        self._append_chat("Type a message below to get started. ", "info")
        self._append_chat("Use the Help menu for available commands.\n\n", "info")

        # === Separator line ===
        tk.Frame(self.root, bg=SEPARATOR, height=1).pack(fill=tk.X, padx=12)

        # === Input area ===
        input_frame = tk.Frame(self.root, bg=BG_DARK)
        input_frame.pack(fill=tk.X, padx=12, pady=(8, 12))

        # Input field
        self.input_field = tk.Entry(
            input_frame, font=FONT_INPUT,
            bg=BG_MEDIUM, fg=FG_TEXT, insertbackground=FG_TEXT,
            relief=tk.FLAT, borderwidth=0,
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True,
                              ipady=10, padx=(0, 8))
        self.input_field.insert(0, "Ask me anything...")
        self.input_field.config(fg=FG_DIM)

        # Placeholder behavior
        self.input_field.bind("<FocusIn>", self._on_focus_in)
        self.input_field.bind("<FocusOut>", self._on_focus_out)
        self.input_field.bind("<Return>", lambda e: self._send_command())

        # Send button
        self.send_btn = tk.Button(
            input_frame, text="  Send  ", font=FONT_BTN,
            bg=ACCENT, fg=FG_TEXT, activebackground=ACCENT_HOVER,
            activeforeground=FG_TEXT, relief=tk.FLAT,
            cursor="hand2", command=self._send_command,
            padx=18, pady=8
        )
        self.send_btn.pack(side=tk.RIGHT)
        self.send_btn.bind("<Enter>",
                           lambda e: self.send_btn.config(bg=ACCENT_HOVER))
        self.send_btn.bind("<Leave>",
                           lambda e: self.send_btn.config(bg=ACCENT))

        # === Bottom accent line ===
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill=tk.X, side=tk.BOTTOM)

        # Set initial focus
        self.input_field.focus_set()

    # ------------------------------------------------------------------
    # Chat area helpers
    # ------------------------------------------------------------------
    def _append_chat(self, text, tag=None):
        """Append text to the chat area."""
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

    def _insert_separator(self):
        """Insert a visual separator line between exchanges."""
        self._append_chat("─" * 60 + "\n", "separator")

    # ------------------------------------------------------------------
    # Input field placeholder
    # ------------------------------------------------------------------
    def _on_focus_in(self, event):
        if self.input_field.get() == "Ask me anything...":
            self.input_field.delete(0, tk.END)
            self.input_field.config(fg=FG_TEXT)

    def _on_focus_out(self, event):
        if not self.input_field.get():
            self.input_field.insert(0, "Ask me anything...")
            self.input_field.config(fg=FG_DIM)

    # ------------------------------------------------------------------
    # Model loading (async at startup)
    # ------------------------------------------------------------------
    def _load_model_async(self):
        """Load the NEXUS model in a background thread."""
        def _load():
            try:
                from model_loader import load_model
                from router import set_conversation_memory
                from memory import ConversationMemory

                load_model()

                # Initialise conversation memory
                self._memory = ConversationMemory()
                set_conversation_memory(self._memory)

                self._model_loaded = True
                self.root.after(0, self._set_status,
                                "✅ Ready — model loaded", SUCCESS_GRN)
                self._append_chat_safe("NEXUS is ready! How can I help?\n\n",
                                       "info")
            except Exception as e:
                self.root.after(0, self._set_status,
                                f"❌ Model load failed: {e}", ERROR_RED)
                self._append_chat_safe(
                    f"Error loading model: {e}\n\n", "error")

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

        if not user_input or user_input == "Ask me anything...":
            return

        if self._processing:
            return  # Don't allow concurrent requests

        # Clear input field
        self.input_field.delete(0, tk.END)

        # Handle built-in GUI commands
        lower = user_input.lower()
        if lower in ("exit", "quit", "bye"):
            self._on_close()
            return
        if lower == "help":
            self._show_commands()
            return
        if lower in ("clear", "new chat"):
            self._new_chat()
            return

        # Display user message
        self._append_chat("You: ", "user_label")
        self._append_chat(f"{user_input}\n", "response")

        # Check if model is loaded
        if not self._model_loaded:
            self._append_chat("NEXUS: ", "nexus_label")
            self._append_chat("Model is still loading. Please wait...\n\n",
                              "thinking")
            return

        # Show thinking indicator
        self._append_chat("NEXUS: ", "nexus_label")
        self._thinking_mark = self.chat_area.index(tk.END + "-1c")
        self._append_chat("Thinking...\n", "thinking")
        self._set_status("⏳ Processing...", THINKING_YLW)
        self._processing = True
        self.send_btn.config(state=tk.DISABLED, bg=BG_MEDIUM)

        # Run the route in a separate thread
        def _process():
            try:
                from router import route
                result = route(user_input)
                self.root.after(0, self._show_response, user_input, result)
            except Exception as e:
                self.root.after(0, self._show_error, str(e))

        t = threading.Thread(target=_process, daemon=True)
        t.start()

    def _show_response(self, user_input, result):
        """Display the response from NEXUS (called on main thread)."""
        # Remove the "Thinking..." line
        self._remove_thinking()

        # Show the actual response
        self._append_chat(f"{result}\n\n", "response")
        self._set_status("✅ Ready", SUCCESS_GRN)
        self._processing = False
        self.send_btn.config(state=tk.NORMAL, bg=ACCENT)

        # Record in conversation memory
        if self._memory:
            self._memory.add_message("user", user_input)
            self._memory.add_message("assistant", result)

    def _show_error(self, error_msg):
        """Display an error message (called on main thread)."""
        self._remove_thinking()

        self._append_chat(f"Error: {error_msg}\n\n", "error")
        self._set_status("⚠️ Error occurred", ERROR_RED)
        self._processing = False
        self.send_btn.config(state=tk.NORMAL, bg=ACCENT)

    def _remove_thinking(self):
        """Remove the 'Thinking...' indicator from the chat area."""
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

    # ------------------------------------------------------------------
    # Menu actions — File
    # ------------------------------------------------------------------
    def _new_chat(self):
        """Clear chat area and reset conversation memory."""
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.config(state=tk.DISABLED)

        if self._memory:
            self._memory.clear()

        self._append_chat("Chat cleared — starting a new conversation.\n\n",
                          "info")

    # ------------------------------------------------------------------
    # Menu actions — Settings
    # ------------------------------------------------------------------
    def _show_model_info(self):
        """Show model information in a dialog."""
        try:
            import model_manager
            info = model_manager.get_model_info()
            self._show_info_dialog("Model Information", info)
        except Exception as e:
            messagebox.showerror("Error", f"Could not get model info:\n{e}",
                                 parent=self.root)

    def _manage_permissions(self):
        """Show permissions management dialog."""
        try:
            from permission_guard import load_permissions, add_permission, \
                remove_permission
        except ImportError:
            messagebox.showerror("Error",
                                 "Could not load permission_guard module.",
                                 parent=self.root)
            return

        # Create permissions dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Permissions")
        dialog.configure(bg=BG_DARK)
        dialog.geometry("520x400")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Centre dialog on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 520) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        dialog.geometry(f"+{x}+{y}")

        # Title
        tk.Label(dialog, text="Allowed Folders", font=FONT_TITLE,
                 bg=BG_DARK, fg=FG_TEXT).pack(pady=(16, 4))
        tk.Label(dialog,
                 text="NEXUS can only access files inside these folders.",
                 font=FONT_STATUS, bg=BG_DARK, fg=FG_DIM).pack(pady=(0, 8))

        # Listbox with current permissions
        list_frame = tk.Frame(dialog, bg=BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        listbox = tk.Listbox(
            list_frame, font=FONT_CHAT, bg=BG_CHAT, fg=FG_TEXT,
            selectbackground=ACCENT, selectforeground=FG_TEXT,
            relief=tk.FLAT, borderwidth=0, highlightthickness=0,
        )
        listbox.pack(fill=tk.BOTH, expand=True)

        # Populate
        perms = load_permissions()
        for p in perms:
            listbox.insert(tk.END, p)

        # Buttons
        btn_frame = tk.Frame(dialog, bg=BG_DARK)
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 16))

        def _add_folder():
            folder = filedialog.askdirectory(
                title="Select a folder to allow",
                parent=dialog
            )
            if folder:
                add_permission(folder)
                listbox.delete(0, tk.END)
                for p in load_permissions():
                    listbox.insert(tk.END, p)

        def _remove_selected():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Info", "Select a folder to remove.",
                                    parent=dialog)
                return
            folder = listbox.get(sel[0])
            confirm = messagebox.askyesno(
                "Confirm",
                f"Remove access for:\n{folder}?",
                parent=dialog
            )
            if confirm:
                remove_permission(folder)
                listbox.delete(0, tk.END)
                for p in load_permissions():
                    listbox.insert(tk.END, p)

        add_btn = tk.Button(btn_frame, text="➕ Add Folder", font=FONT_BTN,
                            bg=ACCENT, fg=FG_TEXT,
                            activebackground=ACCENT_HOVER,
                            activeforeground=FG_TEXT, relief=tk.FLAT,
                            command=_add_folder, padx=12, pady=6)
        add_btn.pack(side=tk.LEFT, padx=(0, 8))

        rem_btn = tk.Button(btn_frame, text="➖ Remove Selected", font=FONT_BTN,
                            bg="#5a3a3a", fg=FG_TEXT,
                            activebackground=ERROR_RED,
                            activeforeground=FG_TEXT, relief=tk.FLAT,
                            command=_remove_selected, padx=12, pady=6)
        rem_btn.pack(side=tk.LEFT, padx=(0, 8))

        close_btn = tk.Button(btn_frame, text="Close", font=FONT_BTN,
                              bg=BG_MEDIUM, fg=FG_TEXT,
                              activebackground=ACCENT,
                              activeforeground=FG_TEXT, relief=tk.FLAT,
                              command=dialog.destroy, padx=12, pady=6)
        close_btn.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Menu actions — Help
    # ------------------------------------------------------------------
    def _show_commands(self):
        """Display available commands in the chat area."""
        commands_text = (
            "━━━ Available Commands ━━━\n"
            "\n"
            "  📄 Summarise a file        \"summarise notes.txt\"\n"
            "  📁 Summarise a folder      \"summarise all files in C:\\docs\"\n"
            "  ❓ Ask a question           \"what is machine learning?\"\n"
            "  🔋 Battery status           \"what is my battery percentage?\"\n"
            "  📊 Running processes        \"show running processes\"\n"
            "  🤖 Model info               \"model info\"\n"
            "  🔄 Reset training           \"reset my training\"\n"
            "  📝 Rename a file            \"rename notes.txt to old.txt\"\n"
            "  📋 Copy a file              \"copy report.pdf to D:\\backup\"\n"
            "  📦 Move a file              \"move data.csv to D:\\archive\"\n"
            "  🗑  Delete a file            \"delete file temp.txt\"\n"
            "  📂 List files               \"list files in C:\\docs\"\n"
            "  🔍 Search documents (RAG)   \"what do my files say about X?\"\n"
            "  🔃 Reindex files            \"reindex my files\"\n"
            "  💬 Clear chat               \"clear\" or \"new chat\"\n"
            "  💻 Shutdown                  \"shut down my computer\"\n"
            "  🔁 Restart                   \"restart the computer\"\n"
            "  😴 Sleep                     \"put the computer to sleep\"\n"
            "  🚪 Exit                      \"exit\"\n"
            "\n"
        )
        self._append_chat(commands_text, "info")

    def _show_about(self):
        """Show the About dialog."""
        about_text = (
            "NEXUS — Offline AI Agent v2.0\n\n"
            "A fully offline, privacy-first AI assistant\n"
            "that runs on your local machine.\n\n"
            "Model: Qwen 2.5 3B Instruct (GGUF)\n"
            "Engine: llama-cpp-python\n"
            "Interface: Tkinter\n\n"
            "All processing happens locally —\n"
            "no data leaves your computer."
        )
        messagebox.showinfo("About NEXUS", about_text, parent=self.root)

    # ------------------------------------------------------------------
    # Generic info dialog (for multi-line content like model info)
    # ------------------------------------------------------------------
    def _show_info_dialog(self, title, content):
        """Show a modal dialog with scrollable text content."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=BG_DARK)
        dialog.geometry("500x360")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Centre on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 360) // 2
        dialog.geometry(f"+{x}+{y}")

        text_area = scrolledtext.ScrolledText(
            dialog, wrap=tk.WORD, font=FONT_CHAT,
            bg=BG_CHAT, fg=FG_TEXT, relief=tk.FLAT,
            borderwidth=0, padx=12, pady=10,
        )
        text_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 4))
        text_area.insert("1.0", content)
        text_area.config(state=tk.DISABLED)

        close_btn = tk.Button(
            dialog, text="Close", font=FONT_BTN,
            bg=ACCENT, fg=FG_TEXT, activebackground=ACCENT_HOVER,
            activeforeground=FG_TEXT, relief=tk.FLAT,
            command=dialog.destroy, padx=16, pady=6
        )
        close_btn.pack(pady=(4, 12))

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
    app = NexusGUI()
    app.run()
