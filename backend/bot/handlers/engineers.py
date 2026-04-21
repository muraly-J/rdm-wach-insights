from __future__ import annotations

"""
bot/handlers/engineers.py
──────────────────────────
Telegram handlers for the engineers group.

Commands:
  /review <id>   — fetch work order details + live FAIR scores
  /edit <id>     — guided edit conversation (title then description)
  /sendback <id> — send edited work order back to managers
  /query <ahu_id> — live AHU health data
  /level <N>     — overview of all AHUs on a level
  /help          — available commands

Inline callbacks:
  edit:{id}      — start edit flow
  sendback:{id}  — send back to manager
"""

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
from bot.config import ENGINEERS_CHAT_ID
from bot.push.notifier import parse_fair, notify_managers

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."
_ERR_NOT_FOUND = "❌ Work order #{} not found."

# ConversationHandler states
EDIT_TITLE = 0
EDIT_DESC = 1

# Context keys for edit state
_EDIT_WO_KEY = "editing_wo_id"
_EDIT_OLD_WO_KEY = "editing_wo_old"


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_review_detail(wo: dict[str, Any]) -> str:
    fair_str = parse_fair(wo.get("fair_snapshot"))
    lines = [
        f"*Work Order #{wo['id']} — Review*",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
        f"Title: {wo.get('title')}",
        f"Description: {wo.get('description') or '—'}",
        f"Status: {wo.get('status')}",
    ]
    if fair_str:
        lines.append(f"FAIR: {fair_str}")
    return "\n".join(lines)


def _format_edit_diff(
    old_wo: dict[str, Any],
    new_title: str | None,
    new_description: str | None,
) -> str:
    lines = ["*Changes to be sent back:*\n"]
    if new_title and new_title != old_wo.get("title"):
        lines += [f"Title: ~~{old_wo.get('title')}~~ → {new_title}"]
    else:
        lines += [f"Title: {old_wo.get('title')} (unchanged)"]
    if new_description is not None and new_description != old_wo.get("description"):
        lines += ["Description: updated"]
    else:
        lines += ["Description: (unchanged)"]
    return "\n".join(lines)


# ── Guards ─────────────────────────────────────────────────────────────────────

def _is_engineers_group(update: Update) -> bool:
    return update.effective_chat.id == ENGINEERS_CHAT_ID


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /review <id>")
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
    await update.message.reply_text(_format_review_detail(wo), parse_mode="Markdown")


async def cmd_sendback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /sendback <id>")
        return
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return
    try:
        await api_client.sendback_work_order(wo_id)
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await notify_managers(wo)
    await update.message.reply_text(f"✅ Work Order #{wo_id} sent back to managers for approval.")


async def cmd_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /query <ahu_id>  e.g. /query e0402")
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
    lines = [f"*AHU {ahu_id} — Live Status*"]
    if isinstance(data, dict):
        for key, val in list(data.items())[:8]:
            lines.append(f"{key}: {val}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /level <N>  e.g. /level 4")
        return
    try:
        level = int(context.args[0])
        if not 1 <= level <= 11:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Level must be 1–11.")
        return
    try:
        data = await api_client._get("/api/dashboard/ranking", params={"level": level, "range": "24h"})
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    lines = [f"*Level {level} — AHU Overview*\n"]
    items = data if isinstance(data, list) else data.get("rankings", data.get("ahus", []))
    for item in items[:10]:
        ahu = item.get("ahu_id", item.get("id", "?"))
        score = item.get("score", item.get("composite", "?"))
        try:
            score_int = int(float(score))
            icon = "🔴" if score_int < 40 else ("🟡" if score_int < 60 else "🟢")
        except (TypeError, ValueError):
            icon = "⚪"
            score_int = score
        lines.append(f"{icon} {ahu}: {score_int}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    text = (
        "*Engineers — Available Commands*\n\n"
        "/review <id> — Work order details + FAIR scores\n"
        "/edit <id> — Edit work order title and description\n"
        "/sendback <id> — Send back to managers\n"
        "/query <ahu_id> — Live AHU health data\n"
        "/level <N> — AHU overview for a level\n"
        "/help — This message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Edit ConversationHandler ───────────────────────────────────────────────────

async def cmd_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_engineers_group(update):
        return ConversationHandler.END
    if not context.args:
        await update.message.reply_text("Usage: /edit <id>")
        return ConversationHandler.END
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return ConversationHandler.END
    try:
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return ConversationHandler.END

    context.user_data[_EDIT_WO_KEY] = wo_id
    context.user_data[_EDIT_OLD_WO_KEY] = wo
    await update.message.reply_text(
        f"Editing Work Order #{wo_id}\n\n"
        f"Current title: *{wo.get('title')}*\n\n"
        f"Send the new title, or /cancel to abort.",
        parse_mode="Markdown",
    )
    return EDIT_TITLE


async def edit_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_title"] = update.message.text.strip()
    old_wo = context.user_data.get(_EDIT_OLD_WO_KEY, {})
    await update.message.reply_text(
        f"Title set to: *{context.user_data['new_title']}*\n\n"
        f"Current description: {old_wo.get('description') or '(none)'}\n\n"
        f"Send the new description, or /skip to keep it unchanged.",
        parse_mode="Markdown",
    )
    return EDIT_DESC


async def edit_receive_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_description"] = update.message.text.strip()
    return await _finish_edit(update, context)


async def edit_skip_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_description"] = None
    return await _finish_edit(update, context)


async def _finish_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    wo_id = context.user_data.get(_EDIT_WO_KEY)
    old_wo = context.user_data.get(_EDIT_OLD_WO_KEY, {})
    new_title = context.user_data.get("new_title")
    new_desc = context.user_data.get("new_description")
    try:
        await api_client.edit_work_order(wo_id, title=new_title, description=new_desc)
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return ConversationHandler.END
    diff = _format_edit_diff(old_wo, new_title, new_desc)
    await update.message.reply_text(
        f"✅ Work Order #{wo_id} updated.\n\n{diff}\n\n"
        f"Use /sendback {wo_id} to send it back to managers.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Edit cancelled.")
    return ConversationHandler.END


async def edit_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update and update.effective_chat else ENGINEERS_CHAT_ID
    await context.bot.send_message(chat_id=chat_id, text="Edit cancelled — timed out.")
    return ConversationHandler.END


# ── Inline callbacks ───────────────────────────────────────────────────────────

async def cb_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_engineers_group(update):
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    await query.message.reply_text(
        f"Use /edit {wo_id} to start editing Work Order #{wo_id}."
    )


async def cb_sendback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_engineers_group(update):
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.sendback_work_order(wo_id)
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await query.edit_message_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await query.edit_message_text(_ERR_UNAVAILABLE)
        return
    except Exception:
        await query.edit_message_text(_ERR_UNAVAILABLE)
        return
    await notify_managers(wo)
    await query.edit_message_text(f"✅ Work Order #{wo_id} sent back to managers.")


# ── Handler registration ───────────────────────────────────────────────────────

def get_handlers() -> list:
    edit_conv = ConversationHandler(
        entry_points=[CommandHandler("edit", cmd_edit_start)],
        states={
            EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_title)],
            EDIT_DESC: [
                CommandHandler("skip", edit_skip_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_desc),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, edit_timeout),
                CallbackQueryHandler(edit_timeout),
            ],
        },
        fallbacks=[CommandHandler("cancel", edit_cancel)],
        conversation_timeout=300,
    )
    return [
        CommandHandler("review", cmd_review),
        CommandHandler("sendback", cmd_sendback),
        CommandHandler("query", cmd_query),
        CommandHandler("level", cmd_level),
        CommandHandler("help", cmd_help),
        CallbackQueryHandler(cb_edit, pattern=r"^edit:\d+$"),
        CallbackQueryHandler(cb_sendback, pattern=r"^sendback:\d+$"),
        edit_conv,
    ]
