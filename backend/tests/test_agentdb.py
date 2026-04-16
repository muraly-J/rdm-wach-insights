"""Tests for AgentDB — work_orders, agent_state, watchman_queue tables."""
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def db(tmp_path):
    from core.agentdb import AgentDB
    return AgentDB(str(tmp_path / "test_agent.duckdb"))


def test_create_work_order(db):
    wo_id = db.create_work_order(
        ahu_id="e0402",
        level=4,
        title="Phase imbalance detected",
        description="Current unbalance >10%",
        severity="warning",
        trigger_source="chat",
        fair_snapshot={"F": 72, "A": 55, "I": 40, "R": 88, "composite": 63},
    )
    assert isinstance(wo_id, int)
    assert wo_id > 0


def test_get_work_order(db):
    wo_id = db.create_work_order(
        ahu_id="e0101",
        level=1,
        title="Test",
        severity="info",
    )
    wo = db.get_work_order(wo_id)
    assert wo["ahu_id"] == "e0101"
    assert wo["status"] == "draft"
    assert wo["created_by"] == "agent"


def test_list_draft_work_orders(db):
    db.create_work_order(ahu_id="e0101", level=1, title="Draft 1", severity="warning")
    db.create_work_order(ahu_id="e0102", level=1, title="Draft 2", severity="warning")
    drafts = db.list_work_orders(status="draft")
    assert len(drafts) == 2


def test_update_work_order_status(db):
    wo_id = db.create_work_order(
        ahu_id="e0101", level=1, title="Test", severity="critical"
    )
    db.update_work_order(wo_id, status="approved", approved_by="user")
    wo = db.get_work_order(wo_id)
    assert wo["status"] == "approved"
    assert wo["approved_by"] == "user"


def test_invalid_status_transition_raises(db):
    wo_id = db.create_work_order(
        ahu_id="e0101", level=1, title="Test", severity="info"
    )
    db.update_work_order(wo_id, status="resolved")  # draft -> resolved is invalid
    wo = db.get_work_order(wo_id)
    assert wo["status"] == "draft"


def test_set_and_get_agent_state(db):
    db.set_agent_state("last_alert:e0402", {"alerted": True})
    val = db.get_agent_state("last_alert:e0402")
    assert val is not None
    assert val["alerted"] is True


def test_get_missing_agent_state_returns_none(db):
    val = db.get_agent_state("nonexistent:key")
    assert val is None


def test_agent_state_expired_returns_none(db):
    from datetime import datetime, timezone, timedelta
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db.set_agent_state("stale:key", {"data": 1}, expires_at=past)
    val = db.get_agent_state("stale:key")
    assert val is None


def test_enqueue_and_dequeue_watchman_alert(db):
    db.enqueue_watchman_alert(ahu_id="e0301", level=3, fair_score=35.0, severity="critical")
    db.enqueue_watchman_alert(ahu_id="e0302", level=3, fair_score=50.0, severity="warning")
    alerts = db.dequeue_watchman_alerts()
    assert len(alerts) == 2
    assert alerts[0]["ahu_id"] == "e0301"
    # After dequeue, they should be marked processed
    alerts_again = db.dequeue_watchman_alerts()
    assert len(alerts_again) == 0
