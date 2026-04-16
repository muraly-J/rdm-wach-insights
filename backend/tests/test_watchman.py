"""Tests for the Watchman pulse threshold logic."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("WATCHMAN_ENABLED", "true")
os.environ.setdefault("WATCHMAN_CRITICAL_THRESHOLD", "40.0")
os.environ.setdefault("WATCHMAN_WARNING_THRESHOLD", "60.0")


@pytest.fixture
def agent_db(tmp_path):
    from core.agentdb import AgentDB
    return AgentDB(str(tmp_path / "test.duckdb"))


def test_classify_score_critical():
    from core.watchman import classify_score
    assert classify_score(35.0) == "critical"


def test_classify_score_warning():
    from core.watchman import classify_score
    assert classify_score(55.0) == "warning"


def test_classify_score_healthy():
    from core.watchman import classify_score
    assert classify_score(75.0) is None


def test_classify_score_boundary_critical():
    from core.watchman import classify_score
    assert classify_score(40.0) == "warning"  # 40.0 is not < 40 → warning


def test_is_in_cooldown_no_state_returns_false(agent_db):
    from core.watchman import is_in_cooldown
    result = is_in_cooldown(agent_db, "e0402", "critical")
    assert result is False


def test_is_in_cooldown_recent_alert_returns_true(agent_db):
    from datetime import datetime, timedelta, timezone

    from core.watchman import is_in_cooldown
    # Set a recent alert in agent state
    expires = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    agent_db.set_agent_state(
        "last_alert:e0402",
        {"notified_at": datetime.now(timezone.utc).isoformat()},
        expires_at=expires,
    )
    result = is_in_cooldown(agent_db, "e0402", "critical")
    assert result is True


@pytest.mark.asyncio
async def test_run_pulse_flags_critical_ahu(agent_db, monkeypatch):
    """Pulse should enqueue critical AHUs."""
    import pandas as pd
    from core.watchman import run_pulse

    # Mock HealthDB.get_latest_snapshot to return one critical AHU
    fake_df = pd.DataFrame([
        {"ahu_id": "e0402", "level": 4, "health_index": 30.0}
    ])

    class FakeHealthDB:
        def get_latest_snapshot(self):
            return fake_df

    monkeypatch.setattr("core.watchman._get_health_db", lambda: FakeHealthDB())
    monkeypatch.setattr("core.watchman._get_agent_db", lambda: agent_db)

    await run_pulse()

    alerts = agent_db.dequeue_watchman_alerts()
    assert len(alerts) == 1
    assert alerts[0]["ahu_id"] == "e0402"
    assert alerts[0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_run_pulse_skips_healthy_ahu(agent_db, monkeypatch):
    import pandas as pd
    from core.watchman import run_pulse

    fake_df = pd.DataFrame([
        {"ahu_id": "e0402", "level": 4, "health_index": 80.0}
    ])

    class FakeHealthDB:
        def get_latest_snapshot(self):
            return fake_df

    monkeypatch.setattr("core.watchman._get_health_db", lambda: FakeHealthDB())
    monkeypatch.setattr("core.watchman._get_agent_db", lambda: agent_db)

    await run_pulse()

    alerts = agent_db.dequeue_watchman_alerts()
    assert len(alerts) == 0
