"""Tests for AgentDB — work_orders, agent_state, watchman_queue tables."""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

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
    result = db.update_work_order(wo_id, status="pending_tech_review")
    assert result is True
    result2 = db.update_work_order(wo_id, status="open", approved_by="user")
    assert result2 is True
    wo = db.get_work_order(wo_id)
    assert wo["status"] == "open"
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
    from datetime import datetime, timedelta, timezone
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


def test_pending_tech_review_transition(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    result = db.update_work_order(wo_id, status="pending_tech_review")
    assert result is True
    assert db.get_work_order(wo_id)["status"] == "pending_tech_review"


def test_pending_tech_review_to_open(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="pending_tech_review")
    result = db.update_work_order(wo_id, status="open")
    assert result is True
    assert db.get_work_order(wo_id)["status"] == "open"


def test_assigned_to_stored_and_retrieved(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="pending_tech_review")
    result = db.update_work_order(wo_id, status="open", assigned_to="any")
    assert result is True
    wo = db.get_work_order(wo_id)
    assert wo["assigned_to"] == "any"


def test_assigned_to_specific_technician(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="pending_tech_review")
    result = db.update_work_order(wo_id, status="open", assigned_to="123456789")
    assert result is True
    wo = db.get_work_order(wo_id)
    assert wo["assigned_to"] == "123456789"


def test_list_work_orders_by_assigned_to(db):
    wo1 = db.create_work_order(ahu_id="e0101", level=1, title="T1", severity="warning")
    wo2 = db.create_work_order(ahu_id="e0102", level=1, title="T2", severity="warning")
    db.update_work_order(wo1, status="pending_tech_review")
    db.update_work_order(wo2, status="pending_tech_review")
    assert db.update_work_order(wo1, status="open", assigned_to="any") is True
    assert db.update_work_order(wo2, status="open", assigned_to="999") is True
    results = db.list_work_orders(assigned_to="any")
    assert len(results) == 1
    assert results[0]["id"] == wo1


def test_invalid_transition_from_resolved(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="pending_tech_review")
    db.update_work_order(wo_id, status="open")
    db.update_work_order(wo_id, status="in_progress")
    db.update_work_order(wo_id, status="resolved")
    result = db.update_work_order(wo_id, status="in_progress")
    assert result is False
