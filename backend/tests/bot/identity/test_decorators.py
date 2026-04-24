"""
Tests for bot/identity/decorators.py — require_role and require_admin.

All tests use mocked PTB (python-telegram-bot) objects so no real Telegram
connection is required.
"""

from __future__ import annotations

import os
import sys

# Ensure backend/ is on the path for bare imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.identity.store import BotUser
from telegram import Update
from telegram.ext import ContextTypes

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_update(user_id: int = 12345) -> MagicMock:
    """Build a minimal mock Update with effective_user and effective_message."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    update.callback_query = None
    return update


def _make_context() -> MagicMock:
    """Build a minimal mock context."""
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    # Remove pre-existing bot_user so attribute setting is detected
    if hasattr(ctx, "bot_user"):
        del ctx.bot_user
    return ctx


def _active_user(role: str = "technician") -> BotUser:
    return BotUser(
        user_id="12345",
        telegram_username="testuser",
        display_name="Test User",
        role=role,
        status="active",
    )


def _pending_user(role: str = "technician") -> BotUser:
    return BotUser(
        user_id="12345",
        telegram_username="testuser",
        display_name="Test User",
        role=role,
        status="pending",
    )


# ── Tests: require_role ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_role_allows_correct_role() -> None:
    """Active technician user calling a technician-required handler runs the handler."""
    from bot.identity.decorators import require_role

    inner = AsyncMock(return_value="ok")

    @require_role("technician")
    async def handler(update, context):
        return await inner(update, context)

    mock_store = MagicMock()
    mock_store.get_user.return_value = _active_user("technician")

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        result = await handler(update, context)

    inner.assert_awaited_once()
    assert result == "ok"


@pytest.mark.asyncio
async def test_require_role_blocks_unregistered_user() -> None:
    """Unregistered user (get_user returns None) is blocked; reply_text called."""
    from bot.identity.decorators import require_role

    inner = AsyncMock()

    @require_role("technician")
    async def handler(update, context):
        await inner(update, context)

    mock_store = MagicMock()
    mock_store.get_user.return_value = None  # not in DB

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await handler(update, context)

    inner.assert_not_awaited()
    update.effective_message.reply_text.assert_awaited_once()
    call_args = update.effective_message.reply_text.call_args[0][0]
    assert "Not authorized" in call_args or "register" in call_args.lower()


@pytest.mark.asyncio
async def test_require_role_blocks_pending_user() -> None:
    """Pending user is blocked even if they have the right role."""
    from bot.identity.decorators import require_role

    inner = AsyncMock()

    @require_role("technician")
    async def handler(update, context):
        await inner(update, context)

    mock_store = MagicMock()
    mock_store.get_user.return_value = _pending_user("technician")

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await handler(update, context)

    inner.assert_not_awaited()
    update.effective_message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_require_role_sets_bot_user_on_context() -> None:
    """After a successful auth check, context.bot_user is set to the BotUser."""
    from bot.identity.decorators import require_role

    captured_context: list = []

    @require_role("technician")
    async def handler(update, context):
        captured_context.append(context)

    active_user = _active_user("technician")
    mock_store = MagicMock()
    mock_store.get_user.return_value = active_user

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await handler(update, context)

    # context.bot_user must be set to the BotUser instance
    assert hasattr(context, "bot_user")
    assert context.bot_user is active_user


@pytest.mark.asyncio
async def test_require_role_blocks_disabled_user() -> None:
    """Disabled user is blocked regardless of role."""
    from bot.identity.decorators import require_role

    inner = AsyncMock()

    @require_role("technician")
    async def handler(update, context):
        await inner(update, context)

    disabled_user = BotUser(
        user_id="12345",
        telegram_username="testuser",
        display_name="Test User",
        role="technician",
        status="disabled",
    )
    mock_store = MagicMock()
    mock_store.get_user.return_value = disabled_user

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await handler(update, context)

    inner.assert_not_awaited()
    update.effective_message.reply_text.assert_awaited_once()


# ── Tests: require_admin ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_admin_blocks_technician() -> None:
    """Active technician calling an admin-only handler is blocked with a permission message."""
    from bot.identity.decorators import require_admin

    inner = AsyncMock()

    @require_admin
    async def admin_handler(update, context):
        await inner(update, context)

    mock_store = MagicMock()
    mock_store.get_user.return_value = _active_user("technician")

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await admin_handler(update, context)

    inner.assert_not_awaited()
    update.effective_message.reply_text.assert_awaited_once()
    call_args = update.effective_message.reply_text.call_args[0][0]
    assert "permission" in call_args.lower()


@pytest.mark.asyncio
async def test_require_admin_allows_admin() -> None:
    """Active admin calling an admin-only handler runs the handler."""
    from bot.identity.decorators import require_admin

    inner = AsyncMock(return_value="admin_result")

    @require_admin
    async def admin_handler(update, context):
        return await inner(update, context)

    mock_store = MagicMock()
    mock_store.get_user.return_value = _active_user("admin")

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        result = await admin_handler(update, context)

    inner.assert_awaited_once()
    assert result == "admin_result"


@pytest.mark.asyncio
async def test_require_admin_blocks_unregistered_user() -> None:
    """Unregistered user is blocked from admin-only handler."""
    from bot.identity.decorators import require_admin

    inner = AsyncMock()

    @require_admin
    async def admin_handler(update, context):
        await inner(update, context)

    mock_store = MagicMock()
    mock_store.get_user.return_value = None

    update = _make_update()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await admin_handler(update, context)

    inner.assert_not_awaited()
    update.effective_message.reply_text.assert_awaited_once()


# ── Tests: no effective_user edge case ────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_role_returns_early_if_no_effective_user() -> None:
    """If update.effective_user is None, the handler returns silently."""
    from bot.identity.decorators import require_role

    inner = AsyncMock()

    @require_role("technician")
    async def handler(update, context):
        await inner(update, context)

    update = _make_update()
    update.effective_user = None  # simulate missing user

    mock_store = MagicMock()
    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await handler(update, context)

    inner.assert_not_awaited()
    # No reply_text called either — just silently returns
    mock_store.get_user.assert_not_called()


# ── Tests: callback_query fallback path ───────────────────────────────────────


@pytest.mark.asyncio
async def test_require_role_uses_callback_query_when_no_message() -> None:
    """When effective_message is None but callback_query exists, answer() is called."""
    from bot.identity.decorators import require_role

    inner = AsyncMock()

    @require_role("technician")
    async def handler(update, context):
        await inner(update, context)

    update = _make_update()
    update.effective_message = None
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()

    mock_store = MagicMock()
    mock_store.get_user.return_value = None  # trigger the not-authorized path

    context = _make_context()

    with patch("bot.identity.decorators.get_store", return_value=mock_store):
        await handler(update, context)

    inner.assert_not_awaited()
    update.callback_query.answer.assert_awaited_once()
