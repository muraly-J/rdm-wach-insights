import os
import sys
import pytest
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.healthdb import HealthDB


@pytest.fixture
def db(tmp_path):
    """Fresh in-file HealthDB for each test."""
    return HealthDB(str(tmp_path / "test.duckdb"))


def test_schema_created(db):
    """Tables and indexes are created on init."""
    result = db._conn().execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name='health_hourly'"
    ).fetchone()
    assert result is not None, "health_hourly table should exist"


def test_upsert_and_count(db):
    """upsert() inserts rows; duplicate primary keys replace."""
    df = pd.DataFrame([{
        "timestamp": pd.Timestamp("2026-03-01 00:00:00", tz="UTC"),
        "ahu_id": "e0101", "level": 1,
        "health_index": 85.0, "tier": "Healthy",
        "energy_anomaly": 0.0, "pf_degradation": 0.0,
        "phase_imbalance": 0.0, "thd_drift": 0.0, "overload": 0.0,
        "raw_power_total": 10.0, "raw_energy_import": 100.0,
        "raw_hourly_delta": 1.0, "raw_predicted_delta": 1.0,
        "raw_energy_anomaly_raw": 0.0, "raw_power_factor_avg": 0.92,
        "raw_current_unbalance": 1.0, "raw_composite_thd": 2.0,
        "raw_apparent_power_total": 11.0,
        "raw_current_l1": 5.0, "raw_current_l2": 5.0, "raw_current_l3": 5.0,
        "raw_volts_l1_n": 230.0, "raw_volts_l2_n": 230.0, "raw_volts_l3_n": 230.0,
        "raw_current_l1_thd": 2.0, "raw_current_l3_thd": 2.0,
        "raw_volts_l1_thd": 1.0, "raw_volts_l2_thd": 1.0, "raw_volts_l3_thd": 1.0,
        "raw_nema_voltage_imbalance": 0.5, "raw_p95_current": 6.0,
        "safety_flags": "",
    }])
    rows = db.upsert(df)
    assert rows == 1

    # Upsert same primary key with updated value
    df2 = df.copy()
    df2["health_index"] = 70.0
    db.upsert(df2)

    result = db._conn().execute(
        "SELECT health_index FROM health_hourly WHERE ahu_id='e0101'"
    ).fetchone()
    assert result[0] == pytest.approx(70.0), "Duplicate PK should update value"


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_row(ahu_id: str, level: int, timestamp: str, health_index: float) -> dict:
    return {
        "timestamp": pd.Timestamp(timestamp, tz="UTC"),
        "ahu_id": ahu_id, "level": level,
        "health_index": health_index, "tier": "Healthy",
        "energy_anomaly": 0.1, "pf_degradation": 0.2,
        "phase_imbalance": 0.1, "thd_drift": 0.05, "overload": 0.0,
        "raw_power_total": 10.0, "raw_energy_import": 100.0,
        "raw_hourly_delta": 1.0, "raw_predicted_delta": 1.0,
        "raw_energy_anomaly_raw": 0.0, "raw_power_factor_avg": 0.92,
        "raw_current_unbalance": 1.0, "raw_composite_thd": 2.0,
        "raw_apparent_power_total": 11.0,
        "raw_current_l1": 5.0, "raw_current_l2": 5.0, "raw_current_l3": 5.0,
        "raw_volts_l1_n": 230.0, "raw_volts_l2_n": 230.0, "raw_volts_l3_n": 230.0,
        "raw_current_l1_thd": 2.0, "raw_current_l3_thd": 2.0,
        "raw_volts_l1_thd": 1.0, "raw_volts_l2_thd": 1.0, "raw_volts_l3_thd": 1.0,
        "raw_nema_voltage_imbalance": 0.5, "raw_p95_current": 6.0,
        "safety_flags": "",
    }


@pytest.fixture
def db_with_data(tmp_path):
    db = HealthDB(str(tmp_path / "test.duckdb"))
    rows = [
        _make_row("e0101", 1, "2026-03-27 00:00:00", 85.0),
        _make_row("e0101", 1, "2026-03-27 01:00:00", 83.0),  # latest for e0101
        _make_row("e0102", 1, "2026-03-27 00:00:00", 60.0),
        _make_row("e0102", 1, "2026-03-27 01:00:00", 58.0),  # latest for e0102
        _make_row("e0201", 2, "2026-03-27 01:00:00", 90.0),  # level 2
    ]
    db.upsert(pd.DataFrame(rows))
    return db


def test_get_latest_snapshot_all(db_with_data):
    """Returns one row per AHU (latest timestamp)."""
    result = db_with_data.get_latest_snapshot()
    assert len(result) == 3  # e0101, e0102, e0201
    e0101 = result[result["ahu_id"] == "e0101"].iloc[0]
    assert e0101["health_index"] == pytest.approx(83.0)


def test_get_latest_snapshot_by_level(db_with_data):
    """Filter to one level returns only that level's AHUs."""
    result = db_with_data.get_latest_snapshot(level=1)
    assert set(result["ahu_id"].tolist()) == {"e0101", "e0102"}


def test_get_latest_snapshot_by_ahu_ids(db_with_data):
    """Filter to specific AHU IDs."""
    result = db_with_data.get_latest_snapshot(ahu_ids=["e0101"])
    assert len(result) == 1
    assert result.iloc[0]["ahu_id"] == "e0101"


def test_get_time_range_all(db_with_data):
    """Returns all rows for a device across timestamps."""
    result = db_with_data.get_time_range(ahu_ids=["e0101"])
    assert len(result) == 2


def test_get_time_range_with_start_filter(db_with_data):
    """Start filter excludes earlier rows."""
    result = db_with_data.get_time_range(
        ahu_ids=["e0101"],
        start="2026-03-27T01:00:00Z"
    )
    assert len(result) == 1
    assert result.iloc[0]["health_index"] == pytest.approx(83.0)


def test_get_time_range_metrics_filter(db_with_data):
    """Requesting specific metrics returns only those columns + identity columns."""
    result = db_with_data.get_time_range(
        ahu_ids=["e0101"],
        metrics=["health_index", "pf_degradation"]
    )
    assert "health_index" in result.columns
    assert "pf_degradation" in result.columns
    assert "raw_power_total" not in result.columns


def test_get_ranking_worst_first(db_with_data):
    """asc order returns lowest health_index first (worst AHU first)."""
    result = db_with_data.get_ranking(level=1, metric="health_index", n=2, order="asc")
    assert result.iloc[0]["ahu_id"] == "e0102"  # 58.0 < 83.0


def test_get_ranking_best_first(db_with_data):
    """desc order returns highest health_index first."""
    result = db_with_data.get_ranking(level=1, metric="health_index", n=2, order="desc")
    assert result.iloc[0]["ahu_id"] == "e0101"


def test_get_latest_timestamp(db_with_data):
    """Returns the most recent timestamp across all rows."""
    ts = db_with_data.get_latest_timestamp()
    assert ts is not None
    assert ts.year == 2026
    assert ts.month == 3
    assert ts.day == 27
    assert ts.hour == 1


def test_get_latest_timestamp_empty_db(tmp_path):
    """Returns None when DB is empty."""
    db = HealthDB(str(tmp_path / "empty.duckdb"))
    assert db.get_latest_timestamp() is None
