from __future__ import annotations

"""
bot/groups.py
─────────────
Maps Telegram chat_id → group role.
Reading config at module load so tests can reload after monkeypatching env.
"""

import os

_MANAGERS_CHAT_ID: int = int(os.environ.get("MANAGERS_CHAT_ID", "0"))
_ENGINEERS_CHAT_ID: int = int(os.environ.get("ENGINEERS_CHAT_ID", "0"))
_TECHNICIANS_CHAT_ID: int = int(os.environ.get("TECHNICIANS_CHAT_ID", "0"))

_CHAT_ID_MAP: dict[int, str] = {}
if _MANAGERS_CHAT_ID:
    _CHAT_ID_MAP[_MANAGERS_CHAT_ID] = "managers"
if _ENGINEERS_CHAT_ID:
    _CHAT_ID_MAP[_ENGINEERS_CHAT_ID] = "engineers"
if _TECHNICIANS_CHAT_ID:
    _CHAT_ID_MAP[_TECHNICIANS_CHAT_ID] = "technicians"


def get_group(chat_id: int) -> str | None:
    """Return the group role for a chat_id, or None if unknown."""
    return _CHAT_ID_MAP.get(chat_id)
