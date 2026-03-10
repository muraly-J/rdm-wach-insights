"""Tests for backend/core/csv_reader.py"""
import pytest
import pandas as pd
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.csv_reader import (
    get_health_index_series,
    get_score_breakdown,
    get_raw_score_relationship,
)

CSV_PATH = os.path.join(os.path.dirname(__file__), '../../data/health_all_levels.csv')

@pytest.fixture
def csv_has_data():
    """Skip tests if CSV is empty."""
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV not found")
    df = pd.read_csv(CSV_PATH)
    if df.empty:
        pytest.skip("CSV is empty")
    return df

def test_health_index_series_returns_list(csv_has_data):
    result = get_health_index_series(level=1, device_id=None, time_range="7d")
    assert isinstance(result, list)
    if result:
        item = result[0]
        assert 'id' in item
        assert 'name' in item
        assert 'data' in item
        if item['data']:
            assert 'timestamp' in item['data'][0]
            assert 'value' in item['data'][0]


def test_health_index_series_flat_shape(csv_has_data):
    result = get_health_index_series(level=1, device_id=None, time_range="30d")
    assert result
    item = result[0]
    assert 'device' not in item, "Shape is nested — expected flat {id, name, data}"
    assert 'id' in item
    assert 'name' in item
    assert 'data' in item

def test_score_breakdown_returns_fair_scores(csv_has_data):
    result = get_score_breakdown(level=1, time_range="7d")
    assert isinstance(result, list)
    if result:
        device = result[0]
        assert 'id' in device
        assert 'scores' in device
        fair_keys = {'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'}
        assert fair_keys.issubset(device['scores'].keys())
        score = device['scores']['energy_anomaly']
        assert 'current' in score
        assert 'trend' in score
        assert 'data' in score

def test_score_values_are_0_to_100(csv_has_data):
    result = get_score_breakdown(level=1, time_range="30d")
    assert result
    # At least one score across all devices must be >= 1.0 — confirms 0-100 scale not 0-1
    max_seen = 0.0
    for device in result:
        for score_name, score in device['scores'].items():
            max_seen = max(max_seen, score['current'])
    assert max_seen >= 1.0, (
        f"All scores look like 0-1 fractions (max seen = {max_seen}); expected 0-100 scale"
    )


def test_raw_score_relationship_has_raw_and_score(csv_has_data):
    df = csv_has_data
    device_id = df['ahu_id'].iloc[0]
    result = get_raw_score_relationship(device_id=device_id, time_range="7d")
    assert isinstance(result, dict)
    if result:
        score_key = list(result.keys())[0]
        entry = result[score_key]
        assert 'rawMetric' in entry
        assert 'rawUnit' in entry
        assert 'rawData' in entry
        assert 'scoreData' in entry


# API endpoint tests
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_level_scores_returns_fair_names():
    resp = client.get("/api/level/1/scores?time_range=7d")
    assert resp.status_code == 200
    data = resp.json()
    assert 'devices' in data
    if data['devices']:
        scores = data['devices'][0]['scores']
        # Must NOT have fake names
        fake_names = {'temperature', 'vibration', 'pressure', 'airflow', 'energy'}
        actual_names = set(scores.keys())
        assert not actual_names.intersection(fake_names), \
            f"Found fake score names: {actual_names.intersection(fake_names)}"
        # Must have FAIR names
        fair_names = {'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'}
        assert fair_names.issubset(actual_names), \
            f"Missing FAIR score names: {fair_names - actual_names}"
