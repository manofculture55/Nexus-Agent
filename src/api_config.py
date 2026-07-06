# -*- coding: utf-8 -*-
"""
api_config.py -- NEXUS API Key Management
Loads and manages API keys from config/api_keys.json.
Provides a centralized way for all modules to access API credentials.

Phase 29 of the NEXUS implementation plan.
"""

import os
import json


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
API_KEYS_FILE = os.path.join(_PROJECT_ROOT, "config", "api_keys.json")
API_KEYS_TEMPLATE = os.path.join(_PROJECT_ROOT, "config", "api_keys.template.json")


# ---------------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------------
def load_api_key(service_name):
    """
    Read an API key from config/api_keys.json.

    Args:
        service_name: The key name in the JSON file, e.g. 'gemini_api_key'.

    Returns:
        The API key string, or None if not found / file missing / invalid.
    """
    if not os.path.isfile(API_KEYS_FILE):
        return None

    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    key = data.get(service_name, None)

    # Reject placeholder values
    if key and key.strip() and key not in ("YOUR_GEMINI_API_KEY_HERE", "YOUR_API_KEY_HERE", ""):
        return key.strip()

    return None


def save_api_key(service_name, api_key):
    """
    Save an API key to config/api_keys.json.

    Args:
        service_name: The key name, e.g. 'gemini_api_key'.
        api_key:      The API key string to store.

    Returns:
        True if saved successfully, False on error.
    """
    # Load existing data
    data = {}
    if os.path.isfile(API_KEYS_FILE):
        try:
            with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    data[service_name] = api_key

    try:
        os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
        with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except OSError:
        return False


def get_setup_instructions():
    """
    Return user-friendly instructions for setting up the Gemini API key.

    Returns:
        Formatted instruction string.
    """
    return (
        "Gemini API key not configured.\n"
        "\n"
        "To enable web search:\n"
        "  1. Go to https://aistudio.google.com/apikey\n"
        "  2. Create a free API key\n"
        "  3. Add it to config/api_keys.json:\n"
        '     {"gemini_api_key": "YOUR_KEY_HERE"}\n'
        "\n"
        "Or use Settings > API Key in the GUI."
    )
