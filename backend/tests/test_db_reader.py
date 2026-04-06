import os
import sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.healthdb import HealthDB
from core import db_reader

SAMPLE_ROW = {
    "timestamp": pd.Timestamp("2026-04-01 10:00:00+00:00"),
    "ahu_id": "e0101",
    "level": 1,
    "health_index": 75.0,
    "tier": "Monitor",
    "energy_anomaly": 0.3,
    "pf_degradation": 0.2,
    "phase_imbalance": 0.1,
    "thd_drift": 0.05,
    "overload": 0.4,
    "raw_power_total": 0.9,
    "raw_energy_import": 10000.0,
    "raw_hourly_delta": 2.0,
    "raw_predicted_delta": 1.5,
    "raw_energy_anomaly_raw": 0.5,
    "raw_power_factor_avg": 0.88,
    "raw_current_unbalance": 2.0,
    "raw_composite_thd": 3.0,
    "raw_apparent_power_total": 3.7,
    "raw_current_l1": 5.5,
    "raw_current_l2": 5.2,
    "raw_current_l3": 5.4,
    "raw_volts_l1_n": 233.0,
    "raw_volts_l2_n": 234.0,
    "raw_volts_l3_n": 232.0,
    "raw_current_l1_thd": 2.6,
    "raw_current_l3_thd": 1.5,
    "raw_volts_l1_thd": 2.8,
    "raw_volts_l2_thd": 2.4,
    "raw_volts_l3_thd": 2.2,
    "raw_nema_voltage_imbalance": 0.66,
    "raw_p95_current": 5.6,
    "safety_flags": "",
}


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """Seed a temp DuckDB and monkeypatch db_reader to use it."""
    db_path = str(tmp_path / "test.duckdb")
    db = HealthDB(db_path)
    df = pd.DataFrame([SAMPLE_ROW])
    db.upsert(df)
    monkeypatch.setattr(db_reader, "_DB_PATH", db_path)
    return db


def test_get_health_index_series(seeded_db):
    result = db_reader.get_health_index_series(level=1, device_id=None, time_range="7d")
    assert len(result) == 1
    assert result[0]["id"] == "e0101"
    assert len(result[0]["data"]) == 1
    assert result[0]["data"][0]["value"] == 75.0


def test_get_score_breakdown(seeded_db):
    result = db_reader.get_score_breakdown(level=1, time_range="7d")
    assert len(result) == 1
    assert "health_index" in result[0]["scores"]
    assert result[0]["scores"]["health_index"]["current"] == 75.0


def test_get_raw_score_relationship(seeded_db):
    result = db_reader.get_raw_score_relationship(device_id="e0101", time_range="7d")
    assert "energy_anomaly" in result
    assert len(result["energy_anomaly"]["series"]) > 0


def test_get_dataframe(seeded_db):
    df = db_reader.get_dataframe(level=1, time_range="7d")
    assert not df.empty
    assert "health_index" in df.columns
    assert df.iloc[0]["level"] == 1  # integer, not "Level 1"


def test_get_health_index_series_device_filter(tmp_path, monkeypatch):
    """Device ID filter returns only the matching AHU."""
    from core.healthdb import HealthDB
    import core.db_reader as dr

    db_path = str(tmp_path / "test2.duckdb")
    db = HealthDB(db_path)
    row1 = SAMPLE_ROW.copy()
    row2 = SAMPLE_ROW.copy()
    row2["ahu_id"] = "e0102"
    db.upsert(pd.DataFrame([row1, row2]))
    monkeypatch.setattr(dr, "_DB_PATH", db_path)

    result = dr.get_health_index_series(level=1, device_id="e0101", time_range="7d")
    assert len(result) == 1
    assert result[0]["id"] == "e0101"


def test_get_health_index_series_30d_resamples(tmp_path, monkeypatch):
    """30d path resamples two hourly rows on different days into two daily points."""
    from core.healthdb import HealthDB
    import core.db_reader as dr

    db_path = str(tmp_path / "test3.duckdb")
    db = HealthDB(db_path)
    row1 = SAMPLE_ROW.copy()  # 2026-04-01 10:00 UTC
    row2 = SAMPLE_ROW.copy()
    row2["timestamp"] = pd.Timestamp("2026-03-31 10:00:00+00:00")
    row2["health_index"] = 80.0
    db.upsert(pd.DataFrame([row1, row2]))
    monkeypatch.setattr(dr, "_DB_PATH", db_path)

    result = dr.get_health_index_series(level=1, device_id=None, time_range="30d")
    assert len(result) == 1  # one AHU
    assert len(result[0]["data"]) == 2  # two daily points
