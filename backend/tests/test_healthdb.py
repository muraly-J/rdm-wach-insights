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
