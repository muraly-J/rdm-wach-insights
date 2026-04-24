"""Tests for technician handler functions (refactored for 2-role model)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_callback_update(callback_data: str, user_id: int = 111222, username: str = "techuser") -> MagicMock:
    """Build a minimal Update mock for callback query tests."""
    update = MagicMock()
    update.callback_query.data = callback_data
    update.callback_query.from_user.id = user_id
    update.callback_query.from_user.username = username
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()
    update.effective_user.id = user_id
    return update


def _make_command_update(user_id: int = 111222) -> MagicMock:
    """Build a minimal Update mock for command tests."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    # effective_message must also be AsyncMock so @require_role decorator can await it
    update.effective_message.reply_text = AsyncMock()
    update.callback_query = None
    return update


def _make_active_tech(user_id: str = "111222") -> MagicMock:
    """Return a mock BotUser representing an active technician."""
    from bot.identity.store import BotUser
    return BotUser(
        user_id=user_id,
        telegram_username="techuser",
        display_name="Tech User",
        role="technician",
        status="active",
    )


# ── Existing tests ─────────────────────────────────────────────────────────────

def test_get_handlers_returns_list():
    """Verify get_handlers returns a non-empty list."""
    from bot.handlers.technicians import get_handlers

    handlers = get_handlers()
    assert isinstance(handlers, list)
    assert len(handlers) > 0


def test_ticket_categories_defined():
    """Verify predefined categories are available."""
    from bot.config import TICKET_CATEGORIES

    assert len(TICKET_CATEGORIES) == 4
    assert "Bug Report" in TICKET_CATEGORIES
    assert "System Error" in TICKET_CATEGORIES
    assert "New Idea or Features" in TICKET_CATEGORIES
    assert "Other Inquiry" in TICKET_CATEGORIES


def test_admin_chat_id_backwards_compat():
    """ADMIN_CHAT_ID should equal MANAGERS_CHAT_ID for backwards compat."""
    from bot.config import ADMIN_CHAT_ID, MANAGERS_CHAT_ID

    assert ADMIN_CHAT_ID == MANAGERS_CHAT_ID


# ── cb_claim_ticket tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cb_claim_ticket_success():
    """Technician claims ticket: db.claim_work_order returns True → edit_message_text called."""
    update = _make_callback_update("claim_ticket:42")
    context = MagicMock()
    context.bot = AsyncMock()

    active_tech = _make_active_tech("111222")

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech
    mock_store.log_audit = MagicMock()

    mock_db = MagicMock()
    mock_db.claim_work_order.return_value = True
    mock_db.get_work_order.return_value = {
        "id": 42,
        "ticket_no": "#42",
        "title": "Fan belt worn",
        "category": "System Error",
        "claimed_by": "111222",
        "status": "pending_tech_review",
    }
    mock_db.update_work_order = MagicMock()

    with (
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
        patch("bot.handlers.technicians._get_db", return_value=mock_db),
    ):
        from bot.handlers.technicians import cb_claim_ticket
        await cb_claim_ticket(update, context)

    update.callback_query.edit_message_text.assert_called_once()
    call_args = update.callback_query.edit_message_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "Claimed" in text or "claimed" in text


@pytest.mark.asyncio
async def test_cb_claim_ticket_already_claimed():
    """Ticket already claimed → query.answer called with alert text."""
    update = _make_callback_update("claim_ticket:42")
    context = MagicMock()

    active_tech = _make_active_tech("111222")

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech

    mock_db = MagicMock()
    mock_db.claim_work_order.return_value = False
    mock_db.get_work_order.return_value = {
        "id": 42,
        "ticket_no": "#42",
        "claimed_by": "999999",
    }

    with (
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
        patch("bot.handlers.technicians._get_db", return_value=mock_db),
    ):
        from bot.handlers.technicians import cb_claim_ticket
        await cb_claim_ticket(update, context)

    update.callback_query.answer.assert_called_once()
    answer_kwargs = update.callback_query.answer.call_args
    # First positional arg is the alert text
    alert_text = answer_kwargs[0][0] if answer_kwargs[0] else answer_kwargs[1].get("text", "")
    show_alert = (
        answer_kwargs[1].get("show_alert", False)
        if answer_kwargs[1]
        else False
    )
    assert "claimed" in alert_text.lower() or "already" in alert_text.lower()
    assert show_alert is True


@pytest.mark.asyncio
async def test_cb_claim_ticket_unauthorized_user():
    """User not in store → answer with 'Not authorized' alert."""
    update = _make_callback_update("claim_ticket:42")
    context = MagicMock()

    mock_store = MagicMock()
    mock_store.get_user.return_value = None

    mock_db = MagicMock()

    with (
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
        patch("bot.handlers.technicians._get_db", return_value=mock_db),
    ):
        from bot.handlers.technicians import cb_claim_ticket
        await cb_claim_ticket(update, context)

    update.callback_query.answer.assert_called_once()
    answer_kwargs = update.callback_query.answer.call_args
    alert_text = answer_kwargs[0][0] if answer_kwargs[0] else answer_kwargs[1].get("text", "")
    assert "not authorized" in alert_text.lower() or "register" in alert_text.lower()


# ── cmd_mywork tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_mywork_no_tickets():
    """list_work_orders returns [] → reply contains 'No tickets'."""
    update = _make_command_update(user_id=111222)
    context = MagicMock()
    active_tech = _make_active_tech("111222")
    context.bot_user = active_tech

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech

    with (
        # patch both decorator's store and handler's store
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
        patch("bot.handlers.technicians.api_client") as mock_api,
    ):
        mock_api.list_work_orders = AsyncMock(return_value=[])
        from bot.handlers.technicians import cmd_mywork
        await cmd_mywork(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "no ticket" in text.lower() or "no tickets" in text.lower()


@pytest.mark.asyncio
async def test_cmd_mywork_returns_my_tickets():
    """list_work_orders with user's tickets → reply contains ticket number."""
    update = _make_command_update(user_id=111222)
    context = MagicMock()
    active_tech = _make_active_tech("111222")
    context.bot_user = active_tech

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech

    work_orders = [
        {
            "id": 5,
            "ticket_no": "#WO-5",
            "title": "Coil fouling",
            "status": "in_progress",
            "claimed_by": "111222",
            "assigned_to": None,
        }
    ]

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
        patch("bot.handlers.technicians.api_client") as mock_api,
    ):
        mock_api.list_work_orders = AsyncMock(return_value=work_orders)
        from bot.handlers.technicians import cmd_mywork
        await cmd_mywork(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "#WO-5" in text or "WO-5" in text


# ── cmd_update_start tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_update_start_no_args():
    """No context.args → reply contains 'Usage:'."""
    update = _make_command_update(user_id=111222)
    context = MagicMock()
    context.args = []
    active_tech = _make_active_tech("111222")
    context.bot_user = active_tech

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
    ):
        from bot.handlers.technicians import cmd_update_start
        await cmd_update_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "usage" in text.lower() or "Usage" in text


@pytest.mark.asyncio
async def test_cmd_update_start_one_arg_only():
    """Only one arg (no status) → reply contains 'Usage:'."""
    update = _make_command_update(user_id=111222)
    context = MagicMock()
    context.args = ["42"]
    active_tech = _make_active_tech("111222")
    context.bot_user = active_tech

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
    ):
        from bot.handlers.technicians import cmd_update_start
        await cmd_update_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "usage" in text.lower() or "Usage" in text


@pytest.mark.asyncio
async def test_cmd_update_start_invalid_status():
    """Status not in allowed list → reply mentions technicians can propose."""
    update = _make_command_update(user_id=111222)
    context = MagicMock()
    context.args = ["42", "closed"]  # 'closed' is admin-only
    active_tech = _make_active_tech("111222")
    context.bot_user = active_tech

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.technicians.get_store", return_value=mock_store),
    ):
        from bot.handlers.technicians import cmd_update_start
        await cmd_update_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    # Should indicate only 'resolved' is allowed
    assert "resolved" in text.lower() or "technician" in text.lower()
