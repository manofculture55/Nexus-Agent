"""
model_loader.py — NEXUS Model Loader
Loads the Qwen 2.5 3B Instruct GGUF model via llama-cpp-python,
handles settings from config/settings.json, auto-detects and applies
LoRA adapter weights if present, and exposes a generate() function
for the rest of the application.
"""

import os
import sys
import json
import time
import threading
import psutil
from llama_cpp import Llama

# ---------------------------------------------------------------------------
# Paths — resolved relative to the project root (one level up from src/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DEFAULT_MODEL_PATH = os.path.join(PROJECT_ROOT, "model", "qwen2.5-3b-instruct-q4_k_m.gguf")
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "config", "settings.json")
LORA_WEIGHTS_PATH = os.path.join(PROJECT_ROOT, "lora-weights")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
model = None
_settings_cache = None  # cached after first load_settings() call


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def load_settings():
    """
    Read config/settings.json and return a dict of settings.
    Falls back to sensible defaults if the file is missing or malformed.
    Results are cached in memory after the first call.
    """
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache
    defaults = {
        "model_path": DEFAULT_MODEL_PATH,
        "max_tokens": 512,
        "n_ctx": 8192,
        "n_threads": 4,
    }

    if not os.path.isfile(SETTINGS_PATH):
        _settings_cache = defaults
        return _settings_cache

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Merge loaded values over defaults so missing keys still have defaults
        for key in defaults:
            if key not in data:
                data[key] = defaults[key]

        # If model_path in settings is relative, resolve it from project root
        if not os.path.isabs(data["model_path"]):
            data["model_path"] = os.path.join(PROJECT_ROOT, data["model_path"])

        _settings_cache = data
        return _settings_cache

    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARNING] Could not parse settings.json ({e}). Using defaults.")
        _settings_cache = defaults
        return _settings_cache


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
def load_model():
    """
    Load the Qwen 2.5 3B Instruct GGUF model into the global `model` variable.
    Automatically applies LoRA adapter weights if they exist in lora-weights/.
    """
    global model

    settings = load_settings()
    model_path = settings["model_path"]
    n_ctx = settings.get("n_ctx", 4096)
    n_threads = settings.get("n_threads", 4)

    # --- Auto-detect optimal thread count -----------------------------------
    auto_threads = settings.get("auto_threads", True)
    if auto_threads:
        physical_cores = psutil.cpu_count(logical=False) or 4
        n_threads = max(4, physical_cores)
        print(f"Detected {physical_cores} CPU cores. Using {n_threads} threads.")

    # --- Verify model file exists -------------------------------------------
    if not os.path.isfile(model_path):
        print(f"[ERROR] Model file not found at: {model_path}")
        print("Please download the GGUF model and place it in the model/ folder.")
        print("See docs/NEXUS_TODO.md — Section 0.5 for instructions.")
        sys.exit(1)

    # --- Load base GGUF model (with progress dots) --------------------------
    print("Loading NEXUS model (Qwen 2.5 3B), please wait", end="", flush=True)

    # Show dots in a background thread so the user knows it hasn't frozen
    loading_done = threading.Event()

    def _show_progress():
        while not loading_done.is_set():
            print(".", end="", flush=True)
            loading_done.wait(timeout=2)  # print a dot every 2 seconds

    progress_thread = threading.Thread(target=_show_progress, daemon=True)
    progress_thread.start()

    try:
        model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=False,
            chat_format="chatml",
        )
    except Exception as e:
        loading_done.set()
        print()  # newline after dots
        print(f"[ERROR] Failed to load model: {e}")
        sys.exit(1)

    loading_done.set()
    progress_thread.join(timeout=1)
    print(" Done!")  # finish the dots line

    # --- LoRA auto-loading --------------------------------------------------
    _apply_lora_if_available()

    # --- Warm up model with a tiny inference --------------------------------
    _warmup_model()


def _warmup_model():
    """
    Run a single tiny inference to warm up CPU caches and memory pages.
    This eliminates the cold-start delay on the first real user command.
    """
    global model
    if model is None:
        return

    print("Warming up...", end=" ", flush=True)
    try:
        model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are an assistant."},
                {"role": "user", "content": "hi"},
            ],
            max_tokens=1,  # Generate only 1 token — just enough to warm caches
        )
        print("Ready!")
    except Exception:
        print("Done.")  # Non-critical — proceed even if warmup fails

def _apply_lora_if_available():
    """
    Check if LoRA adapter weights exist in lora-weights/ and apply them.
    This makes user training seamless — no manual steps required.
    """
    global model

    if not os.path.isdir(LORA_WEIGHTS_PATH):
        print("Using base model (no custom training applied).")
        return

    # Look for common LoRA adapter file patterns
    lora_files = [
        f for f in os.listdir(LORA_WEIGHTS_PATH)
        if f.endswith((".bin", ".gguf", ".safetensors"))
    ]

    if not lora_files:
        print("Using base model (no custom training applied).")
        return

    # Pick the first adapter file found
    lora_file = os.path.join(LORA_WEIGHTS_PATH, lora_files[0])
    print("Custom training detected. Applying LoRA adapter...")

    try:
        model.load_lora(lora_file)
        print(f"LoRA adapter applied successfully: {lora_files[0]}")
    except Exception as e:
        print(f"[WARNING] Could not load LoRA adapter ({e}), using base model only.")


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are NEXUS, a task-oriented offline AI assistant. "
    "Focus on being helpful for computer tasks such as file management, "
    "system monitoring, and summarisation. Answer clearly and concisely. "
    "For general knowledge questions, give brief answers in 2-3 sentences. "
    "Do not over-explain. Be direct and useful."
)


def generate(prompt, max_tokens=None, system_prompt=None, conversation_history=None):
    """
    Generate a response from the loaded model using ChatML chat completion.
    Includes a 120-second timeout to prevent hanging on long inputs.

    Args:
        prompt:                The user message / prompt string.
        max_tokens:            Maximum tokens to generate (default from settings).
        system_prompt:         Optional override for the system message.
        conversation_history:  Optional list of {"role": ..., "content": ...} dicts
                               from previous exchanges. Inserted between the system
                               prompt and the current user message to provide context.

    Returns:
        The generated text string, or an error message on failure.
    """
    global model

    # Lazy-load model if not yet loaded
    if model is None:
        load_model()

    # Resolve max_tokens from settings if not explicitly provided
    if max_tokens is None:
        settings = load_settings()
        max_tokens = settings.get("max_tokens", 512)

    # Build the messages list
    sys_msg = system_prompt if system_prompt else SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": sys_msg},
    ]

    # Insert conversation history (previous exchanges) if provided
    if conversation_history:
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    # Current user message goes last
    messages.append({"role": "user", "content": prompt})

    # Run inference with a timeout to prevent hanging
    result_container = [None]
    error_container = [None]

    def _run_inference():
        try:
            response = model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                stop=["\n\n\n", "<|im_end|>"],  # Stop early instead of generating until limit
            )
            result_container[0] = response["choices"][0]["message"]["content"]
        except Exception as e:
            error_container[0] = e

    inference_thread = threading.Thread(target=_run_inference, daemon=True)
    inference_thread.start()
    inference_thread.join(timeout=120)  # 120-second timeout

    if inference_thread.is_alive():
        # Inference is still running after timeout — don't wait
        print("\n[WARNING] Response timed out after 120 seconds.")
        return "Response timed out. The input may be too long. Try a shorter input."

    if error_container[0] is not None:
        print(f"[ERROR] Generation failed: {error_container[0]}")
        return "Error generating response."

    return result_container[0] or "Error generating response."

