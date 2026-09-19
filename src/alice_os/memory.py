"""Explicit local memory commands and shared validation; no model calls."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import Storage

CATEGORIES = {"preference", "profile", "project", "routine", "fact"}


def validate_memory(content: str) -> str:
    content = content.strip()
    if not content or len(content) > 4000:
        raise ValueError("Memory must contain between 1 and 4,000 characters.")
    if re.search(
        r"(?i)\b(password|passphrase|api[ _-]?key|access[ _-]?token|secret[ _-]?key|"
        r"private[ _-]?key|recovery[ _-]?(?:phrase|code)|seed phrase|"
        r"credit card|account number|social security)\b|"
        r"\b(?:sk-|ghp_|github_pat_|hf_)[a-zA-Z0-9_-]{16,}|"
        r"-----BEGIN .*PRIVATE KEY|\b\d{3}-\d{2}-\d{4}\b|"
        r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", content,
    ):
        raise ValueError("That looks like a credential or sensitive account detail. Keep it out of memory.")
    return content


def parse_memory_command(text: str) -> tuple[str, str] | None:
    text = re.sub(r"^(?:hey\s+)?(?:alice|jarvis)[\s,:]+", "", text.strip(), flags=re.I)
    # Only whole, explicit requests are commands, never quoted or embedded text.
    match = re.fullmatch(r"(?:please\s+)?remember(?:\s+that|\s+this\s*:)?\s+(.+)", text, re.I | re.S)
    if match:
        return "save", match[1].strip()
    match = re.fullmatch(r"(?:please\s+)?forget(?:\s+that)?\s+(.+)", text, re.I | re.S)
    if match:
        return "forget", match[1].strip().rstrip(".!?")
    if re.fullmatch(r"(?:what do you remember(?: about me)?|show (?:my |your )?memories|recall (?:my |your )?memories)[.!?]*", text, re.I):
        return "recall", ""
    if re.fullmatch(r"what were we working on[.!?]*", text, re.I):
        return "projects", ""
    match = re.fullmatch(r"(?:recall|what do you remember about)\s+(.+?)[.!?]*", text, re.I | re.S)
    return ("recall", match[1].strip()) if match else None


def handle_memory_command(storage: Storage, text: str, session_id: str) -> str | None:
    command = parse_memory_command(text)
    if command is None:
        return None
    action, value = command
    if action == "save":
        if value.casefold().strip(" .!?:") in {"this", "that", "it"}:
            return "Tell me the exact fact to save, for example: Remember that I prefer concise answers."
        category = "fact"
        prefix = re.match(r"(preference|profile|project|routine|fact)\s*:\s*(.+)", value, re.I | re.S)
        if prefix:
            category, value = prefix[1].lower(), prefix[2]
        elif re.search(r"\b(?:I prefer|my preferred|I like)\b", value, re.I):
            category = "preference"
        try:
            memory = storage.add_global_memory(value, session_id, category=category, source="explicit")
        except ValueError as error:
            return str(error)
        return f"Remembered: {memory['content']}"
    if action == "forget":
        if value.casefold() in {"this", "that", "it", "everything", "all", "all memories"}:
            return "Open Memory to choose what to delete, or say Forget followed by the exact saved fact."
        # Do not delete loosely related matches or infer a referent from an old turn.
        matches = [m for m in storage.list_global_memories(10000)
                   if value.casefold() in {m['id'].casefold(), m['content'].rstrip('.!?').casefold()}]
        if len(matches) != 1:
            return "I couldn't identify one exact memory. Open Memory to review and delete the right entry."
        storage.delete_global_memory(matches[0]["id"])
        return "Forgot that saved memory. Existing conversation messages are unchanged."
    category = {"preferences": "preference", "projects": "project", "profile": "profile", "routines": "routine", "facts": "fact"}.get(re.sub(r"^(?:my|your)\s+", "", value.casefold()))
    if action == "projects":
        category = "project"
    memories = storage.search_global_memories(value, 20) if value and not category else storage.list_global_memories(10000)
    if category:
        memories = [m for m in memories if m["category"] == category]
    if not memories:
        return "No matching saved memories yet. Say Remember project: followed by your project and next step." if action == "projects" else "No matching saved memories yet."
    shown = memories[:20]
    return "Here's what I have saved:\n" + "\n".join(f"- {m['content']}" for m in shown) + (
        "\nOpen Memory to see all entries." if len(memories) > 20 else ""
    )
