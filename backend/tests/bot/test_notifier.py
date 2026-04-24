"""Tests for push notifier message formatting and send functions."""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

os.environ.setdefault("ADMIN_CHAT_ID", "-1001111")
os.environ.setdefault("TECHNICIANS_CHAT_ID", "-1003333")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")


SAMPLE_WO = {
    "id": 12,
    "ahu_id": "e0402",
    "level": 4,
    "title": "Chiller coil overtemperature",
    "description": "FAIR composite dropped below threshold",
    "category": "System Error",
    "severity": "Critical",
    "status": "draft",
    "fair_snapshot": '{"F": 42, "A": 38, "I": 61, "R": 55, "composite": 49}',
    "created_at": "2026-04-20T09:14:00+00:00",
}


# ── Formatter tests ────────────────────────────────────────────────────────────

def test_format_manager_alert_contains_title():
    from bot.push.notifier import _format_manager_alert
    text = _format_manager_alert(SAMPLE_WO)
    assert "Chiller coil overtemperature" in text
    assert "e0402" in text
    assert "Level 4" in text


def test_format_manager_alert_contains_fair():
    from bot.push.notifier import _format_manager_alert
    text = _format_manager_alert(SAMPLE_WO)
    assert "F:42" in text


def test_format_technician_assignment_contains_ahu():
    from bot.push.notifier import _format_technician_assignment
    text = _format_technician_assignment(SAMPLE_WO)
    assert "e0402" in text
    assert "#12" in text


def test_format_draft_card_contains_required_fields():
    from bot.push.notifier import _format_draft_card
    text = _format_draft_card("#12", SAMPLE_WO)
    assert "📋 New Draft Ticket — #12" in text
    assert "Subject: Chiller coil overtemperature" in text
    assert "Category: System Error" in text
    assert "AHU: e0402 · Level 4" in text
    assert "FAIR composite dropped below threshold" in text
    assert "🤖 Agent" in text


def test_format_draft_card_truncates_description():
    from bot.push.notifier import _format_draft_card
    long_desc = "A" * 300
    wo = {**SAMPLE_WO, "description": long_desc}
    text = _format_draft_card("#12", wo)
    # Only first 200 chars should appear
    assert "A" * 200 in text
    assert "A" * 201 not in text


# ── parse_fair tests ───────────────────────────────────────────────────────────

def test_parse_fair_valid():
    from bot.push.notifier import parse_fair
    result = parse_fair('{"F": 42, "A": 38, "I": 61, "R": 55, "composite": 49}')
    assert result == "F:42 A:38 I:61 R:55 · Composite: 49"


def test_parse_fair_empty():
    from bot.push.notifier import parse_fair
    assert parse_fair(None) == ""
    assert parse_fair("") == ""


# ── Async send function tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notify_admins_calls_send_message():
    from bot.push import notifier
    mock_bot = AsyncMock()
    with patch.object(notifier, "Bot", return_value=mock_bot):
        from bot.push.notifier import notify_admins
        await notify_admins(SAMPLE_WO)
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == -1001111


@pytest.mark.asyncio
async def test_notify_admins_skips_when_no_chat_id():
    from bot.push import notifier
    mock_bot = AsyncMock()
    original = notifier._ADMIN_CHAT_ID
    notifier._ADMIN_CHAT_ID = 0
    try:
        with patch.object(notifier, "Bot", return_value=mock_bot):
            await notifier.notify_admins(SAMPLE_WO)
            mock_bot.send_message.assert_not_called()
    finally:
        notifier._ADMIN_CHAT_ID = original


@pytest.mark.asyncio
async def test_send_draft_card_sends_to_technicians_with_inline_button():
    from bot.push.notifier import send_draft_card, _TECHNICIANS_CHAT_ID
    from telegram import InlineKeyboardMarkup

    mock_bot = AsyncMock()
    await send_draft_card(mock_bot, "#12", SAMPLE_WO)

    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs

    # Sent to technicians chat
    assert call_kwargs["chat_id"] == _TECHNICIANS_CHAT_ID

    # Text contains key fields
    text = call_kwargs["text"]
    assert "📋 New Draft Ticket — #12" in text
    assert "e0402" in text

    # Inline keyboard has claim_ticket callback
    markup = call_kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    buttons = [btn for row in markup.inline_keyboard for btn in row]
    assert len(buttons) == 1
    assert buttons[0].callback_data == "claim_ticket:12"
    assert "🙋" in buttons[0].text


@pytest.mark.asyncio
async def test_send_draft_card_skips_when_no_chat_id():
    from bot.push import notifier
    mock_bot = AsyncMock()
    original = notifier._TECHNICIANS_CHAT_ID
    notifier._TECHNICIANS_CHAT_ID = 0
    try:
        await notifier.send_draft_card(mock_bot, "#12", SAMPLE_WO)
        mock_bot.send_message.assert_not_called()
    finally:
        notifier._TECHNICIANS_CHAT_ID = original


# ── emit() dispatcher tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_draft_created_calls_send_draft_card():
    from bot.push import notifier
    with patch.object(notifier, "send_draft_card", new_callable=AsyncMock) as mock_sdc:
        mock_bot = MagicMock()
        await notifier.emit("draft_created", SAMPLE_WO, bot=mock_bot)
        mock_sdc.assert_called_once()
        call_args = mock_sdc.call_args
        assert call_args.args[0] is mock_bot
        assert "#12" in call_args.args[1]


@pytest.mark.asyncio
async def test_emit_ticket_opened_calls_notify_admins():
    from bot.push import notifier
    with patch.object(notifier, "notify_admins", new_callable=AsyncMock) as mock_na:
        await notifier.emit("ticket_opened", SAMPLE_WO, token="test-token")
        mock_na.assert_called_once_with(SAMPLE_WO, token="test-token")


@pytest.mark.asyncio
async def test_emit_status_changed_notifies_both_groups():
    from bot.push import notifier
    with (
        patch.object(notifier, "notify_admins", new_callable=AsyncMock) as mock_na,
        patch.object(notifier, "notify_technicians", new_callable=AsyncMock) as mock_nt,
    ):
        await notifier.emit("status_changed", SAMPLE_WO, token="test-token")
        mock_na.assert_called_once_with(SAMPLE_WO, token="test-token")
        mock_nt.assert_called_once_with(SAMPLE_WO, token="test-token")


@pytest.mark.asyncio
async def test_emit_unknown_event_does_nothing():
    from bot.push import notifier
    with (
        patch.object(notifier, "notify_admins", new_callable=AsyncMock) as mock_na,
        patch.object(notifier, "notify_technicians", new_callable=AsyncMock) as mock_nt,
        patch.object(notifier, "send_draft_card", new_callable=AsyncMock) as mock_sdc,
    ):
        await notifier.emit("unknown_event", SAMPLE_WO)
        mock_na.assert_not_called()
        mock_nt.assert_not_called()
        mock_sdc.assert_not_called()
