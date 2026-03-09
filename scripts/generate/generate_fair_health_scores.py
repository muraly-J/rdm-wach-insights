#!/usr/bin/env python3
"""
generate_fair_health_scores.py
───────────────────────────────
Two-step process:
1. FETCH_RAW: Pull raw metrics from InfluxDB and save to intermediate CSV
2. COMPUTE_SCORES: Load raw data, apply FAIR scoring (median+MAD + 70/30 blend), generate health scores

FAIR Scoring Algorithm (per-AHU baseline only):
- Each AHU is judged entirely against its own historical baseline
- No fleet comparison needed - each unit has different characteristics
- Uses median + MAD (robust stats) instead of mean + std

Usage:
    # Both steps at once
    python generate_fair_health_scores.py --range 7d

    # Step 1 only: fetch raw data
    python generate_fair_health_scores.py --fetch-only

    # Step 2 only: compute scores from existing raw data
    python generate_fair_health_scores.py --compute-only

Output:
- data/level1_raw_metrics_<range>.csv - Raw InfluxDB measurements
- data/level1_hourly_health_<range>.csv - Final output with health index and scores
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import argparse

# Add backend to path for imports (scripts/generate → .. → scripts → .. → backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

# Import from backend
from models.schemas import ALLOWED_DEVICES
from core.influx_client import fetch_time_series, get_available_devices


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# Level vs trend blend (70% level + 30% trend)
LEVEL_WEIGHT = 0.70
TREND_WEIGHT = 0.30

# Sensitivity factors for each score
SENSITIVITY = {
    "energy_anomaly": 2.0,
    "pf_degradation": 2.5,
    "phase_imbalance": 2.0,
    "thd_drift": 2.0,
    "overload": 2.0,
}

# Slope sensitivity (after normalising slope by own robust-std)
SLOPE_SENS = 3.0

# PF load discount thresholds
PF_DISCOUNT_THRESHOLD = 0.60   # below 60% of own median power
PF_DISCOUNT_FACTOR = 0.35      # reduce score to 35% of computed value

# Minimum robust-std (prevents division by near-zero)
MIN_RSTD = {
    "delta_kwh": 0.05,
    "power_factor_avg": 0.008,
    "current_unbalance": 0.15,
    "composite_thd_24h": 0.15,
    "power_total": 0.05,
}

# THD uses 24h rolling mean to filter transient spikes
THD_ROLLING_H = 24

# Slope computed over this many hours of history (7 days)
TREND_WINDOW_H = 168


# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def robust_params(values):
    """
    Compute robust location (median) and scale (1.4826 × MAD).
    
    1.4826 × MAD equals std for a normal distribution.
    For heavy-tailed or bimodal distributions it is far more stable.
    
    Returns (median, rstd) where rstd >= MIN_RSTD.
    """
    v = values[~np.isnan(values)]
    if len(v) < 3:
        median = float(np.nanmedian(values)) if len(values) > 0 else 0.0
        return median, MIN_RSTD.get('default', 0.01)
    
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, MIN_RSTD.get('default', 0.01))
    return med, rstd


def sigmoid(x: float) -> float:
    """Numerically stable logistic sigmoid."""
    x = max(-500, min(500, x))
    return 1.0 / (1.0 + np.exp(-x))


def sigmoid_score(raw: float) -> float:
    """
    Map raw penalty to [0, 1] where raw=0 gives score=0.
    
    Standard sigmoid gives 0.5 at raw=0. We shift and rescale:
        score = clip(sigmoid(raw) * 2 - 1, 0, 1)
    
    Behaviour:
        raw = 0  → 0.00   (exactly at own baseline, no concern)
        raw = 1  → 0.46   (1 std above/below)
        raw = 2  → 0.76   (2 std)
        raw = 3  → 0.91   (3 std)
    """
    raw = max(-500.0, min(500.0, float(raw)))
    s = sigmoid(raw) * 2.0 - 1.0
    return float(np.clip(s, 0.0, 1.0))


def ols_slope(values):
    """
    OLS slope β through equally-spaced points (0, y_0), (1, y_1), …
    
    Closed-form: β = [n·Σ(i·y) − Σ(i)·Σ(y)] / [n·Σ(i²) − (Σ(i))²]
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 3:
        return 0.0
    i_arr = np.arange(n, dtype=float)
    num = n * np.dot(i_arr, v) - i_arr.sum() * v.sum()
    denom = n * np.dot(i_arr, i_arr) - i_arr.sum() ** 2
    return float(num / denom) if denom != 0 else 0.0


def clamp01(x: float) -> float:
    """Clamp value to [0, 1]."""
    return float(np.clip(x, 0.0, 1.0))


def compute_7d_slope(series):
    """Calculate normalized 7-day slope."""
    if len(series) < TREND_WINDOW_H:
        return 0.0
    y = series.dropna().values
    if len(y) < 2:
        return 0.0
    try:
        x = list(range(len(y)))
        y_mean = np.mean(y)
        numerator = sum((xi - x[-1]/2) * (yi - y_mean) for xi, yi in zip(x, y))
        denominator = sum((xi - x[-1]/2) ** 2 for xi in x)
        if denominator == 0:
            return 0.0
        slope = numerator / denominator
        value_range = max(y) - min(y) if max(y) != min(y) else 1.0
        return slope / value_range if value_range > 0 else 0.0
    except:
        return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# SCORING FUNCTIONS (FAIR METHOD - PER-AHU BASELINE ONLY)
# ──────────────────────────────────────────────────────────────────────────────

def score_energy_anomaly(delta_kwh, ahu_median_delta, ahu_rstd_delta, hist_delta_series):
    """
    Score 1 · Energy Anomaly (weight 15%)
    
    Is this AHU consuming an unusual amount of energy this hour compared
    to what IT normally consumes (based on its own historical baseline).
    
    Level term (70%): z = (delta_kwh − median) / rstd
    Trend term (30%): slope over 7 days
    
    Returns score ∈ [0,1]
    """
    if delta_kwh is None or np.isnan(delta_kwh) or delta_kwh < 0:
        return 0.0, np.nan
    
    if ahu_median_delta is None or np.isnan(ahu_median_delta):
        return 0.0, np.nan
    
    rstd = max(ahu_rstd_delta, MIN_RSTD["delta_kwh"])
    if rstd <= 0:
        return 0.0, np.nan
    
    z = (delta_kwh - ahu_median_delta) / rstd
    raw = 0.6 * abs(z) + 0.4 * max(0.0, z)
    lv = sigmoid_score(raw * SENSITIVITY["energy_anomaly"])
    
    # Trend term
    slope_n = float(np.clip(ols_slope(hist_delta_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)


def score_pf_degradation(pf, power, ahu_median_pf, ahu_rstd_pf, hist_pf_series):
    """
    Score 2 · PF Degradation (weight 25%)
    
    Is this AHU's power factor lower than its own established normal,
    and is it trending downward.
    
    Level term (70%): z = (median_PF − current_PF) / rstd_PF
    Trend term (30%): declining slope = worsening
    
    Load discount: if power < 60% of median, scale score × 0.35
    """
    if pf is None or np.isnan(pf):
        return 0.0, np.nan
    
    if ahu_median_pf is None or np.isnan(ahu_median_pf):
        return 0.0, np.nan
    
    rstd = max(ahu_rstd_pf, MIN_RSTD["power_factor_avg"])
    if rstd <= 0:
        return 0.0, np.nan
    
    z = (ahu_median_pf - pf) / rstd   # positive = below own normal = bad
    lv = sigmoid_score(z * SENSITIVITY["pf_degradation"])
    
    slope_n = float(np.clip(ols_slope(hist_pf_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, -slope_n) * SLOPE_SENS)
    
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    
    # Load discount
    if (power is not None and not np.isnan(power) 
        and ahu_median_pf > 0
        and power < PF_DISCOUNT_THRESHOLD * ahu_median_pf):
        score *= PF_DISCOUNT_FACTOR
    
    return clamp01(score), round(z, 3)


def score_phase_imbalance(unbal, ahu_median_unbal, ahu_rstd_unbal, hist_unbal_series):
    """
    Score 3 · Phase Imbalance (weight 25%)
    
    Is this AHU's current unbalance higher than its own established normal,
    and is it trending upward.
    
    Level term (70%): z = (current − median) / rstd
    Trend term (30%): rising slope = worsening
    """
    if unbal is None or np.isnan(unbal):
        return 0.0, np.nan
    
    if ahu_median_unbal is None or np.isnan(ahu_median_unbal):
        return 0.0, np.nan
    
    rstd = max(ahu_rstd_unbal, MIN_RSTD["current_unbalance"])
    if rstd <= 0:
        return 0.0, np.nan
    
    z = (unbal - ahu_median_unbal) / rstd
    lv = sigmoid_score(z * SENSITIVITY["phase_imbalance"])
    
    slope_n = float(np.clip(ols_slope(hist_unbal_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)


def score_thd_drift(thd_24h, ahu_median_thd, ahu_rstd_thd, hist_thd_24h_series):
    """
    Score 4 · THD Drift (weight 15%)
    
    Is this AHU's harmonic distortion elevated above its own normal trend,
    and is it drifting upward.
    
    CRITICAL: Input thd_24h is the 24-hour rolling mean.
    Baseline MUST also be computed on 24h-mean series, not instantaneous.
    """
    if thd_24h is None or np.isnan(thd_24h):
        return 0.0, np.nan
    
    if ahu_median_thd is None or np.isnan(ahu_median_thd):
        return 0.0, np.nan
    
    rstd = max(ahu_rstd_thd, MIN_RSTD["composite_thd_24h"])
    if rstd <= 0:
        return 0.0, np.nan
    
    z = (thd_24h - ahu_median_thd) / rstd
    lv = sigmoid_score(z * SENSITIVITY["thd_drift"])
    
    slope_n = float(np.clip(ols_slope(hist_thd_24h_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)


def score_overload(power, ahu_median_power, ahu_rstd_power, ahu_p95_power, hist_power_series):
    """
    Score 5 · Overload (weight 20%)
    
    Is this AHU approaching or exceeding its own historical power ceiling,
    and is load trending upward.
    
    Three components:
    A. Ceiling term (50%): how far above own p95
    B. Z-score term (30%): current vs own median  
    C. Trend term (20%): rising load over 7 days
    """
    if power is None or np.isnan(power):
        return 0.0, np.nan
    
    if ahu_median_power is None or np.isnan(ahu_median_power):
        return 0.0, np.nan
    
    if ahu_p95_power is None or np.isnan(ahu_p95_power) or ahu_p95_power <= 0:
        return 0.0, np.nan
    
    rstd = max(ahu_rstd_power, MIN_RSTD["power_total"])
    
    # A: ceiling proximity
    power_ratio = power / ahu_p95_power
    demand = max(0.0, power_ratio - 0.85)
    score_A = sigmoid_score(demand * 8.0)
    
    # B: z-score vs own mean
    z = (power - ahu_median_power) / rstd
    score_B = sigmoid_score(z * 1.5)
    
    # C: trend
    slope_n = float(np.clip(ols_slope(hist_power_series) / rstd, -10, 10))
    score_C = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    
    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score), round(z, 3)


def calculate_health_index(risk_scores):
    """
    health_index = 100 - penalty × 100
    where penalty = Σ weight_i × score_i
    
    All scores at 0 → index = 100 (perfect)
    All scores at 1 → index = 0 (critical)
    
    Weights: energy=0.15, pf=0.25, imbalance=0.25, thd=0.15, overload=0.20
    """
    WEIGHTS = {
        "energy_anomaly": 0.15,
        "pf_degradation": 0.25,
        "phase_imbalance": 0.25,
        "thd_drift": 0.15,
        "overload": 0.20,
    }
    
    penalty = sum(WEIGHTS.get(k, 0) * score for k, score in risk_scores.items())
    health_index = 100 - (penalty * 100)
    return float(np.clip(health_index, 0.0, 100.0))


def get_health_tier(health_index):
    """Map health index to tier string."""
    if health_index >= 80:
        return "Healthy"
    elif health_index >= 60:
        return "Monitor"
    elif health_index >= 40:
        return "Maintenance Soon"
    else:
        return "Critical"


# ──────────────────────────────────────────────────────────────────────────────
# DATA PROCESSING
# ──────────────────────────────────────────────────────────────────────────────

def fetch_raw_metrics(level=1, time_range="all_time"):
    """
    Fetch raw metrics from InfluxDB for all AHUs on a level.
    
    Returns DataFrame with columns:
        timestamp, ahu_id, power_total, energy_import,
        power_factor_avg, current_unbalance, current_l1_thd, current_l3_thd
    """
    # Get all devices on this level
    available_devices = get_available_devices(time_range)
    level_prefix = f"e{str(level).zfill(2)}"
    level_devices = [d for d in available_devices if d.startswith(level_prefix)]
    
    print(f"Level {level}: Found {len(level_devices)} devices")
    if not level_devices:
        return pd.DataFrame()
    
    # Fetch all metrics
    print("  Fetching raw time series data from InfluxDB...")
    
    df_power = fetch_time_series(level_devices, "power_total", time_range)
    df_energy = fetch_time_series(level_devices, "energy_import", time_range)
    df_pf = fetch_time_series(level_devices, "power_factor_avg", time_range)
    df_unbalance = fetch_time_series(level_devices, "current_unbalance", time_range)
    df_thd_l1 = fetch_time_series(level_devices, "current_l1_thd", time_range)
    df_thd_l3 = fetch_time_series(level_devices, "current_l3_thd", time_range)
    
    if df_power.empty:
        print("  No data available!")
        return pd.DataFrame()
    
    # Combine all metrics into single DataFrame
    print("  Combining metrics...")
    
    records = []
    for ts in df_power.index:
        for ahu_id in level_devices:
            try:
                power = float(df_power.loc[ts, ahu_id]) if pd.notna(df_power.loc[ts, ahu_id]) else None
                energy = float(df_energy.loc[ts, ahu_id]) if pd.notna(df_energy.loc[ts, ahu_id]) else None
                pf = float(df_pf.loc[ts, ahu_id]) if pd.notna(df_pf.loc[ts, ahu_id]) else None
                unbalance = float(df_unbalance.loc[ts, ahu_id]) if pd.notna(df_unbalance.loc[ts, ahu_id]) else None
                thd_l1 = float(df_thd_l1.loc[ts, ahu_id]) if pd.notna(df_thd_l1.loc[ts, ahu_id]) else None
                thd_l3 = float(df_thd_l3.loc[ts, ahu_id]) if pd.notna(df_thd_l3.loc[ts, ahu_id]) else None
                
                records.append({
                    "timestamp": ts.isoformat(),
                    "ahu_id": ahu_id,
                    "power_total": power,
                    "energy_import": energy,
                    "power_factor_avg": pf,
                    "current_unbalance": unbalance,
                    "current_l1_thd": thd_l1,
                    "current_l3_thd": thd_l3,
                })
            except Exception as e:
                continue
    
    df = pd.DataFrame(records)
    if df.empty:
        return df
    
    # Sort by timestamp then ahu_id
    df = df.sort_values(["timestamp", "ahu_id"]).reset_index(drop=True)
    
    return df


def compute_fair_health_scores(df):
    """
    Compute health scores from raw metrics DataFrame using FAIR per-AHU method.
    
    For each row (ahu_id at timestamp):
    - Compute robust baselines (median + MAD) from ALL data for that AHU
    - Apply per-AHU scoring (no fleet comparison)
    
    Returns DataFrame with columns matching original output schema.
    """
    print("Computing FAIR health scores (per-AHU baseline)...")
    
    # Composite THD
    df["composite_thd"] = df[["current_l1_thd", "current_l3_thd"]].max(axis=1)
    
    # Compute 24h rolling mean of THD (for proper baseline comparison)
    df["thd_24h_mean"] = (
        df.groupby("ahu_id")["composite_thd"]
          .transform(lambda s: s.rolling(THD_ROLLING_H, min_periods=1).mean())
    )
    
    # Build per-AHU baselines
    print("  Computing robust baselines (median + MAD)...")
    
    # Pre-compute per-AHU statistics
    ahu_baselines = {}
    for ahu_id in df['ahu_id'].unique():
        ahu_df = df[df['ahu_id'] == ahu_id].copy()
        
        # Power
        power_vals = ahu_df['power_total'].dropna().values
        power_median, power_rstd = robust_params(power_vals)
        
        # Energy (delta_kwh computed from cumulative meter)
        energy_vals = ahu_df['energy_import'].dropna().values
        if len(energy_vals) >= 2:
            delta_vals = np.diff(energy_vals)
            delta_median, delta_rstd = robust_params(delta_vals)
        else:
            delta_median, delta_rstd = 0.0, MIN_RSTD["delta_kwh"]
        
        # Power factor
        pf_vals = ahu_df['power_factor_avg'].dropna().values
        pf_median, pf_rstd = robust_params(pf_vals)
        
        # Unbalance
        unbal_vals = ahu_df['current_unbalance'].dropna().values
        unbal_median, unbal_rstd = robust_params(unbal_vals)
        
        # THD (use the 24h rolling mean series for both score and baseline)
        thd_24h_vals = ahu_df['thd_24h_mean'].dropna().values
        thd_median, thd_rstd = robust_params(thd_24h_vals)
        
        ahu_baselines[ahu_id] = {
            "power_median": power_median,
            "power_rstd": power_rstd,
            "power_p95": float(np.nanpercentile(power_vals, 95)) if len(power_vals) > 0 else None,
            "energy_median": delta_median,
            "energy_rstd": delta_rstd,
            "pf_median": pf_median,
            "pf_rstd": pf_rstd,
            "unbal_median": unbal_median,
            "unbal_rstd": unbal_rstd,
            "thd_median": thd_median,
            "thd_rstd": thd_rstd,
        }
    
    # Process each AHU separately
    results = []
    ahu_ids = sorted(df['ahu_id'].unique())
    
    for i, ahu_id in enumerate(ahu_ids):
        if i % 5 == 0:
            print(f"  [{i+1}/{len(ahu_ids)}] Processing {ahu_id}...")
        
        ahu_df = df[df['ahu_id'] == ahu_id].copy()
        ahu_df = ahu_df.sort_values('timestamp').reset_index(drop=True)
        
        baseline = ahu_baselines[ahu_id]
        
        # Pre-extract numpy arrays for efficient history slicing
        a_power = ahu_df['power_total'].values.astype(float)
        a_energy = ahu_df['energy_import'].values.astype(float)
        a_pf = ahu_df['power_factor_avg'].values.astype(float)
        a_unbal = ahu_df['current_unbalance'].values.astype(float)
        a_thd24 = ahu_df['thd_24h_mean'].values.astype(float)
        
        # Compute delta_kwh from cumulative energy
        a_delta = np.empty(len(ahu_df), dtype=float)
        a_delta[:] = np.nan
        if len(a_energy) >= 2:
            for j in range(1, len(a_delta)):
                diff = a_energy[j] - a_energy[j-1]
                a_delta[j] = diff if diff >= 0 else np.nan
        
        for pos in range(len(ahu_df)):
            # History window: up to TREND_WINDOW_H hours ending at current row
            start_idx = max(0, pos - TREND_WINDOW_H + 1)
            
            # Get current values
            power_current = a_power[pos]
            energy_current = a_energy[pos]
            delta_kwh = a_delta[pos]
            pf_current = a_pf[pos]
            unbalance_current = a_unbal[pos]
            thd_24h = a_thd24[pos]
            
            # Extract history slices
            hist_delta = a_delta[start_idx:pos+1]
            hist_pf = a_pf[start_idx:pos+1]
            hist_unbal = a_unbal[start_idx:pos+1]
            hist_thd24 = a_thd24[start_idx:pos+1]
            hist_power = a_power[start_idx:pos+1]
            
            # Compute scores
            energy_score, z_energy = score_energy_anomaly(
                delta_kwh, baseline["energy_median"], baseline["energy_rstd"], hist_delta
            )
            
            pf_score, z_pf = score_pf_degradation(
                pf_current, power_current,
                baseline["pf_median"], baseline["pf_rstd"], hist_pf
            )
            
            unbal_score, z_unbal = score_phase_imbalance(
                unbalance_current,
                baseline["unbal_median"], baseline["unbal_rstd"], hist_unbal
            )
            
            thd_score, z_thd = score_thd_drift(
                thd_24h,
                baseline["thd_median"], baseline["thd_rstd"], hist_thd24
            )
            
            overload_score, z_overload = score_overload(
                power_current,
                baseline["power_median"], baseline["power_rstd"],
                baseline["power_p95"], hist_power
            )
            
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
            
            # Raw measurements
            row = ahu_df.iloc[pos]
            
            results.append({
                "timestamp": row['timestamp'],
                "ahu_id": ahu_id,
                "level": f"Level {row.get('level', 1)}",
                "health_index": round(health_index, 1),
                "tier": tier,
                "energy_anomaly": risk_scores["energy_anomaly"],
                "pf_degradation": risk_scores["pf_degradation"],
                "phase_imbalance": risk_scores["phase_imbalance"],
                "thd_drift": risk_scores["thd_drift"],
                "overload": risk_scores["overload"],
                "power_total": round(power_current, 3) if power_current is not None else None,
                "power_factor": round(pf_current, 4) if pf_current is not None else None,
                "unbalance_pct": round(unbalance_current, 3) if unbalance_current is not None else None,
                "thd_24h": round(thd_24h, 3) if thd_24h is not None else None,
                "delta_kwh": round(delta_kwh, 3) if delta_kwh is not None else None,
                "data_quality_flag": 0 if not np.isnan(thd_24h) else 1,
                "safety_flags": "",
                "z_energy": round(z_energy, 3) if z_energy is not None else None,
                "z_pf": round(z_pf, 3) if z_pf is not None else None,
                "z_imbalance": round(z_unbal, 3) if z_unbal is not None else None,
                "z_thd": round(z_thd, 3) if z_thd is not None else None,
                "z_overload": round(z_overload, 3) if z_overload is not None else None,
            })
    
    return pd.DataFrame(results)


def generate_all_time_ranges(output_dir=None):
    """Generate health scores for all time ranges: 24h, 7d, 30d"""
    if output_dir is None:
        output_dir = "/Users/rdmasia/wach-insight/data"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Map display names to InfluxDB time range keys
    time_ranges = [
        ("last_24h", "24h"),
        ("last_7d", "7d"),
        ("last_30d", "30d"),
    ]
    
    for range_key, range_name in time_ranges:
        raw_path = os.path.join(output_dir, f"level1_raw_metrics_{range_name}.csv")
        output_path = os.path.join(output_dir, f"level1_hourly_health_{range_name}.csv")
        
        # Phase 1: Fetch raw data
        print(f"\n{'='*60}")
        print(f"  Generating for {range_name} ({range_key})")
        print('='*60)
        
        df_raw = fetch_raw_metrics(level=1, time_range=range_key)
        if df_raw.empty:
            print(f"  No data for {range_name}")
            continue
        
        # Save raw metrics
        df_raw.to_csv(raw_path, index=False)
        print(f"✓ Saved raw metrics: {raw_path} ({len(df_raw)} rows)")
        
        # Phase 2: Compute FAIR health scores
        print(f"\nComputing FAIR health scores...")
        df_scores = compute_fair_health_scores(df_raw)
        
        # Save final output
        df_scores = df_scores.sort_values(["timestamp", "ahu_id"]).reset_index(drop=True)
        df_scores.to_csv(output_path, index=False)
        
        print(f"\n✓ Saved {len(df_scores)} records to {output_path}")
        
        # Summary
        print(f"\nSummary for {range_name}:")
        print(f"  AHUs: {df_scores['ahu_id'].nunique()}")
        print(f"  Hours: {df_scores['timestamp'].nunique()}")
        print(f"  Health Index: [{df_scores['health_index'].min():.1f}, {df_scores['health_index'].max():.1f}]")
        print(f"  Health Tiers: {dict(df_scores['tier'].value_counts())}")


def main():
    parser = argparse.ArgumentParser(description="Generate FAIR health scores for AHU fleet")
    parser.add_argument("--fetch-only", action="store_true",
                       help="Only fetch raw data, don't compute scores")
    parser.add_argument("--compute-only", action="store_true",
                       help="Only compute scores from existing raw data")
    parser.add_argument("--range", type=str, default=None,
                       help="Time range: 24h, 7d, 30d (default: all ranges)")
    parser.add_argument("--output", type=str, default=None,
                       help="Output CSV path for scores")
    parser.add_argument("--raw-output", type=str, default=None,
                       help="Output CSV path for raw metrics")
    parser.add_argument("--all-ranges", action="store_true",
                       help="Generate for all time ranges (24h, 7d, 30d)")
    
    args = parser.parse_args()
    
    if args.all_ranges:
        generate_all_time_ranges()
    elif args.fetch_only:
        # Phase 1 only: fetch raw data
        generate_all_time_ranges()
    elif args.compute_only:
        # Phase 2 only: compute scores from existing raw files
        output_dir = "/Users/rdmasia/wach-insight/data"
        time_ranges = ["24h", "7d", "30d"]
        
        for range_name in time_ranges:
            raw_path = os.path.join(output_dir, f"level1_raw_metrics_{range_name}.csv")
            output_path = args.output or os.path.join(output_dir, f"level1_hourly_health_{range_name}.csv")
            
            if os.path.exists(raw_path):
                print(f"\nComputing FAIR scores for {range_name}...")
                df_raw = pd.read_csv(raw_path, parse_dates=['timestamp'])
                print(f"  Loaded {len(df_raw)} rows from {raw_path}")
                
                # Check for required columns
                required = ['power_total', 'energy_import', 'power_factor_avg', 
                           'current_unbalance', 'current_l1_thd', 'current_l3_thd']
                missing = [c for c in required if c not in df_raw.columns]
                if missing:
                    print(f"  WARNING: Missing columns: {missing}")
                
                df_scores = compute_fair_health_scores(df_raw)
                df_scores.to_csv(output_path, index=False)
                print(f"✓ Saved {len(df_scores)} records to {output_path}")
            else:
                print(f"\n⚠ Raw data not found: {raw_path}")
    elif args.range:
        # Generate for a specific range (both phases)
        range_map = {
            "24h": "last_24h",
            "7d": "last_7d", 
            "30d": "last_30d",
        }
        range_key = range_map.get(args.range)
        if range_key is None:
            print(f"Invalid time range: {args.range}")
            print("Valid options: 24h, 7d, 30d")
        else:
            output_path = args.output or f"/Users/rdmasia/wach-insight/data/level1_hourly_health_{args.range}.csv"
            raw_output_path = args.raw_output or f"/Users/rdmasia/wach-insight/data/level1_raw_metrics_{args.range}.csv"
            
            # Phase 1: Fetch raw data
            print(f"\nFetching raw data for {args.range}...")
            df_raw = fetch_raw_metrics(level=1, time_range=range_key)
            if not df_raw.empty:
                df_raw.to_csv(raw_output_path, index=False)
                print(f"✓ Saved {len(df_raw)} rows to {raw_output_path}")
            else:
                print("⚠ No data available")
            
            # Phase 2: Compute FAIR scores
            if not df_raw.empty:
                print(f"\nComputing health scores for {args.range}...")
                df_scores = compute_fair_health_scores(df_raw)
                if not df_scores.empty:
                    df_scores.to_csv(output_path, index=False)
                    print(f"✓ Saved {len(df_scores)} records to {output_path}")
    else:
        # Default: generate for all ranges
        generate_all_time_ranges()
    
    print("\nDone!")


if __name__ == "__main__":
    main()
