from __future__ import annotations

"""
bot/handlers/__init__.py
────────────────────────
Central handler registry. Aggregates handlers from all modules.
"""

from core.logger import get_logger

logger = get_logger(__name__)


def handler_registry() -> list:
    """Return all handlers from all bot modules, in priority order."""
    from bot.handlers import common, admin, technicians, ask as ask_handlers
    from bot.identity import registration

    handlers = []

    # Registration (highest priority — conversation handler)
    handlers.extend(registration.get_handlers())

    # Common commands (/start, /help, /menu)
    handlers.extend(common.get_handlers())

    # Role-specific handlers
    handlers.extend(admin.get_handlers())
    handlers.extend(technicians.get_handlers())

    # Agent commands (/ask)
    handlers.extend(ask_handlers.get_handlers())

    logger.info(f"Registered {len(handlers)} bot handlers")
    return handlers
