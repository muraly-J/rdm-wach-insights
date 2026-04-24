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

# Group chat IDs — 2 groups only (technicians + admin/managers)
ADMIN_CHAT_ID: int = int(os.environ.get("ADMIN_CHAT_ID", os.environ.get("MANAGERS_CHAT_ID", "0")))
TECHNICIANS_CHAT_ID: int = int(os.environ.get("TECHNICIANS_CHAT_ID", "0"))

# Backwards compat alias (used by existing code that references MANAGERS_CHAT_ID)
MANAGERS_CHAT_ID: int = ADMIN_CHAT_ID

# REMOVED: ENGINEERS_CHAT_ID — engineer role no longer exists

API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://localhost:8081")
FRONTEND_BASE_URL: str = os.environ.get("FRONTEND_BASE_URL", "")

# Admin user IDs (Telegram user_id) — seeded as admin role on boot
BOT_ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.environ.get("BOT_ADMIN_IDS", "").split(",")
    if x.strip()
]

# Feature flags
BOT_AGENT_ENABLED: bool = os.environ.get("BOT_AGENT_ENABLED", "false").lower() == "true"

# Rate limiting
BOT_RATE_LIMIT_DEFAULT: int = int(os.environ.get("BOT_RATE_LIMIT_DEFAULT", "30"))
BOT_RATE_LIMIT_ASK: int = int(os.environ.get("BOT_RATE_LIMIT_ASK", "5"))

# Dict of technician display name → telegram user_id (as string)
# env: TECHNICIANS_JSON='{"Alice": "123456789", "Bob": "987654321"}'
TECHNICIANS: dict[str, str] = json.loads(os.environ.get("TECHNICIANS_JSON", "{}"))

# Predefined ticket categories
TICKET_CATEGORIES: list[str] = [
    "Bug Report",
    "System Error",
    "New Idea or Features",
    "Other Inquiry",
]
