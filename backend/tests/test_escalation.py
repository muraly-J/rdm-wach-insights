import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_list_stale_tickets_returns_overdue(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    import core.agentdb as agentdb_module
    from core.agentdb import AgentDB

    db = AgentDB(db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr(agentdb_module, "_db_instance", db)

    # Create a work order, then manually set created_at 3 hours ago, priority=Critical, status=open
    wo_id = db.create_work_order(
        ahu_id="e0101",
        level=1,
        title="High THD",
        severity="Critical",
        description="THD exceeded",
        trigger_source="manual",
        status="open",
    )

    old_time = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    ticket_no = "TCK-TEST-001"
    with db._connect() as conn:
        conn.execute(
            """
            UPDATE work_orders
            SET created_at = ?, priority = 'Critical', ticket_no = ?
            WHERE id = ?
            """,
            [old_time, ticket_no, wo_id],
        )

    stale = db.list_stale_tickets()
    assert len(stale) >= 1
    assert any(r["ticket_no"] == "TCK-TEST-001" for r in stale)


def test_list_stale_tickets_excludes_claimed(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    import core.agentdb as agentdb_module
    from core.agentdb import AgentDB

    db = AgentDB(db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr(agentdb_module, "_db_instance", db)

    wo_id = db.create_work_order(
        ahu_id="e0102",
        level=1,
        title="Claimed issue",
        severity="Critical",
        description="desc",
        trigger_source="manual",
        status="open",
    )

    old_time = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    ticket_no = "TCK-TEST-002"
    with db._connect() as conn:
        conn.execute(
            """
            UPDATE work_orders
            SET created_at = ?, priority = 'Critical', ticket_no = ?, claimed_by = 'tech_user_1'
            WHERE id = ?
            """,
            [old_time, ticket_no, wo_id],
        )

    stale = db.list_stale_tickets()
    assert not any(r["ticket_no"] == "TCK-TEST-002" for r in stale)
