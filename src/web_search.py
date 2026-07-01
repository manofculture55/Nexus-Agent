# -*- coding: utf-8 -*-
"""
web_search.py -- NEXUS Web Search via Gemini API
Provides web search capabilities using Google's Gemini API.

Phase 29 of the NEXUS implementation plan.
Placeholder -- will be fully implemented in Phase 29.
"""


def search_web_gemini(query):
    """
    Search the web using Google Gemini API.

    Args:
        query: The search query string.

    Returns:
        Search result string.

    Raises:
        ImportError: If google-genai package is not installed.
    """
    try:
        from google import genai
    except ImportError:
        return ("Gemini API not available.\n"
                "Install with: pip install google-genai\n"
                "Then set your API key in Settings.")

    # API key check
    import os
    api_key = _load_api_key()
    if not api_key:
        return ("No Gemini API key found.\n"
                "Set your API key in Settings > API Key,\n"
                "or create config/api_keys.json with: {\"gemini_api_key\": \"YOUR_KEY\"}")

    return f"Web search not yet implemented. (Phase 29)\nQuery: \"{query}\""


def _load_api_key():
    """Load Gemini API key from config/api_keys.json."""
    import os
    import json

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    key_file = os.path.join(project_root, "config", "api_keys.json")

    if not os.path.isfile(key_file):
        return None

    try:
        with open(key_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("gemini_api_key", None)
    except (json.JSONDecodeError, OSError):
        return None
