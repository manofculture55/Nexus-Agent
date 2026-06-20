"""
persistent_memory.py — NEXUS Long-Term Persistent Memory
Stores user facts across sessions in a JSON file on disk.
Unlike ConversationMemory (session-only), this survives restarts.

Phase 28 of the NEXUS implementation plan.
"""

import os
import json
from datetime import datetime


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Resolve path relative to the project root (nexus-agent/config/)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
MEMORY_FILE = os.path.join(_PROJECT_ROOT, "config", "user_memory.json")


# ---------------------------------------------------------------------------
# Load / Save helpers
# ---------------------------------------------------------------------------
def load_memory():
    """
    Read user_memory.json and return its contents as a dict.
    Returns an empty dict with a 'facts' key if the file is missing
    or corrupted.
    """
    if not os.path.isfile(MEMORY_FILE):
        return {"facts": []}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure the expected structure exists
        if not isinstance(data, dict) or "facts" not in data:
            return {"facts": []}
        return data
    except (json.JSONDecodeError, OSError, ValueError):
        return {"facts": []}


def save_memory(data):
    """
    Write the memory dict to user_memory.json.

    Args:
        data: Dict with at least a 'facts' key containing a list.
    """
    try:
        # Ensure the config directory exists
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"Warning: Could not save memory file: {e}")


# ---------------------------------------------------------------------------
# Store and recall facts
# ---------------------------------------------------------------------------
def remember_fact(fact_text):
    """
    Store a user fact with a timestamp.

    Args:
        fact_text: The fact string to remember.

    Returns:
        Confirmation message string.
    """
    if not fact_text or not fact_text.strip():
        return "Please provide a fact to remember. Example: /remember my favourite movie is Avengers Endgame"

    fact_text = fact_text.strip()
    data = load_memory()

    # Check for duplicate facts (case-insensitive)
    for existing in data["facts"]:
        if existing["text"].lower() == fact_text.lower():
            return f"I already know that: \"{fact_text}\""

    # Add the new fact
    data["facts"].append({
        "text": fact_text,
        "stored_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    save_memory(data)
    return f"Got it! I'll remember: \"{fact_text}\""


def recall_facts(query=None):
    """
    Return all stored facts, optionally filtered by a keyword query.

    Args:
        query: Optional keyword string to filter facts.
               If None or empty, returns all facts.

    Returns:
        Formatted string listing the stored facts.
    """
    data = load_memory()
    facts = data.get("facts", [])

    if not facts:
        return "No memories stored yet. Use /remember to store facts about yourself."

    # Filter by keyword if a query is provided
    if query and query.strip():
        query_lower = query.strip().lower()
        filtered = [
            f for f in facts
            if query_lower in f["text"].lower()
        ]
        if not filtered:
            return f"No memories matching \"{query}\". Use /recall to see all stored facts."
        facts = filtered

    # Build numbered list
    lines = ["Stored memories:"]
    lines.append("-" * 45)
    for i, fact in enumerate(facts, 1):
        timestamp = fact.get("stored_at", "unknown date")
        lines.append(f"  {i}. {fact['text']}")
        lines.append(f"     (stored: {timestamp})")
    lines.append("-" * 45)
    lines.append(f"Total: {len(facts)} {'memory' if len(facts) == 1 else 'memories'}")

    return "\n".join(lines)


def forget_fact(index_or_keyword):
    """
    Remove a specific stored fact by index number or keyword match.

    Args:
        index_or_keyword: Either a numeric index (1-based) shown by /recall,
                          or a keyword string to match against stored facts.

    Returns:
        Confirmation or error message string.
    """
    if not index_or_keyword or not str(index_or_keyword).strip():
        return ("Please specify which memory to forget.  \n"
                "Use a number: /forget 1  \n"
                "Or a keyword: /forget favourite movie")

    data = load_memory()
    facts = data.get("facts", [])

    if not facts:
        return "No memories stored. Nothing to forget."

    target = str(index_or_keyword).strip()

    # Try numeric index first
    try:
        idx = int(target) - 1  # Convert 1-based to 0-based
        if 0 <= idx < len(facts):
            removed = facts.pop(idx)
            save_memory(data)
            return f"Forgotten: \"{removed['text']}\""
        else:
            return f"Invalid memory number. Use /recall to see the list (1-{len(facts)})."
    except ValueError:
        pass  # Not a number — try keyword match

    # Keyword match — find the first fact containing the keyword
    target_lower = target.lower()
    for i, fact in enumerate(facts):
        if target_lower in fact["text"].lower():
            removed = facts.pop(i)
            save_memory(data)
            return f"Forgotten: \"{removed['text']}\""

    return f"No memory matching \"{target}\". Use /recall to see all stored facts."


def clear_all_memories():
    """
    Delete ALL stored facts after confirmation.
    Note: This function is called programmatically — the caller
    should handle confirmation prompting.

    Returns:
        Confirmation message string.
    """
    data = load_memory()
    count = len(data.get("facts", []))

    if count == 0:
        return "No memories stored. Nothing to clear."

    data["facts"] = []
    save_memory(data)
    return f"All {count} memories cleared."


def list_memories():
    """
    Show all stored facts in a numbered list.
    Alias for recall_facts(None).

    Returns:
        Formatted string listing all stored facts.
    """
    return recall_facts(None)


# ---------------------------------------------------------------------------
# Memory injection — retrieve relevant facts for QA context
# ---------------------------------------------------------------------------
def get_relevant_memories(question):
    """
    Retrieve user memories that are relevant to the given question.
    Uses simple keyword overlap to determine relevance.

    Args:
        question: The user's question string.

    Returns:
        A context string to prepend to the model prompt, or empty
        string if no relevant memories are found.
    """
    data = load_memory()
    facts = data.get("facts", [])

    if not facts:
        return ""

    # Extract meaningful words from the question (3+ chars, lowercased)
    question_lower = question.lower()
    question_words = set(
        word.strip(".,!?;:'\"()[]")
        for word in question_lower.split()
        if len(word.strip(".,!?;:'\"()[]")) >= 3
    )

    # Filter out common stop words that would cause false matches
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all",
        "can", "had", "her", "was", "one", "our", "out", "has",
        "its", "any", "who", "what", "when", "where", "why", "how",
        "this", "that", "with", "from", "they", "been", "have",
        "will", "each", "make", "like", "just", "about", "over",
        "such", "take", "than", "them", "very", "some", "could",
        "would", "should", "into", "also", "these", "tell", "does",
        "much", "know", "which", "there", "their", "more", "other",
        "most", "only", "your", "then", "many",
    }
    question_words -= stop_words

    if not question_words:
        return ""

    # Find facts that share keywords with the question
    relevant = []
    for fact in facts:
        fact_lower = fact["text"].lower()
        fact_words = set(
            word.strip(".,!?;:'\"()[]")
            for word in fact_lower.split()
            if len(word.strip(".,!?;:'\"()[]")) >= 3
        )
        fact_words -= stop_words

        # Check for keyword overlap
        overlap = question_words & fact_words
        if overlap:
            relevant.append(fact["text"])

    if not relevant:
        return ""

    # Build context string
    facts_text = "\n".join(f"- {f}" for f in relevant)
    return (
        "The user has previously told you these personal facts:\n"
        f"{facts_text}\n"
        "Use this information if it's relevant to answering their question.\n\n"
    )
