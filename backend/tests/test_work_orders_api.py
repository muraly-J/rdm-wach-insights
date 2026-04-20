"""Tests for /api/work-orders endpoints."""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["API_KEY"] = "test-key"
os.environ["DEV_API_KEY"] = "test-key"


@pytest.fixture
def client(tmp_path, monkeypatch):
    from core import agentdb as agentdb_module
    from core.agentdb import AgentDB

    temp_db = AgentDB(str(tmp_path / "test.duckdb"))
    monkeypatch.setattr(agentdb_module, "_db_instance", temp_db)

    from main import app

    return TestClient(app, headers={"Authorization": "Bearer test-key"})


def test_list_work_orders_empty(client):
    resp = client.get("/api/work-orders")
    assert resp.status_code == 200
    assert resp.json()["work_orders"] == []


def test_list_draft_work_orders(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")

    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)

    resp = client.get("/api/work-orders?status=draft")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["work_orders"]) == 1
    assert data["work_orders"][0]["ahu_id"] == "e0402"


def test_approve_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")

    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)

    resp = client.post(f"/api/work-orders/{wo_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_dismiss_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0101", level=1, title="Test", severity="info")

    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)

    resp = client.post(f"/api/work-orders/{wo_id}/dismiss")
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


def test_sendback_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="pending_approval")
    db.update_work_order(wo_id, status="approved")
    db.update_work_order(wo_id, status="in_progress")

    import duckdb

    with duckdb.connect(db._path) as conn:
        conn.execute(
            "UPDATE work_orders SET status = ? WHERE id = ?", ["pending_engineer_review", wo_id]
        )

    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/sendback")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_approval"


def test_approve_nonexistent_work_order_returns_404(client):
    resp = client.post("/api/work-orders/99999/approve")
    assert resp.status_code == 404


def test_push_to_engineers(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/push-to-engineers")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_engineer_review"


def test_start_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="approved", assigned_to="any")
    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_resolve_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="approved")
    db.update_work_order(wo_id, status="in_progress")
    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/resolve", json={"notes": "Fixed the fan."})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_assign_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="approved")
    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/assign", json={"assigned_to": "123456789"})
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] == "123456789"


def test_list_work_orders_filter_assigned_to(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo1 = db.create_work_order(ahu_id="e0101", level=1, title="T1", severity="warning")
    wo2 = db.create_work_order(ahu_id="e0102", level=1, title="T2", severity="warning")
    db.update_work_order(wo1, status="approved", assigned_to="any")
    db.update_work_order(wo2, status="approved", assigned_to="999")
    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.get("/api/work-orders?assigned_to=any")
    assert resp.status_code == 200
    assert len(resp.json()["work_orders"]) == 1


def test_sendback_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="pending_engineer_review")
    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/sendback")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_approval"


def test_delete_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB

    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    import core.agentdb as m

    monkeypatch.setattr(m, "_db_instance", db)

    # Verify the work order exists
    resp = client.get(f"/api/work-orders/{wo_id}")
    assert resp.status_code == 200

    # Delete the work order
    resp = client.delete(f"/api/work-orders/{wo_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Verify it's deleted
    resp = client.get(f"/api/work-orders/{wo_id}")
    assert resp.status_code == 404


def test_delete_nonexistent_work_order_returns_404(client):
    resp = client.delete("/api/work-orders/99999")
    assert resp.status_code == 404
