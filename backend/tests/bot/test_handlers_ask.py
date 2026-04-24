"""Tests for /ask handler (Phase 4: agent wiring)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("ADMIN_CHAT_ID", "-1001111")
os.environ.setdefault("TECHNICIANS_CHAT_ID", "-1003333")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_command_update(user_id: int = 900001) -> MagicMock:
    """Build a minimal Update mock for command tests."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.id = -1001111
    update.message.reply_text = AsyncMock()
    update.effective_message.reply_text = AsyncMock()
    update.callback_query = None
    return update


def _make_active_admin(user_id: str = "900001") -> MagicMock:
    """Return a mock BotUser representing an active admin."""
    from bot.identity.store import BotUser
    return BotUser(
        user_id=user_id,
        telegram_username="adminuser",
        display_name="Admin User",
        role="admin",
        status="active",
    )


# ── test_ask_disabled_when_feature_flag_off ────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_disabled_when_feature_flag_off():
    """BOT_AGENT_ENABLED=False → reply contains 'disabled'."""
    update = _make_command_update()
    context = MagicMock()
    context.args = ["why", "did", "e0507", "fail?"]
    context.bot = AsyncMock()

    active_admin = _make_active_admin("900001")
    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.ask.get_store", return_value=mock_store),
        patch("bot.handlers.ask.BOT_AGENT_ENABLED", False),
    ):
        from bot.handlers.ask import cmd_ask
        await cmd_ask(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "disabled" in text.lower()


# ── test_ask_no_args ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_no_args():
    """No context.args → reply contains 'Usage:'."""
    update = _make_command_update()
    context = MagicMock()
    context.args = []
    context.bot = AsyncMock()

    active_admin = _make_active_admin("900001")
    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.ask.get_store", return_value=mock_store),
        patch("bot.handlers.ask.BOT_AGENT_ENABLED", True),
    ):
        from bot.handlers.ask import cmd_ask
        await cmd_ask(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "usage" in text.lower() or "Usage" in text


# ── test_ask_rate_limited ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_rate_limited():
    """Second call after exhausting limiter → rate limit reply."""
    from bot.rate_limit import RateLimiter

    # Limiter with max_calls=1 so 2nd call is blocked
    tight_limiter = RateLimiter(max_calls=1, period_seconds=300)
    user_id = "900001"

    # Exhaust the single allowed call
    tight_limiter.is_allowed(user_id)

    update = _make_command_update(user_id=int(user_id))
    context = MagicMock()
    context.args = ["is the building okay?"]
    context.bot = AsyncMock()

    active_admin = _make_active_admin(user_id)
    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.ask.get_store", return_value=mock_store),
        patch("bot.handlers.ask.BOT_AGENT_ENABLED", True),
        patch("bot.handlers.ask.get_ask_limiter", return_value=tight_limiter),
    ):
        from bot.handlers.ask import cmd_ask
        await cmd_ask(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "rate limit" in text.lower() or "limit" in text.lower()


# ── test_ask_calls_agent_and_replies ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_calls_agent_and_replies():
    """Mock bot.agent.ask.ask, verify reply contains the agent answer."""
    from bot.rate_limit import RateLimiter

    unlimited_limiter = RateLimiter(max_calls=100, period_seconds=300)

    update = _make_command_update()
    context = MagicMock()
    context.args = ["why", "did", "e0507", "fail?"]
    context.bot = AsyncMock()

    active_admin = _make_active_admin("900001")
    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin
    mock_store.log_audit = MagicMock()

    mock_answer = "e0507 failed due to coil fouling detected at 08:14."

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.ask.get_store", return_value=mock_store),
        patch("bot.handlers.ask.BOT_AGENT_ENABLED", True),
        patch("bot.handlers.ask.get_ask_limiter", return_value=unlimited_limiter),
        patch("bot.agent.ask.ask", new=AsyncMock(return_value=mock_answer)),
    ):
        from bot.handlers.ask import cmd_ask
        await cmd_ask(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert mock_answer in text
    assert "WACH Agent" in text


# ── test_ask_agent_failure_replies_gracefully ──────────────────────────────────

@pytest.mark.asyncio
async def test_ask_agent_failure_replies_gracefully():
    """Agent raises exception → graceful error reply, no crash."""
    from bot.rate_limit import RateLimiter

    unlimited_limiter = RateLimiter(max_calls=100, period_seconds=300)

    update = _make_command_update()
    context = MagicMock()
    context.args = ["what", "is", "the", "health", "score?"]
    context.bot = AsyncMock()

    active_admin = _make_active_admin("900001")
    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.ask.get_store", return_value=mock_store),
        patch("bot.handlers.ask.BOT_AGENT_ENABLED", True),
        patch("bot.handlers.ask.get_ask_limiter", return_value=unlimited_limiter),
        patch("bot.agent.ask.ask", new=AsyncMock(side_effect=Exception("Connection refused"))),
    ):
        from bot.handlers.ask import cmd_ask
        await cmd_ask(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    # Should be a graceful error message, not a traceback
    assert "could not" in text.lower() or "⚠️" in text


# ── test_ask_logs_audit ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_logs_audit():
    """Verify store.log_audit called with action='ask' after successful response."""
    from bot.rate_limit import RateLimiter

    unlimited_limiter = RateLimiter(max_calls=100, period_seconds=300)

    update = _make_command_update()
    context = MagicMock()
    context.args = ["summarise", "level", "5"]
    context.bot = AsyncMock()

    active_admin = _make_active_admin("900001")
    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin
    mock_store.log_audit = MagicMock()

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.ask.get_store", return_value=mock_store),
        patch("bot.handlers.ask.BOT_AGENT_ENABLED", True),
        patch("bot.handlers.ask.get_ask_limiter", return_value=unlimited_limiter),
        patch("bot.agent.ask.ask", new=AsyncMock(return_value="Level 5 looks healthy.")),
    ):
        from bot.handlers.ask import cmd_ask
        await cmd_ask(update, context)

    mock_store.log_audit.assert_called_once()
    call_kwargs = mock_store.log_audit.call_args
    # Support both positional and keyword call styles
    kwargs = call_kwargs[1] if call_kwargs[1] else {}
    args = call_kwargs[0] if call_kwargs[0] else ()

    # action should be 'ask'
    action = kwargs.get("action") or (args[1] if len(args) > 1 else None)
    assert action == "ask"

    # details should contain the question
    details = kwargs.get("details") or (args[3] if len(args) > 3 else None)
    assert details is not None
    assert "question" in details
