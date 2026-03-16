import numpy as np
import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta

from core.prediction_engine import (
    _compute_1h_pred,
    _compute_same_hour_pred,
    _compute_delta_kwh,
    compute_predictions,
)


def make_series(values, start_hour=0):
    """Helper: build pd.Series with hourly DatetimeIndex."""
    idx = pd.date_range(
        start=datetime(2026, 3, 9, start_hour, tzinfo=timezone.utc),
        periods=len(values),
        freq="h",
    )
    return pd.Series(values, index=idx)


def test_linear_trend_1h():
    """Linear series → pred = last + slope."""
    s = make_series([10.0, 11.0, 12.0, 13.0])
    pred = _compute_1h_pred(s)
    assert abs(pred - 14.0) < 0.01


def test_same_hour_avg_12h():
    """Same-hour slots across 3 weeks average correctly."""
    base = datetime(2026, 2, 23, 0, tzinfo=timezone.utc)
    full_idx = pd.date_range(base, periods=21 * 24, freq="h")
    s = pd.Series(0.0, index=full_idx)
    for i in range(21):
        dt = base + timedelta(days=i)
        s[dt] = float(i + 1)
    pred = _compute_same_hour_pred(s, target_hour=0, n_slots=3)
    assert abs(pred - np.mean([19.0, 20.0, 21.0])) < 0.01


def test_delta_kwh_baseline():
    """delta = predicted - 3-week same-hour mean."""
    full_idx = pd.date_range(
        datetime(2026, 2, 23, 0, tzinfo=timezone.utc), periods=21 * 24, freq="h"
    )
    s = pd.Series(10.0, index=full_idx)
    delta = _compute_delta_kwh(predicted_energy=12.0, energy_series=s, target_hour=0)
    assert abs(delta - 2.0) < 0.01


def test_insufficient_data_1h():
    """Series with < 2 points returns None."""
    s = make_series([10.0])
    result = _compute_1h_pred(s)
    assert result is None


def test_predict_fair_scores_smoke(mocker):
    """Predicted measurements feed into score functions without crashing."""
    mocker.patch(
        "core.prediction_engine._fetch_3week_hourly",
        return_value=_make_mock_df(),
    )
    result = compute_predictions("e0202", horizons=["1h"])
    assert result is not None
    h = result["horizons"]["1h"]
    assert 0 <= h["predicted_health_index"] <= 100
    for k in ("energy_anomaly", "power_factor", "phase_imbalance", "thd_drift", "overload"):
        assert 0 <= h["fair_scores"][k] <= 1


def test_health_index_range(mocker):
    """Predicted health index is always in [0, 100]."""
    mocker.patch(
        "core.prediction_engine._fetch_3week_hourly",
        return_value=_make_mock_df(),
    )
    result = compute_predictions("e0202", horizons=["1h", "12h", "24h", "168h"])
    for h_key, h_data in result["horizons"].items():
        assert 0 <= h_data["predicted_health_index"] <= 100, f"OOB for horizon {h_key}"


def _make_mock_df():
    """Create a plausible 3-week hourly DataFrame for e0202."""
    idx = pd.date_range(
        datetime(2026, 2, 23, 0, tzinfo=timezone.utc), periods=504, freq="h"
    )
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "power_total": rng.uniform(7.0, 10.0, 504),
            "energy_import": rng.uniform(10.0, 15.0, 504),
            "power_factor_avg": rng.uniform(0.85, 0.95, 504),
            "current_unbalance": rng.uniform(0.5, 2.5, 504),
            "composite_thd": rng.uniform(2.0, 6.0, 504),
        },
        index=idx,
    )
