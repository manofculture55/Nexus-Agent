"""
ui.py — NEXUS Rich CLI Output Module
Centralised UI output using the `rich` library for colourful, formatted
terminal output. All display functions are here so the rest of the
codebase can call ui.print_*() instead of plain print().
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

# Global console instance — used throughout the module
console = Console()


# ---------------------------------------------------------------------------
# Welcome banner (16.2.1)
# ---------------------------------------------------------------------------
def print_welcome():
    """Print the NEXUS startup banner with rich Panel and styled text."""
    ascii_art = r"""
     _   _ _______  ___   _ ____
    | \ | | ____\ \/ / | | / ___|
    |  \| |  _|  \  /| | | \___ \
    | |\  | |___ /  \| |_| |___) |
    |_| \_|_____/_/\_\\___/|____/
    """
    banner = Text(ascii_art, style="bold cyan")
    banner.append("\n         Offline AI Agent v2.0\n", style="bold white")

    console.print(Panel(
        banner,
        title="[bold bright_white]N E X U S[/bold bright_white]",
        subtitle="[dim]Type 'help' for commands | 'exit' to quit[/dim]",
        border_style="bright_cyan",
        padding=(0, 2),
    ))
    console.print()


# ---------------------------------------------------------------------------
# Help menu (16.2.2)
# ---------------------------------------------------------------------------
def print_help():
    """Print all available commands as a rich Table."""
    table = Table(
        title="[bold bright_cyan]NEXUS — What I Can Do[/bold bright_cyan]",
        border_style="bright_cyan",
        show_header=True,
        header_style="bold bright_white",
        padding=(0, 1),
    )
    table.add_column("Feature", style="bold yellow", min_width=20)
    table.add_column("Example Command", style="white")

    table.add_row("[>] Summarise a file",    '"summarise my notes.txt"')
    table.add_row("[>] Summarise a folder",  '"summarise all files in C:\\my-notes"')
    table.add_row("[>] Ask a question",       '"what is machine learning?"')
    table.add_row("[>] Battery status",       '"what is my battery percentage?"')
    table.add_row("[>] Running processes",    '"show me what is running"')
    table.add_row("[>] Model info",           '"model info"')
    table.add_row("[>] Reset training",       '"reset my training"')
    table.add_row("[>] Shutdown",              '"shut down my computer"')
    table.add_row("[>] Restart",               '"restart the computer"')
    table.add_row("[>] Sleep",                 '"put the computer to sleep"')
    table.add_row("[>] Cancel shutdown",       '"cancel shutdown"')
    table.add_row("[>] Rename a file",         '"rename notes.txt to notes_old.txt"')
    table.add_row("[>] Copy a file",           '"copy report.pdf to D:\\backup"')
    table.add_row("[>] Move a file",           '"move data.csv to D:\\archive"')
    table.add_row("[>] Delete a file",         '"delete file temp.txt"')
    table.add_row("[>] List files",            '"list files in C:\\my-docs"')
    table.add_row("[>] Search my documents",   '"what do my files say about X?"')
    table.add_row("[>] Reindex files",         '"reindex my files"')
    table.add_row("[>] Open a URL",            '"open google.com"')
    table.add_row("[>] Search the web",        '"search for python tutorials"')
    table.add_row("[>] Stock prices",          '"get stock price of Reliance"')
    table.add_row("[>] Fetch web page",        '"fetch data from example.com"')
    table.add_row("[>] Fetch & save",          '"prices of TCS save to stocks.txt"')
    table.add_row("[>] Clear chat history",    '"clear" or "new chat"')
    table.add_row("[>] Exit",                 '"exit"')

    console.print()
    console.print(table)
    console.print()
    console.print(
        "[dim]Tip: To process long text, save it as a .txt file "
        'and use "summarise filename.txt"[/dim]'
    )
    console.print()


# ---------------------------------------------------------------------------
# Response output (16.2.3)
# ---------------------------------------------------------------------------
def print_response(text):
    """Display an agent response with coloured NEXUS prefix and Panel."""
    if not text or not text.strip():
        text = "[No response generated]"

    console.print()
    console.print(Panel(
        text.strip(),
        title="[bold bright_cyan]NEXUS[/bold bright_cyan]",
        border_style="bright_cyan",
        padding=(1, 2),
    ))
    console.print()


# ---------------------------------------------------------------------------
# Error output (16.2.4)
# ---------------------------------------------------------------------------
def print_error(text):
    """Display an error message with red styling."""
    console.print(f"[bold red][ERROR][/bold red] {text}")


# ---------------------------------------------------------------------------
# Status / progress output (16.2.5)
# ---------------------------------------------------------------------------
def print_status(text):
    """Display a progress/status message with yellow/dim styling."""
    console.print(f"[yellow]  {text}[/yellow]")


# ---------------------------------------------------------------------------
# Spinner context manager for model loading (16.2.8)
# ---------------------------------------------------------------------------
def spinner(message="Loading..."):
    """
    Return a rich Status (spinner) context manager.
    Usage:
        with ui.spinner("Loading model..."):
            load_model()
    """
    return console.status(f"[bright_cyan]{message}[/bright_cyan]", spinner="dots")


# ---------------------------------------------------------------------------
# Input prompt
# ---------------------------------------------------------------------------
def get_input_prompt():
    """Return a styled input prompt string."""
    return "[bold bright_green]You:[/bold bright_green] "


def print_input_prompt():
    """Print the styled input prompt without newline."""
    console.print("[bold bright_green]You:[/bold bright_green] ", end="")
