from __future__ import annotations

"""Telegram bot entry point."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.ext import Application

from bot.config import BOT_TOKEN
from bot.handlers import engineers, managers, technicians

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Add it to your .env file before starting the bot."
        )
    app = Application.builder().token(BOT_TOKEN).build()

    for handler in managers.get_handlers():
        app.add_handler(handler)
    for handler in engineers.get_handlers():
        app.add_handler(handler)
    for handler in technicians.get_handlers():
        app.add_handler(handler)

    logger.info("Bot handlers registered: managers, engineers, technicians")
    return app


def main() -> None:
    app = build_application()
    logger.info("Starting bot polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
