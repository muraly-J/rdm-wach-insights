"""Tests for financial impact calculations including kVA demand charge (GAP-001)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch

import pandas as pd


def _mock_df():
    """Minimal DataFrame matching db_reader.get_dataframe() output."""
    now = pd.Timestamp.now(tz="UTC")
    return pd.DataFrame({
        'timestamp':                [now,     now],
        'ahu_id':                   ['e0101', 'e0101'],
        'level':                    [1,       1],
        'health_index':             [75.0,    72.0],
        'raw_hourly_delta':         [10.0,    12.0],
        'raw_predicted_delta':      [8.0,     9.0],
        'raw_power_factor_avg':     [0.90,    0.91],
        'raw_apparent_power_total': [50.0,    60.0],
    })


def test_demand_charge_present_in_response():
    """Response must contain demand_charge_myr field."""
    with patch('core.db_reader.get_dataframe', return_value=_mock_df()):
        from routes.financial_impact import _compute_impact
        result = _compute_impact(level=1, time_range="30d")
    assert "demand_charge_myr" in result, \
        f"demand_charge_myr missing. Keys: {list(result.keys())}"


def test_demand_charge_calculation(monkeypatch):
    """demand_charge_myr = max_demand_rate × peak kVA in period."""
    mock_cfg = {
        "tariff_rate": 0.365,
        "max_demand_rate": 30.30,   # RM/kVA/month
        "planned_maintenance_cost": 500.0,
        "emergency_multiplier": 3.0,
        "currency": "RM",
    }

    # Controlled stub DataFrame — known values for predictable assertion
    stub_df = pd.DataFrame([{
        "timestamp": pd.Timestamp("2026-04-01 10:00:00+00:00"),
        "ahu_id": "e0101",
        "level": 1,
        "health_index": 90.0,
        "tier": "Healthy",
        "raw_hourly_delta": 2.0,
        "raw_predicted_delta": 1.5,
        "raw_power_factor_avg": 0.95,  # above 0.85 so no PF penalty
        "raw_apparent_power_total": 10.0,  # kVA — demand charge = 10.0 * max_demand_rate
    }])

    with patch("core.db_reader.get_dataframe", return_value=stub_df), \
         patch('routes.financial_impact._load_config', return_value=mock_cfg):
        from routes.financial_impact import _compute_impact
        result = _compute_impact(level=1, time_range="7d", device_id=None)

    # max_demand_rate default = 30.30 RM/kVA/month, peak_kva = 10.0
    expected_demand = round(10.0 * 30.30, 2)
    assert result["demand_charge_myr"] == expected_demand, \
        f"Expected {expected_demand}, got {result['demand_charge_myr']}"
    assert result["pf_penalty_cost"] == 0.0, \
        f"PF 0.95 > 0.85 — expected no penalty, got {result['pf_penalty_cost']}"
    assert result["grand_total"] > 0


def test_demand_charge_in_grand_total():
    """grand_total must equal the sum of all four cost components."""
    with patch('core.db_reader.get_dataframe', return_value=_mock_df()):
        from routes.financial_impact import _compute_impact
        result = _compute_impact(level=1, time_range="30d")
    expected_total = round(
        result["excess_energy_cost"]
        + result["pf_penalty_cost"]
        + result["maintenance_risk"]
        + result["demand_charge_myr"],
        2
    )
    assert result["grand_total"] == expected_total, \
        f"grand_total {result['grand_total']} ≠ sum of components {expected_total}"


def test_empty_response_has_demand_charge_zero():
    """_empty_response must include demand_charge_myr: 0."""
    with patch('core.db_reader.get_dataframe', return_value=pd.DataFrame()):
        from routes.financial_impact import _compute_impact
        result = _compute_impact(level=99, time_range="30d")
    assert result.get("demand_charge_myr") == 0, \
        f"empty response demand_charge_myr should be 0, got {result.get('demand_charge_myr')}"


def test_top_ahus_have_demand_charge_field():
    """Each AHU entry in top_ahus must include demand_charge_myr."""
    with patch('core.db_reader.get_dataframe', return_value=_mock_df()):
        from routes.financial_impact import _compute_impact
        result = _compute_impact(level=1, time_range="30d")
    for ahu in result.get("top_ahus", []):
        assert "demand_charge_myr" in ahu, \
            f"top_ahus entry {ahu.get('ahu_id')} missing demand_charge_myr"
