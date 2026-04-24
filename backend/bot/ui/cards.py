from __future__ import annotations

"""
bot/ui/cards.py
────────────────
Card text renderers for the WACH Insight Telegram bot.

Each function returns a plain string — no Telegram API calls are made here.
Handlers are responsible for passing the text to send_message / edit_message_text.
"""

PRIORITY_ICONS: dict[str, str] = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
    "not_set": "⚪",
}

STATUS_ICONS: dict[str, str] = {
    "draft": "📋",
    "pending_tech_review": "🔍",
    "open": "🟢",
    "in_progress": "🔵",
    "resolved": "✅",
    "closed": "🔒",
    "dismissed": "❌",
}


def draft_card(ticket_no: str, wo: dict) -> str:
    """📋 New Draft Ticket card text. Description is truncated to 200 chars."""
    description = (wo.get("description") or "")[:200]
    lines = [
        f"📋 New Draft Ticket — {ticket_no}",
        "",
        f"Subject: {wo.get('title', '—')}",
        f"Category: {wo.get('category', 'Uncategorised')}",
        f"AHU: {wo.get('ahu_id', '—')} · Level {wo.get('level', '—')}",
        "",
        description,
        "",
        "Created by: 🤖 Agent",
    ]
    return "\n".join(lines)


def claimed_card(ticket_no: str, wo: dict, username: str) -> str:
    """📋 Claimed card text with investigator username."""
    lines = [
        f"📋 Claimed — {ticket_no}",
        f"🔧 Investigating: @{username}",
        "",
        f"Subject: {wo.get('title', '—')}",
        f"Category: {wo.get('category', '—')}",
    ]
    return "\n".join(lines)


def approved_ticket_card(ticket_no: str, wo: dict, tech_username: str) -> str:
    """🎫 New Ticket card text for admin group."""
    priority = wo.get("priority", "not_set")
    priority_icon = PRIORITY_ICONS.get(priority, "⚪")
    lines = [
        f"🎫 New Ticket — {ticket_no}",
        "",
        f"Subject: {wo.get('title', '—')}",
        f"Category: {wo.get('category', '—')}",
        f"Priority: {priority_icon} {priority.replace('_', ' ').title()}",
        f"Status: 🟢 Open",
        f"AHU: {wo.get('ahu_id', '—')} · Level {wo.get('level', '—')}",
        "",
        f"Verified by: @{tech_username} (Technician)",
    ]
    return "\n".join(lines)


def status_change_card(
    ticket_no: str,
    wo: dict,
    tech_username: str,
    proposed_status: str,
    notes: str | None,
) -> str:
    """📝 Status Change Request card text."""
    current_status = wo.get("status", "open")
    current_icon = STATUS_ICONS.get(current_status, "📋")
    proposed_icon = STATUS_ICONS.get(proposed_status, "📋")

    lines = [
        f"📝 Status Change Request — {ticket_no}",
        "",
        f"Requested by: @{tech_username} (Technician)",
        f"Current: {current_icon} {current_status.replace('_', ' ').title()}",
        f"Proposed: {proposed_icon} {proposed_status.replace('_', ' ').title()}",
    ]
    if notes:
        lines.extend(["", f'Note: "{notes}"'])
    return "\n".join(lines)
