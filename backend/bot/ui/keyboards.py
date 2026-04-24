from __future__ import annotations

"""
bot/ui/keyboards.py
────────────────────
Inline keyboard factories for the WACH Insight Telegram bot.

Each function returns a ready-to-use InlineKeyboardMarkup so that
handlers stay free of keyboard construction logic.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def draft_ticket_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    """[🙋 I'll Investigate] button for draft ticket cards."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🙋 I'll Investigate", callback_data=f"claim_ticket:{wo_id}"),
        ]
    ])


def claimed_ticket_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    """[✏️ Edit & Review] [❌ Reject Ticket] buttons for claimed ticket cards."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit & Review", callback_data=f"edit_review:{wo_id}"),
            InlineKeyboardButton("❌ Reject Ticket", callback_data=f"reject_ticket:{wo_id}"),
        ]
    ])


def review_ticket_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    """[✅ Approve & Send to Admin] [↩ Edit Again] for review preview cards."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Send to Admin", callback_data=f"approve_ticket:{wo_id}"),
            InlineKeyboardButton("↩ Edit Again", callback_data=f"edit_review:{wo_id}"),
        ]
    ])


def admin_ticket_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    """Priority row [🔴 High][🟡 Medium][🟢 Low] + status row [▶️ In Progress][🔒 Close] for admin ticket cards."""
    return InlineKeyboardMarkup([
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


def status_change_keyboard(req_id: int) -> InlineKeyboardMarkup:
    """[✅ Approve Change] [❌ Reject Change] for status change request cards."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve Change", callback_data=f"approve_change:{req_id}"),
            InlineKeyboardButton("❌ Reject Change", callback_data=f"reject_change:{req_id}"),
        ]
    ])


def reject_confirm_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    """[✅ Yes, Reject] [❌ Cancel] for reject confirmation."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Reject", callback_data=f"confirm_reject:{wo_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_reject:{wo_id}"),
        ]
    ])
