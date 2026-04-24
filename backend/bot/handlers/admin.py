from __future__ import annotations

"""
bot/handlers/admin.py
─────────────────────
Telegram handlers for the Admin/Manager role.

Commands:
  /pending         — list tickets awaiting action
  /ticket <no>     — view ticket details
  /setstatus <no> <status>     — directly set ticket status
  /setpriority <no> <priority> — set ticket priority
  /summary         — building health snapshot
  /activity        — recent audit log
  /users           — list registered users
  /help            — available commands (handled in common.py)

Inline callbacks:
  set_priority:{wo_id}:{priority}  — set priority on ticket card
  set_status:{wo_id}:{status}      — set status on ticket card
  approve_change:{req_id}          — approve a status change request
  reject_change:{req_id}           — reject a status change request
"""

import re
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from bot import api_client
from bot.config import ADMIN_CHAT_ID, TECHNICIANS_CHAT_ID
from bot.identity.decorators import require_admin
from bot.identity.store import get_store
from core.logger import get_logger

logger = get_logger(__name__)

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."


# ── Helpers ────────────────────────────────────────────────────────────────────

_PRIORITY_ICONS = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
    "not_set": "⚪",
}

_STATUS_ICONS = {
    "draft": "📋",
    "pending_tech_review": "📋",
    "open": "🟢",
    "in_progress": "🔵",
    "resolved": "✅",
    "closed": "🔒",
    "dismissed": "❌",
}


def _format_ticket_detail(wo: dict[str, Any]) -> str:
    """Format a full ticket detail card."""
    ticket_no = wo.get("ticket_no") or f"#{wo['id']}"
    priority = wo.get("priority", "not_set")
    status = wo.get("status", "draft")
    p_icon = _PRIORITY_ICONS.get(priority, "⚪")
    s_icon = _STATUS_ICONS.get(status, "📋")
    created = str(wo.get("created_at", ""))[:16].replace("T", " ")
    updated = str(wo.get("updated_at", ""))[:16].replace("T", " ")

    lines = [
        f"🎫 *Ticket {ticket_no}*",
        "",
        f"Subject: {wo.get('title', '—')}",
        f"Category: {wo.get('category', '—')}",
        f"Priority: {p_icon} {priority.replace('_', ' ').title()}",
        f"Status: {s_icon} {status.replace('_', ' ').title()}",
        f"AHU: {wo.get('ahu_id', '—')} · Level {wo.get('level', '—')}",
        "",
        f"User: {wo.get('created_by', 'Agent')}",
        f"Created: {created}",
        f"Last Updated: {updated}",
    ]
    if wo.get("claimed_by"):
        lines.append(f"Claimed by: {wo.get('claimed_by')}")
    if wo.get("description"):
        desc = wo["description"][:200]
        lines.insert(7, f"\n{desc}")
    return "\n".join(lines)


def _ticket_admin_keyboard(wo: dict[str, Any]) -> InlineKeyboardMarkup:
    """Inline keyboard for admin ticket card."""
    wo_id = wo["id"]
    status = wo.get("status", "open")
    rows = []

    # Priority buttons (only if not set or changeable)
    rows.append([
        InlineKeyboardButton("🔴 High", callback_data=f"set_priority:{wo_id}:high"),
        InlineKeyboardButton("🟡 Medium", callback_data=f"set_priority:{wo_id}:medium"),
        InlineKeyboardButton("🟢 Low", callback_data=f"set_priority:{wo_id}:low"),
    ])

    # Status buttons based on current status
    status_row = []
    if status == "open":
        status_row.append(InlineKeyboardButton("▶️ In Progress", callback_data=f"set_status:{wo_id}:in_progress"))
        status_row.append(InlineKeyboardButton("🔒 Close", callback_data=f"set_status:{wo_id}:closed"))
    elif status == "in_progress":
        status_row.append(InlineKeyboardButton("✅ Resolved", callback_data=f"set_status:{wo_id}:resolved"))
        status_row.append(InlineKeyboardButton("↩ Reopen", callback_data=f"set_status:{wo_id}:open"))
    elif status == "resolved":
        status_row.append(InlineKeyboardButton("🔒 Close", callback_data=f"set_status:{wo_id}:closed"))
        status_row.append(InlineKeyboardButton("↩ Reopen", callback_data=f"set_status:{wo_id}:open"))
    if status_row:
        rows.append(status_row)

    return InlineKeyboardMarkup(rows)


# ── Command handlers ───────────────────────────────────────────────────────────

@require_admin
async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List work orders awaiting admin action."""
    try:
        drafts = await api_client.list_work_orders(status="open")
        in_progress = await api_client.list_work_orders(status="in_progress")
        orders = drafts + in_progress
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return

    if not orders:
        await update.message.reply_text("✅ No pending tickets.")
        return

    lines = ["*Pending Tickets*\n"]
    for wo in orders:
        ticket_no = wo.get("ticket_no") or f"#{wo['id']}"
        s_icon = _STATUS_ICONS.get(wo.get("status", ""), "📋")
        p_icon = _PRIORITY_ICONS.get(wo.get("priority", "not_set"), "⚪")
        lines.append(
            f"{s_icon} *{ticket_no}* {p_icon} — {wo.get('title', '—')}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_admin
async def cmd_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show full ticket details with inline action buttons."""
    if not context.args:
        await update.message.reply_text("Usage: /ticket <ticket_no or id>")
        return

    ticket_ref = context.args[0]
    try:
        # Try as numeric ID first
        wo_id = int(ticket_ref)
        wo = await api_client.get_work_order(wo_id)
    except ValueError:
        # Try as ticket number — need to search
        try:
            orders = await api_client.list_work_orders()
            wo = next((o for o in orders if o.get("ticket_no") == ticket_ref), None)
            if not wo:
                await update.message.reply_text(f"❌ Ticket {ticket_ref} not found.")
                return
        except Exception:
            await update.message.reply_text(_ERR_UNAVAILABLE)
            return
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(f"❌ Ticket {ticket_ref} not found.")
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return

    text = _format_ticket_detail(wo)
    keyboard = _ticket_admin_keyboard(wo)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


@require_admin
async def cmd_setstatus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Directly set ticket status (admin bypass — no approval needed)."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /setstatus <ticket_no or id> <status>\n"
            "Statuses: open, in_progress, resolved, closed"
        )
        return

    ticket_ref = context.args[0]
    new_status = context.args[1].lower()
    valid = {"open", "in_progress", "resolved", "closed"}
    if new_status not in valid:
        await update.message.reply_text(f"❌ Invalid status. Use: {', '.join(valid)}")
        return

    try:
        wo_id = int(ticket_ref)
    except ValueError:
        await update.message.reply_text("❌ Please use the numeric ID for now.")
        return

    try:
        result = await api_client._post(
            f"/api/work-orders/{wo_id}/status",
            json={"status": new_status},
        )
    except api_client.WACHAPIError as e:
        await update.message.reply_text(f"❌ {e.detail}")
        return
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return

    s_icon = _STATUS_ICONS.get(new_status, "📋")
    await update.message.reply_text(
        f"{s_icon} Ticket #{wo_id} status set to *{new_status.replace('_', ' ').title()}*.",
        parse_mode="Markdown",
    )

    # Audit
    store = get_store()
    store.log_audit(
        actor_id=str(update.effective_user.id),
        action="set_status",
        details={"work_order_id": wo_id, "new_status": new_status},
    )


@require_admin
async def cmd_setpriority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set ticket priority."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /setpriority <id> <priority>\n"
            "Priorities: low, medium, high"
        )
        return

    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return

    priority = context.args[1].lower()
    if priority not in ("low", "medium", "high"):
        await update.message.reply_text("❌ Priority must be: low, medium, high")
        return

    try:
        await api_client._patch(
            f"/api/work-orders/{wo_id}",
            json={"priority": priority},
        )
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return

    p_icon = _PRIORITY_ICONS.get(priority, "⚪")
    await update.message.reply_text(
        f"{p_icon} Ticket #{wo_id} priority set to *{priority.title()}*.",
        parse_mode="Markdown",
    )

    store = get_store()
    store.log_audit(
        actor_id=str(update.effective_user.id),
        action="set_priority",
        details={"work_order_id": wo_id, "priority": priority},
    )


@require_admin
async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Building health summary — reuses existing /summary logic."""
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


@require_admin
async def cmd_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent audit log entries."""
    store = get_store()
    entries = store.list_audit(limit=15)
    if not entries:
        await update.message.reply_text("No activity yet.")
        return

    lines = ["*Recent Activity*\n"]
    for e in entries:
        ts = str(e.get("created_at", ""))[:16].replace("T", " ")
        lines.append(f"• `{ts}` — {e['action']} by {e['actor_id']}")
        if e.get("ticket_no"):
            lines[-1] += f" ({e['ticket_no']})"
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_admin
async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all registered bot users."""
    store = get_store()
    users = store.list_users()
    if not users:
        await update.message.reply_text("No registered users.")
        return

    lines = ["*Registered Users*\n"]
    for u in users:
        status_icon = {"active": "🟢", "pending": "🟡", "disabled": "🔴"}.get(u.status, "⚪")
        at = f"@{u.telegram_username}" if u.telegram_username else f"ID:{u.user_id}"
        lines.append(f"{status_icon} {u.display_name} — {u.role} ({at})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Inline callback handlers ───────────────────────────────────────────────────

async def cb_set_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin taps a priority button on a ticket card."""
    query = update.callback_query
    parts = query.data.split(":")
    wo_id = int(parts[1])
    priority = parts[2]
    admin_id = str(query.from_user.id)

    # Verify admin
    store = get_store()
    admin_user = store.get_user(admin_id)
    if not admin_user or admin_user.role != "admin" or admin_user.status != "active":
        await query.answer("Not authorized.", show_alert=True)
        return

    await query.answer(f"Priority → {priority.title()}")

    try:
        await api_client._patch(f"/api/work-orders/{wo_id}", json={"priority": priority})
        wo = await api_client.get_work_order(wo_id)
    except Exception:
        await query.edit_message_text(f"❌ Could not set priority.")
        return

    # Re-render the card with updated priority
    text = _format_ticket_detail(wo)
    keyboard = _ticket_admin_keyboard(wo)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    store.log_audit(
        actor_id=admin_id,
        action="set_priority",
        details={"work_order_id": wo_id, "priority": priority},
    )


async def cb_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin taps a status button on a ticket card."""
    query = update.callback_query
    parts = query.data.split(":")
    wo_id = int(parts[1])
    new_status = parts[2]
    admin_id = str(query.from_user.id)

    store = get_store()
    admin_user = store.get_user(admin_id)
    if not admin_user or admin_user.role != "admin" or admin_user.status != "active":
        await query.answer("Not authorized.", show_alert=True)
        return

    s_icon = _STATUS_ICONS.get(new_status, "📋")
    await query.answer(f"Status → {new_status.replace('_', ' ').title()}")

    try:
        await api_client._post(
            f"/api/work-orders/{wo_id}/status",
            json={"status": new_status},
        )
        wo = await api_client.get_work_order(wo_id)
    except Exception:
        await query.edit_message_text(f"❌ Could not set status.")
        return

    text = _format_ticket_detail(wo)
    keyboard = _ticket_admin_keyboard(wo)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    store.log_audit(
        actor_id=admin_id,
        action="set_status",
        details={"work_order_id": wo_id, "new_status": new_status},
    )

    # Notify technicians group of status change
    if TECHNICIANS_CHAT_ID:
        ticket_no = wo.get("ticket_no") or f"#{wo_id}"
        try:
            await context.bot.send_message(
                chat_id=TECHNICIANS_CHAT_ID,
                text=(
                    f"{s_icon} *Status Update* — {ticket_no}\n\n"
                    f"Status changed to *{new_status.replace('_', ' ').title()}*\n"
                    f"by @{admin_user.telegram_username or admin_user.display_name}"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify technicians of status change: {e}")


async def cb_approve_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin approves a status change request from a technician."""
    query = update.callback_query
    req_id = int(query.data.split(":")[1])
    admin_id = str(query.from_user.id)

    store = get_store()
    admin_user = store.get_user(admin_id)
    if not admin_user or admin_user.role != "admin" or admin_user.status != "active":
        await query.answer("Not authorized.", show_alert=True)
        return

    # Get the request
    from core.agentdb import AgentDB
    import core.agentdb as agentdb_module
    if agentdb_module._db_instance is None:
        agentdb_module._db_instance = AgentDB()
    db = agentdb_module._db_instance

    req = db.get_status_change_request(req_id)
    if not req:
        await query.answer("Request not found.", show_alert=True)
        return
    if req.get("decision"):
        await query.answer(f"Already {req['decision']}.", show_alert=True)
        return

    # Apply the status change
    success = db.decide_status_change(req_id, "approved", admin_id)
    if not success:
        await query.answer("Could not approve.", show_alert=True)
        return

    # Actually update the work order status
    db.update_work_order(
        req["work_order_id"],
        status=req["proposed_status"],
    )

    await query.answer("✅ Approved!")
    admin_name = admin_user.telegram_username or admin_user.display_name
    await query.edit_message_text(
        f"✅ *Status Change Approved*\n\n"
        f"Ticket: {req['ticket_no']}\n"
        f"{req['current_status']} → *{req['proposed_status'].replace('_', ' ').title()}*\n"
        f"Approved by @{admin_name}",
        parse_mode="Markdown",
    )

    store.log_audit(
        actor_id=admin_id,
        action="approve_status_change",
        ticket_no=req["ticket_no"],
        details={"request_id": req_id, "new_status": req["proposed_status"]},
    )

    # Notify technicians
    if TECHNICIANS_CHAT_ID:
        s_icon = _STATUS_ICONS.get(req["proposed_status"], "📋")
        try:
            await context.bot.send_message(
                chat_id=TECHNICIANS_CHAT_ID,
                text=(
                    f"{s_icon} *Status Update* — {req['ticket_no']}\n\n"
                    f"Status: *{req['proposed_status'].replace('_', ' ').title()}*\n"
                    f"Approved by @{admin_name}"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify technicians: {e}")


async def cb_reject_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin rejects a status change request."""
    query = update.callback_query
    req_id = int(query.data.split(":")[1])
    admin_id = str(query.from_user.id)

    store = get_store()
    admin_user = store.get_user(admin_id)
    if not admin_user or admin_user.role != "admin" or admin_user.status != "active":
        await query.answer("Not authorized.", show_alert=True)
        return

    from core.agentdb import AgentDB
    import core.agentdb as agentdb_module
    if agentdb_module._db_instance is None:
        agentdb_module._db_instance = AgentDB()
    db = agentdb_module._db_instance

    req = db.get_status_change_request(req_id)
    if not req:
        await query.answer("Request not found.", show_alert=True)
        return
    if req.get("decision"):
        await query.answer(f"Already {req['decision']}.", show_alert=True)
        return

    success = db.decide_status_change(req_id, "rejected", admin_id)
    if not success:
        await query.answer("Could not reject.", show_alert=True)
        return

    await query.answer("❌ Rejected.")
    admin_name = admin_user.telegram_username or admin_user.display_name
    await query.edit_message_text(
        f"❌ *Status Change Rejected*\n\n"
        f"Ticket: {req['ticket_no']}\n"
        f"Proposed: {req['proposed_status'].replace('_', ' ').title()}\n"
        f"Rejected by @{admin_name}",
        parse_mode="Markdown",
    )

    store.log_audit(
        actor_id=admin_id,
        action="reject_status_change",
        ticket_no=req["ticket_no"],
        details={"request_id": req_id},
    )

    # DM the requesting technician
    try:
        await context.bot.send_message(
            chat_id=int(req["requested_by"]),
            text=(
                f"❌ Your status change for *{req['ticket_no']}* was rejected by @{admin_name}.\n"
                f"Proposed: {req['proposed_status'].replace('_', ' ').title()}"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Could not DM technician about rejection: {e}")


# ── Handler registration ───────────────────────────────────────────────────────

def get_handlers() -> list:
    return [
        CommandHandler("pending", cmd_pending),
        CommandHandler("ticket", cmd_ticket),
        CommandHandler("setstatus", cmd_setstatus),
        CommandHandler("setpriority", cmd_setpriority),
        CommandHandler("summary", cmd_summary),
        CommandHandler("activity", cmd_activity),
        CommandHandler("users", cmd_users),
        # Keep old /workorder as alias for /ticket
        CommandHandler("workorder", cmd_ticket),
        # Inline callbacks
        CallbackQueryHandler(cb_set_priority, pattern=r"^set_priority:\d+:(high|medium|low)$"),
        CallbackQueryHandler(cb_set_status, pattern=r"^set_status:\d+:\w+$"),
        CallbackQueryHandler(cb_approve_change, pattern=r"^approve_change:\d+$"),
        CallbackQueryHandler(cb_reject_change, pattern=r"^reject_change:\d+$"),
    ]
