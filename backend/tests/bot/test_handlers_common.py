"""Tests for common handler functions (/start in all user states)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_update(user_id: int = 123456) -> MagicMock:
    """Build a minimal Update mock for command tests."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.first_name = "Test"
    update.message.reply_text = AsyncMock()
    return update


def _make_context() -> MagicMock:
    context = MagicMock()
    context.args = []
    return context


# ── /start tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_unregistered_user():
    """/start when user is not in identity store → reply contains 'register'."""
    update = _make_update()
    context = _make_context()

    mock_store = MagicMock()
    mock_store.get_user.return_value = None

    with patch("bot.handlers.common.get_store", return_value=mock_store):
        from bot.handlers.common import cmd_start
        await cmd_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "register" in text.lower()


@pytest.mark.asyncio
async def test_start_pending_user():
    """/start when user.status='pending' → reply contains 'pending' or 'approval'."""
    update = _make_update()
    context = _make_context()

    from bot.identity.store import BotUser
    pending_user = BotUser(
        user_id="123456",
        telegram_username="testuser",
        display_name="Test User",
        role="technician",
        status="pending",
    )

    mock_store = MagicMock()
    mock_store.get_user.return_value = pending_user

    with patch("bot.handlers.common.get_store", return_value=mock_store):
        from bot.handlers.common import cmd_start
        await cmd_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    text_lower = text.lower()
    assert "pending" in text_lower or "approval" in text_lower or "waiting" in text_lower or "approved" in text_lower


@pytest.mark.asyncio
async def test_start_active_technician():
    """/start when user is active technician → reply contains commands or 'help'."""
    update = _make_update()
    context = _make_context()

    from bot.identity.store import BotUser
    active_tech = BotUser(
        user_id="123456",
        telegram_username="tech1",
        display_name="Tech One",
        role="technician",
        status="active",
    )

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_tech

    with patch("bot.handlers.common.get_store", return_value=mock_store):
        from bot.handlers.common import cmd_start
        await cmd_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    text_lower = text.lower()
    # Active user gets a greeting with their name and /help reference
    assert "tech one" in text_lower or "help" in text_lower or "/help" in text_lower or "technician" in text_lower


@pytest.mark.asyncio
async def test_start_active_admin():
    """/start when user is active admin → reply contains greeting or help."""
    update = _make_update(user_id=999001)
    context = _make_context()

    from bot.identity.store import BotUser
    active_admin = BotUser(
        user_id="999001",
        telegram_username="admin1",
        display_name="Admin One",
        role="admin",
        status="active",
    )

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin

    with patch("bot.handlers.common.get_store", return_value=mock_store):
        from bot.handlers.common import cmd_start
        await cmd_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    text_lower = text.lower()
    # Active admin gets a greeting — check for their name or admin label or help
    assert "admin one" in text_lower or "admin" in text_lower or "help" in text_lower or "/help" in text_lower


@pytest.mark.asyncio
async def test_start_disabled_user():
    """/start when user.status='disabled' → reply mentions disabled/contact."""
    update = _make_update()
    context = _make_context()

    from bot.identity.store import BotUser
    disabled_user = BotUser(
        user_id="123456",
        telegram_username="extech",
        display_name="Ex Tech",
        role="technician",
        status="disabled",
    )

    mock_store = MagicMock()
    mock_store.get_user.return_value = disabled_user

    with patch("bot.handlers.common.get_store", return_value=mock_store):
        from bot.handlers.common import cmd_start
        await cmd_start(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    text_lower = text.lower()
    assert "disabled" in text_lower or "contact" in text_lower


@pytest.mark.asyncio
async def test_start_no_effective_user():
    """/start when effective_user is None → no reply sent (early return)."""
    update = MagicMock()
    update.effective_user = None
    update.message.reply_text = AsyncMock()
    context = _make_context()

    mock_store = MagicMock()
    mock_store.get_user.return_value = None

    with patch("bot.handlers.common.get_store", return_value=mock_store):
        from bot.handlers.common import cmd_start
        await cmd_start(update, context)

    update.message.reply_text.assert_not_called()


# ── get_handlers registration ─────────────────────────────────────────────────

def test_common_get_handlers_returns_list():
    """common.get_handlers() returns a non-empty list."""
    from bot.handlers.common import get_handlers
    handlers = get_handlers()
    assert isinstance(handlers, list)
    assert len(handlers) >= 4  # start, help, menu, cancel
