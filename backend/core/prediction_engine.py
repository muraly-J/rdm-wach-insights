"""
prediction_engine.py
────────────────────
Math-only prediction engine for AHU health index and FAIR scores.

Exports:
    _compute_1h_pred          – linear OLS 1-hour-ahead prediction
    _compute_same_hour_pred   – same-hour-of-day average across past n weeks
    _compute_delta_kwh        – predicted energy delta vs 3-week baseline
    _compute_yesterday_pred   – same hour value from 24h ago
    _compute_lastweek_pred    – same hour value from 168h ago
    compute_predictions       – full prediction bundle for one device
    compute_predictions_async – async wrapper around compute_predictions
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Awaitable, Optional

import numpy as np
import pandas as pd

from core.fair_health_scoring import (
    build_baselines,
    calculate_health_index,
    score_energy_anomaly,
    score_overload,
    score_phase_imbalance,
    score_power_factor,
    score_thd_drift,
)

logger = logging.getLogger(__name__)

# Supported forecast horizons (hours)
DEFAULT_HORIZONS = ["1h", "12h", "24h", "168h"]
_HORIZON_MAP = {
    "1h": 1,
    "12h": 12,
    "24h": 24,
    "168h": 168,
}

# Metrics to fetch from InfluxDB (composite_thd is derived, not a raw metric)
_METRICS = [
    "power_total",
    "energy_import",
    "power_factor_avg",
    "current_unbalance",
    "current_l1_thd",
    "current_l3_thd",
]
# Derived metrics computed after fetch
_DERIVED_METRICS = ["composite_thd"]


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_3week_hourly(device_id: str) -> Optional[pd.DataFrame]:
    """
    Fetch ~3 weeks of hourly data for one device across all required metrics.

    Returns a wide DataFrame with columns:
        power_total, energy_import, power_factor_avg, current_unbalance, composite_thd
    indexed by DatetimeIndex (hourly).
    Returns None on any error.
    """
    try:
        from core.influx_client import fetch_time_series

        frames: dict[str, pd.Series] = {}
        for metric in _METRICS:
            df = fetch_time_series(
                device_ids=[device_id],
                metric=metric,
                time_range="last_30d_hourly",
            )
            if df is None or df.empty or device_id not in df.columns:
                logger.warning("No data for device=%s metric=%s", device_id, metric)
                frames[metric] = pd.Series(dtype=float)
            else:
                frames[metric] = df[device_id]

        wide = pd.DataFrame(frames)

        # Compute composite_thd = max(current_l1_thd, current_l3_thd) row-wise
        # (mirrors the calculation in fair_health_scoring.py)
        l1 = wide.get("current_l1_thd", pd.Series(dtype=float))
        l3 = wide.get("current_l3_thd", pd.Series(dtype=float))
        wide["composite_thd"] = pd.concat([l1, l3], axis=1).max(axis=1)

        wide.index.name = "time"
        return wide if not wide.empty else None
    except Exception as exc:
        logger.error("_fetch_3week_hourly failed for %s: %s", device_id, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CORE MATH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _compute_1h_pred(series: pd.Series) -> Optional[float]:
    """
    Linear OLS trend over the full series → predict one step ahead.

    Returns None if fewer than 2 data points are available.
    """
    s = series.dropna()
    if len(s) < 2:
        return None

    x = np.arange(len(s), dtype=float)
    y = s.values.astype(float)
    # OLS: slope, intercept
    slope = float(np.polyfit(x, y, 1)[0])
    last_val = float(y[-1])
    return last_val + slope


def _compute_trend_pred(series: pd.Series, offset_hours: int) -> Optional[float]:
    """
    Linear OLS trend over the last 4 points → predict offset_hours steps ahead.

    Returns None if fewer than 2 data points are available.
    """
    s = series.dropna()
    if len(s) < 2:
        return None

    tail = s.iloc[-4:] if len(s) >= 4 else s
    x = np.arange(len(tail), dtype=float)
    y = tail.values.astype(float)
    slope = float(np.polyfit(x, y, 1)[0])
    last_val = float(y[-1])
    return last_val + slope * offset_hours


def _compute_same_hour_pred(
    series: pd.Series,
    target_hour: int,
    n_slots: int = 3,
) -> Optional[float]:
    """
    Average the last n_slots occurrences of target_hour across the series.

    Returns None if no matching slots exist.
    """
    s = series.dropna()
    if s.empty:
        return None

    # Filter to rows where hour == target_hour
    matching = s[s.index.hour == target_hour]
    if matching.empty:
        return None

    # Take last n_slots
    slots = matching.iloc[-n_slots:]
    return float(slots.mean())


def _compute_yesterday_pred(series: pd.Series, target_hour: int) -> Optional[float]:
    """Return the value at the same hour exactly 24h before the last timestamp."""
    s = series.dropna()
    if s.empty:
        return None

    last_ts = s.index[-1]
    target_ts = last_ts - timedelta(hours=24)
    # Find closest hour match using target_hour parameter
    matching = s[s.index.hour == target_hour]
    if matching.empty:
        return None
    idx = matching.index.get_indexer([target_ts], method="nearest")[0]
    return float(matching.iloc[idx])


def _compute_lastweek_pred(series: pd.Series, target_hour: int) -> Optional[float]:
    """Return the value at the same hour exactly 168h before the last timestamp."""
    s = series.dropna()
    if s.empty:
        return None

    last_ts = s.index[-1]
    target_ts = last_ts - timedelta(hours=168)
    # Find closest hour match using target_hour parameter
    matching = s[s.index.hour == target_hour]
    if matching.empty:
        return None
    idx = matching.index.get_indexer([target_ts], method="nearest")[0]
    return float(matching.iloc[idx])


def _compute_delta_kwh(
    predicted_energy: float,
    energy_series: pd.Series,
    target_hour: int,
) -> float:
    """
    delta = predicted_energy − 3-week same-hour average of energy_series.

    Falls back to 0.0 if baseline cannot be computed.
    """
    baseline = _compute_same_hour_pred(energy_series, target_hour=target_hour, n_slots=3)
    if baseline is None:
        return 0.0
    return predicted_energy - baseline


# ─────────────────────────────────────────────────────────────────────────────
# METRIC PREDICTION
# ─────────────────────────────────────────────────────────────────────────────

def _predict_metric(series: pd.Series, offset_hours: int) -> Optional[float]:
    """
    Predict the value of a metric `offset_hours` ahead of the last observation.

    Strategy:
      - For 1h: linear OLS trend
      - For 12h+: blend of same-hour-of-day average (3 weeks) and linear trend
    """
    s = series.dropna()
    if len(s) < 2:
        return None

    if offset_hours == 1:
        return _compute_1h_pred(s)

    # Determine target hour
    last_ts = s.index[-1]
    target_ts = last_ts + timedelta(hours=offset_hours)
    target_hour = target_ts.hour

    same_hr = _compute_same_hour_pred(s, target_hour=target_hour, n_slots=3)
    trend = _compute_trend_pred(s, offset_hours=offset_hours)

    if same_hr is None and trend is None:
        return None
    if same_hr is None:
        return trend
    if trend is None:
        return same_hr

    # Blend: 70% same-hour historical, 30% linear trend
    return 0.7 * same_hr + 0.3 * trend


# ─────────────────────────────────────────────────────────────────────────────
# FAIR SCORES FOR PREDICTED VALUES
# ─────────────────────────────────────────────────────────────────────────────

def _predict_fair_scores(
    df: pd.DataFrame,
    device_id: str,
    predictions: dict[str, float],
    offset_hours: int,
) -> tuple[dict[str, float], float]:
    """
    Compute FAIR health scores for the predicted measurement values.

    Returns (fair_scores dict, predicted_health_index).
    """
    # Build baseline df with required columns
    baseline_df = df.copy()
    baseline_df["device_id"] = device_id
    baseline_df["timestamp"] = baseline_df.index
    baseline_df["delta_kwh"] = baseline_df["energy_import"].diff().fillna(0.0)

    # Build per-AHU baselines
    try:
        baselines = build_baselines(baseline_df)
    except Exception as exc:
        logger.warning("build_baselines failed: %s", exc)
        baselines = {}

    b = baselines.get(device_id, {})

    # --- Extract predicted values (with safe fallbacks to last known) ---
    last = df.iloc[-1] if not df.empty else {}

    def _get(key: str, fallback: float = 0.0) -> float:
        val = predictions.get(key)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            if hasattr(last, "__getitem__") and key in last.index:
                return float(last[key])
            return fallback
        return float(val)

    pred_power = _get("power_total", 8.0)
    pred_energy = _get("energy_import", 12.0)
    pred_pf = _get("power_factor_avg", 0.9)
    pred_unbal = _get("current_unbalance", 1.0)
    pred_thd = _get("composite_thd", 4.0)

    # Predicted delta_kwh
    last_ts = df.index[-1] if not df.empty else datetime.now(tz=timezone.utc)
    target_ts = last_ts + timedelta(hours=offset_hours)
    target_hour = target_ts.hour

    delta_kwh = _compute_delta_kwh(
        predicted_energy=pred_energy,
        energy_series=df["energy_import"],
        target_hour=target_hour,
    )

    # 24h rolling mean of composite_thd for predicted value
    thd_series = df["composite_thd"].ffill().fillna(4.0)
    thd_24h_rolling = thd_series.rolling(24, min_periods=1).mean()
    thd_24h_val = float(thd_24h_rolling.iloc[-1]) if not thd_24h_rolling.empty else pred_thd

    # Historical arrays for trend calculation
    hist_delta = baseline_df["delta_kwh"].values
    hist_pf = df["power_factor_avg"].values
    hist_unbal = df["current_unbalance"].values
    hist_thd_24h = thd_24h_rolling.values
    hist_power = df["power_total"].values

    # Baseline statistics (with safe fallbacks)
    def _bstat(metric: str, stat: str, default: float) -> float:
        return float(b.get(metric, {}).get(stat, default))

    # --- Score 1: Energy Anomaly ---
    ea_score, _ = score_energy_anomaly(
        delta_kwh=delta_kwh,
        ahu_median_delta=_bstat("delta_kwh", "median", 0.0),
        ahu_rstd_delta=_bstat("delta_kwh", "rstd", 0.05),
        hist_delta_series=hist_delta,
    )

    # --- Score 2: Power Factor ---
    pf_score, _ = score_power_factor(
        pf=pred_pf,
        power=pred_power,
        ahu_median_pf=_bstat("power_factor_avg", "median", 0.9),
        ahu_rstd_pf=_bstat("power_factor_avg", "rstd", 0.008),
        hist_pf_series=hist_pf,
    )

    # --- Score 3: Phase Imbalance ---
    pi_score, _ = score_phase_imbalance(
        unbal=pred_unbal,
        ahu_median_unbal=_bstat("current_unbalance", "median", 1.0),
        ahu_rstd_unbal=_bstat("current_unbalance", "rstd", 0.15),
        hist_unbal_series=hist_unbal,
    )

    # --- Score 4: THD Drift ---
    thd_score, _ = score_thd_drift(
        thd_24h=thd_24h_val,
        ahu_median_thd=_bstat("composite_thd_24h", "median", 4.0),
        ahu_rstd_thd=_bstat("composite_thd_24h", "rstd", 0.15),
        hist_thd_24h_series=hist_thd_24h,
    )

    # --- Score 5: Overload ---
    ol_score, _ = score_overload(
        power=pred_power,
        ahu_median_power=_bstat("power_total", "median", 8.0),
        ahu_rstd_power=_bstat("power_total", "rstd", 0.05),
        ahu_p95_power=b.get("power_total", {}).get("p95", 9.0),
        hist_power_series=hist_power,
    )

    fair_scores = {
        "energy_anomaly": float(np.clip(ea_score, 0.0, 1.0)),
        "power_factor": float(np.clip(pf_score, 0.0, 1.0)),
        "phase_imbalance": float(np.clip(pi_score, 0.0, 1.0)),
        "thd_drift": float(np.clip(thd_score, 0.0, 1.0)),
        "overload": float(np.clip(ol_score, 0.0, 1.0)),
    }

    health_index = calculate_health_index(fair_scores)
    health_index = float(np.clip(health_index, 0.0, 100.0))

    return fair_scores, health_index


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY PROFILES
# ─────────────────────────────────────────────────────────────────────────────

def _build_history_profile(
    df: pd.DataFrame, offset_days: int, label: str
) -> list[dict]:
    """
    Extract 24h window starting offset_days before the last row.
    Returns list of hourly records with metric values.
    """
    if df.empty:
        return []

    last_ts = df.index[-1]
    start_ts = last_ts - timedelta(days=offset_days) - timedelta(hours=12)
    end_ts = last_ts - timedelta(days=offset_days) + timedelta(hours=12)

    window = df[(df.index >= start_ts) & (df.index <= end_ts)]
    records = []
    for i, (ts, row) in enumerate(window.iterrows()):
        record: dict = {"offset_hours": i, "timestamp": ts.isoformat()}
        for col in df.columns:
            val = row.get(col)
            record[col] = None if (val is None or (isinstance(val, float) and np.isnan(val))) else float(val)
        records.append(record)
    return records


def _build_actuals(df: pd.DataFrame, n_hours: int = 24) -> list[dict]:
    """Return the last n_hours rows as actuals records."""
    if df.empty:
        return []

    tail = df.iloc[-n_hours:] if len(df) >= n_hours else df
    records = []
    for i, (ts, row) in enumerate(tail.iterrows()):
        record: dict = {"offset_hours": i - len(tail) + 1, "timestamp": ts.isoformat()}
        for col in df.columns:
            val = row.get(col)
            record[col] = None if (val is None or (isinstance(val, float) and np.isnan(val))) else float(val)
        records.append(record)
    return records


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINTS
# ─────────────────────────────────────────────────────────────────────────────

def compute_predictions(
    device_id: str,
    horizons: list[str] | None = None,
) -> dict | None:
    """
    Compute multi-horizon predictions for a single AHU device.

    Parameters
    ----------
    device_id : str
        AHU device identifier (e.g. "e0202")
    horizons : list[str] | None
        Subset of ["1h","12h","24h","168h"]. Defaults to all.

    Returns
    -------
    dict or None
        Full prediction bundle, or None if insufficient data.
    """
    if horizons is None:
        horizons = DEFAULT_HORIZONS

    df = _fetch_3week_hourly(device_id)
    if df is None or len(df) < 24:
        logger.warning("Insufficient data for device=%s (got %s rows)", device_id, len(df) if df is not None else 0)
        return None

    now = datetime.now(tz=timezone.utc)
    last_ts = df.index[-1]

    # Build horizon predictions
    horizon_results: dict[str, dict] = {}
    for horizon_key in horizons:
        offset_hours = _HORIZON_MAP.get(horizon_key)
        if offset_hours is None:
            logger.warning("Unknown horizon key: %s", horizon_key)
            continue

        target_ts = last_ts + timedelta(hours=offset_hours)
        target_hour = target_ts.hour

        # Predict each metric (raw + derived composite_thd)
        preds: dict[str, float] = {}
        for metric in _METRICS + _DERIVED_METRICS:
            if metric not in df.columns:
                preds[metric] = float("nan")
                continue
            val = _predict_metric(df[metric], offset_hours=offset_hours)
            preds[metric] = val if val is not None else float("nan")

        # Compute delta_kwh for this horizon
        energy_pred = preds.get("energy_import", float("nan"))
        if not np.isnan(energy_pred):
            delta_kwh = _compute_delta_kwh(
                predicted_energy=energy_pred,
                energy_series=df["energy_import"],
                target_hour=target_hour,
            )
        else:
            delta_kwh = 0.0

        # FAIR scores for predicted values
        fair_scores, predicted_health_index = _predict_fair_scores(
            df=df,
            device_id=device_id,
            predictions=preds,
            offset_hours=offset_hours,
        )

        # Clean preds for output
        clean_preds = {
            k: (None if np.isnan(v) else round(v, 4))
            for k, v in preds.items()
        }

        horizon_results[horizon_key] = {
            "offset_hours": offset_hours,
            "target_time": target_ts.isoformat(),
            "predictions": clean_preds,
            "delta_kwh": round(delta_kwh, 4),
            "fair_scores": {k: round(v, 4) for k, v in fair_scores.items()},
            "predicted_health_index": round(predicted_health_index, 2),
        }

    # History profiles
    history_profiles = {
        "yesterday": _build_history_profile(df, offset_days=1, label="yesterday"),
        "last_week": _build_history_profile(df, offset_days=7, label="last_week"),
        "two_weeks_ago": _build_history_profile(df, offset_days=14, label="two_weeks_ago"),
    }

    actuals = _build_actuals(df, n_hours=48)

    return {
        "device_id": device_id,
        "generated_at": now.isoformat(),
        "t_now": last_ts.isoformat(),
        "history_profiles": history_profiles,
        "actuals": actuals,
        "horizons": horizon_results,
    }


async def compute_predictions_async(
    device_id: str,
    horizons: list[str] | None = None,
) -> dict | None:
    """Async wrapper — runs compute_predictions in a thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, compute_predictions, device_id, horizons
    )
