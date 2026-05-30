"""
agent.py — NEXUS Main Agent Loop
Entry point for the NEXUS offline AI agent. Handles first-run setup,
model loading, the interactive command loop, and graceful exit.
Run with: python src/agent.py  (from the nexus-agent root folder)
"""

import os
import sys
import time

# Add src/ to the path so local imports work correctly
sys.path.insert(0, os.path.dirname(__file__))

from model_loader import load_model
from router import route, set_conversation_memory
from permission_guard import add_permission, load_permissions
from memory import ConversationMemory
import ui


# ---------------------------------------------------------------------------
# First-run setup — configure allowed folders
# ---------------------------------------------------------------------------
def first_run_setup():
    """
    If no folders have been whitelisted yet, walk the user through
    adding at least one folder that NEXUS is allowed to access.
    """
    perms = load_permissions()
    if perms:
        return  # already configured

    ui.console.print()
    ui.console.print("[bold bright_cyan]═" * 60 + "[/bold bright_cyan]")
    ui.console.print("  [bold bright_white]WELCOME TO NEXUS — First-Time Setup[/bold bright_white]")
    ui.console.print("[bold bright_cyan]═" * 60 + "[/bold bright_cyan]")
    ui.console.print()
    ui.console.print("  NEXUS needs permission to access folders on your computer.")
    ui.console.print("  This keeps your files safe — NEXUS will [bold]ONLY[/bold] read files")
    ui.console.print("  inside the folders you approve below.")
    ui.console.print()

    while True:
        folder = input("  Enter a folder path NEXUS is allowed to access\n"
                        "  (e.g. C:\\Users\\You\\Documents): ").strip()

        if not folder:
            ui.print_error("No path entered. Please try again.")
            continue

        if add_permission(folder):
            ui.print_status(f"Access granted for: {folder}")
        else:
            ui.print_error(f"Could not add that folder. Please check the path.")

        another = input("  Add another folder? (y/n): ").strip().lower()
        if another != "y":
            break

    ui.console.print("\n  [bright_green]Setup complete![/bright_green] You can add more folders later.\n")


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------
def main():
    """Entry point: setup → load model → interactive loop."""

    # First-run folder permissions setup
    first_run_setup()

    # Pre-load the AI model with a spinner (16.2.8)
    with ui.spinner("Initialising NEXUS — loading model..."):
        load_model()

    # Show the welcome banner
    ui.print_welcome()

    # Initialise conversation memory (Phase 19)
    memory = ConversationMemory()
    set_conversation_memory(memory)

    # Interactive command loop
    while True:
        try:
            # Flush any leftover stdin data (handles multi-line paste on Windows)
            _flush_stdin()
            ui.print_input_prompt()
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            ui.console.print("\n[bright_cyan]Goodbye![/bright_cyan]")
            break

        # Skip empty input
        if not user_input:
            continue

        # Reject very long inputs — user likely pasted something by accident
        if len(user_input) > 500:
            ui.print_error("Input too long — rejected (over 500 characters).")
            ui.console.print(
                '  [dim]Tip: Save long text as a .txt file and use "summarise filename.txt"[/dim]'
            )
            continue

        # Exit command
        if user_input.lower() in ("exit", "quit", "bye"):
            ui.console.print("\n[bright_cyan]Goodbye![/bright_cyan]")
            break

        # Help command
        if user_input.lower() == "help":
            ui.print_help()
            continue

        # Clear / new chat command (Phase 19)
        if user_input.lower() in ("clear", "new chat"):
            memory.clear()
            ui.print_response("Conversation history cleared. Starting a fresh chat!")
            continue

        # Route the input to the appropriate handler
        try:
            result = route(user_input)

            # Record the exchange in conversation memory
            memory.add_message("user", user_input)
            memory.add_message("assistant", result)

            ui.print_response(result)
        except Exception as e:
            ui.print_error(f"An error occurred: {e}")
            ui.console.print("  [dim]Please try rephrasing your request.[/dim]\n")

        # Brief pause to prevent rapid-fire processing of pasted lines
        time.sleep(0.1)


def _flush_stdin():
    """Flush any buffered stdin data (e.g. from multi-line paste on Windows)."""
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        pass  # Not on Windows — skip


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
