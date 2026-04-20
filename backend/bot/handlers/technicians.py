from __future__ import annotations

"""Telegram handlers for the technicians group."""

import re
from typing import Any

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot import api_client
from bot.config import TECHNICIANS_CHAT_ID

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."
_ERR_NOT_FOUND = "❌ Work order #{} not found."

DONE_NOTE = 0
_DONE_WO_KEY = "done_wo_id"


def _format_my_work(orders: list[dict[str, Any]]) -> str:
    if not orders:
        return "✅ No work orders assigned to you or available for any technician."
    lines = ["*Your Work Orders*\n"]
    for wo in orders:
        status_icon = "▶️" if wo.get("status") == "in_progress" else "🔧"
        lines.append(
            f"{status_icon} *#{wo['id']}* — {wo.get('ahu_id')} (Level {wo.get('level')})\n"
            f"  {wo.get('title')} [{wo.get('status')}]"
        )
    return "\n".join(lines)


def _format_ahu_status(ahu_id: str, data: dict[str, Any]) -> str:
    lines = [f"*AHU {ahu_id} — Status*\n"]
    for key, val in list(data.items())[:10]:
        lines.append(f"{key}: {val}")
    return "\n".join(lines)


def _is_technicians_group(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.id == TECHNICIANS_CHAT_ID)


async def cmd_mywork(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    user_id = str(update.effective_user.id)
    try:
        any_orders = await api_client.list_work_orders(status="approved", assigned_to="any")
        my_orders = await api_client.list_work_orders(assigned_to=user_id)
        in_progress = await api_client.list_work_orders(status="in_progress", assigned_to=user_id)
        combined = {wo["id"]: wo for wo in any_orders + my_orders + in_progress}
        orders = list(combined.values())
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_my_work(orders), parse_mode="Markdown")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /start <id>")
        return
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return
    try:
        await api_client.start_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(f"▶️ Work Order #{wo_id} marked as *in progress*.", parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /status <ahu_id>  e.g. /status e0402")
        return
    ahu_id = context.args[0].lower()
    if not re.match(r"^e\d{4}$", ahu_id):
        await update.message.reply_text("❌ Unknown device ID. Use format e0101.")
        return
    try:
        data = await api_client.get_ahu_status(ahu_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(f"❌ No data found for {ahu_id}.")
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_ahu_status(ahu_id, data), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    text = (
        "*Technicians — Available Commands*\n\n"
        "/mywork — List your assigned work orders\n"
        "/start <id> — Mark work order as in progress\n"
        "/done <id> — Mark work order as resolved\n"
        "/status <ahu_id> — Current AHU health data\n"
        "/help — This message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_done_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_technicians_group(update):
        return ConversationHandler.END
    if not context.args:
        await update.message.reply_text("Usage: /done <id>")
        return ConversationHandler.END
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return ConversationHandler.END
    context.user_data[_DONE_WO_KEY] = wo_id
    await update.message.reply_text(
        f"Completing Work Order #{wo_id}.\n\nBriefly describe what was done (or /skip):"
    )
    return DONE_NOTE


async def done_receive_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    notes = update.message.text.strip()
    return await _finish_done(update, context, notes=notes)


async def done_skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _finish_done(update, context, notes=None)


async def _finish_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    notes: str | None,
) -> int:
    wo_id = context.user_data.get(_DONE_WO_KEY)
    try:
        await api_client.resolve_work_order(wo_id, notes=notes)
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return ConversationHandler.END
    await update.message.reply_text(f"✅ Work Order #{wo_id} marked as *resolved*.", parse_mode="Markdown")
    return ConversationHandler.END


async def done_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def cb_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != TECHNICIANS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.start_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not start: {e.detail}")
        return
    await query.edit_message_text(f"▶️ Work Order #{wo_id} — *in progress*.", parse_mode="Markdown")


async def cb_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != TECHNICIANS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    await query.message.reply_text(f"Use /done {wo_id} to complete this work order with a note.")


def get_handlers() -> list:
    done_conv = ConversationHandler(
        entry_points=[CommandHandler("done", cmd_done_start)],
        states={
            DONE_NOTE: [
                CommandHandler("skip", done_skip_note),
                MessageHandler(filters.TEXT & ~filters.COMMAND, done_receive_note),
            ],
        },
        fallbacks=[CommandHandler("cancel", done_cancel)],
        conversation_timeout=300,
    )
    return [
        CommandHandler("mywork", cmd_mywork),
        CommandHandler("start", cmd_start),
        CommandHandler("status", cmd_status),
        CommandHandler("help", cmd_help),
        CallbackQueryHandler(cb_start, pattern=r"^start:\d+$"),
        CallbackQueryHandler(cb_done, pattern=r"^done:\d+$"),
        done_conv,
    ]
