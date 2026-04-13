import os
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import db_reader
from core.healthdb import HealthDB


# Patch DB before app import so the route uses the test DB
@pytest.fixture()
def client_with_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.duckdb")
    db = HealthDB(db_path)
    row = {
        "timestamp": pd.Timestamp("2026-04-01 10:00:00+00:00"),
        "ahu_id": "e0101", "level": 1, "health_index": 75.0, "tier": "Monitor",
        "energy_anomaly": 0.3, "pf_degradation": 0.2, "phase_imbalance": 0.1,
        "thd_drift": 0.05, "overload": 0.4,
        "raw_power_total": 0.9, "raw_energy_import": 10000.0,
        "raw_hourly_delta": 2.0, "raw_predicted_delta": 1.5,
        "raw_energy_anomaly_raw": 0.5, "raw_power_factor_avg": 0.88,
        "raw_current_unbalance": 2.0, "raw_composite_thd": 3.0,
        "raw_apparent_power_total": 3.7,
        "raw_current_l1": 5.5, "raw_current_l2": 5.2, "raw_current_l3": 5.4,
        "raw_volts_l1_n": 233.0, "raw_volts_l2_n": 234.0, "raw_volts_l3_n": 232.0,
        "raw_current_l1_thd": 2.6, "raw_current_l3_thd": 1.5,
        "raw_volts_l1_thd": 2.8, "raw_volts_l2_thd": 2.4, "raw_volts_l3_thd": 2.2,
        "raw_nema_voltage_imbalance": 0.66, "raw_p95_current": 5.6, "safety_flags": "",
    }
    db.upsert(pd.DataFrame([row]))
    monkeypatch.setattr(db_reader, "_DB_PATH", db_path)
    db_reader._DB_INSTANCES.clear()
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DEV_API_KEY", "test-key")

    from main import app
    return TestClient(app, headers={"Authorization": "Bearer test-key"})


def test_get_off_periods_known_device_always_on(client_with_db):
    resp = client_with_db.get("/api/on-off-periods/e0101?range=7d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ahu_id"] == "e0101"
    assert body["range"] == "7d"
    assert body["off_periods"] == []


def test_get_off_periods_unknown_device(client_with_db):
    resp = client_with_db.get("/api/on-off-periods/e9999?range=7d")
    assert resp.status_code == 404


def test_get_off_periods_invalid_range(client_with_db):
    resp = client_with_db.get("/api/on-off-periods/e0101?range=bad")
    assert resp.status_code == 400
