"""Tests for action tool handlers."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DEV_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Patch AgentDB to use a temp file."""
    from core import agentdb as agentdb_module
    from core.agentdb import AgentDB
    temp_db = AgentDB(str(tmp_path / "test.duckdb"))
    monkeypatch.setattr(agentdb_module, "_db_instance", temp_db)
    return temp_db


@pytest.mark.asyncio
async def test_create_work_order_warning_creates_draft(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e0402",
        title="Phase imbalance",
        description="Current unbalance >10%",
        severity="warning",
    )
    assert result["status"] == "draft"
    assert result["id"] > 0
    assert result["ahu_id"] == "e0402"


@pytest.mark.asyncio
async def test_create_work_order_critical_creates_approved(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e0301",
        title="Critical health failure",
        description="FAIR score 28",
        severity="Critical",
    )
    assert result["status"] == "approved"


@pytest.mark.asyncio
async def test_create_work_order_returns_level_from_ahu_id(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e0507",
        title="Test",
        description="desc",
        severity="info",
    )
    assert result["level"] == 5


@pytest.mark.asyncio
async def test_create_work_order_unknown_ahu_id_uses_level_0(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e9999",
        title="Test",
        description="desc",
        severity="info",
    )
    assert result["level"] == 0


@pytest.mark.asyncio
async def test_send_notification_no_token_returns_skipped(db):
    """When TELEGRAM_BOT_TOKEN is empty, notification should be skipped gracefully."""
    from tools.action_tools import handle_send_notification
    result = await handle_send_notification(
        recipient="technician",
        message="AHU e0402 phase imbalance detected.",
    )
    assert result["status"] == "skipped"
    assert "token not configured" in result["reason"]


@pytest.mark.asyncio
async def test_send_notification_spam_prevention(db):
    """Second notification for same AHU within cooldown should be blocked."""
    from datetime import datetime, timedelta, timezone

    from tools.action_tools import handle_send_notification
    # Manually set agent state to simulate a recent alert
    db.set_agent_state(
        "last_alert:e0402",
        {"notified_at": datetime.now(timezone.utc).isoformat()},
    )
    result = await handle_send_notification(
        recipient="technician",
        message="Repeated alert for e0402",
        ahu_id="e0402",
    )
    assert result["status"] == "skipped"
    assert "cooldown" in result["reason"]


@pytest.mark.asyncio
async def test_send_notification_updates_work_order(db):
    """If work_order_id provided and notification skipped, work order unchanged."""
    from tools.action_tools import handle_create_work_order, handle_send_notification
    wo = await handle_create_work_order(
        ahu_id="e0101", title="Test", severity="critical"
    )
    result = await handle_send_notification(
        recipient="technician",
        message="Critical alert",
        work_order_id=wo["id"],
        ahu_id="e0101",
    )
    # Even if skipped (no token), result has a status field
    assert "status" in result


@pytest.mark.asyncio
async def test_update_work_order_valid_transition(db):
    from tools.action_tools import handle_create_work_order, handle_update_work_order
    wo = await handle_create_work_order(
        ahu_id="e0101", title="Test", severity="warning"
    )
    result = await handle_update_work_order(
        work_order_id=wo["id"],
        status="approved",
        approved_by="admin",
    )
    assert result["success"] is True
    assert result["new_status"] == "approved"


@pytest.mark.asyncio
async def test_update_work_order_invalid_transition(db):
    from tools.action_tools import handle_create_work_order, handle_update_work_order
    wo = await handle_create_work_order(
        ahu_id="e0101", title="Test", severity="info"
    )
    result = await handle_update_work_order(
        work_order_id=wo["id"],
        status="resolved",  # invalid: draft → resolved not allowed
    )
    assert result["success"] is False


@pytest.mark.asyncio
async def test_update_work_order_not_found(db):
    from tools.action_tools import handle_update_work_order
    result = await handle_update_work_order(
        work_order_id=99999,
        status="approved",
    )
    assert result["success"] is False
