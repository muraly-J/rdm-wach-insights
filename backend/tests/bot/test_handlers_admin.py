"""Tests for admin handler functions (priority, status, approve/reject change)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("ADMIN_CHAT_ID", "-1001111")
os.environ.setdefault("TECHNICIANS_CHAT_ID", "-1003333")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_callback_update(
    callback_data: str,
    user_id: int = 900001,
    username: str = "adminuser",
) -> MagicMock:
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


def _make_command_update(user_id: int = 900001) -> MagicMock:
    """Build a minimal Update mock for command tests."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    # effective_message must also be AsyncMock so @require_admin decorator can await it
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


def _make_sample_wo(wo_id: int = 42, priority: str = "not_set", status: str = "open") -> dict:
    return {
        "id": wo_id,
        "ticket_no": f"#WO-{wo_id}",
        "title": "Chiller fault",
        "category": "System Error",
        "priority": priority,
        "status": status,
        "ahu_id": "e0402",
        "level": 4,
        "created_by": "Agent",
        "claimed_by": None,
        "created_at": "2026-04-23T10:00:00+00:00",
        "updated_at": "2026-04-23T10:00:00+00:00",
        "description": None,
    }


# ── cb_set_priority tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cb_set_priority_high():
    """Admin sets priority=high → api_client._patch called with priority='high'."""
    update = _make_callback_update("set_priority:42:high")
    context = MagicMock()
    context.bot = AsyncMock()

    admin_user = _make_active_admin("900001")

    mock_store = MagicMock()
    mock_store.get_user.return_value = admin_user
    mock_store.log_audit = MagicMock()

    sample_wo = _make_sample_wo(42, priority="high")

    with (
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("bot.handlers.admin.api_client") as mock_api,
    ):
        mock_api._patch = AsyncMock()
        mock_api.get_work_order = AsyncMock(return_value=sample_wo)
        from bot.handlers.admin import cb_set_priority
        await cb_set_priority(update, context)

    mock_api._patch.assert_called_once()
    patch_call = mock_api._patch.call_args
    assert "/api/work-orders/42" in patch_call[0][0]
    assert patch_call[1]["json"]["priority"] == "high"


@pytest.mark.asyncio
async def test_cb_set_priority_medium():
    """Admin sets priority=medium → api_client._patch called with priority='medium'."""
    update = _make_callback_update("set_priority:42:medium")
    context = MagicMock()
    context.bot = AsyncMock()

    admin_user = _make_active_admin("900001")

    mock_store = MagicMock()
    mock_store.get_user.return_value = admin_user
    mock_store.log_audit = MagicMock()

    sample_wo = _make_sample_wo(42, priority="medium")

    with (
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("bot.handlers.admin.api_client") as mock_api,
    ):
        mock_api._patch = AsyncMock()
        mock_api.get_work_order = AsyncMock(return_value=sample_wo)
        from bot.handlers.admin import cb_set_priority
        await cb_set_priority(update, context)

    mock_api._patch.assert_called_once()
    patch_call = mock_api._patch.call_args
    assert patch_call[1]["json"]["priority"] == "medium"


@pytest.mark.asyncio
async def test_cb_set_priority_unauthorized():
    """Non-admin user → query.answer with 'Not authorized' alert."""
    update = _make_callback_update("set_priority:42:high", user_id=555555)
    context = MagicMock()

    mock_store = MagicMock()
    mock_store.get_user.return_value = None  # not in store

    with patch("bot.handlers.admin.get_store", return_value=mock_store):
        from bot.handlers.admin import cb_set_priority
        await cb_set_priority(update, context)

    update.callback_query.answer.assert_called_once()
    answer_kwargs = update.callback_query.answer.call_args
    text = answer_kwargs[0][0] if answer_kwargs[0] else answer_kwargs[1].get("text", "")
    assert "not authorized" in text.lower() or "authorized" in text.lower()


# ── cb_set_status tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cb_set_status_in_progress():
    """Admin sets status=in_progress → api_client._post called with status='in_progress'."""
    update = _make_callback_update("set_status:42:in_progress")
    context = MagicMock()
    context.bot = AsyncMock()

    admin_user = _make_active_admin("900001")

    mock_store = MagicMock()
    mock_store.get_user.return_value = admin_user
    mock_store.log_audit = MagicMock()

    sample_wo = _make_sample_wo(42, status="in_progress")

    with (
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("bot.handlers.admin.api_client") as mock_api,
        patch("bot.handlers.admin.TECHNICIANS_CHAT_ID", 0),  # suppress notification
    ):
        mock_api._post = AsyncMock()
        mock_api.get_work_order = AsyncMock(return_value=sample_wo)
        from bot.handlers.admin import cb_set_status
        await cb_set_status(update, context)

    mock_api._post.assert_called_once()
    post_call = mock_api._post.call_args
    assert "/api/work-orders/42/status" in post_call[0][0]
    assert post_call[1]["json"]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_cb_set_status_closed():
    """Admin sets status=closed → api_client._post called with status='closed'."""
    update = _make_callback_update("set_status:42:closed")
    context = MagicMock()
    context.bot = AsyncMock()

    admin_user = _make_active_admin("900001")

    mock_store = MagicMock()
    mock_store.get_user.return_value = admin_user
    mock_store.log_audit = MagicMock()

    sample_wo = _make_sample_wo(42, status="closed")

    with (
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("bot.handlers.admin.api_client") as mock_api,
        patch("bot.handlers.admin.TECHNICIANS_CHAT_ID", 0),
    ):
        mock_api._post = AsyncMock()
        mock_api.get_work_order = AsyncMock(return_value=sample_wo)
        from bot.handlers.admin import cb_set_status
        await cb_set_status(update, context)

    mock_api._post.assert_called_once()
    post_call = mock_api._post.call_args
    assert post_call[1]["json"]["status"] == "closed"


# ── cb_approve_change tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cb_approve_change():
    """Admin approves a status change request → work order updated + message edited."""
    update = _make_callback_update("approve_change:7")
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()

    admin_user = _make_active_admin("900001")

    mock_store = MagicMock()
    mock_store.get_user.return_value = admin_user
    mock_store.log_audit = MagicMock()

    mock_db = MagicMock()
    mock_db.get_status_change_request.return_value = {
        "id": 7,
        "ticket_no": "#WO-42",
        "work_order_id": 42,
        "requested_by": "111222",
        "current_status": "in_progress",
        "proposed_status": "resolved",
        "notes": "All done",
        "decision": None,
    }
    mock_db.decide_status_change.return_value = True
    mock_db.update_work_order = MagicMock()

    with (
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("bot.handlers.admin.TECHNICIANS_CHAT_ID", 0),  # suppress notification
        patch("core.agentdb.AgentDB", return_value=mock_db),
        patch("core.agentdb._db_instance", mock_db),
    ):
        import core.agentdb as agentdb_module
        agentdb_module._db_instance = mock_db
        from bot.handlers.admin import cb_approve_change
        await cb_approve_change(update, context)

    # Work order status should be updated to 'resolved'
    mock_db.update_work_order.assert_called_once_with(42, status="resolved")
    # Message should be edited to show approval
    update.callback_query.edit_message_text.assert_called_once()
    edit_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "approved" in edit_text.lower() or "Approved" in edit_text


@pytest.mark.asyncio
async def test_cb_approve_change_already_decided():
    """Request already decided → query.answer with 'Already ...' alert, no update."""
    update = _make_callback_update("approve_change:7")
    context = MagicMock()

    admin_user = _make_active_admin("900001")

    mock_store = MagicMock()
    mock_store.get_user.return_value = admin_user

    mock_db = MagicMock()
    mock_db.get_status_change_request.return_value = {
        "id": 7,
        "ticket_no": "#WO-42",
        "work_order_id": 42,
        "requested_by": "111222",
        "current_status": "in_progress",
        "proposed_status": "resolved",
        "notes": None,
        "decision": "approved",  # already decided
    }
    mock_db.update_work_order = MagicMock()

    with (
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("core.agentdb._db_instance", mock_db),
    ):
        import core.agentdb as agentdb_module
        agentdb_module._db_instance = mock_db
        from bot.handlers.admin import cb_approve_change
        await cb_approve_change(update, context)

    # No work order update should happen
    mock_db.update_work_order.assert_not_called()
    # Alert shown
    update.callback_query.answer.assert_called_once()
    answer_kwargs = update.callback_query.answer.call_args
    show_alert = answer_kwargs[1].get("show_alert", False) if answer_kwargs[1] else False
    assert show_alert is True


# ── cmd_pending tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_pending_empty():
    """list_work_orders returns [] for both statuses → reply contains 'No pending'."""
    update = _make_command_update(user_id=900001)
    context = MagicMock()
    active_admin = _make_active_admin("900001")
    context.bot_user = active_admin

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("bot.handlers.admin.api_client") as mock_api,
    ):
        mock_api.list_work_orders = AsyncMock(return_value=[])
        from bot.handlers.admin import cmd_pending
        await cmd_pending(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "no pending" in text.lower() or "no ticket" in text.lower()


@pytest.mark.asyncio
async def test_cmd_pending_lists_tickets():
    """list_work_orders returns work orders → reply contains ticket numbers."""
    update = _make_command_update(user_id=900001)
    context = MagicMock()
    active_admin = _make_active_admin("900001")
    context.bot_user = active_admin

    mock_store = MagicMock()
    mock_store.get_user.return_value = active_admin

    open_orders = [_make_sample_wo(10, status="open")]
    in_progress_orders = [_make_sample_wo(11, status="in_progress")]

    async def mock_list_work_orders(status=None):
        if status == "open":
            return open_orders
        elif status == "in_progress":
            return in_progress_orders
        return []

    with (
        patch("bot.identity.decorators.get_store", return_value=mock_store),
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("bot.handlers.admin.api_client") as mock_api,
    ):
        mock_api.list_work_orders = mock_list_work_orders
        from bot.handlers.admin import cmd_pending
        await cmd_pending(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "#WO-10" in text or "WO-10" in text


# ── cb_reject_change tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cb_reject_change():
    """Admin rejects a status change request → message edited + DM sent to tech."""
    update = _make_callback_update("reject_change:8")
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()

    admin_user = _make_active_admin("900001")

    mock_store = MagicMock()
    mock_store.get_user.return_value = admin_user
    mock_store.log_audit = MagicMock()

    mock_db = MagicMock()
    mock_db.get_status_change_request.return_value = {
        "id": 8,
        "ticket_no": "#WO-43",
        "work_order_id": 43,
        "requested_by": "111222",
        "current_status": "open",
        "proposed_status": "resolved",
        "notes": None,
        "decision": None,
    }
    mock_db.decide_status_change.return_value = True

    with (
        patch("bot.handlers.admin.get_store", return_value=mock_store),
        patch("core.agentdb._db_instance", mock_db),
    ):
        import core.agentdb as agentdb_module
        agentdb_module._db_instance = mock_db
        from bot.handlers.admin import cb_reject_change
        await cb_reject_change(update, context)

    # Message edited to show rejection
    update.callback_query.edit_message_text.assert_called_once()
    edit_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "rejected" in edit_text.lower() or "Rejected" in edit_text

    # DM sent to the requesting technician
    context.bot.send_message.assert_called_once()
    dm_kwargs = context.bot.send_message.call_args[1]
    assert dm_kwargs["chat_id"] == 111222


# ── get_handlers registration ─────────────────────────────────────────────────

def test_admin_get_handlers_returns_list():
    """admin.get_handlers() returns a non-empty list."""
    from bot.handlers.admin import get_handlers
    handlers = get_handlers()
    assert isinstance(handlers, list)
    assert len(handlers) > 0
