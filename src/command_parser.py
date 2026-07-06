# -*- coding: utf-8 -*-
"""
command_parser.py -- NEXUS Slash Command System
Detects and routes slash commands (/task, /web, /save, /remember, /open, /help)
directly to handler functions, bypassing LLM intent detection entirely.
This makes NEXUS faster and more predictable for known commands.

Phase 27 of the NEXUS implementation plan.
"""

import os
import re
import subprocess


# ---------------------------------------------------------------------------
# Supported slash commands
# ---------------------------------------------------------------------------
SUPPORTED_COMMANDS = {
    "/task": "Execute a system task (battery, processes, shutdown, file ops, etc.)",
    "/web": "Search the web using Gemini API (Phase 29)",
    "/save": "Save data to a file",
    "/remember": "Store a fact in persistent memory (Phase 28)",
    "/open": "Open a website or URL in the browser",
    "/help": "Show all available slash commands and examples",
    "/recall": "List stored memories (Phase 28)",
    "/forget": "Remove a stored memory (Phase 28)",
}


# ---------------------------------------------------------------------------
# Smart URL mapping -- keywords to popular websites
# ---------------------------------------------------------------------------
_URL_MAP = {
    # Shopping
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "myntra": "https://www.myntra.com",
    "meesho": "https://www.meesho.com",
    # Entertainment
    "youtube": "https://www.youtube.com",
    "netflix": "https://www.netflix.com",
    "hotstar": "https://www.hotstar.com",
    "disney": "https://www.hotstar.com",
    "spotify": "https://www.spotify.com",
    "prime video": "https://www.primevideo.com",
    "prime": "https://www.primevideo.com",
    # Social
    "instagram": "https://www.instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "facebook": "https://www.facebook.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    # Productivity / Mail
    "gmail": "https://mail.google.com",
    "google mail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "notion": "https://www.notion.so",
    # Dev
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "chatgpt": "https://chat.openai.com",
    "gemini": "https://gemini.google.com",
    # Reference / Knowledge
    "google": "https://www.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "wiki": "https://www.wikipedia.org",
    # Movies / Ratings
    "imdb": "https://www.imdb.com",
    "rotten tomatoes": "https://www.rottentomatoes.com",
    # Booking
    "bookmyshow": "https://www.bookmyshow.com",
    "book my show": "https://www.bookmyshow.com",
    "makemytrip": "https://www.makemytrip.com",
    "make my trip": "https://www.makemytrip.com",
    "irctc": "https://www.irctc.co.in",
    "zomato": "https://www.zomato.com",
    "swiggy": "https://www.swiggy.com",
    # News
    "news": "https://news.google.com",
    "google news": "https://news.google.com",
    # Maps
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
}

# Fuzzy keyword mapping -- descriptive phrases to site names
_FUZZY_MAP = {
    "shopping": "amazon",
    "online shopping": "amazon",
    "buy": "amazon",
    "movie ticket": "bookmyshow",
    "movie tickets": "bookmyshow",
    "ticket booking": "bookmyshow",
    "movie ticket booking": "bookmyshow",
    "book tickets": "bookmyshow",
    "rate movies": "imdb",
    "movie ratings": "imdb",
    "movie reviews": "imdb",
    "food delivery": "zomato",
    "order food": "zomato",
    "train tickets": "irctc",
    "train booking": "irctc",
    "book train": "irctc",
    "flight booking": "makemytrip",
    "book flight": "makemytrip",
    "hotel booking": "makemytrip",
    "book hotel": "makemytrip",
    "travel booking": "makemytrip",
    "music": "spotify",
    "listen to music": "spotify",
    "play music": "spotify",
    "watch videos": "youtube",
    "video": "youtube",
    "videos": "youtube",
    "coding help": "stackoverflow",
    "programming help": "stackoverflow",
    "search": "google",
    "web search": "google",
    "directions": "maps",
    "navigate": "maps",
    "navigation": "maps",
}


# ---------------------------------------------------------------------------
# Task keyword mapping -- /task subcommands to handler functions
# ---------------------------------------------------------------------------
_TASK_KEYWORDS = {
    # System info
    "battery": "battery",
    "charge": "battery",
    "charging": "battery",
    "power": "battery",
    "processes": "processes",
    "process": "processes",
    "tasks": "processes",
    "running": "processes",
    "running programs": "processes",
    "running apps": "processes",
    "task manager": "processes",
    # System commands
    "shutdown": "shutdown",
    "shut down": "shutdown",
    "turn off": "shutdown",
    "power off": "shutdown",
    "restart": "restart",
    "reboot": "restart",
    "sleep": "sleep",
    "hibernate": "sleep",
    "standby": "sleep",
    "cancel shutdown": "cancel_shutdown",
    "cancel restart": "cancel_shutdown",
    # File management
    "rename": "rename",
    "copy": "copy",
    "move": "move",
    "delete": "delete",
    "remove": "delete",
    "list": "list_files",
    "list files": "list_files",
    "show files": "list_files",
    "dir": "list_files",
    # System utilities
    "disk cleanup": "disk_cleanup",
    "clean disk": "disk_cleanup",
    "cleanup": "disk_cleanup",
    "wallpaper": "set_wallpaper",
    "set wallpaper": "set_wallpaper",
    "desktop wallpaper": "set_wallpaper",
    "background": "set_wallpaper",
    # Model management
    "reset training": "reset_training",
    "reset model": "reset_training",
    "clear training": "reset_training",
    "model info": "model_info",
    "model status": "model_info",
}


# ---------------------------------------------------------------------------
# Core parser -- detect and extract slash commands
# ---------------------------------------------------------------------------
def parse_command(user_input):
    """
    Detect and extract a slash command from user input.

    Args:
        user_input: Raw string from the user.

    Returns:
        Tuple of (command, args) if a slash command is found.
        command is lowercase (e.g. "/task").
        args is the remaining text after the command.
        Returns None if no slash command is detected.
    """
    stripped = user_input.strip()

    if not stripped.startswith("/"):
        return None

    # Split into command and args
    parts = stripped.split(None, 1)  # Split on first whitespace
    command = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    # Validate that the command is supported
    if command not in SUPPORTED_COMMANDS:
        return None

    return (command, args)


# ---------------------------------------------------------------------------
# Multi-command parser -- split input by slash prefixes
# ---------------------------------------------------------------------------
def parse_multi_commands(user_input):
    """
    Split input containing multiple slash commands into separate commands.
    Handles: "/web get stock prices and /save to stocks.txt"

    Args:
        user_input: Raw string possibly containing multiple slash commands.

    Returns:
        List of (command, args) tuples. Returns a single-element list if
        only one command is present. Returns None if no commands found.
    """
    stripped = user_input.strip()

    if not stripped.startswith("/"):
        return None

    # Find all slash command positions
    # Pattern: / followed by a known command name
    command_names = "|".join(
        re.escape(cmd.lstrip("/")) for cmd in SUPPORTED_COMMANDS
    )
    pattern = rf"(/(?:{command_names}))\b"
    matches = list(re.finditer(pattern, stripped, re.IGNORECASE))

    if not matches:
        return None

    commands = []
    for i, match in enumerate(matches):
        start = match.start()
        # End is either the start of the next command or end of string
        end = matches[i + 1].start() if i + 1 < len(matches) else len(stripped)

        chunk = stripped[start:end].strip()
        # Remove trailing "and" connector if present
        chunk = re.sub(r"\s+and\s*$", "", chunk, flags=re.IGNORECASE).strip()

        result = parse_command(chunk)
        if result:
            commands.append(result)

    return commands if commands else None


# ---------------------------------------------------------------------------
# /task handler
# ---------------------------------------------------------------------------
def handle_task(args):
    """
    Handle /task commands -- route directly to system_tasks or file_ops.

    Args:
        args: The text after "/task ", e.g. "battery" or "list files in C:\\docs"

    Returns:
        Result string from the appropriate handler.
    """
    if not args:
        return ("No task specified. Try:\n"
                "  /task battery\n"
                "  /task processes\n"
                "  /task shutdown\n"
                "  /task rename <file>\n"
                "  /task list files <folder>\n"
                "  /task disk cleanup\n"
                "Type /help for all available commands.")

    lower = args.lower().strip()

    # Try to match task keywords (check longer phrases first)
    matched_task = None
    for keyword in sorted(_TASK_KEYWORDS.keys(), key=len, reverse=True):
        if lower.startswith(keyword) or lower == keyword:
            matched_task = _TASK_KEYWORDS[keyword]
            # Extract remaining args after the keyword
            remaining = args[len(keyword):].strip()
            break

    if matched_task is None:
        # Try word-by-word matching for single keywords
        first_word = lower.split()[0] if lower.split() else ""
        if first_word in _TASK_KEYWORDS:
            matched_task = _TASK_KEYWORDS[first_word]
            remaining = args[len(first_word):].strip()

    if matched_task is None:
        return (f"Unknown task: \"{args}\"\n"
                "Available tasks: battery, processes, shutdown, restart, sleep,\n"
                "  rename, copy, move, delete, list files, disk cleanup, set wallpaper,\n"
                "  reset training, model info\n"
                "Type /help for full list.")

    # Route to the correct handler
    if matched_task == "battery":
        import system_tasks
        return system_tasks.get_battery()

    elif matched_task == "processes":
        import system_tasks
        return system_tasks.get_processes()

    elif matched_task == "shutdown":
        import system_tasks
        return system_tasks.shutdown_system()

    elif matched_task == "restart":
        import system_tasks
        return system_tasks.restart_system()

    elif matched_task == "sleep":
        import system_tasks
        return system_tasks.sleep_system()

    elif matched_task == "cancel_shutdown":
        import system_tasks
        return system_tasks.cancel_shutdown()

    elif matched_task == "rename":
        import file_ops
        from utils import extract_filepath
        filepath = extract_filepath(remaining)
        if not filepath:
            return "Please specify a file to rename. Example: /task rename notes.txt to notes_old.txt"
        new_name = _extract_rename_target(remaining)
        if not new_name:
            return f"Please specify the new name. Example: /task rename {filepath} to new_name.txt"
        return file_ops.rename_file(filepath, new_name)

    elif matched_task == "copy":
        import file_ops
        from utils import extract_filepath
        filepath = extract_filepath(remaining)
        if not filepath:
            return "Please specify a file to copy. Example: /task copy notes.txt to D:\\backup"
        dest = _extract_destination(remaining)
        if not dest:
            return f"Please specify the destination. Example: /task copy {filepath} to D:\\backup"
        return file_ops.copy_file(filepath, dest)

    elif matched_task == "move":
        import file_ops
        from utils import extract_filepath
        filepath = extract_filepath(remaining)
        if not filepath:
            return "Please specify a file to move. Example: /task move notes.txt to D:\\docs"
        dest = _extract_destination(remaining)
        if not dest:
            return f"Please specify the destination. Example: /task move {filepath} to D:\\docs"
        return file_ops.move_file(filepath, dest)

    elif matched_task == "delete":
        import file_ops
        from utils import extract_filepath
        filepath = extract_filepath(remaining)
        if not filepath:
            return "Please specify a file to delete. Example: /task delete old_notes.txt"
        return file_ops.delete_file(filepath)

    elif matched_task == "list_files":
        import file_ops
        from utils import extract_filepath
        # Remove "files" or "in" from args before extracting path
        clean_remaining = re.sub(r"^(files?\s+)?(in\s+)?", "", remaining, flags=re.IGNORECASE).strip()
        filepath = extract_filepath(clean_remaining) if clean_remaining else None
        if not filepath and clean_remaining:
            filepath = clean_remaining  # Use the raw text as a path
        if not filepath:
            return "Please specify a folder to list. Example: /task list files in C:\\docs"
        return file_ops.list_files(filepath)

    elif matched_task == "disk_cleanup":
        return _run_disk_cleanup(remaining)

    elif matched_task == "set_wallpaper":
        from utils import extract_filepath
        filepath = extract_filepath(remaining)
        if not filepath:
            return "Please specify an image file. Example: /task set wallpaper C:\\pics\\bg.jpg"
        return _set_wallpaper(filepath)

    elif matched_task == "reset_training":
        import model_manager
        return model_manager.reset_training()

    elif matched_task == "model_info":
        import model_manager
        return model_manager.get_model_info()

    return f"Task '{matched_task}' is not yet implemented."


# ---------------------------------------------------------------------------
# /web handler -- Web search via Gemini API (Phase 29)
# ---------------------------------------------------------------------------
def handle_web(query):
    """
    Handle /web commands -- search the web using Gemini API.

    Args:
        query: The search query text.

    Returns:
        Result string with answer and sources.
    """
    if not query:
        return ("No search query provided. Try:\n"
                "  /web highest grossing movie in the world\n"
                "  /web current weather in Mumbai\n"
                "  /web price of top 10 Nifty 50 stocks")

    # Try Gemini API first (Phase 29)
    import web_search
    result = web_search.search_web_gemini(query)

    # If Gemini returned an error about missing package or key,
    # try Selenium fallback
    if result and ("not installed" in result or "not configured" in result):
        try:
            import browser_tasks
            return browser_tasks.search_web(query)
        except Exception:
            pass  # Fall through to return the Gemini error message

    return result


# ---------------------------------------------------------------------------
# /save handler
# ---------------------------------------------------------------------------
def handle_save(args):
    """
    Handle /save commands -- save data to a file.

    Args:
        args: Text containing the data and filename.
              e.g. "this to notes.txt" or "to stocks.txt"

    Returns:
        Result string.
    """
    if not args:
        return ("No save target specified. Try:\n"
                "  /save to notes.txt\n"
                "  /save data to C:\\docs\\output.txt")

    import web_fetch
    from permission_guard import is_allowed

    # Try to extract filename from args
    filepath = None
    data = args

    # Pattern: "to <filename>"
    to_match = re.search(r"\bto\s+([^\s]+\.(?:txt|csv|json|xlsx?))\b", args, re.IGNORECASE)
    if to_match:
        filepath = to_match.group(1)
        data = args[:to_match.start()].strip()

    if not filepath:
        # Try to find any filename pattern
        file_match = re.search(r"([^\s]+\.(?:txt|csv|json|xlsx?))\b", args, re.IGNORECASE)
        if file_match:
            filepath = file_match.group(1)
            data = args.replace(filepath, "").strip()

    if not filepath:
        return ("Could not determine the filename. Try:\n"
                "  /save to notes.txt\n"
                "  /save my data to output.txt")

    # If we have no data content, check if there's a previous response to save
    if not data:
        data = "[No data provided -- use /save <data> to <filename>]"

    filepath = os.path.abspath(filepath)

    if not is_allowed(filepath):
        return (f"Permission denied: Cannot save to {filepath}\n"
                "This location is not in your allowed folders.")

    return web_fetch.save_to_txt(data, filepath, format_type="text")


# ---------------------------------------------------------------------------
# /open handler
# ---------------------------------------------------------------------------
def handle_open(args):
    """
    Handle /open commands -- open a URL or mapped website.

    Args:
        args: Website name, keyword, or direct URL.
              e.g. "amazon", "movie tickets", "google.com"

    Returns:
        Result string.
    """
    if not args:
        return ("No website specified. Try:\n"
                "  /open amazon\n"
                "  /open youtube\n"
                "  /open google.com\n"
                "  /open movie ticket booking")

    lower = args.lower().strip()

    # 1. Check direct URL (contains http:// or https:// or has domain pattern)
    if re.match(r"https?://", lower) or re.search(r"\w+\.\w{2,}", lower):
        try:
            import browser_tasks
            return browser_tasks.open_browser(args.strip())
        except Exception as e:
            return f"Could not open URL: {e}"

    # 2. Check exact match in URL map
    if lower in _URL_MAP:
        try:
            import browser_tasks
            url = _URL_MAP[lower]
            return browser_tasks.open_browser(url)
        except Exception as e:
            return f"Could not open {lower}: {e}"

    # 3. Check fuzzy keyword map
    if lower in _FUZZY_MAP:
        site_key = _FUZZY_MAP[lower]
        if site_key in _URL_MAP:
            try:
                import browser_tasks
                url = _URL_MAP[site_key]
                return browser_tasks.open_browser(url)
            except Exception as e:
                return f"Could not open {site_key}: {e}"

    # 4. Partial match in URL map (e.g. "book my" -> "bookmyshow")
    for key, url in _URL_MAP.items():
        if lower in key or key in lower:
            try:
                import browser_tasks
                return browser_tasks.open_browser(url)
            except Exception as e:
                return f"Could not open {key}: {e}"

    # 5. Partial match in fuzzy map
    for phrase, site_key in _FUZZY_MAP.items():
        if lower in phrase or phrase in lower:
            if site_key in _URL_MAP:
                try:
                    import browser_tasks
                    return browser_tasks.open_browser(_URL_MAP[site_key])
                except Exception as e:
                    return f"Could not open {site_key}: {e}"

    # 6. Fallback -- try adding .com
    guess_url = f"https://www.{lower.replace(' ', '')}.com"
    try:
        import browser_tasks
        return browser_tasks.open_browser(guess_url)
    except Exception as e:
        return f"Could not open \"{args}\". Try providing a full URL like: /open https://example.com"


# ---------------------------------------------------------------------------
# /remember handler
# ---------------------------------------------------------------------------
def handle_remember(args):
    """
    Handle /remember commands -- store a fact in persistent memory.

    Args:
        args: The fact to remember.

    Returns:
        Result string.
    """
    if not args:
        return ("No fact provided. Try:\n"
                "  /remember my favourite movie is Avengers Endgame\n"
                "  /remember I work at Google\n"
                "  /remember my birthday is 15 March")

    import persistent_memory
    return persistent_memory.remember_fact(args)


# ---------------------------------------------------------------------------
# /recall handler
# ---------------------------------------------------------------------------
def handle_recall(args):
    """
    Handle /recall commands -- list stored memories.
    Optionally filter by keyword.
    """
    import persistent_memory
    return persistent_memory.recall_facts(args if args else None)


# ---------------------------------------------------------------------------
# /forget handler
# ---------------------------------------------------------------------------
def handle_forget(args):
    """
    Handle /forget commands -- remove a stored memory by index or keyword.
    """
    if not args:
        return ("Please specify which memory to forget.\n"
                "  /forget 1              (by number from /recall)\n"
                "  /forget favourite movie (by keyword)")

    import persistent_memory
    return persistent_memory.forget_fact(args)


# ---------------------------------------------------------------------------
# /help handler
# ---------------------------------------------------------------------------
def handle_help():
    """
    Show all available slash commands with descriptions and examples.

    Returns:
        Formatted help text string.
    """
    help_text = """
+------------------------------------------------------+
|              NEXUS Slash Commands                     |
+------------------------------------------------------+

  /task <action>     - Execute a system task directly
    Examples:
      /task battery              -> Show battery percentage
      /task processes             -> List top 10 running processes
      /task shutdown              -> Shut down computer (with confirmation)
      /task restart               -> Restart computer
      /task sleep                 -> Put computer to sleep
      /task rename file.txt to new.txt  -> Rename a file
      /task copy file.txt to D:\\backup  -> Copy a file
      /task move file.txt to D:\\docs    -> Move a file
      /task delete old_file.txt   -> Delete a file
      /task list files in C:\\docs -> List files in a folder
      /task disk cleanup          -> Run Windows disk cleanup
      /task set wallpaper bg.jpg  -> Set desktop wallpaper
      /task model info            -> Show model status

  /web <query>       - Search the web (via Gemini API)
    Examples:
      /web highest grossing movie in the world
      /web current weather in Mumbai
      /web price of Nifty 50 stocks

  /save <data> to <filename>  - Save data to a file
    Examples:
      /save to notes.txt
      /save my notes to output.txt

  /open <website>    - Open a website in the browser
    Examples:
      /open amazon               -> Opens Amazon.in
      /open youtube              -> Opens YouTube
      /open movie ticket booking -> Opens BookMyShow
      /open google.com           -> Opens Google
      /open https://github.com   -> Opens any URL

  /remember <fact>   - Store a fact for long-term memory
    Examples:
      /remember my favourite movie is Avengers Endgame
      /remember I work at Google

  /recall            - Show all stored memories
  /forget <fact>     - Remove a stored memory

  /help              - Show this help message

------------------------------------------------------
Tip: You can also use multiple commands in one line:
  /web get stock prices and /save to stocks.txt
------------------------------------------------------
Without a slash prefix, NEXUS uses AI to understand
your intent automatically.
"""
    return help_text.strip()


# ---------------------------------------------------------------------------
# Main dispatcher -- route slash commands to handlers
# ---------------------------------------------------------------------------
def execute_command(command, args):
    """
    Execute a slash command by routing to the appropriate handler.

    Args:
        command: The slash command (e.g. "/task").
        args:    The arguments after the command.

    Returns:
        Result string from the handler.
    """
    if command == "/task":
        return handle_task(args)
    elif command == "/web":
        return handle_web(args)
    elif command == "/save":
        return handle_save(args)
    elif command == "/open":
        return handle_open(args)
    elif command == "/remember":
        return handle_remember(args)
    elif command == "/recall":
        return handle_recall(args)
    elif command == "/forget":
        return handle_forget(args)
    elif command == "/help":
        return handle_help()
    else:
        return f"Unknown command: {command}\nType /help for available commands."


def execute_input(user_input):
    """
    Process user input -- check for slash commands (single or multi),
    execute them, and return the combined result.

    This is the main entry point called by router.py before
    falling through to normal routing.

    Args:
        user_input: Raw string from the user.

    Returns:
        Result string if slash commands were found and executed,
        or None if no slash commands detected (caller should proceed
        with normal routing).
    """
    stripped = user_input.strip()

    if not stripped.startswith("/"):
        return None

    # Check for multi-command input first
    multi = parse_multi_commands(stripped)
    if multi and len(multi) > 1:
        results = []
        prev_result = None
        for cmd, cmd_args in multi:
            # If /save comes after /web or /task, pass the previous result
            if cmd == "/save" and prev_result and not cmd_args:
                cmd_args = f"to output.txt"  # Default filename
            result = execute_command(cmd, cmd_args)
            results.append(result)
            prev_result = result
        return "\n\n".join(results)

    # Single command
    parsed = parse_command(stripped)
    if parsed:
        cmd, args = parsed
        return execute_command(cmd, args)

    # Starts with / but not a known command
    return f"Unknown command: \"{stripped.split()[0]}\"\nType /help for available commands."


# ---------------------------------------------------------------------------
# Helper functions for /task subcommands
# ---------------------------------------------------------------------------
def _extract_rename_target(text):
    """Extract new name from text like 'file.txt to new_name.txt'."""
    lower = text.lower()
    for keyword in (" to ", " as ", " into "):
        idx = lower.find(keyword)
        if idx != -1:
            candidate = text[idx + len(keyword):].strip().strip('"').strip("'")
            if candidate:
                return candidate
    return None


def _extract_destination(text):
    """Extract destination path from text like 'file.txt to D:\\backup'."""
    lower = text.lower()
    for keyword in (" to ", " into "):
        idx = lower.find(keyword)
        if idx != -1:
            candidate = text[idx + len(keyword):].strip().strip('"').strip("'")
            if candidate:
                return candidate
    return None


def _run_disk_cleanup(args):
    """Run Windows Disk Cleanup utility via subprocess."""
    try:
        # Parse drive letter from args (default to C:)
        drive = "C"
        if args:
            drive_match = re.search(r"([A-Za-z])[\s:]*drive", args, re.IGNORECASE)
            if drive_match:
                drive = drive_match.group(1).upper()
            elif len(args.strip()) == 1 and args.strip().isalpha():
                drive = args.strip().upper()

        print(f"\n  Starting Disk Cleanup for drive {drive}:...")
        print("  This will open the Windows Disk Cleanup utility.")
        confirm = input("  Proceed? (y/n): ").strip().lower()

        if confirm != "y":
            return "Disk cleanup cancelled."

        subprocess.Popen(["cleanmgr", f"/d", drive])
        return f"Disk Cleanup started for drive {drive}:. Follow the on-screen prompts."
    except Exception as e:
        return f"Could not start Disk Cleanup: {e}"


def _set_wallpaper(filepath):
    """Set desktop wallpaper using ctypes (Windows)."""
    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        return f"Image file not found: {filepath}"

    # Check file extension
    valid_exts = (".jpg", ".jpeg", ".png", ".bmp")
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in valid_exts:
        return f"Unsupported image format: {ext}\nSupported: {', '.join(valid_exts)}"

    try:
        import ctypes
        SPI_SETDESKWALLPAPER = 0x0014
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, filepath, 3
        )
        if result:
            return f"Desktop wallpaper set to: {os.path.basename(filepath)}"
        else:
            return "Failed to set wallpaper. The system call returned an error."
    except Exception as e:
        return f"Could not set wallpaper: {e}"
