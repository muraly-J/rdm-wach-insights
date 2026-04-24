from __future__ import annotations

"""
bot/identity/decorators.py
──────────────────────────
Role-based access control decorators for bot handlers.

Usage:
    @require_role('technician')
    async def cmd_mywork(update, context):
        user = context.bot_user  # guaranteed to be set
        ...

    @require_admin
    async def cmd_users(update, context):
        ...
"""

import functools
from collections.abc import Callable

from core.logger import get_logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.identity.store import get_store, role_satisfies

logger = get_logger(__name__)


def require_role(*roles: str) -> Callable:
    """
    Decorator that ensures the calling user is registered, active,
    and has one of the specified roles.

    Sets `context.bot_user` (BotUser) for downstream use.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.effective_user:
                return

            store = get_store()
            user = store.get_user(str(update.effective_user.id))

            if not user or user.status != "active":
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "⚠️ Not authorized. Tap /register if you're new."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "Not authorized. DM the bot and /register first.",
                        show_alert=True,
                    )
                return

            if not any(role_satisfies(user.role, r) for r in roles):
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "🚫 You don't have permission for this command."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "You don't have permission for this action.",
                        show_alert=True,
                    )
                return

            # Attach user to context for downstream handlers
            context.bot_user = user  # type: ignore[attr-defined]
            return await fn(update, context, *args, **kwargs)

        return wrapper
    return decorator


# Convenience aliases
require_technician = require_role("technician")
require_admin = require_role("admin")
