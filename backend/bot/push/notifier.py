from __future__ import annotations

"""
bot/push/notifier.py
─────────────────────
Formats and sends rich Telegram alerts with inline keyboards.
Called by action_tools.handle_send_notification() and directly by bot handlers.

No backend model imports — only telegram lib and os.environ.
"""

import json
import os
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

_MANAGERS_CHAT_ID: int = int(os.environ.get("MANAGERS_CHAT_ID", "0"))
_ENGINEERS_CHAT_ID: int = int(os.environ.get("ENGINEERS_CHAT_ID", "0"))
_TECHNICIANS_CHAT_ID: int = int(os.environ.get("TECHNICIANS_CHAT_ID", "0"))
_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")


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


def _format_engineer_review(wo: dict[str, Any]) -> str:
    fair_str = parse_fair(wo.get("fair_snapshot"))
    lines = [
        f"🔍 Review Requested — Work Order #{wo.get('id')}",
        "",
        f"Title: {wo.get('title')}",
        f"Description: {wo.get('description') or 'No description'}",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
    ]
    if fair_str:
        lines.append(f"FAIR snapshot: {fair_str}")
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


# ── Inline keyboards ───────────────────────────────────────────────────────────

def _manager_alert_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{wo_id}"),
            InlineKeyboardButton("❌ Dismiss", callback_data=f"dismiss:{wo_id}"),
            InlineKeyboardButton("🔍 Push to Engineers", callback_data=f"push_engineers:{wo_id}"),
        ]
    ])


def _assignment_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👷 Any Technician", callback_data=f"assign_any:{wo_id}"),
            InlineKeyboardButton("👤 Pick Specific", callback_data=f"assign_pick:{wo_id}"),
        ]
    ])


def _engineer_review_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Edit", callback_data=f"edit:{wo_id}"),
            InlineKeyboardButton("✅ Send Back to Manager", callback_data=f"sendback:{wo_id}"),
        ]
    ])


def _technician_assignment_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Start", callback_data=f"start:{wo_id}"),
            InlineKeyboardButton("✅ Done", callback_data=f"done:{wo_id}"),
        ]
    ])


# ── Public send functions ──────────────────────────────────────────────────────

async def notify_managers(wo: dict[str, Any], token: str | None = None) -> None:
    """Send work order alert to managers group with approve/dismiss/engineers buttons."""
    if not _MANAGERS_CHAT_ID:
        return
    bot = Bot(token=token or _BOT_TOKEN)
    await bot.send_message(
        chat_id=_MANAGERS_CHAT_ID,
        text=_format_manager_alert(wo),
        reply_markup=_manager_alert_keyboard(wo["id"]),
    )


async def notify_engineers(wo: dict[str, Any], token: str | None = None) -> None:
    """Send review request to engineers group with edit/sendback buttons."""
    if not _ENGINEERS_CHAT_ID:
        return
    bot = Bot(token=token or _BOT_TOKEN)
    await bot.send_message(
        chat_id=_ENGINEERS_CHAT_ID,
        text=_format_engineer_review(wo),
        reply_markup=_engineer_review_keyboard(wo["id"]),
    )


async def notify_technicians(
    wo: dict[str, Any],
    token: str | None = None,
    assigned_to: str | None = None,
) -> None:
    """Send assignment alert to technicians group with start/done buttons."""
    if not _TECHNICIANS_CHAT_ID:
        return
    bot = Bot(token=token or _BOT_TOKEN)
    await bot.send_message(
        chat_id=_TECHNICIANS_CHAT_ID,
        text=_format_technician_assignment(wo),
        reply_markup=_technician_assignment_keyboard(wo["id"]),
    )


async def notify_group(
    recipient: str,
    wo: dict[str, Any],
    token: str,
) -> None:
    """Route a group notification by recipient name."""
    if recipient == "manager":
        await notify_managers(wo, token=token)
    elif recipient == "engineers":
        await notify_engineers(wo, token=token)
    elif recipient == "technician":
        await notify_technicians(wo, token=token)
