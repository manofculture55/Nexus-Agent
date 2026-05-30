"""
memory.py — NEXUS Conversation History & Context
Stores the current session's conversation history so the agent remembers
what was discussed. Each message is stored as {role, content}. The history
is kept in memory only — it resets when the agent restarts.

Phase 19 of the NEXUS implementation plan.
"""


class ConversationMemory:
    """
    In-memory conversation history for a single NEXUS session.
    Stores user and assistant messages as a list of dicts and
    provides helpers to retrieve, format, and clear the history.
    """

    def __init__(self):
        self._history = []  # list of {"role": str, "content": str}

    # ------------------------------------------------------------------
    # Add a message to history
    # ------------------------------------------------------------------
    def add_message(self, role, content):
        """
        Append a message to the conversation history.

        Args:
            role:    "user" or "assistant"
            content: The message text.
        """
        if not content or not content.strip():
            return  # don't store empty messages

        self._history.append({
            "role": role,
            "content": content.strip(),
        })

    # ------------------------------------------------------------------
    # Retrieve recent history
    # ------------------------------------------------------------------
    def get_history(self, max_turns=5):
        """
        Return the last N *exchanges* (user + assistant pairs) from history.
        An exchange = one user message + one assistant response = 2 entries.

        Args:
            max_turns: Maximum number of exchanges to return (default 5).

        Returns:
            List of {"role": ..., "content": ...} dicts, in chronological order.
        """
        # Each "turn" is a user+assistant pair = 2 messages
        max_messages = max_turns * 2
        if len(self._history) <= max_messages:
            return list(self._history)
        return list(self._history[-max_messages:])

    # ------------------------------------------------------------------
    # Clear history
    # ------------------------------------------------------------------
    def clear(self):
        """Reset conversation history — start a fresh session."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Format history for the model prompt
    # ------------------------------------------------------------------
    def get_context_string(self, max_turns=5):
        """
        Build a plain-text context string from recent history, suitable
        for prepending to a model prompt. Uses a simple format:

            User: ...
            NEXUS: ...
            User: ...
            NEXUS: ...

        Args:
            max_turns: Maximum number of exchanges to include.

        Returns:
            A formatted string of recent conversation, or empty string
            if there is no history.
        """
        recent = self.get_history(max_turns)
        if not recent:
            return ""

        lines = []
        for msg in recent:
            if msg["role"] == "user":
                lines.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                lines.append(f"NEXUS: {msg['content']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Build messages list for chat completion API
    # ------------------------------------------------------------------
    def get_messages_for_model(self, max_turns=5):
        """
        Return the history as a list of message dicts ready for the
        model's create_chat_completion() messages parameter.
        Does NOT include the system prompt — the caller should prepend that.

        Args:
            max_turns: Maximum number of exchanges to include.

        Returns:
            List of {"role": "user"|"assistant", "content": ...} dicts.
        """
        return self.get_history(max_turns)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def length(self):
        """Number of individual messages stored."""
        return len(self._history)

    @property
    def is_empty(self):
        """True if no messages have been stored yet."""
        return len(self._history) == 0

    def __len__(self):
        return len(self._history)

    def __repr__(self):
        return f"ConversationMemory({len(self._history)} messages)"
