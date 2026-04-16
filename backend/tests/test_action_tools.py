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
        severity="critical",
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
