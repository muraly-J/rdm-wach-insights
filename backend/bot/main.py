from __future__ import annotations

"""Telegram bot entry point."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.ext import Application

from bot.config import BOT_TOKEN, BOT_ADMIN_IDS
from bot.handlers import handler_registry

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _seed_admins() -> None:
    """Seed admin users from BOT_ADMIN_IDS env var on boot."""
    if not BOT_ADMIN_IDS:
        return
    from bot.identity.store import get_store
    store = get_store()
    for admin_id in BOT_ADMIN_IDS:
        store.upsert_admin(str(admin_id))
        logger.info(f"Seeded admin user: {admin_id}")


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Add it to your .env file before starting the bot."
        )

    # Seed admin users before registering handlers
    _seed_admins()

    app = Application.builder().token(BOT_TOKEN).build()

    for handler in handler_registry():
        app.add_handler(handler)

    logger.info("Bot handlers registered via handler_registry()")
    return app


def main() -> None:
    app = build_application()
    logger.info("Starting bot polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
