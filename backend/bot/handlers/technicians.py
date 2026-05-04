from __future__ import annotations

"""
bot/handlers/technicians.py
────────────────────────────
Telegram handlers for the Technician role (refactored for 2-role model).

Flow 1 callbacks (Ticket Generation):
  claim_ticket:{id}           — technician claims a draft ticket
  edit_review:{id}            — start edit & review ConversationHandler
  approve_ticket:{id}         — approve and send to admin
  reject_ticket:{id}          — reject the ticket
  confirm_reject:{id}         — confirm rejection
  cancel_reject:{id}          — cancel rejection

Commands:
  /mywork              — list claimed/active tickets
  /update <no> <status> — propose a status change
  /status <ahu_id>     — AHU health data
  /help                — (handled in common.py)
"""

import re

from core.logger import get_logger
from rag.retriever import Retriever
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot import api_client
from bot.config import ADMIN_CHAT_ID, TICKET_CATEGORIES
from bot.identity.decorators import require_role
from bot.identity.store import get_store

logger = get_logger(__name__)

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."

# ConversationHandler states for edit/review
EDIT_SUBJECT, EDIT_CATEGORY, EDIT_DESC, EDIT_ATTACH, EDIT_PREVIEW = range(5)
_EDIT_WO_KEY = "edit_wo_id"
_EDIT_DATA_KEY = "edit_data"

# ConversationHandler states for status update
UPDATE_NOTE = 0
_UPDATE_WO_KEY = "update_wo_id"
_UPDATE_STATUS_KEY = "update_new_status"


# ── Helpers ──────────────────────────────────────────────────────────────

def _get_db():
    import core.agentdb as m
    if m._db_instance is None:
        from core.agentdb import AgentDB
        m._db_instance = AgentDB()
    return m._db_instance


def _get_retriever() -> Retriever:
    return Retriever()


# ── Claim callback ───────────────────────────────────────────────────────

async def cb_claim_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Technician taps [🙋 I'll Investigate] on a draft ticket."""
    query = update.callback_query
    wo_id = int(query.data.split(":")[1])
    user_id = str(query.from_user.id)

    store = get_store()
    user = store.get_user(user_id)
    if not user or user.status != "active":
        await query.answer("Not authorized. /register first.", show_alert=True)
        return

    db = _get_db()
    success = db.claim_work_order(wo_id, claimed_by=user_id)

    if not success:
        wo = db.get_work_order(wo_id)
        claimer = wo.get("claimed_by", "someone") if wo else "someone"
        await query.answer(f"📌 Already claimed by {claimer}", show_alert=True)
        return

    await query.answer("✅ Claimed!")

    # Update the card in-place
    wo = db.get_work_order(wo_id)
    ticket_no = wo.get("ticket_no") or f"#{wo_id}"
    username = query.from_user.username or user.display_name

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit & Review", callback_data=f"edit_review:{wo_id}"),
            InlineKeyboardButton("❌ Reject Ticket", callback_data=f"reject_ticket:{wo_id}"),
        ]
    ])
    await query.edit_message_text(
        f"📋 *Claimed — {ticket_no}*\n"
        f"🔧 Investigating: @{username}\n\n"
        f"Subject: {wo.get('title', '—')}\n"
        f"Category: {wo.get('category', '—')}",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

    # Transition status
    db.update_work_order(wo_id, status="pending_tech_review")

    store.log_audit(
        actor_id=user_id,
        action="claim_ticket",
        ticket_no=ticket_no,
        details={"work_order_id": wo_id},
    )


# ── Edit & Review ConversationHandler ────────────────────────────────────

async def cb_edit_review_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the edit/review flow from inline button."""
    query = update.callback_query
    wo_id = int(query.data.split(":")[1])
    user_id = str(query.from_user.id)

    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        await query.answer("Ticket not found.", show_alert=True)
        return ConversationHandler.END
    if wo.get("claimed_by") != user_id:
        await query.answer("Only the claimer can edit.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    context.user_data[_EDIT_WO_KEY] = wo_id
    context.user_data[_EDIT_DATA_KEY] = {
        "title": wo.get("title"),
        "category": wo.get("category"),
        "description": wo.get("description"),
    }

    await query.message.reply_text(
        f"✏️ *Editing Ticket #{wo_id}*\n\n"
        f"Current Subject: _{wo.get('title', '—')}_\n\n"
        f"Send new Subject, or /skip to keep it.",
        parse_mode="Markdown",
    )
    return EDIT_SUBJECT


async def edit_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_EDIT_DATA_KEY]["title"] = update.message.text.strip()
    cats = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(TICKET_CATEGORIES))
    await update.message.reply_text(
        f"Current Category: _{context.user_data[_EDIT_DATA_KEY].get('category', '—')}_\n\n"
        f"Pick a category number:\n{cats}\n\nOr /skip to keep it.",
        parse_mode="Markdown",
    )
    return EDIT_CATEGORY


async def edit_skip_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cats = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(TICKET_CATEGORIES))
    await update.message.reply_text(
        f"Current Category: _{context.user_data[_EDIT_DATA_KEY].get('category', '—')}_\n\n"
        f"Pick a category number:\n{cats}\n\nOr /skip to keep it.",
        parse_mode="Markdown",
    )
    return EDIT_CATEGORY


async def edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        idx = int(text) - 1
        if 0 <= idx < len(TICKET_CATEGORIES):
            context.user_data[_EDIT_DATA_KEY]["category"] = TICKET_CATEGORIES[idx]
        else:
            context.user_data[_EDIT_DATA_KEY]["category"] = text
    except ValueError:
        context.user_data[_EDIT_DATA_KEY]["category"] = text

    desc = context.user_data[_EDIT_DATA_KEY].get("description", "—") or "—"
    short = desc[:150] + "..." if len(desc) > 150 else desc
    await update.message.reply_text(
        f"Current Description:\n_{short}_\n\nSend new description, or /skip.",
        parse_mode="Markdown",
    )
    return EDIT_DESC


async def edit_skip_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    desc = context.user_data[_EDIT_DATA_KEY].get("description", "—") or "—"
    short = desc[:150] + "..." if len(desc) > 150 else desc
    await update.message.reply_text(
        f"Current Description:\n_{short}_\n\nSend new description, or /skip.",
        parse_mode="Markdown",
    )
    return EDIT_DESC


async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_EDIT_DATA_KEY]["description"] = update.message.text.strip()
    await update.message.reply_text("📎 Attach a photo/document, or /skip.")
    return EDIT_ATTACH


async def edit_skip_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📎 Attach a photo/document, or /skip.")
    return EDIT_ATTACH


async def edit_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo or document attachment."""
    if update.message.photo:
        file = update.message.photo[-1]
        context.user_data[_EDIT_DATA_KEY]["attachment"] = {
            "file_id": file.file_id, "type": "photo",
        }
    elif update.message.document:
        doc = update.message.document
        context.user_data[_EDIT_DATA_KEY]["attachment"] = {
            "file_id": doc.file_id, "type": "document",
            "filename": doc.file_name, "mime": doc.mime_type,
        }
    return await _show_preview(update, context)


async def edit_skip_attach(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _show_preview(update, context)


async def _show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data[_EDIT_DATA_KEY]
    wo_id = context.user_data[_EDIT_WO_KEY]
    att = data.get("attachment")
    att_str = f"📎 {att.get('filename', 'photo')}" if att else "None"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Send to Admin", callback_data=f"approve_ticket:{wo_id}"),
            InlineKeyboardButton("↩ Edit Again", callback_data=f"edit_review:{wo_id}"),
        ]
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        f"📋 *Review Preview*\n\n"
        f"Subject: {data.get('title', '—')}\n"
        f"Category: {data.get('category', '—')}\n"
        f"Description: {(data.get('description') or '—')[:100]}\n"
        f"Attachment: {att_str}\n\n"
        f"Tap ✅ to approve and send to Admin.",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Edit cancelled.")
    return ConversationHandler.END


# ── Approve ticket callback ──────────────────────────────────────────────

async def cb_approve_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Technician approves the ticket and sends it to admin."""
    query = update.callback_query
    wo_id = int(query.data.split(":")[1])
    user_id = str(query.from_user.id)

    store = get_store()
    user = store.get_user(user_id)
    db = _get_db()
    wo = db.get_work_order(wo_id)

    if not wo or wo.get("claimed_by") != user_id:
        await query.answer("Only the claimer can approve.", show_alert=True)
        return

    # Apply edits if stored in user_data
    edit_data = context.user_data.get(_EDIT_DATA_KEY, {})
    if edit_data:
        att = edit_data.pop("attachment", None)
        attachments = [att] if att else None
        db.edit_work_order_fields(
            wo_id,
            title=edit_data.get("title"),
            description=edit_data.get("description"),
            category=edit_data.get("category"),
            attachments=attachments,
        )

    # Transition: pending_tech_review → open
    db.update_work_order(wo_id, status="open", approved_by=user_id)
    wo = db.get_work_order(wo_id)
    ticket_no = wo.get("ticket_no") or f"#{wo_id}"

    await query.answer("✅ Sent to Admin!")
    username = query.from_user.username or user.display_name

    await query.edit_message_text(
        f"✅ *Ticket Approved* — {ticket_no}\n"
        f"Sent to Admin by @{username}",
        parse_mode="Markdown",
    )

    store.log_audit(
        actor_id=user_id, action="approve_ticket",
        ticket_no=ticket_no, details={"work_order_id": wo_id},
    )

    # Post to admin group
    if ADMIN_CHAT_ID:
        p_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            wo.get("priority", "not_set"), "⚪"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔴 High", callback_data=f"set_priority:{wo_id}:high"),
                InlineKeyboardButton("🟡 Medium", callback_data=f"set_priority:{wo_id}:medium"),
                InlineKeyboardButton("🟢 Low", callback_data=f"set_priority:{wo_id}:low"),
            ],
            [
                InlineKeyboardButton("▶️ In Progress", callback_data=f"set_status:{wo_id}:in_progress"),
                InlineKeyboardButton("🔒 Close", callback_data=f"set_status:{wo_id}:closed"),
            ],
        ])
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"🎫 *New Ticket — {ticket_no}*\n\n"
                    f"Subject: {wo.get('title', '—')}\n"
                    f"Category: {wo.get('category', '—')}\n"
                    f"Priority: {p_icon} Not Set\n"
                    f"Status: 🟢 Open\n"
                    f"AHU: {wo.get('ahu_id', '—')} · Level {wo.get('level', '—')}\n\n"
                    f"Verified by: @{username} (Technician)"
                ),
                reply_markup=kb,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify admin group: {e}")


# ── Reject ticket ────────────────────────────────────────────────────────

async def cb_reject_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Reject", callback_data=f"confirm_reject:{wo_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_reject:{wo_id}"),
        ]
    ])
    ticket_no = f"#{wo_id}"
    await query.edit_message_text(
        f"⚠️ Reject {ticket_no}? This cannot be undone.",
        reply_markup=kb,
    )


async def cb_confirm_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    wo_id = int(query.data.split(":")[1])
    user_id = str(query.from_user.id)

    db = _get_db()
    db.update_work_order(wo_id, status="dismissed")
    wo = db.get_work_order(wo_id)
    ticket_no = wo.get("ticket_no") or f"#{wo_id}"
    username = query.from_user.username or "technician"

    await query.answer("❌ Rejected.")
    await query.edit_message_text(
        f"❌ *{ticket_no}* dismissed by @{username}",
        parse_mode="Markdown",
    )

    store = get_store()
    store.log_audit(
        actor_id=user_id, action="reject_ticket",
        ticket_no=ticket_no, details={"work_order_id": wo_id},
    )


async def cb_cancel_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    wo_id = int(query.data.split(":")[1])
    await query.answer("Cancelled.")

    db = _get_db()
    wo = db.get_work_order(wo_id)
    ticket_no = wo.get("ticket_no") or f"#{wo_id}"
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit & Review", callback_data=f"edit_review:{wo_id}"),
            InlineKeyboardButton("❌ Reject Ticket", callback_data=f"reject_ticket:{wo_id}"),
        ]
    ])
    await query.edit_message_text(
        f"📋 *Claimed — {ticket_no}*\n"
        f"Subject: {wo.get('title', '—')}\n"
        f"Category: {wo.get('category', '—')}",
        reply_markup=kb,
        parse_mode="Markdown",
    )


# ── Commands ─────────────────────────────────────────────────────────────

@require_role("technician")
async def cmd_mywork(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List tickets claimed by or assigned to this technician."""
    user_id = str(update.effective_user.id)
    try:
        all_orders = await api_client.list_work_orders()
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return

    my = [o for o in all_orders if o.get("claimed_by") == user_id or o.get("assigned_to") == user_id]
    if not my:
        await update.message.reply_text("✅ No tickets assigned to you.")
        return

    lines = ["*Your Tickets*\n"]
    for wo in my:
        tno = wo.get("ticket_no") or f"#{wo['id']}"
        s = wo.get("status", "?")
        lines.append(f"• *{tno}* — {wo.get('title', '—')} [{s}]")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_role("technician")
async def cmd_update_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Propose a status change: /update <id> <status>"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /update <ticket_id> <new_status>\n"
            "Statuses: resolved"
        )
        return ConversationHandler.END
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return ConversationHandler.END

    new_status = context.args[1].lower()
    if new_status not in ("resolved",):
        await update.message.reply_text("❌ Technicians can propose: resolved")
        return ConversationHandler.END

    context.user_data[_UPDATE_WO_KEY] = wo_id
    context.user_data[_UPDATE_STATUS_KEY] = new_status
    await update.message.reply_text(
        f"Proposing status change to *{new_status}* for #{wo_id}.\n\n"
        f"Add a note describing what was done (or /skip):",
        parse_mode="Markdown",
    )
    return UPDATE_NOTE


async def update_receive_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _finish_update(update, context, notes=update.message.text.strip())


async def update_skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _finish_update(update, context, notes=None)


async def _finish_update(update: Update, context: ContextTypes.DEFAULT_TYPE, notes: str | None) -> int:
    wo_id = context.user_data.get(_UPDATE_WO_KEY)
    new_status = context.user_data.get(_UPDATE_STATUS_KEY)
    user_id = str(update.effective_user.id)

    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        await update.message.reply_text(f"❌ Ticket #{wo_id} not found.")
        return ConversationHandler.END

    ticket_no = wo.get("ticket_no") or f"#{wo_id}"
    req_id = db.create_status_change_request(
        ticket_no=ticket_no, work_order_id=wo_id,
        requested_by=user_id, current_status=wo["status"],
        proposed_status=new_status, notes=notes,
    )

    await update.message.reply_text(
        f"📝 Status change request submitted for *{ticket_no}*.\n"
        f"Awaiting admin approval.",
        parse_mode="Markdown",
    )

    store = get_store()
    user = store.get_user(user_id)
    username = user.display_name if user else user_id

    store.log_audit(
        actor_id=user_id, action="request_status_change",
        ticket_no=ticket_no, details={"proposed": new_status, "notes": notes},
    )

    # Post to admin group
    if ADMIN_CHAT_ID:
        s_icons = {"in_progress": "🔵", "resolved": "✅", "open": "🟢"}
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_change:{req_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_change:{req_id}"),
            ]
        ])
        note_line = f'\nNote: "{notes}"' if notes else ""
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"📝 *Status Change Request* — {ticket_no}\n\n"
                    f"Requested by: @{username} (Technician)\n"
                    f"Current: {s_icons.get(wo['status'], '📋')} {wo['status'].replace('_',' ').title()}\n"
                    f"Proposed: {s_icons.get(new_status, '📋')} {new_status.replace('_',' ').title()}"
                    f"{note_line}"
                ),
                reply_markup=kb,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify admin of status change request: {e}")

    return ConversationHandler.END


async def update_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Status update cancelled.")
    return ConversationHandler.END


async def solve_handler(update, context) -> None:
    """/solve <ticket_no> — query RAG for fix suggestions."""
    text = (update.message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Usage: /solve <ticket_no>  e.g. /solve TCK-005"
        )
        return

    ticket_no = parts[1].strip().upper()
    db = _get_db()
    wo = db.get_work_order_by_ticket_no(ticket_no)

    if not wo:
        await update.message.reply_text(f"❌ Ticket {ticket_no} not found.")
        return

    query = f"{wo['title']}. {wo.get('description', '')}"
    retriever = _get_retriever()
    docs = retriever.query(query, top_k=3)

    if not docs:
        await update.message.reply_text(
            f"🔍 *{ticket_no}* — No relevant documentation found.\n\n"
            f"Issue: {wo['title']}",
            parse_mode="Markdown",
        )
        return

    context_text = "\n\n".join(f"• {d}" for d in docs)
    reply = (
        f"🧠 *Suggested Fix for {ticket_no}*\n"
        f"AHU: `{wo['ahu_id']}` | Severity: {wo.get('severity', 'Unknown')}\n\n"
        f"*Issue:* {wo['title']}\n\n"
        f"*Relevant guidance:*\n{context_text}"
    )
    await update.message.reply_text(reply, parse_mode="Markdown")


@require_role("technician")
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """AHU health status."""
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
            await update.message.reply_text(f"❌ No data for {ahu_id}.")
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    lines = [f"*AHU {ahu_id} — Status*\n"]
    for key, val in list(data.items())[:10]:
        lines.append(f"{key}: {val}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Handler registration ─────────────────────────────────────────────────

def get_handlers() -> list:
    edit_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_edit_review_start, pattern=r"^edit_review:\d+$"),
        ],
        states={
            EDIT_SUBJECT: [
                CommandHandler("skip", edit_skip_subject),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_subject),
            ],
            EDIT_CATEGORY: [
                CommandHandler("skip", edit_skip_category),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_category),
            ],
            EDIT_DESC: [
                CommandHandler("skip", edit_skip_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description),
            ],
            EDIT_ATTACH: [
                CommandHandler("skip", edit_skip_attach),
                MessageHandler(filters.PHOTO | filters.Document.ALL, edit_attachment),
            ],
        },
        fallbacks=[CommandHandler("cancel", edit_cancel)],
        conversation_timeout=300,
        per_message=False,
    )

    update_conv = ConversationHandler(
        entry_points=[CommandHandler("update", cmd_update_start)],
        states={
            UPDATE_NOTE: [
                CommandHandler("skip", update_skip_note),
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_receive_note),
            ],
        },
        fallbacks=[CommandHandler("cancel", update_cancel)],
        conversation_timeout=300,
    )

    return [
        edit_conv,
        update_conv,
        CommandHandler("mywork", cmd_mywork),
        CommandHandler("status", cmd_status),
        CommandHandler("solve", solve_handler),
        CallbackQueryHandler(cb_claim_ticket, pattern=r"^claim_ticket:\d+$"),
        CallbackQueryHandler(cb_approve_ticket, pattern=r"^approve_ticket:\d+$"),
        CallbackQueryHandler(cb_reject_ticket, pattern=r"^reject_ticket:\d+$"),
        CallbackQueryHandler(cb_confirm_reject, pattern=r"^confirm_reject:\d+$"),
        CallbackQueryHandler(cb_cancel_reject, pattern=r"^cancel_reject:\d+$"),
    ]
