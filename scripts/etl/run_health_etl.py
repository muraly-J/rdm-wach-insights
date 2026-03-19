#!/usr/bin/env python3
"""
run_health_etl.py
─────────────────
ETL Pipeline for FAIR Health Scoring

This script implements a 4-step ETL process:
1. EXTRACT: Fetch latest hourly data from InfluxDB for all AHUs
2. TRANSFORM: Compute health scores using FAIR algorithm
3. LOAD: Append results to health_all_levels.csv
4. SAFETY FLAGS: Generate engineering audit flags

Usage:
    python scripts/run_health_etl.py
    python scripts/run_health_etl.py --output custom_output.csv
    python scripts/run_health_etl.py --dry-run
    python scripts/run_health_etl.py --level 1           # Test Level 1 only
    python scripts/run_health_etl.py --level all         # All levels

Output:
    data/health_all_levels.csv - Health scores with all required columns
"""

import sys
import os
import argparse
import time
from datetime import datetime

# Add backend to path for imports (scripts/etl → .. → scripts → .. → backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pandas as pd
import numpy as np

# Import ETL components
from core.influx_client import fetch_latest_hourly_data, get_available_devices

# Add models for AHU level config
from models.schemas import AHU_LEVEL_CONFIG, get_devices_by_level


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, "health_all_levels.csv")
OUTPUT_HOURLY_FILE = os.path.join(DATA_DIR, "health_hourly.csv")

# Timing utilities
_timers = {}


def start_timer(name: str):
    """Start timing a named operation."""
    _timers[name] = time.time()
    print(f"\n[START] {name}...")

def end_timer(name: str) -> float:
    """End timing and return elapsed seconds."""
    if name not in _timers:
        return 0.0
    elapsed = time.time() - _timers[name]
    print(f"[DONE]  {name}: {elapsed:.2f}s")
    return elapsed


# ──────────────────────────────────────────────────────────────────────────────

# Health Index Weights
HEALTH_INDEX_WEIGHTS = {
    "energy_anomaly": 0.15,
    "power_factor":   0.25,
    "phase_imbalance": 0.25,
    "thd_drift":      0.15,
    "overload":       0.20,
}

# Sensitivity factors
SENSITIVITY = {
    "energy_anomaly":  2.0,
    "pf_degradation":  2.5,
    "phase_imbalance": 2.0,
    "thd_drift":       2.0,
    "overload":        2.0,
}

# Level vs trend blend
LEVEL_WEIGHT = 0.70
TREND_WEIGHT = 0.30
SLOPE_SENS = 3.0

# Minimum robust-std values
MIN_RSTD = {
    "delta_kwh":          0.05,
    "power_factor_avg":   0.008,
    "current_unbalance":  0.15,
    "composite_thd_24h":  0.15,
    "power_total":        0.05,
}

# THD uses 24h rolling mean
THD_ROLLING_H = 24

# Safety flag thresholds
SAFETY_FLAGS_DEF = {
    "THD_CHRONIC_HIGH":  ("composite_thd_24h", ">", 5.0),
    "IMBALANCE_SEVERE":  ("current_unbalance",  ">", 5.0),
    "PF_CHRONIC_LOW":    ("power_factor_avg",   "<",  0.85),
    "OVERLOAD_CHRONIC":  ("power_total",        ">",  None),  # computed separately
}


# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS (from fair_health_scoring.py)
# ──────────────────────────────────────────────────────────────────────────────

def sigmoid(x):
    """Numerically stable logistic sigmoid."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def sigmoid_score(raw):
    """Map raw penalty to [0, 1] where raw = 0 → score = 0."""
    return float(np.clip(sigmoid(raw) * 2.0 - 1.0, 0.0, 1.0))


def clamp01(x):
    """Clamp value to [0, 1]."""
    return float(np.clip(x, 0.0, 1.0))


def robust_params(values, min_rstd=0.01):
    """
    Compute robust location (median) and scale (1.4826 × MAD).

    Returns (median, rstd) where rstd >= min_rstd.
    """
    v = values[~np.isnan(values)]
    if len(v) < 3:
        median = float(np.nanmedian(values)) if len(values) > 0 else 0.0
        return median, min_rstd

    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, min_rstd)
    return med, rstd


def ols_slope(values):
    """Compute OLS slope for equally-spaced points."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 3:
        return 0.0
    i = np.arange(n, dtype=float)
    num = n * np.dot(i, v) - i.sum() * v.sum()
    denom = n * np.dot(i, i) - i.sum() ** 2
    return float(num / denom) if denom != 0 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# SCORING FUNCTIONS (from fair_health_scoring.py)
# ──────────────────────────────────────────────────────────────────────────────

def score_energy_anomaly(delta_kwh, ahu_median_delta, ahu_rstd_delta, hist_delta_series):
    """
    Score 1 · Energy Anomaly (weight 15%)

    Returns (score ∈ [0,1], z_diagnostic, level_term, trend_term)
    """
    if hist_delta_series is None or len(hist_delta_series) < 24:
        return 0.5, np.nan, np.nan, np.nan

    if delta_kwh is None or np.isnan(delta_kwh):
        return 0.5, np.nan, np.nan, np.nan

    if ahu_median_delta is None or np.isnan(ahu_median_delta):
        return 0.5, np.nan, np.nan, np.nan

    # Use robust std with minimum
    rstd = max(ahu_rstd_delta, MIN_RSTD.get("delta_kwh", 0.05))
    if rstd <= 0:
        return 0.5, np.nan, np.nan, np.nan

    # Level term: z-score vs own median
    z = (delta_kwh - ahu_median_delta) / rstd
    raw = 0.6 * abs(z) + 0.4 * max(0.0, z)
    lv = sigmoid_score(raw * SENSITIVITY["energy_anomaly"])

    # Trend term - requires at least 168h (7 days) of data
    hist_clean = np.asarray(hist_delta_series, dtype=float)
    hist_clean = hist_clean[~np.isnan(hist_clean)]
    if len(hist_clean) >= 168:
        slope_n = float(np.clip(ols_slope(hist_clean) / rstd, -10, 10))
        tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    else:
        tr = 0.0

    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)


def score_power_factor(pf, power, ahu_median_pf, ahu_rstd_pf, hist_pf_series):
    """
    Score 2 · PF Degradation (weight 25%)

    Returns (score ∈ [0,1], z_diagnostic, level_term, trend_term)
    """
    if pf is None or np.isnan(pf):
        return 0.0, np.nan, np.nan, np.nan

    if ahu_median_pf is None or np.isnan(ahu_median_pf):
        return 0.0, np.nan, np.nan, np.nan

    # Use robust std with minimum
    rstd = max(ahu_rstd_pf, MIN_RSTD.get("power_factor_avg", 0.008))
    if rstd <= 0:
        return 0.0, np.nan, np.nan, np.nan

    # Level term: z-score (negative means below median)
    z = (ahu_median_pf - pf) / rstd
    lv = sigmoid_score(z * SENSITIVITY["pf_degradation"])

    # Trend term (negative slope = falling = bad)
    slope_n = float(np.clip(ols_slope(hist_pf_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, -slope_n) * SLOPE_SENS)

    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)


def score_phase_imbalance(unbal, ahu_median_unbal, ahu_rstd_unbal, hist_unbal_series):
    """
    Score 3 · Phase Imbalance (weight 25%)

    Returns (score ∈ [0,1], z_diagnostic, level_term, trend_term)
    """
    if unbal is None or np.isnan(unbal):
        return 0.0, np.nan, np.nan, np.nan

    if ahu_median_unbal is None or np.isnan(ahu_median_unbal):
        return 0.0, np.nan, np.nan, np.nan

    # Use robust std with minimum
    rstd = max(ahu_rstd_unbal, MIN_RSTD.get("current_unbalance", 0.15))
    if rstd <= 0:
        return 0.0, np.nan, np.nan, np.nan

    # Level term: z-score
    z = (unbal - ahu_median_unbal) / rstd
    lv = sigmoid_score(z * SENSITIVITY["phase_imbalance"])

    # Trend term
    slope_n = float(np.clip(ols_slope(hist_unbal_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)

    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)


def score_thd_drift(thd_24h, ahu_median_thd, ahu_rstd_thd, hist_thd_24h_series):
    """
    Score 4 · THD Drift (weight 15%)

    Returns (score ∈ [0,1], z_diagnostic, level_term, trend_term)
    """
    if thd_24h is None or np.isnan(thd_24h):
        return 0.0, np.nan, np.nan, np.nan

    if ahu_median_thd is None or np.isnan(ahu_median_thd):
        return 0.0, np.nan, np.nan, np.nan

    # Use robust std with minimum
    rstd = max(ahu_rstd_thd, MIN_RSTD.get("composite_thd_24h", 0.15))
    if rstd <= 0:
        return 0.0, np.nan, np.nan, np.nan

    # Level term: z-score
    z = (thd_24h - ahu_median_thd) / rstd
    lv = sigmoid_score(z * SENSITIVITY["thd_drift"])

    # Trend term
    slope_n = float(np.clip(ols_slope(hist_thd_24h_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)

    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)


def score_overload(power, ahu_median_power, ahu_rstd_power, ahu_p95_power, hist_power_series):
    """
    Score 5 · Overload (weight 20%)

    Returns (score ∈ [0,1], z_diagnostic, score_A, score_B, score_C)
    """
    # Minimum history check
    if hist_power_series is None or len(hist_power_series) < 24:
        return 0.5, np.nan, np.nan, np.nan, np.nan

    if power is None or np.isnan(power):
        return 0.5, np.nan, np.nan, np.nan, np.nan

    if ahu_median_power is None or np.isnan(ahu_median_power):
        return 0.5, np.nan, np.nan, np.nan, np.nan

    if ahu_p95_power is None or np.isnan(ahu_p95_power) or ahu_p95_power <= 0:
        return 0.5, np.nan, np.nan, np.nan, np.nan

    # Check for valid std
    if ahu_rstd_power is None or np.isnan(ahu_rstd_power) or ahu_rstd_power <= 0:
        ahu_rstd_power = MIN_RSTD.get("power_total", 0.05)

    # Use robust std with minimum
    rstd = max(ahu_rstd_power, MIN_RSTD.get("power_total", 0.05))

    # A: ceiling proximity
    power_ratio = power / ahu_p95_power
    demand = max(0.0, power_ratio - 0.85)
    score_A = sigmoid_score(demand * 8.0)

    # B: z-score vs own median
    z = (power - ahu_median_power) / rstd
    score_B = sigmoid_score(z * 1.5)

    # C: trend
    hist_clean = np.asarray(hist_power_series, dtype=float)
    hist_clean = hist_clean[~np.isnan(hist_clean)]
    if len(hist_clean) >= 168:
        slope_n = float(np.clip(ols_slope(hist_clean) / rstd, -10, 10))
        score_C = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    else:
        score_C = 0.0

    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score), round(z, 3), round(score_A, 4), round(score_B, 4), round(score_C, 4)


def calculate_health_index(scores):
    """
    health_index = clip(100 − penalty × 100,  0, 100)
    penalty      = Σ weight_i × score_i   ∈ [0, 1]

    All scores at 0 (exactly at own baseline) → penalty = 0 → index = 100
    All scores at 1 (maximum deviation on all metrics) → index = 0
    """
    penalty = sum(HEALTH_INDEX_WEIGHTS.get(k, 0) * score for k, score in scores.items())
    return float(np.clip(100.0 - penalty * 100.0, 0.0, 100.0))


def get_health_tier(index):
    """Map health index to tier string."""
    for threshold, label in [(80, "Healthy"), (60, "Monitor"), (40, "Maintenance Soon"), (0, "Critical")]:
        if index >= threshold:
            return label
    return "Critical"


# ──────────────────────────────────────────────────────────────────────────────
# SAFETY FLAGS FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def compute_safety_flags(baseline):
    """
    Evaluate baseline against structural safety thresholds.

    Returns list of flag strings.
    """
    flags = []

    thd_med = baseline.get("composite_thd_24h", {}).get("median", np.nan)
    imb_med = baseline.get("current_unbalance", {}).get("median", np.nan)
    pf_med  = baseline.get("power_factor_avg",  {}).get("median", np.nan)
    pwr_med = baseline.get("power_total",       {}).get("median", np.nan)
    pwr_p95 = baseline.get("power_total",       {}).get("p95",    np.nan)

    if not np.isnan(thd_med) and thd_med > 5.0:
        flags.append("THD_CHRONIC_HIGH")
    if not np.isnan(imb_med) and imb_med > 5.0:
        flags.append("IMBALANCE_SEVERE")
    if not np.isnan(pf_med) and pf_med < 0.85:
        flags.append("PF_CHRONIC_LOW")
    if (not np.isnan(pwr_med) and not np.isnan(pwr_p95)
            and pwr_p95 > 0 and pwr_med / pwr_p95 > 0.90):
        flags.append("OVERLOAD_CHRONIC")

    return flags


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: EXTRACT - Fetch Raw Data
# ──────────────────────────────────────────────────────────────────────────────

def extract_raw_data(metrics_to_fetch=None, level_filter=None):
    """
    Step 1: Fetch latest hourly data for all AHUs from InfluxDB.

    Args:
        metrics_to_fetch: List of metric names to fetch
        level_filter: Optional level number (1-11) to filter devices

    Returns:
        DataFrame with raw metrics for all AHUs
    """
    print("\n" + "="*70)
    print("STEP 1: EXTRACT - Fetching Raw Data from InfluxDB")
    print("="*70)

    if metrics_to_fetch is None:
        metrics_to_fetch = [
            "power_total",
            "energy_import",
            "power_factor_avg",
            "current_unbalance",
            "current_l1_thd",
            "current_l3_thd",
            "apparent_power_total",
            "current_l1",
            "current_l2",
            "current_l3",
            "volts_l1_n",
            "volts_l2_n",
            "volts_l3_n",
            "volts_l1_thd",
            "volts_l2_thd",
            "volts_l3_thd",
        ]

    try:
        df = fetch_latest_hourly_data(
            metrics_to_fetch=metrics_to_fetch,
            level_filter=level_filter
        )

        if df.empty:
            print("[ERROR] No data retrieved from InfluxDB!")
            return None

        print(f"[OK] Retrieved {len(df)} AHU readings")
        print(f"    Columns: {list(df.columns)}")

        return df

    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {e}")
        import traceback
        traceback.print_exc()
        return None


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: TRANSFORM - Compute Health Scores
# ──────────────────────────────────────────────────────────────────────────────

def build_baselines(df):
    """
    Build per-AHU baselines from raw data.

    Returns dict: { ahu_id: { metric: {median, rstd, p5, p25, p75, p95} } }
    """
    baselines = {}

    for ahu_id, grp in df.groupby("ahu_id"):
        grp = grp.sort_values("timestamp")
        b   = {}

        # Standard metrics
        for col, min_r in [
            ("delta_kwh",         MIN_RSTD["delta_kwh"]),
            ("power_factor_avg",  MIN_RSTD["power_factor_avg"]),
            ("current_unbalance", MIN_RSTD["current_unbalance"]),
            ("power_total",       MIN_RSTD["power_total"]),
        ]:
            vals = grp[col].dropna().values if col in grp.columns else np.array([])
            if len(vals) < 3:
                b[col] = dict(
                    median=np.nan,
                    rstd=min_r,
                    p5=np.nan, p25=np.nan, p75=np.nan, p95=np.nan,
                    n=len(vals)
                )
                continue
            med, rstd = robust_params(vals, min_r)
            b[col] = dict(
                median=med,
                rstd=rstd,
                p5=float(np.percentile(vals, 5)),
                p25=float(np.percentile(vals, 25)),
                p75=float(np.percentile(vals, 75)),
                p95=float(np.percentile(vals, 95)),
                n=len(vals),
            )

        # THD baseline - MUST use 24h rolling mean, not instantaneous
        if "composite_thd" in grp.columns:
            thd_24h_series = (
                grp["composite_thd"]
                .rolling(THD_ROLLING_H, min_periods=1)
                .mean()
                .dropna()
                .values
            )
        else:
            thd_24h_series = np.array([])

        if len(thd_24h_series) < 3:
            b["composite_thd_24h"] = dict(
                median=np.nan,
                rstd=MIN_RSTD["composite_thd_24h"],
                p5=np.nan, p95=np.nan,
                n=0
            )
        else:
            med, rstd = robust_params(thd_24h_series, MIN_RSTD["composite_thd_24h"])
            b["composite_thd_24h"] = dict(
                median=med,
                rstd=rstd,
                p5=float(np.percentile(thd_24h_series, 5)),
                p95=float(np.percentile(thd_24h_series, 95)),
                n=len(thd_24h_series),
            )

        # Per-AHU P95 of max-phase current (for overload chart reference line)
        current_cols = ["current_l1", "current_l2", "current_l3"]
        avail_current_cols = [c for c in current_cols if c in grp.columns]
        if avail_current_cols:
            max_current = grp[avail_current_cols].max(axis=1).dropna().values
            if len(max_current) >= 3:
                b["max_phase_current"] = dict(
                    p95=float(np.percentile(max_current, 95)),
                    n=len(max_current)
                )
            else:
                b["max_phase_current"] = dict(p95=np.nan, n=0)
        else:
            b["max_phase_current"] = dict(p95=np.nan, n=0)

        baselines[ahu_id] = b

    return baselines


def transform_health_scores(df_raw):
    """
    Step 2: Run all 5 scoring functions per AHU.

    Args:
        df_raw: Raw metrics DataFrame

    Returns:
        DataFrame with health scores and scores
    """
    print("\n" + "="*70)
    print("STEP 2: TRANSFORM - Computing Health Scores (FAIR Algorithm)")
    print("="*70)

    if df_raw is None or df_raw.empty:
        print("[ERROR] No raw data to transform!")
        return None

    results = []

    # Build per-AHU baselines
    print(f"Building baselines for {df_raw['ahu_id'].nunique()} AHUs...")
    ahu_baselines = build_baselines(df_raw)

    # Compute safety flags
    print("Computing safety flags...")
    safety_flags = {}
    for ahu_id, baseline in ahu_baselines.items():
        safety_flags[ahu_id] = compute_safety_flags(baseline)

    # Process each row
    print(f"Computing scores for {len(df_raw)} records...")

    df_sorted = df_raw.sort_values(['ahu_id', 'timestamp']).reset_index(drop=True)

    for idx, row in df_sorted.iterrows():
        if (idx + 1) % 100 == 0:
            print(f"  Processing record {idx+1}/{len(df_raw)}...")

        ahu_id = row['ahu_id']
        baseline = ahu_baselines[ahu_id]

        # Get current values
        power_current = float(row['power_total']) if pd.notna(row.get('power_total')) else None
        energy_current = float(row['energy_import']) if pd.notna(row.get('energy_import')) else None
        pf_current = float(row['power_factor_avg']) if pd.notna(row.get('power_factor_avg')) else None
        unbalance_current = float(row['current_unbalance']) if pd.notna(row.get('current_unbalance')) else None
        thd_24h = float(row['composite_thd']) if pd.notna(row.get('composite_thd')) else None

        # Extract new per-phase raw values
        apparent_power_current = float(row['apparent_power_total']) if pd.notna(row.get('apparent_power_total')) else None
        current_l1 = float(row['current_l1']) if pd.notna(row.get('current_l1')) else None
        current_l2 = float(row['current_l2']) if pd.notna(row.get('current_l2')) else None
        current_l3 = float(row['current_l3']) if pd.notna(row.get('current_l3')) else None
        volts_l1_n = float(row['volts_l1_n']) if pd.notna(row.get('volts_l1_n')) else None
        volts_l2_n = float(row['volts_l2_n']) if pd.notna(row.get('volts_l2_n')) else None
        volts_l3_n = float(row['volts_l3_n']) if pd.notna(row.get('volts_l3_n')) else None
        current_l1_thd = float(row['current_l1_thd']) if pd.notna(row.get('current_l1_thd')) else None
        current_l3_thd = float(row['current_l3_thd']) if pd.notna(row.get('current_l3_thd')) else None
        volts_l1_thd = float(row['volts_l1_thd']) if pd.notna(row.get('volts_l1_thd')) else None
        volts_l2_thd = float(row['volts_l2_thd']) if pd.notna(row.get('volts_l2_thd')) else None
        volts_l3_thd = float(row['volts_l3_thd']) if pd.notna(row.get('volts_l3_thd')) else None

        # NEMA voltage imbalance (%)
        nema_voltage_imbalance = None
        if all(v is not None for v in [volts_l1_n, volts_l2_n, volts_l3_n]):
            v_avg = (volts_l1_n + volts_l2_n + volts_l3_n) / 3.0
            if v_avg > 0:
                v_max_dev = max(abs(volts_l1_n - v_avg), abs(volts_l2_n - v_avg), abs(volts_l3_n - v_avg))
                nema_voltage_imbalance = round(100.0 * v_max_dev / v_avg, 3)

        # Compute delta_kwh
        ahu_df = df_sorted[df_sorted['ahu_id'] == ahu_id].copy()
        ahu_df = ahu_df.sort_values('timestamp').reset_index(drop=True)

        curr_pos = ahu_df[ahu_df['timestamp'] == row['timestamp']].index.tolist()
        delta_kwh = None
        if curr_pos and curr_pos[0] > 0:
            prev_energy = ahu_df.loc[curr_pos[0] - 1, 'energy_import']
            curr_energy = row['energy_import']
            delta_kwh = float(curr_energy - prev_energy)
            if delta_kwh < 0:
                delta_kwh = None

        # Get historical series (last 168 hours)
        start_idx = max(0, len(ahu_df) - 168)
        hist_df = ahu_df.iloc[start_idx:]

        # Build history series
        hist_power = hist_df['power_total'].values.astype(float) if len(hist_df) > 0 else np.array([])
        hist_energy = hist_df['energy_import'].values.astype(float) if len(hist_df) > 0 else np.array([])
        hist_pf = hist_df['power_factor_avg'].values.astype(float) if len(hist_df) > 0 else np.array([])
        hist_unbal = hist_df['current_unbalance'].values.astype(float) if len(hist_df) > 0 else np.array([])

        # Compute delta series for trend
        hist_delta = np.empty(len(hist_df), dtype=float)
        hist_delta[:] = np.nan
        if len(hist_energy) >= 2:
            for j in range(1, len(hist_delta)):
                diff = hist_energy[j] - hist_energy[j-1]
                hist_delta[j] = diff if diff >= 0 else np.nan

        # Compute all 5 scores
        try:
            energy_score, z_energy, lv_energy, tr_energy = score_energy_anomaly(
                delta_kwh,
                baseline["delta_kwh"]["median"],
                baseline["delta_kwh"]["rstd"],
                hist_delta if len(hist_delta) >= 2 else np.array([])
            )
        except Exception as e:
            energy_score, z_energy, lv_energy, tr_energy = 0.5, np.nan, np.nan, np.nan

        try:
            pf_score, z_pf, lv_pf, tr_pf = score_power_factor(
                pf_current, power_current,
                baseline["power_factor_avg"]["median"], baseline["power_factor_avg"]["rstd"],
                hist_pf if len(hist_pf) >= 2 else np.array([])
            )
        except Exception as e:
            pf_score, z_pf, lv_pf, tr_pf = 0.0, np.nan, np.nan, np.nan

        try:
            unbal_score, z_unbal, lv_unbal, tr_unbal = score_phase_imbalance(
                unbalance_current,
                baseline["current_unbalance"]["median"],
                baseline["current_unbalance"]["rstd"],
                hist_unbal if len(hist_unbal) >= 2 else np.array([])
            )
        except Exception as e:
            unbal_score, z_unbal, lv_unbal, tr_unbal = 0.0, np.nan, np.nan, np.nan

        try:
            thd_score, z_thd, lv_thd, tr_thd = score_thd_drift(
                thd_24h,
                baseline["thd_median"],
                baseline["thd_rstd"],
                hist_df['composite_thd'].values.astype(float) if 'composite_thd' in hist_df.columns else np.array([])
            )
        except Exception as e:
            thd_score, z_thd, lv_thd, tr_thd = 0.0, np.nan, np.nan, np.nan

        try:
            overload_score, z_overload, score_A, score_B, score_C = score_overload(
                power_current,
                baseline["power_total"]["median"],
                baseline["power_total"]["rstd"],
                baseline["power_total"].get("p95"),
                hist_power if len(hist_power) >= 24 else np.array([])
            )
        except Exception as e:
            overload_score, z_overload, score_A, score_B, score_C = 0.5, np.nan, np.nan, np.nan, np.nan

        # Calculate health index
        risk_scores = {
            "energy_anomaly": round(energy_score, 4),
            "pf_degradation": round(pf_score, 4),
            "phase_imbalance": round(unbal_score, 4),
            "thd_drift": round(thd_score, 4),
            "overload": round(overload_score, 4),
        }

        health_index = calculate_health_index(risk_scores)
        tier = get_health_tier(health_index)

        # Get safety flags
        sf_flags = safety_flags.get(ahu_id, [])
        safety_flags_str = ",".join(sf_flags) if sf_flags else ""

        # Build result row with diagnostic columns
        results.append({
            "timestamp": row['timestamp'],
            "ahu_id": ahu_id,
            "level": row.get('level', f"Level {ahu_id[1:3]}"),

            # === Health Index ===
            "health_index": round(health_index, 1),
            "tier": tier,

            # === Component Scores ===
            "energy_anomaly": round(energy_score, 4),
            "pf_degradation": round(pf_score, 4),
            "phase_imbalance": round(unbal_score, 4),
            "thd_drift": round(thd_score, 4),
            "overload": round(overload_score, 4),

            # === Raw Metrics (Current Hour) ===
            "raw_power_total": power_current,
            "raw_energy_import": energy_current,
            "raw_power_factor_avg": pf_current,
            "raw_current_unbalance": unbalance_current,
            "raw_composite_thd": thd_24h,

            # === New Per-Phase Raw Metrics ===
            "raw_apparent_power_total": apparent_power_current,
            "raw_current_l1": current_l1,
            "raw_current_l2": current_l2,
            "raw_current_l3": current_l3,
            "raw_volts_l1_n": volts_l1_n,
            "raw_volts_l2_n": volts_l2_n,
            "raw_volts_l3_n": volts_l3_n,
            "raw_current_l1_thd": current_l1_thd,
            "raw_current_l3_thd": current_l3_thd,
            "raw_volts_l1_thd": volts_l1_thd,
            "raw_volts_l2_thd": volts_l2_thd,
            "raw_volts_l3_thd": volts_l3_thd,
            "raw_nema_voltage_imbalance": nema_voltage_imbalance,
            "raw_p95_current": baseline.get("max_phase_current", {}).get("p95"),

            # === Baseline Statistics (30-day) ===
            "baseline_power_median": baseline["power_total"]["median"],
            "baseline_power_rstd": baseline["power_total"]["rstd"],
            "baseline_power_p5": baseline["power_total"]["p5"],
            "baseline_power_p25": baseline["power_total"]["p25"],
            "baseline_power_p75": baseline["power_total"]["p75"],
            "baseline_power_p95": baseline["power_total"]["p95"],

            "baseline_energy_median": baseline["delta_kwh"]["median"],
            "baseline_energy_rstd": baseline["delta_kwh"]["rstd"],
            "baseline_energy_p5": baseline["delta_kwh"]["p5"],
            "baseline_energy_p25": baseline["delta_kwh"]["p25"],
            "baseline_energy_p75": baseline["delta_kwh"]["p75"],
            "baseline_energy_p95": baseline["delta_kwh"]["p95"],

            "baseline_pf_median": baseline["power_factor_avg"]["median"],
            "baseline_pf_rstd": baseline["power_factor_avg"]["rstd"],
            "baseline_pf_p5": baseline["power_factor_avg"]["p5"],
            "baseline_pf_p25": baseline["power_factor_avg"]["p25"],
            "baseline_pf_p75": baseline["power_factor_avg"]["p75"],
            "baseline_pf_p95": baseline["power_factor_avg"]["p95"],

            "baseline_unbalance_median": baseline["current_unbalance"]["median"],
            "baseline_unbalance_rstd": baseline["current_unbalance"]["rstd"],
            "baseline_unbalance_p5": baseline["current_unbalance"]["p5"],
            "baseline_unbalance_p25": baseline["current_unbalance"]["p25"],
            "baseline_unbalance_p75": baseline["current_unbalance"]["p75"],
            "baseline_unbalance_p95": baseline["current_unbalance"]["p95"],

            "baseline_thd_24h_median": baseline["composite_thd_24h"].get("median", np.nan),
            "baseline_thd_24h_rstd": baseline["composite_thd_24h"].get("rstd", np.nan),
            "baseline_thd_24h_p5": baseline["composite_thd_24h"].get("p5", np.nan),
            "baseline_thd_24h_p95": baseline["composite_thd_24h"].get("p95", np.nan),

            # === Z-Scores (Current Reading vs Baseline) ===
            "z_energy": round(z_energy, 3),
            "z_power_factor": round(z_pf, 3),
            "z_phase_imbalance": round(z_unbal, 3),
            "z_thd_drift": round(z_thd, 3),
            "z_overload": round(z_overload, 3),

            # === Level Term (70% weight) ===
            "level_energy": round(lv_energy, 4),
            "level_pf": round(lv_pf, 4),
            "level_unbalance": round(lv_unbal, 4),
            "level_thd": round(lv_thd, 4),

            # === Trend Term (30% weight) ===
            "trend_energy": round(tr_energy, 4),
            "trend_pf": round(tr_pf, 4),
            "trend_unbalance": round(tr_unbal, 4),
            "trend_thd": round(tr_thd, 4),

            # === Overload Components (A: ceiling, B: z-score, C: trend) ===
            "overload_power_ratio": round(power_current / baseline["power_total"]["p95"], 4) if baseline["power_total"].get("p95") else None,
            "overload_demand": round(max(0.0, power_current / baseline["power_total"]["p95"] - 0.85), 4) if baseline["power_total"].get("p95") else None,
            "score_overload_A": round(score_A, 4),
            "score_overload_B": round(score_B, 4),
            "score_overload_C": round(score_C, 4),

            # === Safety Flags (Boolean) ===
            "flag_thd_chronic_high": "THD_CHRONIC_HIGH" in sf_flags,
            "flag_imbalance_severe": "IMBALANCE_SEVERE" in sf_flags,
            "flag_pf_chronic_low": "PF_CHRONIC_LOW" in sf_flags,
            "flag_overload_chronic": "OVERLOAD_CHRONIC" in sf_flags,

            # === Safety Flags (String) ===
            "safety_flags": safety_flags_str,
        })

    print(f"[OK] Computed scores for {len(results)} records")
    return pd.DataFrame(results)


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3: LOAD - Write to CSV
# ──────────────────────────────────────────────────────────────────────────────

def load_to_csv(df_scores, output_path=None):
    """
    Step 3: Append health scores to CSV file.

    Args:
        df_scores: DataFrame with health scores
        output_path: Path to output CSV file

    Returns:
        Number of rows written
    """
    print("\n" + "="*70)
    print("STEP 3: LOAD - Writing to health_all_levels.csv")
    print("="*70)

    if output_path is None:
        output_path = OUTPUT_FILE

    # Ensure directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Determine if file exists and needs header
    file_exists = os.path.exists(output_path)

    # Define columns in order
    # All columns to include (all diagnostic columns)
    required_cols = [
        # Core columns
        "timestamp", "ahu_id", "level", "health_index", "tier",

        # Component scores
        "energy_anomaly", "pf_degradation", "phase_imbalance", "thd_drift", "overload",

        # Raw metrics
        "raw_power_total", "raw_energy_import", "raw_power_factor_avg",
        "raw_current_unbalance", "raw_composite_thd",
        "raw_apparent_power_total",
        "raw_current_l1", "raw_current_l2", "raw_current_l3",
        "raw_volts_l1_n", "raw_volts_l2_n", "raw_volts_l3_n",
        "raw_current_l1_thd", "raw_current_l3_thd",
        "raw_volts_l1_thd", "raw_volts_l2_thd", "raw_volts_l3_thd",
        "raw_nema_voltage_imbalance",
        "raw_p95_current",

        # Baseline statistics
        "baseline_power_median", "baseline_power_rstd",
        "baseline_power_p5", "baseline_power_p25", "baseline_power_p75", "baseline_power_p95",
        "baseline_energy_median", "baseline_energy_rstd",
        "baseline_energy_p5", "baseline_energy_p25", "baseline_energy_p75", "baseline_energy_p95",
        "baseline_pf_median", "baseline_pf_rstd",
        "baseline_pf_p5", "baseline_pf_p25", "baseline_pf_p75", "baseline_pf_p95",
        "baseline_unbalance_median", "baseline_unbalance_rstd",
        "baseline_unbalance_p5", "baseline_unbalance_p25", "baseline_unbalance_p75", "baseline_unbalance_p95",
        "baseline_thd_24h_median", "baseline_thd_24h_rstd",
        "baseline_thd_24h_p5", "baseline_thd_24h_p95",

        # Z-scores
        "z_energy", "z_power_factor", "z_phase_imbalance", "z_thd_drift", "z_overload",

        # Level and trend breakdowns
        "level_energy", "trend_energy",
        "level_pf", "trend_pf",
        "level_unbalance", "trend_unbalance",
        "level_thd", "trend_thd",

        # Overload components
        "overload_power_ratio", "overload_demand",
        "score_overload_A", "score_overload_B", "score_overload_C",

        # Safety flags (boolean)
        "flag_thd_chronic_high", "flag_imbalance_severe",
        "flag_pf_chronic_low", "flag_overload_chronic",

        # Safety flags (string)
        "safety_flags"
    ]

    # Reorder columns - only include columns that exist in the DataFrame
    available_cols = [c for c in required_cols if c in df_scores.columns]
    df_output = df_scores[available_cols]

    df_output = df_scores[[c for c in required_cols if c in df_scores.columns]]

    # Append mode
    mode = 'a' if file_exists else 'w'
    header = not file_exists

    try:
        df_output.to_csv(output_path, mode=mode, header=header, index=False)

        if file_exists:
            print(f"[OK] Appended {len(df_output)} rows to existing file")
        else:
            print(f"[OK] Created new file with {len(df_output)} rows")

        return len(df_output)

    except Exception as e:
        print(f"[ERROR] Failed to write CSV: {e}")
        import traceback
        traceback.print_exc()
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3b: LOAD - Write Hourly CSV (Append-only for 24h chart)
# ──────────────────────────────────────────────────────────────────────────────

def save_hourly_health(health_df: pd.DataFrame):
    """
    Append hourly health records to health_hourly.csv (append-only).
    This file is used for 24h time range charts.

    Args:
        health_df: DataFrame with health scores

    Returns:
        True if successful, False otherwise
    """
    print("\n" + "="*70)
    print("STEP 3b: LOAD - Appending to health_hourly.csv (24h chart)")
    print("="*70)

    if health_df.empty:
        print("[ERROR] No hourly data to save!")
        return False

    os.makedirs(os.path.dirname(OUTPUT_HOURLY_FILE), exist_ok=True)

    # Check if file exists and has data
    if os.path.exists(OUTPUT_HOURLY_FILE) and os.path.getsize(OUTPUT_HOURLY_FILE) > 0:
        # Read existing data
        try:
            existing_df = pd.read_csv(OUTPUT_HOURLY_FILE, parse_dates=['timestamp'])

            # Combine and dedupe on (timestamp, ahu_id) - keep latest
            combined = pd.concat([existing_df, health_df], ignore_index=True)

            # Deduplicate on timestamp + ahu_id, keep last (most recent)
            combined = combined.drop_duplicates(
                subset=['timestamp', 'ahu_id'], keep='last'
            ).sort_values(['timestamp', 'ahu_id'])

            combined.to_csv(OUTPUT_HOURLY_FILE, index=False)
            print(f"[OK] Appended {len(health_df)} new hourly records (total: {len(combined)})")
        except Exception as e:
            print(f"[ERROR] Failed to merge with existing file: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        # Create new file
        try:
            health_df.to_csv(OUTPUT_HOURLY_FILE, index=False)
            print(f"[OK] Created health_hourly.csv with {len(health_df)} records")
        except Exception as e:
            print(f"[ERROR] Failed to write hourly CSV: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4: Safety Flags Summary
# ──────────────────────────────────────────────────────────────────────────────

def print_safety_flags_summary(df_scores):
    """
    Step 4: Generate and display safety flags summary.

    Args:
        df_scores: DataFrame with health scores
    """
    print("\n" + "="*70)
    print("STEP 4: SAFETY FLAGS SUMMARY")
    print("="*70)

    if df_scores is None or df_scores.empty:
        print("[WARNING] No data to summarize")
        return

    # Count unique AHUs with each flag
    if 'safety_flags' in df_scores.columns:
        all_flags = df_scores['safety_flags'].dropna()

        if len(all_flags) > 0:
            flag_counts = {}
            for flags in all_flags:
                if pd.notna(flags) and str(flags).strip() != "":
                    for flag in str(flags).split(","):
                        if flag.strip():
                            flag_counts[flag] = flag_counts.get(flag, 0) + 1

            total_ahus = df_scores['ahu_id'].nunique()

            print(f"Total unique AHUs: {total_ahus}")
            print(f"\nSafety Flags Distribution:")

            for flag, count in sorted(flag_counts.items(), key=lambda x: -x[1]):
                pct = 100 * count / total_ahus if total_ahus > 0 else 0
                print(f"  {flag}: {count} AHUs ({pct:.1f}%)")
        else:
            print("No safety flags found in data")
    else:
        print("[WARNING] 'safety_flags' column not present")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN ETL FUNCTION
# ──────────────────────────────────────────────────────────────────────────────

def run_etl_pipeline(output_path=None, dry_run=False, level=None, scheduled=False, output_hourly=False):
    """
    Run the complete ETL pipeline.

    Args:
        output_path: Path to output CSV file
        dry_run: If True, skip writing to file
        level: Filter by specific level (1-11) or None for all levels
        scheduled: If True, run in scheduled mode (quiet output)
        output_hourly: If True, also generate health_hourly.csv

    Returns:
        Dictionary with ETL results
    """
    if not scheduled:
        print("\n" + "="*70)
        print("FAIR HEALTH SCORING ETL PIPELINE")
    print(f"Started at: {datetime.now().isoformat()}")
    if level:
        print(f"Level filter: Level {level} only")
    else:
        print("Level filter: All levels")
    print("="*70)

    # Track timing
    total_start = time.time()
    step_timings = {}

    results = {
        "status": "success",
        "rows_extracted": 0,
        "rows_transformed": 0,
        "rows_loaded": 0,
        "output_path": output_path or OUTPUT_FILE,
        "level_filter": level,
    }

    # STEP 1: EXTRACT
    start_timer("STEP 1: Extract raw data")
    df_raw = extract_raw_data(level_filter=level)
    step_timings["extract"] = end_timer("STEP 1: Extract raw data")
    if df_raw is None:
        results["status"] = "error"
        return results

    results["rows_extracted"] = len(df_raw)

    # STEP 2: TRANSFORM
    start_timer("STEP 2: Transform (FAIR scoring)")
    df_scores = transform_health_scores(df_raw)
    step_timings["transform"] = end_timer("STEP 2: Transform (FAIR scoring)")
    if df_scores is None:
        results["status"] = "error"
        return results

    results["rows_transformed"] = len(df_scores)

    # STEP 3: LOAD
    if dry_run:
        print("\n[DRY RUN] Skipping file write")
        results["rows_loaded"] = len(df_scores)
    else:
        start_timer("STEP 3: Load to CSV")
        rows_written = load_to_csv(df_scores, output_path)
        step_timings["load"] = end_timer("STEP 3: Load to CSV")
        results["rows_loaded"] = rows_written

        # STEP 3b: Load hourly CSV (append-only for 24h chart) - conditional
        if output_hourly:
            start_timer("STEP 3b: Load hourly CSV")
            hourly_written = save_hourly_health(df_scores)
            step_timings["load_hourly"] = end_timer("STEP 3b: Load hourly CSV")
            if hourly_written:
                results["rows_loaded_hourly"] = len(df_scores)

    # STEP 4: Safety Flags Summary
    print_safety_flags_summary(df_scores)

    # Total time calculation
    total_elapsed = time.time() - total_start

    # Final summary with timing
    if not scheduled:
        print("\n" + "="*70)
        print("ETL PIPELINE COMPLETE")
        print("="*70)
        print(f"  Status: {results['status']}")
        print(f"  Rows extracted:   {results['rows_extracted']}")
        print(f"  Rows transformed: {results['rows_transformed']}")
        print(f"  Rows loaded:      {results['rows_loaded']}")
        print(f"  Output file:      {results['output_path']}")
        if level:
            print(f"  Level filter:     Level {level} only")
        print("-"*70)
        print("  TIMING BREAKDOWN:")
        print(f"    Extract:     {step_timings.get('extract', 0):.2f}s")
        print(f"    Transform:   {step_timings.get('transform', 0):.2f}s")
        print(f"    Load:        {step_timings.get('load', 0):.2f}s")
        print(f"    TOTAL:       {total_elapsed:.2f}s")
        print("="*70)

        # Check if within target
        if total_elapsed < 45:
            print(f"\n✓ Pipeline completed in {total_elapsed:.2f}s (TARGET: <45s)")
        else:
            print(f"\n⚠ Pipeline took {total_elapsed:.2f}s (TARGET: <45s)")
    else:
        # Scheduled mode: print minimal summary
        print(f"[INFO] ETL Complete | Status: {results['status']} | Rows: {results['rows_loaded']} | Time: {total_elapsed:.1f}s")

    return results


# ──────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FAIR Health Scoring ETL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 scripts/run_health_etl.py                    # Run full pipeline
  python3 scripts/run_health_etl.py --dry-run          # Test without writing
  python3 scripts/run_health_etl.py -o custom.csv    # Custom output file
  python3 scripts/run_health_etl.py --level 1          # Test Level 1 only (22 AHUs)
  python3 scripts/run_health_etl.py --level all        # All levels

Output:
  data/health_all_levels.csv
"""
    )

    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output CSV file path (default: data/health_all_levels.csv)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run ETL but skip file write"
    )

    parser.add_argument(
        "--level",
        default=None,
        help="Filter by specific level (1-11) or 'all' for all levels"
    )

    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run in scheduled mode (quiet output, automatic settings)"
    )

    parser.add_argument(
        "--output-hourly",
        action="store_true",
        help="Generate health_hourly.csv (hourly append mode)"
    )

    args = parser.parse_args()

    # Parse level filter
    level_filter = None
    if args.level and args.level.lower() != 'all':
        try:
            level_filter = int(args.level)
            if level_filter < 1 or level_filter > 11:
                print(f"Error: Level must be 1-11, got {level_filter}")
                sys.exit(1)
        except ValueError:
            print(f"Error: Invalid level '{args.level}'. Must be integer 1-11 or 'all'")
            sys.exit(1)

    # Set default output path
    if args.output is None:
        args.output = OUTPUT_FILE

    # Run pipeline
    results = run_etl_pipeline(
        output_path=args.output,
        dry_run=args.dry_run,
        level=level_filter,
        scheduled=args.scheduled,
        output_hourly=args.output_hourly
    )

    # Exit with appropriate code
    if results["status"] == "success":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
