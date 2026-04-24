from __future__ import annotations

"""
bot/handlers/common.py
──────────────────────
Common commands available to all users regardless of role.

Commands:
  /start — greeting / registration prompt / menu based on user state
  /help  — role-specific command list
  /menu  — show menu card
  /cancel — cancel any active conversation
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.identity.store import get_store
from core.logger import get_logger

logger = get_logger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start dispatcher based on user state:
    - Unregistered → registration prompt
    - Pending → waiting for approval
    - Active → menu + greeting
    - Disabled → account disabled message
    """
    if not update.effective_user:
        return

    store = get_store()
    user = store.get_user(str(update.effective_user.id))

    if not user:
        # Unregistered
        await update.message.reply_text(
            "👋 Welcome to *WACH Insight Bot*!\n\n"
            "I help manage building health tickets and work orders.\n\n"
            "Use /register to get started.",
            parse_mode="Markdown",
        )
        return

    if user.status == "pending":
        await update.message.reply_text(
            "⏳ Your registration is pending admin approval.\n"
            "You'll be notified once approved."
        )
        return

    if user.status == "disabled":
        await update.message.reply_text(
            "🚫 Your account is disabled. Contact an admin."
        )
        return

    # Active user — show greeting
    role_label = "Admin/Manager" if user.role == "admin" else "Technician"
    await update.message.reply_text(
        f"👋 Hello, *{user.display_name}*!\n"
        f"Role: {role_label}\n\n"
        f"Use /help to see your available commands.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show role-specific help text."""
    if not update.effective_user:
        return

    store = get_store()
    user = store.get_user(str(update.effective_user.id))

    if not user or user.status != "active":
        await update.message.reply_text(
            "*Available Commands*\n\n"
            "/start — Get started\n"
            "/register — Register your account\n"
            "/help — This message\n"
            "/cancel — Cancel current action",
            parse_mode="Markdown",
        )
        return

    if user.role == "admin":
        await update.message.reply_text(
            "*Admin — Available Commands*\n\n"
            "📋 *Ticket Management*\n"
            "/pending — List tickets awaiting action\n"
            "/ticket <no> — View ticket details\n"
            "/setstatus <no> <status> — Set ticket status\n"
            "/setpriority <no> <priority> — Set ticket priority\n"
            "\n📈 *Overview*\n"
            "/summary — Building health snapshot\n"
            "/activity — Recent audit log\n"
            "\n👥 *User Management*\n"
            "/users — List registered users\n"
            "\n🔧 *General*\n"
            "/help — This message\n"
            "/cancel — Cancel current action",
            parse_mode="Markdown",
        )
    else:
        # Technician
        await update.message.reply_text(
            "*Technician — Available Commands*\n\n"
            "📋 *Tickets*\n"
            "/mywork — Your claimed tickets\n"
            "/update <no> <status> — Propose status change\n"
            "/status <ahu_id> — AHU health status\n"
            "\n🔧 *General*\n"
            "/help — This message\n"
            "/cancel — Cancel current action",
            parse_mode="Markdown",
        )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show menu — alias for /help for now."""
    await cmd_help(update, context)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel any active operation."""
    await update.message.reply_text("Cancelled.")


def get_handlers() -> list:
    """Return common command handlers."""
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("help", cmd_help),
        CommandHandler("menu", cmd_menu),
        CommandHandler("cancel", cmd_cancel),
    ]
