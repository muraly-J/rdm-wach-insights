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


def test_approve_nonexistent_work_order_returns_404(client):
    resp = client.post("/api/work-orders/99999/approve")
    assert resp.status_code == 404
