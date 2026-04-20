from __future__ import annotations

"""
bot/handlers/managers.py
─────────────────────────
Telegram handlers for the managers group.

Commands:
  /pending   — list work orders awaiting approval
  /workorder <id> — details of a specific work order
  /summary   — building health snapshot
  /help      — available commands

Inline callbacks:
  approve:{id}        — approve work order
  dismiss:{id}        — dismiss work order
  push_engineers:{id} — push to engineers
  assign_any:{id}     — assign to any technician
  assign_pick:{id}    — show specific technician picker
  assign_tech:{id}:{user_id} — assign to specific technician
"""

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from bot import api_client
from bot.config import MANAGERS_CHAT_ID, TECHNICIANS
from bot.groups import get_group
from bot.push.notifier import notify_engineers, notify_technicians

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."
_ERR_NOT_FOUND = "❌ Work order #{} not found."


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_pending_list(orders: list[dict[str, Any]]) -> str:
    if not orders:
        return "✅ No pending work orders."
    lines = ["*Pending Work Orders*\n"]
    for wo in orders:
        icon = "🚨" if str(wo.get("severity", "")).lower() == "critical" else "⚠️"
        lines.append(
            f"{icon} *#{wo['id']}* — {wo.get('ahu_id')} (Level {wo.get('level')})\n"
            f"  {wo.get('title')}"
        )
    return "\n".join(lines)


def _format_work_order_detail(wo: dict[str, Any]) -> str:
    lines = [
        f"*Work Order #{wo['id']}*",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
        f"Title: {wo.get('title')}",
        f"Description: {wo.get('description') or '—'}",
        f"Severity: {wo.get('severity')}",
        f"Status: {wo.get('status')}",
        f"Created: {str(wo.get('created_at', ''))[:16].replace('T', ' ')}",
    ]
    return "\n".join(lines)


# ── Guards ─────────────────────────────────────────────────────────────────────

def _is_managers_group(update: Update) -> bool:
    return update.effective_chat.id == MANAGERS_CHAT_ID


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    try:
        orders = await api_client.list_work_orders(status="draft")
        orders += await api_client.list_work_orders(status="pending_approval")
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_pending_list(orders), parse_mode="Markdown")


async def cmd_workorder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /workorder <id>")
        return
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return
    try:
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_work_order_detail(wo), parse_mode="Markdown")


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    try:
        data = await api_client.get_health_scores()
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    scores = data if isinstance(data, list) else data.get("scores", data.get("levels", []))
    if not scores:
        await update.message.reply_text("No health score data available.")
        return
    lines = ["*Building Health Summary*\n"]
    for item in scores:
        level = item.get("level", item.get("Level", "?"))
        score = item.get("score", item.get("composite", item.get("health_score", "?")))
        try:
            score_int = int(float(score))
            icon = "🔴" if score_int < 40 else ("🟡" if score_int < 60 else "🟢")
        except (TypeError, ValueError):
            icon = "⚪"
            score_int = score
        lines.append(f"{icon} Level {level}: {score_int}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    text = (
        "*Managers — Available Commands*\n\n"
        "/pending — List work orders awaiting approval\n"
        "/workorder <id> — Details of a work order\n"
        "/summary — Building health snapshot\n"
        "/help — This message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Inline callback handlers ───────────────────────────────────────────────────

async def cb_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_managers_group(update):
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.approve_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not approve: {e.detail}")
        return
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👷 Any Technician", callback_data=f"assign_any:{wo_id}"),
            InlineKeyboardButton("👤 Pick Specific", callback_data=f"assign_pick:{wo_id}"),
        ]
    ])
    await query.edit_message_text(
        f"✅ Work Order #{wo_id} approved.\n\nAssign to:",
        reply_markup=keyboard,
    )


async def cb_dismiss(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_managers_group(update):
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.dismiss_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not dismiss: {e.detail}")
        return
    await query.edit_message_text(f"❌ Work Order #{wo_id} dismissed.")


async def cb_push_engineers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_managers_group(update):
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.push_to_engineers(wo_id)
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not push: {e.detail}")
        return
    await notify_engineers(wo)
    await query.edit_message_text(f"🔍 Work Order #{wo_id} sent to engineers for review.")


async def cb_assign_any(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_managers_group(update):
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.assign_work_order(wo_id, assigned_to="any")
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not assign: {e.detail}")
        return
    await notify_technicians(wo)
    await query.edit_message_text(f"🔧 Work Order #{wo_id} assigned to any available technician.")


async def cb_assign_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_managers_group(update):
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    if not TECHNICIANS:
        await query.edit_message_text("⚠️ No technicians configured. Set TECHNICIANS_JSON env var.")
        return
    buttons = [
        [InlineKeyboardButton(name, callback_data=f"assign_tech:{wo_id}:{user_id}")]
        for name, user_id in TECHNICIANS.items()
    ]
    await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))


async def cb_assign_tech(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_managers_group(update):
        await query.answer()
        return
    _, wo_id_str, user_id = query.data.split(":", 2)
    wo_id = int(wo_id_str)
    await query.answer()
    tech_name = next((n for n, uid in TECHNICIANS.items() if uid == user_id), user_id)
    try:
        await api_client.assign_work_order(wo_id, assigned_to=user_id)
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not assign: {e.detail}")
        return
    await notify_technicians(wo)
    await query.edit_message_text(f"🔧 Work Order #{wo_id} assigned to {tech_name}.")


# ── Handler registration ───────────────────────────────────────────────────────

def get_handlers() -> list:
    return [
        CommandHandler("pending", cmd_pending),
        CommandHandler("workorder", cmd_workorder),
        CommandHandler("summary", cmd_summary),
        CommandHandler("help", cmd_help),
        CallbackQueryHandler(cb_approve, pattern=r"^approve:\d+$"),
        CallbackQueryHandler(cb_dismiss, pattern=r"^dismiss:\d+$"),
        CallbackQueryHandler(cb_push_engineers, pattern=r"^push_engineers:\d+$"),
        CallbackQueryHandler(cb_assign_any, pattern=r"^assign_any:\d+$"),
        CallbackQueryHandler(cb_assign_pick, pattern=r"^assign_pick:\d+$"),
        CallbackQueryHandler(cb_assign_tech, pattern=r"^assign_tech:\d+:.+$"),
    ]
