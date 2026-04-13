"""Tests for history_generator scoring formulas."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'etl'))

import numpy as np
import pandas as pd
from history_generator import compute_ahu_health_score, sigmoid_score


def make_energy_df(ahu_id: str, values: list) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.DataFrame({ahu_id: values}, index=idx)


def _dummy_thd_df(ahu_id: str, n: int = 60) -> pd.DataFrame:
    """Non-empty but flat THD series so concat doesn't crash."""
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({ahu_id: [5.0] * n}, index=idx)


def test_energy_anomaly_zero_when_no_deviation():
    """delta_kwh ≈ 0 means no anomaly → score should be near 0."""
    vals = [5000 + i * 30 for i in range(60)]  # cumulative, ~30 kWh/day
    df_e = make_energy_df("ahu1", vals)
    df_thd = _dummy_thd_df("ahu1")
    result = compute_ahu_health_score(
        ahu_id="ahu1",
        energy_anomaly_val=0.0,   # delta_kwh = 0
        current_pf=0.85,
        current_power=100,
        current_unbalance=0.02,
        current_composite_thd=0.03,
        df_energy=df_e,
        df_pf=pd.DataFrame(),
        df_power=pd.DataFrame(),
        df_unbalance=pd.DataFrame(),
        df_l1_thd=df_thd,
        df_l3_thd=df_thd,
    )
    assert result is not None, "Function returned None (crashed)"
    assert result['risk_scores']['energy_anomaly'] < 0.1, (
        f"Expected near-zero anomaly for delta_kwh=0, got {result['risk_scores']['energy_anomaly']}"
    )


def test_energy_anomaly_high_when_large_positive_delta():
    """Large positive delta_kwh (consumed much more than predicted) → score > 0.5."""
    import random
    random.seed(42)
    vals = [5000 + i * 30 + random.gauss(0, 20) for i in range(60)]
    df_e = make_energy_df("ahu1", vals)
    df_thd = _dummy_thd_df("ahu1")
    # daily_std ≈ 20 kWh; delta_kwh = 200 → z_score = 200/20 = 10 → near max
    result = compute_ahu_health_score(
        ahu_id="ahu1",
        energy_anomaly_val=200.0,
        current_pf=0.85,
        current_power=100,
        current_unbalance=0.02,
        current_composite_thd=0.03,
        df_energy=df_e,
        df_pf=pd.DataFrame(),
        df_power=pd.DataFrame(),
        df_unbalance=pd.DataFrame(),
        df_l1_thd=df_thd,
        df_l3_thd=df_thd,
    )
    assert result is not None, "Function returned None (crashed)"
    assert result['risk_scores']['energy_anomaly'] > 0.5, (
        f"Expected high anomaly for large delta_kwh, got {result['risk_scores']['energy_anomaly']}"
    )
