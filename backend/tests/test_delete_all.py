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


def test_delete_all_work_orders_returns_200(client):
    resp = client.delete("/api/work-orders")
    assert resp.status_code == 200
    data = resp.json()
    assert "deleted" in data
    assert isinstance(data["deleted"], int)


def test_delete_all_leaves_empty_list(client):
    # Seed a work order first
    from core import agentdb as agentdb_module
    agentdb_module._db_instance.create_work_order(
        ahu_id="e0101", level=1, title="Test WO", severity="warning"
    )

    # Confirm it exists
    resp = client.get("/api/work-orders")
    assert resp.json()["count"] >= 1

    # Delete all
    del_resp = client.delete("/api/work-orders")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] >= 1

    # Confirm empty
    resp = client.get("/api/work-orders")
    assert resp.json()["count"] == 0
