# -*- coding: utf-8 -*-
"""
quick_open.py -- NEXUS Quick Menu (Primary Interface)
A compact, ChatGPT-like overlay window toggled with Ctrl+Alt+N.
Features: slash command pills, three-dot menu, theme switching,
minimize/maximize/close controls, and clean visual design.

Phase 30 of the NEXUS implementation plan.

Launch with:  pythonw src/quick_open.py   (no console window)
    or:       python  src/quick_open.py   (with console for debugging)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog

# Add src/ to the path so local imports work correctly
sys.path.insert(0, os.path.dirname(__file__))

try:
    from pynput.keyboard import GlobalHotKeys
    _HAS_PYNPUT = True
except ImportError:
    _HAS_PYNPUT = False

import themes


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_TITLE   = ("Segoe UI", 11, "bold")
FONT_CHAT    = ("Consolas", 10)
FONT_INPUT   = ("Segoe UI", 10)
FONT_BTN     = ("Segoe UI", 9)
FONT_PILL    = ("Segoe UI", 8)
FONT_MENU    = ("Segoe UI", 9)
FONT_STATUS  = ("Segoe UI", 8)
FONT_WCTRL   = ("Segoe UI", 12)

# Window dimensions (compact calculator-like default)
WIN_WIDTH    = 420
WIN_HEIGHT   = 560


# ---------------------------------------------------------------------------
# Quick Menu Application
# ---------------------------------------------------------------------------
class QuickOpenApp:
    """The main Quick Menu application -- primary NEXUS interface."""

    def __init__(self):
        self.root = tk.Tk()
        self._visible = True
        self._model_loaded = False
        self._processing = False
        self._maximized = False
        self._saved_geometry = None
        self._menu_window = None
        self._theme_name = themes.load_saved_theme()
        self._theme = themes.get_theme(self._theme_name)

        # Collect themed widgets for live theme switching
        self._themed_widgets = []

        self._setup_window()
        self._build_ui()
        self._setup_hotkey()
        self._load_model_async()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------
    def _setup_window(self):
        """Configure the main overlay window."""
        self.root.title("NEXUS")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self._theme["bg_dark"])

        try:
            self.root.attributes("-alpha", 0.97)
        except tk.TclError:
            pass

        # Position on the right edge of the screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - WIN_WIDTH - 20
        y = (screen_h - WIN_HEIGHT) // 2
        self.root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}+{x}+{y}")

        self._drag_x = 0
        self._drag_y = 0

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        """Construct all UI elements with the redesigned layout."""
        t = self._theme

        # === Custom title bar ===
        self._title_bar = tk.Frame(self.root, bg=t["bg_medium"], height=38)
        self._title_bar.pack(fill=tk.X, side=tk.TOP)
        self._title_bar.pack_propagate(False)

        self._title_bar.bind("<Button-1>", self._start_drag)
        self._title_bar.bind("<B1-Motion>", self._do_drag)

        # Title label
        self._title_label = tk.Label(
            self._title_bar, text="  NEXUS", font=FONT_TITLE,
            bg=t["bg_medium"], fg=t["fg_text"], anchor="w"
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self._title_label.bind("<Button-1>", self._start_drag)
        self._title_label.bind("<B1-Motion>", self._do_drag)

        # --- Window controls (right side): three-dot, minimize, maximize, close ---

        # Three-dot menu button
        self._menu_btn = tk.Label(
            self._title_bar, text=" \u22ee ", font=FONT_WCTRL,
            bg=t["bg_medium"], fg=t["fg_dim"], cursor="hand2"
        )
        self._menu_btn.pack(side=tk.RIGHT, padx=(0, 2))
        self._menu_btn.bind("<Button-1>", lambda e: self._show_menu())
        self._menu_btn.bind("<Enter>", lambda e: self._menu_btn.config(bg=t["accent"]))
        self._menu_btn.bind("<Leave>", lambda e: self._menu_btn.config(bg=t["bg_medium"]))

        # Close button
        self._close_btn = tk.Label(
            self._title_bar, text=" \u2715 ", font=("Segoe UI", 10, "bold"),
            bg=t["bg_medium"], fg=t["error_red"], cursor="hand2"
        )
        self._close_btn.pack(side=tk.RIGHT, padx=(0, 1))
        self._close_btn.bind("<Button-1>", lambda e: self._on_close())
        self._close_btn.bind("<Enter>", lambda e: self._close_btn.config(bg="#C0392B"))
        self._close_btn.bind("<Leave>", lambda e: self._close_btn.config(bg=t["bg_medium"]))

        # Maximize button
        self._max_btn = tk.Label(
            self._title_bar, text=" \u25a1 ", font=("Segoe UI", 10),
            bg=t["bg_medium"], fg=t["fg_dim"], cursor="hand2"
        )
        self._max_btn.pack(side=tk.RIGHT, padx=(0, 1))
        self._max_btn.bind("<Button-1>", lambda e: self._toggle_maximize())
        self._max_btn.bind("<Enter>", lambda e: self._max_btn.config(bg=t["accent"]))
        self._max_btn.bind("<Leave>", lambda e: self._max_btn.config(bg=t["bg_medium"]))

        # Minimize button
        self._min_btn = tk.Label(
            self._title_bar, text=" \u2014 ", font=("Segoe UI", 10),
            bg=t["bg_medium"], fg=t["fg_dim"], cursor="hand2"
        )
        self._min_btn.pack(side=tk.RIGHT, padx=(0, 1))
        self._min_btn.bind("<Button-1>", lambda e: self._minimize_window())
        self._min_btn.bind("<Enter>", lambda e: self._min_btn.config(bg=t["accent"]))
        self._min_btn.bind("<Leave>", lambda e: self._min_btn.config(bg=t["bg_medium"]))

        # === Status bar ===
        self._status_label = tk.Label(
            self.root, text="Loading model...", font=FONT_STATUS,
            bg=t["bg_dark"], fg=t["thinking_ylw"], anchor="w"
        )
        self._status_label.pack(fill=tk.X, padx=10, pady=(2, 0))

        # === Chat area ===
        self._chat_frame = tk.Frame(self.root, bg=t["bg_dark"])
        self._chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 4))

        self.chat_area = scrolledtext.ScrolledText(
            self._chat_frame, wrap=tk.WORD, font=FONT_CHAT,
            bg=t["bg_chat"], fg=t["fg_text"], insertbackground=t["fg_text"],
            relief=tk.FLAT, borderwidth=0, padx=12, pady=10,
            state=tk.DISABLED, cursor="arrow",
            selectbackground=t["accent"], selectforeground=t["fg_text"],
            spacing1=2, spacing3=2,
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        # Configure text tags
        self._configure_tags()

        # Show welcome message
        self._append_chat("Welcome to NEXUS\n", "nexus")
        self._append_chat("Use slash commands for quick actions:\n", "info")
        self._append_chat("  /task  /web  /open  /remember  /help\n", "info")
        self._append_chat("Or just type naturally and NEXUS will understand.\n", "info")
        self._append_chat("Press Ctrl+Alt+N to show/hide this window.\n\n", "info")

        # === Slash command pill buttons ===
        self._pill_frame = tk.Frame(self.root, bg=t["bg_dark"])
        self._pill_frame.pack(fill=tk.X, padx=8, pady=(0, 4))

        pill_commands = ["/task", "/web", "/open", "/remember", "/help"]
        self._pill_buttons = []
        for cmd in pill_commands:
            pill = tk.Label(
                self._pill_frame, text=cmd, font=FONT_PILL,
                bg=t["pill_bg"], fg=t["fg_dim"], cursor="hand2",
                padx=10, pady=3, relief=tk.FLAT,
            )
            pill.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
            pill.bind("<Button-1>", lambda e, c=cmd: self._insert_slash_command(c))
            pill.bind("<Enter>", lambda e, p=pill: p.config(
                bg=self._theme["pill_hover"], fg=self._theme["fg_text"]))
            pill.bind("<Leave>", lambda e, p=pill: p.config(
                bg=self._theme["pill_bg"], fg=self._theme["fg_dim"]))
            self._pill_buttons.append(pill)

        # === Input area ===
        self._input_frame = tk.Frame(self.root, bg=t["bg_dark"])
        self._input_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        # Input field with rounded-look frame wrapper
        input_wrapper = tk.Frame(
            self._input_frame, bg=t["bg_medium"], padx=2, pady=2
        )
        input_wrapper.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self._input_wrapper = input_wrapper

        self.input_field = tk.Entry(
            input_wrapper, font=FONT_INPUT,
            bg=t["bg_medium"], fg=t["fg_text"], insertbackground=t["fg_text"],
            relief=tk.FLAT, borderwidth=0,
        )
        self.input_field.pack(fill=tk.X, ipady=8, padx=6)
        self.input_field.insert(0, "Type a command...")
        self.input_field.config(fg=t["fg_dim"])

        self.input_field.bind("<FocusIn>", self._on_focus_in)
        self.input_field.bind("<FocusOut>", self._on_focus_out)
        self.input_field.bind("<Return>", lambda e: self._send_command())

        # Send button
        self._send_btn = tk.Button(
            self._input_frame, text="->", font=("Segoe UI", 10, "bold"),
            bg=t["accent"], fg=t["fg_text"], activebackground=t["accent_hover"],
            activeforeground=t["fg_text"], relief=tk.FLAT,
            cursor="hand2", command=self._send_command,
            padx=12, pady=5, width=3,
        )
        self._send_btn.pack(side=tk.RIGHT)
        self._send_btn.bind("<Enter>", lambda e: self._send_btn.config(bg=t["accent_hover"]))
        self._send_btn.bind("<Leave>", lambda e: self._send_btn.config(bg=t["accent"]))

        # === Bottom accent border ===
        self._bottom_border = tk.Frame(self.root, bg=t["accent"], height=3)
        self._bottom_border.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------------------
    # Text tag configuration
    # ------------------------------------------------------------------
    def _configure_tags(self):
        """Configure text tags for the chat area based on current theme."""
        t = self._theme
        self.chat_area.tag_configure("user", foreground=t["success_grn"],
                                     font=("Consolas", 10, "bold"))
        self.chat_area.tag_configure("nexus", foreground=t["accent_hover"],
                                     font=("Consolas", 10, "bold"))
        self.chat_area.tag_configure("thinking", foreground=t["thinking_ylw"],
                                     font=("Consolas", 10, "italic"))
        self.chat_area.tag_configure("error", foreground=t["error_red"])
        self.chat_area.tag_configure("info", foreground=t["fg_dim"])
        self.chat_area.tag_configure("response", foreground=t["fg_text"])

    # ------------------------------------------------------------------
    # Slash command pill buttons
    # ------------------------------------------------------------------
    def _insert_slash_command(self, command):
        """Insert a slash command prefix into the input field."""
        # Clear placeholder if present
        current = self.input_field.get()
        if current == "Type a command...":
            self.input_field.delete(0, tk.END)
            self.input_field.config(fg=self._theme["fg_text"])

        self.input_field.delete(0, tk.END)
        self.input_field.insert(0, command + " ")
        self.input_field.focus_set()
        self.input_field.icursor(tk.END)

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
        """Thread-safe version -- schedules on the main thread."""
        self.root.after(0, self._append_chat, text, tag)

    # ------------------------------------------------------------------
    # Input placeholder
    # ------------------------------------------------------------------
    def _on_focus_in(self, event):
        if self.input_field.get() == "Type a command...":
            self.input_field.delete(0, tk.END)
            self.input_field.config(fg=self._theme["fg_text"])

    def _on_focus_out(self, event):
        if not self.input_field.get():
            self.input_field.insert(0, "Type a command...")
            self.input_field.config(fg=self._theme["fg_dim"])

    # ------------------------------------------------------------------
    # Window dragging
    # ------------------------------------------------------------------
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        if self._maximized:
            return  # Don't drag when maximized
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Window controls: Minimize, Maximize, Close
    # ------------------------------------------------------------------
    def _minimize_window(self):
        """Minimize (iconify) the window."""
        # Need to briefly show the window with overrideredirect(False)
        # so Windows can iconify it, then restore overrideredirect
        self.root.overrideredirect(False)
        self.root.iconify()
        # Re-enable overrideredirect when restored
        self.root.bind("<Map>", self._on_deiconify)

    def _on_deiconify(self, event):
        """Restore overrideredirect after un-minimizing."""
        self.root.unbind("<Map>")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

    def _toggle_maximize(self):
        """Toggle between compact mode and fullscreen."""
        if self._maximized:
            # Restore to saved size/position
            if self._saved_geometry:
                self.root.geometry(self._saved_geometry)
            self.root.attributes("-topmost", True)
            self._max_btn.config(text=" \u25a1 ")  # Square for maximize
            self._maximized = False
        else:
            # Save current geometry, go fullscreen
            self._saved_geometry = self.root.geometry()
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_w}x{screen_h}+0+0")
            self.root.attributes("-topmost", False)
            self._max_btn.config(text=" \u2750 ")  # Overlapping squares for restore
            self._maximized = True

    # ------------------------------------------------------------------
    # Global hotkey (Ctrl+Alt+N)
    # ------------------------------------------------------------------
    def _setup_hotkey(self):
        """Register Ctrl+Alt+N as a global hotkey using pynput."""
        if not _HAS_PYNPUT:
            self.root.after(100, self._set_status,
                            "pynput not installed -- hotkey disabled", self._theme["thinking_ylw"])
            return

        hotkeys = GlobalHotKeys({
            "<ctrl>+<alt>+n": self._on_hotkey_pressed,
        })
        hotkeys.daemon = True
        hotkeys.start()
        self._hotkey_listener = hotkeys

    def _on_hotkey_pressed(self):
        """Called from the hotkey thread."""
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
            if self.input_field.get() == "Type a command...":
                self.input_field.delete(0, tk.END)
                self.input_field.config(fg=self._theme["fg_text"])
            self._visible = True

    # ------------------------------------------------------------------
    # Three-dot menu
    # ------------------------------------------------------------------
    def _show_menu(self):
        """Show the three-dot dropdown menu."""
        # Close existing menu if open
        if self._menu_window and self._menu_window.winfo_exists():
            self._menu_window.destroy()
            self._menu_window = None
            return

        t = self._theme

        menu = tk.Toplevel(self.root)
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        menu.configure(bg=t["menu_bg"])
        self._menu_window = menu

        # Position below the three-dot button
        btn_x = self._menu_btn.winfo_rootx()
        btn_y = self._menu_btn.winfo_rooty() + self._menu_btn.winfo_height()
        menu_width = 200

        # Adjust position so menu doesn't go off-screen
        screen_w = self.root.winfo_screenwidth()
        if btn_x + menu_width > screen_w:
            btn_x = screen_w - menu_width - 5
        menu.geometry(f"{menu_width}+{btn_x}+{btn_y}")

        # Menu items
        menu_items = [
            ("Settings", self._open_settings),
            ("Reset Model", self._reset_model),
            ("Train on Dataset", self._train_dataset),
            ("Manage Folders", self._manage_folders),
            None,  # Separator
            ("Clear Chat", self._clear_chat),
            None,  # Separator
        ]

        # Add theme sub-items
        for item in menu_items:
            if item is None:
                # Separator
                sep = tk.Frame(menu, bg=t["border"], height=1)
                sep.pack(fill=tk.X, padx=8, pady=2)
            else:
                text, cmd = item
                lbl = tk.Label(
                    menu, text=f"  {text}", font=FONT_MENU,
                    bg=t["menu_bg"], fg=t["fg_text"], anchor="w",
                    cursor="hand2", padx=8, pady=5
                )
                lbl.pack(fill=tk.X)
                lbl.bind("<Button-1>", lambda e, c=cmd: self._menu_action(c))
                lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg=t["menu_hover"]))
                lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=t["menu_bg"]))

        # Theme section header
        theme_header = tk.Label(
            menu, text="  Theme", font=(FONT_MENU[0], FONT_MENU[1], "bold"),
            bg=t["menu_bg"], fg=t["fg_dim"], anchor="w", padx=8, pady=3
        )
        theme_header.pack(fill=tk.X)

        for theme_name in themes.get_theme_names():
            indicator = " *" if theme_name == self._theme_name else ""
            lbl = tk.Label(
                menu, text=f"    {theme_name}{indicator}", font=FONT_MENU,
                bg=t["menu_bg"], fg=t["fg_text"], anchor="w",
                cursor="hand2", padx=8, pady=4
            )
            lbl.pack(fill=tk.X)
            lbl.bind("<Button-1>", lambda e, tn=theme_name: self._menu_action(
                lambda: self._switch_theme(tn)))
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg=t["menu_hover"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=t["menu_bg"]))

        # Separator before About
        sep = tk.Frame(menu, bg=t["border"], height=1)
        sep.pack(fill=tk.X, padx=8, pady=2)

        # About
        about_lbl = tk.Label(
            menu, text="  About NEXUS", font=FONT_MENU,
            bg=t["menu_bg"], fg=t["fg_text"], anchor="w",
            cursor="hand2", padx=8, pady=5
        )
        about_lbl.pack(fill=tk.X)
        about_lbl.bind("<Button-1>", lambda e: self._menu_action(self._show_about))
        about_lbl.bind("<Enter>", lambda e: about_lbl.config(bg=t["menu_hover"]))
        about_lbl.bind("<Leave>", lambda e: about_lbl.config(bg=t["menu_bg"]))

        # Update menu height
        menu.update_idletasks()
        menu_h = menu.winfo_reqheight()
        menu.geometry(f"{menu_width}x{menu_h}+{btn_x}+{btn_y}")

        # Close menu when clicking elsewhere
        menu.bind("<FocusOut>", lambda e: self._close_menu_delayed())
        menu.focus_set()

    def _close_menu_delayed(self):
        """Close menu with a small delay to allow click events to fire."""
        if self._menu_window:
            self.root.after(150, self._close_menu)

    def _close_menu(self):
        """Close the dropdown menu."""
        if self._menu_window and self._menu_window.winfo_exists():
            self._menu_window.destroy()
            self._menu_window = None

    def _menu_action(self, callback):
        """Execute a menu action and close the menu."""
        self._close_menu()
        if callable(callback):
            callback()

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------
    def _open_settings(self):
        """Open settings -- placeholder for Phase 31."""
        self._append_chat("NEXUS: ", "nexus")
        self._append_chat("Settings panel will be available in a future update.\n\n", "info")

    def _reset_model(self):
        """Reset model training (LoRA weights)."""
        def _do_reset():
            try:
                import model_manager
                result = model_manager.reset_training()
                self.root.after(0, self._append_chat, "NEXUS: ", "nexus")
                self.root.after(0, self._append_chat, f"{result}\n\n", "response")
            except Exception as e:
                self.root.after(0, self._append_chat, f"Error: {e}\n\n", "error")
        threading.Thread(target=_do_reset, daemon=True).start()

    def _train_dataset(self):
        """Open folder picker to select training dataset."""
        folder = filedialog.askdirectory(title="Select Training Dataset Folder")
        if not folder:
            return
        self._append_chat("NEXUS: ", "nexus")
        self._append_chat(f"Training on: {folder}\n", "info")
        self._append_chat("This may take a while...\n\n", "thinking")

        def _do_train():
            try:
                import trainer
                result = trainer.train_on_folder(folder)
                self.root.after(0, self._append_chat, "NEXUS: ", "nexus")
                self.root.after(0, self._append_chat, f"{result}\n\n", "response")
            except Exception as e:
                self.root.after(0, self._append_chat, f"Training error: {e}\n\n", "error")
        threading.Thread(target=_do_train, daemon=True).start()

    def _manage_folders(self):
        """Open manage folders -- placeholder for Phase 31."""
        self._append_chat("NEXUS: ", "nexus")
        self._append_chat("Folder management will be available in a future update.\n\n", "info")

    def _clear_chat(self):
        """Clear the chat area."""
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.config(state=tk.DISABLED)
        self._append_chat("Chat cleared.\n\n", "info")

    def _show_about(self):
        """Show About NEXUS info in chat."""
        t = self._theme
        about_text = (
            "--- About NEXUS ---\n"
            "Version: V3.0\n"
            f"Theme: {self._theme_name}\n"
            f"Model loaded: {'Yes' if self._model_loaded else 'No'}\n"
            "Hotkey: Ctrl+Alt+N\n"
            "---\n"
            "NEXUS is a local AI assistant that runs\n"
            "entirely on your machine.\n"
        )
        self._append_chat(about_text + "\n", "info")

    # ------------------------------------------------------------------
    # Theme switching
    # ------------------------------------------------------------------
    def _switch_theme(self, theme_name):
        """Switch to a different theme and apply it to all widgets."""
        self._theme_name = theme_name
        self._theme = themes.get_theme(theme_name)
        themes.save_theme(theme_name)
        self._apply_theme()

    def _apply_theme(self):
        """Apply the current theme to all widgets."""
        t = self._theme

        # Root
        self.root.configure(bg=t["bg_dark"])

        # Title bar
        self._title_bar.configure(bg=t["bg_medium"])
        self._title_label.configure(bg=t["bg_medium"], fg=t["fg_text"])

        # Window control buttons
        for btn in [self._min_btn, self._max_btn, self._menu_btn]:
            btn.configure(bg=t["bg_medium"], fg=t["fg_dim"])
        self._close_btn.configure(bg=t["bg_medium"], fg=t["error_red"])

        # Rebind hover events with new theme colors
        self._min_btn.bind("<Enter>", lambda e: self._min_btn.config(bg=t["accent"]))
        self._min_btn.bind("<Leave>", lambda e: self._min_btn.config(bg=t["bg_medium"]))
        self._max_btn.bind("<Enter>", lambda e: self._max_btn.config(bg=t["accent"]))
        self._max_btn.bind("<Leave>", lambda e: self._max_btn.config(bg=t["bg_medium"]))
        self._menu_btn.bind("<Enter>", lambda e: self._menu_btn.config(bg=t["accent"]))
        self._menu_btn.bind("<Leave>", lambda e: self._menu_btn.config(bg=t["bg_medium"]))
        self._close_btn.bind("<Enter>", lambda e: self._close_btn.config(bg="#C0392B"))
        self._close_btn.bind("<Leave>", lambda e: self._close_btn.config(bg=t["bg_medium"]))

        # Status label
        self._status_label.configure(bg=t["bg_dark"])

        # Chat area
        self._chat_frame.configure(bg=t["bg_dark"])
        self.chat_area.configure(
            bg=t["bg_chat"], fg=t["fg_text"],
            insertbackground=t["fg_text"],
            selectbackground=t["accent"],
        )
        self._configure_tags()

        # Pill buttons
        self._pill_frame.configure(bg=t["bg_dark"])
        for pill in self._pill_buttons:
            pill.configure(bg=t["pill_bg"], fg=t["fg_dim"])
            pill.bind("<Enter>", lambda e, p=pill: p.config(
                bg=self._theme["pill_hover"], fg=self._theme["fg_text"]))
            pill.bind("<Leave>", lambda e, p=pill: p.config(
                bg=self._theme["pill_bg"], fg=self._theme["fg_dim"]))

        # Input area
        self._input_frame.configure(bg=t["bg_dark"])
        self._input_wrapper.configure(bg=t["bg_medium"])
        self.input_field.configure(
            bg=t["bg_medium"], fg=t["fg_text"],
            insertbackground=t["fg_text"]
        )
        if self.input_field.get() == "Type a command...":
            self.input_field.config(fg=t["fg_dim"])

        # Send button
        self._send_btn.configure(
            bg=t["accent"], fg=t["fg_text"],
            activebackground=t["accent_hover"]
        )
        self._send_btn.bind("<Enter>", lambda e: self._send_btn.config(bg=t["accent_hover"]))
        self._send_btn.bind("<Leave>", lambda e: self._send_btn.config(bg=t["accent"]))

        # Bottom border
        self._bottom_border.configure(bg=t["accent"])

        # Status -- refresh appearance
        self._append_chat(f"Theme changed to: {self._theme_name}\n\n", "info")

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------
    def _load_model_async(self):
        """Load the NEXUS model in a background thread."""
        def _load():
            try:
                from model_loader import load_model
                load_model()
                self._model_loaded = True
                self.root.after(0, self._set_status,
                                "Ready -- model loaded", self._theme["success_grn"])
            except Exception as e:
                self.root.after(0, self._set_status,
                                f"Model load failed: {e}", self._theme["error_red"])

        t = threading.Thread(target=_load, daemon=True)
        t.start()

    def _set_status(self, text, color=None):
        """Update the status bar text and color."""
        if color is None:
            color = self._theme["fg_dim"]
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
            return

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
        self._set_status("Processing...", self._theme["thinking_ylw"])
        self._processing = True

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
        """Display the response from NEXUS."""
        # Remove the "Thinking..." line
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

        self._append_chat(f"{result}\n\n", "response")
        self._set_status("Ready", self._theme["success_grn"])
        self._processing = False

    def _show_error(self, error_msg):
        """Display an error message."""
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
        self._set_status("Error occurred", self._theme["error_red"])
        self._processing = False

    # ------------------------------------------------------------------
    # Close / cleanup
    # ------------------------------------------------------------------
    def _on_close(self):
        """Clean shutdown -- stop hotkey listener and destroy window."""
        # Stop hotkey listener if it exists
        if _HAS_PYNPUT and hasattr(self, '_hotkey_listener'):
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
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
