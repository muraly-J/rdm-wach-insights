"""Prototype 3-5 new candidate scores. Reuse Wed AM data fetch. Plot distributions.

Run from backend dir: python -m scripts.research.score_prototypes
Output: data/research/2026-05-06/prototype_scores.csv + PNG plots.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backend.core.healthdb import HealthDB
from backend.core.fair_health_scoring import sigmoid_score

REF_PATH = Path("data/research/2026-05-06/reference_ahus.json")
OUT_DIR = Path("data/research/2026-05-06")
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOOKBACK_DAYS = 7


def fetch_series(ahu_id: str, raw_col: str) -> pd.Series:
    """Fetch a metric time series for one AHU over the last 7 days."""
    db = HealthDB()
    latest_ts = db.get_latest_timestamp()
    if latest_ts is None:
        return pd.Series(dtype=float)

    from datetime import timedelta
    start = (latest_ts - timedelta(days=LOOKBACK_DAYS)).isoformat()

    df = db.get_time_range(
        ahu_ids=[ahu_id], start=start, end=latest_ts.isoformat(),
        metrics=["timestamp", raw_col], limit=None,
    )
    if df.empty or raw_col not in df.columns:
        return pd.Series(dtype=float)

    return pd.Series(
        df[raw_col].astype(float).values,
        index=pd.to_datetime(df["timestamp"], utc=True),
    ).sort_index()


# ─── Candidate score formulas ───────────────────────────────────────────────

def pf_stability(pf_series: pd.Series) -> float:
    """Lower rolling std = more stable = healthier. Returns 0-100 high=good."""
    if pf_series.empty:
        return 50.0
    rolling = pf_series.rolling("24h", min_periods=2).std().dropna()
    if rolling.empty:
        return 50.0
    raw = float(rolling.median())
    # Calibrate: median rolling std of 0.005 = healthy, 0.05 = bad.
    score_0_1 = 1.0 - sigmoid_score((raw - 0.005) * 100.0)
    return max(0.0, min(100.0, score_0_1 * 100.0))


def imbalance_peaks(unbal_series: pd.Series, threshold: float = 5.0) -> float:
    """Count of 1h windows exceeding threshold. More breaches = worse."""
    if unbal_series.empty:
        return 50.0
    hourly_max = unbal_series.resample("1h").max().dropna()
    if hourly_max.empty:
        return 50.0
    breaches = int((hourly_max > threshold).sum())
    # Calibrate: 0 breaches = 100, 24+ breaches over 7d = 0.
    score_0_1 = max(0.0, 1.0 - breaches / 24.0)
    return max(0.0, min(100.0, score_0_1 * 100.0))


def thd_spread(thd_series: pd.Series) -> float:
    """Range (p95 - p05) of THD. Wider range = noisier = worse."""
    if thd_series.empty:
        return 50.0
    p95 = float(thd_series.quantile(0.95))
    p05 = float(thd_series.quantile(0.05))
    spread = p95 - p05
    score_0_1 = 1.0 - sigmoid_score((spread - 1.0) * 1.0)
    return max(0.0, min(100.0, score_0_1 * 100.0))


def cycling_frequency(power_series: pd.Series, on_threshold_kw: float = 1.0) -> float:
    """Excessive on/off cycling = motor wear. Returns 0-100 high=good."""
    if power_series.empty:
        return 50.0
    on = power_series > on_threshold_kw
    transitions = int((on.astype(int).diff().abs() == 1).sum())
    cycles_per_day = transitions / 7.0
    # Calibrate: 0 cycles = 100, 20+/day = 0.
    score_0_1 = max(0.0, 1.0 - cycles_per_day / 20.0)
    return max(0.0, min(100.0, score_0_1 * 100.0))


def voltage_sag_count(voltage_series: pd.Series, nominal: float = 230.0) -> float:
    """Count of dips below 95% nominal in 24h windows."""
    if voltage_series.empty:
        return 50.0
    sags = int((voltage_series < 0.95 * nominal).sum())
    score_0_1 = max(0.0, 1.0 - sags / 50.0)
    return max(0.0, min(100.0, score_0_1 * 100.0))


CANDIDATES = {
    "pf_stability": ("raw_power_factor_avg", pf_stability),
    "imbalance_peaks": ("raw_current_unbalance", imbalance_peaks),
    "thd_spread": ("raw_composite_thd", thd_spread),
    "cycling_frequency": ("raw_power_total", cycling_frequency),
    "voltage_sag_count": ("raw_volts_l_n_avg", voltage_sag_count),
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ref = json.loads(REF_PATH.read_text())

    rows = []
    for label, info in ref.items():
        ahu = info["ahu_id"]
        record = {"label": label, "ahu_id": ahu}
        for name, (field, fn) in CANDIDATES.items():
            series = fetch_series(ahu, field)
            record[name] = round(fn(series), 2)
        rows.append(record)

    df = pd.DataFrame(rows)
    csv_path = OUT_DIR / "prototype_scores.csv"
    df.to_csv(csv_path, index=False)
    print(df.to_string(index=False))

    # Distribution plots
    fig, axes = plt.subplots(1, len(CANDIDATES), figsize=(4 * len(CANDIDATES), 4))
    if len(CANDIDATES) == 1:
        axes = [axes]
    for ax, name in zip(axes, CANDIDATES, strict=True):
        ax.bar(df["label"], df[name], color=["#4CAF50", "#FF9800", "#F44336"])
        ax.set_title(name)
        ax.set_ylim(0, 100)
        ax.axhline(50, color="grey", linestyle="--")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "prototype_scores.png", dpi=120)
    print(f"Wrote {csv_path} + {OUT_DIR / 'prototype_scores.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())