"""
model_manager.py — NEXUS Model Manager
Provides commands for managing the AI model: resetting LoRA training,
viewing model status/info, and related utilities.
Can also be run directly (e.g. via reset.bat) to reset training data.
"""

import os
import sys
import json
import shutil
from utils import format_size

# ---------------------------------------------------------------------------
# Paths — resolved relative to the project root (one level up from src/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LORA_WEIGHTS_PATH = os.path.join(PROJECT_ROOT, "lora-weights")
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "config", "settings.json")
MODEL_NAME = "Qwen 2.5 3B Instruct (Q4_K_M GGUF)"




def _get_dir_size(path):
    """Calculate total size of all files in a directory (recursive)."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


# ---------------------------------------------------------------------------
# Reset training — delete all LoRA adapter files
# ---------------------------------------------------------------------------
def reset_training():
    """
    Delete all files inside the lora-weights/ folder to reset custom training.
    Lists files before deletion and asks for user confirmation.

    Returns:
        A status message string.
    """
    # Check if the folder exists
    if not os.path.isdir(LORA_WEIGHTS_PATH):
        return "No training data found. The lora-weights/ folder does not exist."

    # List all files and subdirectories
    contents = os.listdir(LORA_WEIGHTS_PATH)

    # Filter out empty directories — check if there's anything to delete
    if not contents:
        return "No training data found. The lora-weights/ folder is already empty."

    # Build a summary of what will be deleted
    print("\n  Files/folders that will be deleted:")
    print("  " + "-" * 44)

    files_to_remove = []
    dirs_to_remove = []
    total_size = 0

    for item in sorted(contents):
        item_path = os.path.join(LORA_WEIGHTS_PATH, item)
        if os.path.isdir(item_path):
            dir_size = _get_dir_size(item_path)
            total_size += dir_size
            print(f"    [DIR]  {item}  ({format_size(dir_size)})")
            dirs_to_remove.append(item_path)
        else:
            file_size = os.path.getsize(item_path)
            total_size += file_size
            print(f"    [FILE] {item}  ({format_size(file_size)})")
            files_to_remove.append(item_path)

    print("  " + "-" * 44)
    print(f"  Total: {len(files_to_remove)} file(s), {len(dirs_to_remove)} folder(s) — {format_size(total_size)}")
    print()

    # Ask for confirmation
    confirm = input("  Are you sure you want to delete all training data? (y/n): ").strip().lower()
    if confirm != "y":
        return "Reset cancelled. No files were deleted."

    # Delete individual files
    for fp in files_to_remove:
        try:
            os.remove(fp)
        except OSError as e:
            print(f"  [WARNING] Could not delete {os.path.basename(fp)}: {e}")

    # Delete subdirectories (checkpoint folders etc.)
    for dp in dirs_to_remove:
        try:
            shutil.rmtree(dp)
        except OSError as e:
            print(f"  [WARNING] Could not delete folder {os.path.basename(dp)}: {e}")

    return "Training data cleared. NEXUS will use the base model on next start."


# ---------------------------------------------------------------------------
# Model info — show current model status and settings
# ---------------------------------------------------------------------------
def get_model_info():
    """
    Return a formatted string showing the current model status:
    - Base model name
    - LoRA adapter status (applied / not applied)
    - Adapter file details and total size
    - Current settings from config/settings.json
    """
    lines = []
    lines.append("")
    lines.append("  NEXUS — Model Information")
    lines.append("  " + "-" * 40)

    # Base model
    lines.append(f"  Base Model:    {MODEL_NAME}")

    # LoRA status
    if os.path.isdir(LORA_WEIGHTS_PATH):
        lora_files = [
            f for f in os.listdir(LORA_WEIGHTS_PATH)
            if f.endswith((".bin", ".gguf", ".safetensors"))
        ]
        if lora_files:
            total_size = _get_dir_size(LORA_WEIGHTS_PATH)
            lines.append(f"  LoRA Status:   Applied ({len(lora_files)} adapter file(s))")
            lines.append(f"  Adapter Size:  {format_size(total_size)}")
            for lf in sorted(lora_files):
                fsize = os.path.getsize(os.path.join(LORA_WEIGHTS_PATH, lf))
                lines.append(f"                 - {lf} ({format_size(fsize)})")
        else:
            lines.append("  LoRA Status:   Not applied (no adapter files found)")
    else:
        lines.append("  LoRA Status:   Not applied (lora-weights/ folder missing)")

    # Settings from config/settings.json
    lines.append("")
    lines.append("  Current Settings:")
    lines.append("  " + "-" * 40)

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        lines.append(f"  Context Window: {settings.get('n_ctx', 'N/A')} tokens")
        lines.append(f"  Max Tokens:     {settings.get('max_tokens', 'N/A')}")
        lines.append(f"  Threads:        {settings.get('n_threads', 'N/A')}")
        lines.append(f"  Auto Threads:   {settings.get('auto_threads', 'N/A')}")
    except (FileNotFoundError, json.JSONDecodeError):
        lines.append("  [Could not read settings.json]")

    lines.append("  " + "-" * 40)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Direct execution — used by reset.bat
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # When run directly (e.g. via reset.bat), perform a training reset
    print("\n" + "=" * 50)
    print("  NEXUS — Training Data Reset Tool")
    print("=" * 50)
    print()
    result = reset_training()
    print(f"\n  {result}\n")
