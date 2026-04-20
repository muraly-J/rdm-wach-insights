from __future__ import annotations

"""
bot/config.py
─────────────
Standalone env var config for the Telegram bot process.
Does NOT import from backend config.py — bot is a separate process.
"""

import json
import os

BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MANAGERS_CHAT_ID: int = int(os.environ.get("MANAGERS_CHAT_ID", "0"))
ENGINEERS_CHAT_ID: int = int(os.environ.get("ENGINEERS_CHAT_ID", "0"))
TECHNICIANS_CHAT_ID: int = int(os.environ.get("TECHNICIANS_CHAT_ID", "0"))
API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://localhost:8081")

# Dict of technician display name → telegram user_id (as string)
# env: TECHNICIANS_JSON='{"Alice": "123456789", "Bob": "987654321"}'
TECHNICIANS: dict[str, str] = json.loads(os.environ.get("TECHNICIANS_JSON", "{}"))
