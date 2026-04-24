from __future__ import annotations

"""
bot/push/notifier.py
─────────────────────
Formats and sends rich Telegram alerts with inline keyboards.
Called by action_tools.handle_send_notification() and directly by bot handlers.

2-role model: technicians + admins only (engineer role removed).
No backend model imports — only telegram lib and bot.config.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import ADMIN_CHAT_ID, BOT_TOKEN, TECHNICIANS_CHAT_ID

logger = logging.getLogger(__name__)

_ADMIN_CHAT_ID: int = ADMIN_CHAT_ID
_TECHNICIANS_CHAT_ID: int = TECHNICIANS_CHAT_ID
_BOT_TOKEN: str = BOT_TOKEN


# ── Message formatters ─────────────────────────────────────────────────────────

def parse_fair(fair_snapshot: str | dict | None) -> str:
    """Return 'F:42 A:38 I:61 R:55 · Composite: 49' or empty string."""
    if not fair_snapshot:
        return ""
    try:
        data = json.loads(fair_snapshot) if isinstance(fair_snapshot, str) else fair_snapshot
        f = data.get("F", data.get("f"))
        a = data.get("A", data.get("a"))
        i = data.get("I", data.get("i"))
        r = data.get("R", data.get("r"))
        c = data.get("composite")
        if any(v is None for v in (f, a, i, r, c)):
            return ""
        f, a, i, r, c = int(f), int(a), int(i), int(r), int(c)
        return f"F:{f} A:{a} I:{i} R:{r} · Composite: {c}"
    except Exception:
        return ""


def _format_manager_alert(wo: dict[str, Any]) -> str:
    severity_icon = "🚨" if str(wo.get("severity", "")).lower() == "critical" else "⚠️"
    fair_str = parse_fair(wo.get("fair_snapshot"))
    created = str(wo.get("created_at", ""))[:16].replace("T", " ")
    lines = [
        f"{severity_icon} {wo.get('severity', 'ALERT').upper()} — Level {wo.get('level')} · {wo.get('ahu_id')}",
        "",
        f"Title: {wo.get('title')}",
    ]
    if fair_str:
        lines.append(f"FAIR: {fair_str}")
    lines += ["", f"Created by: Agent · {created}"]
    return "\n".join(lines)


def _format_technician_assignment(wo: dict[str, Any]) -> str:
    lines = [
        f"🔧 New Work Order Assigned — #{wo.get('id')}",
        "",
        f"Title: {wo.get('title')}",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
        "Approved by: Manager",
    ]
    return "\n".join(lines)


def _format_draft_card(ticket_no: str, wo: dict[str, Any]) -> str:
    """Format the 'New Draft Ticket' card sent to technicians when a draft is created."""
    description = (wo.get("description") or "")[:200]
    created_at = wo.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                # Parse ISO string; strip timezone for a simple relative display
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                dt = created_at
            now = datetime.now(tz=timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = now - dt
            minutes = int(delta.total_seconds() // 60)
            if minutes < 1:
                created_relative = "just now"
            elif minutes < 60:
                created_relative = f"{minutes}m ago"
            else:
                hours = minutes // 60
                created_relative = f"{hours}h ago"
        except Exception:
            created_relative = str(created_at)[:16].replace("T", " ")
    else:
        created_relative = "unknown"

    lines = [
        f"📋 New Draft Ticket — {ticket_no}",
        "",
        f"Subject: {wo.get('title')}",
        f"Category: {wo.get('category', 'Uncategorised')}",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
        "",
        description,
        "",
        f"Created by: 🤖 Agent · {created_relative}",
    ]
    return "\n".join(lines)


# ── Inline keyboards ───────────────────────────────────────────────────────────

def _manager_alert_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{wo_id}"),
            InlineKeyboardButton("❌ Dismiss", callback_data=f"dismiss:{wo_id}"),
        ]
    ])


def _assignment_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👷 Any Technician", callback_data=f"assign_any:{wo_id}"),
            InlineKeyboardButton("👤 Pick Specific", callback_data=f"assign_pick:{wo_id}"),
        ]
    ])


def _technician_assignment_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Start", callback_data=f"start:{wo_id}"),
            InlineKeyboardButton("✅ Done", callback_data=f"done:{wo_id}"),
        ]
    ])


def _draft_card_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🙋 I'll Investigate", callback_data=f"claim_ticket:{wo_id}"),
        ]
    ])


# ── Public send functions ──────────────────────────────────────────────────────

async def notify_admins(
    wo: dict[str, Any],
    token: str | None = None,
    bot: Bot | None = None,
) -> None:
    """Send work order alert to admins group with approve/dismiss buttons."""
    if not _ADMIN_CHAT_ID:
        return
    effective_bot = bot if bot is not None else Bot(token=token or _BOT_TOKEN)
    try:
        await effective_bot.send_message(
            chat_id=_ADMIN_CHAT_ID,
            text=_format_manager_alert(wo),
            reply_markup=_manager_alert_keyboard(wo["id"]),
        )
    except Exception as e:
        logger.warning(f"notify_admins: failed to send message to admins: {e}")


async def notify_technicians(
    wo: dict[str, Any],
    token: str | None = None,
    bot: Bot | None = None,
) -> None:
    """Send assignment alert to technicians group with start/done buttons."""
    if not _TECHNICIANS_CHAT_ID:
        return
    effective_bot = bot if bot is not None else Bot(token=token or _BOT_TOKEN)
    try:
        await effective_bot.send_message(
            chat_id=_TECHNICIANS_CHAT_ID,
            text=_format_technician_assignment(wo),
            reply_markup=_technician_assignment_keyboard(wo["id"]),
        )
    except Exception as e:
        logger.warning(f"notify_technicians: failed to send message to technicians: {e}")


async def send_draft_card(
    bot: Bot | None,
    ticket_no: str,
    wo: dict[str, Any],
    token: str | None = None,
) -> None:
    """Send the '📋 New Draft Ticket' card to TECHNICIANS_CHAT_ID with a claim button."""
    if not _TECHNICIANS_CHAT_ID:
        return
    effective_bot = bot if bot is not None else Bot(token=token or _BOT_TOKEN)
    try:
        await effective_bot.send_message(
            chat_id=_TECHNICIANS_CHAT_ID,
            text=_format_draft_card(ticket_no, wo),
            reply_markup=_draft_card_keyboard(wo["id"]),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Could not send draft card: {e}")


async def emit(event: str, wo: dict[str, Any], bot: Bot | None = None, token: str | None = None) -> None:
    """
    Dispatcher: routes a work-order lifecycle event to the right groups.

    Events:
      "draft_created"   → send_draft_card to technicians
      "ticket_opened"   → notify_admins
      "status_changed"  → notify_admins + notify_technicians
    """
    effective_token = token or _BOT_TOKEN

    if event == "draft_created":
        if bot is None:
            bot = Bot(token=effective_token)
        ticket_no = f"#{wo.get('id', '?')}"
        await send_draft_card(bot, ticket_no, wo)

    elif event == "ticket_opened":
        await notify_admins(wo, token=effective_token, bot=bot)

    elif event == "status_changed":
        await notify_admins(wo, token=effective_token, bot=bot)
        await notify_technicians(wo, token=effective_token, bot=bot)
