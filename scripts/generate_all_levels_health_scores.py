#!/usr/bin/env python3
"""
generate_all_levels_health_scores.py
─────────────────────────────────────
Multi-level health score generation with FAIR algorithm.

This script:
1. Fetches raw metrics from InfluxDB for sample AHUs across all 11 levels
2. Applies FAIR scoring (per-AHU baseline with median + MAD)
3. Generates health reports for all levels

Batch Processing:
- Processes one level at a time with configurable delay
- Avoids InfluxDB timeouts by spacing out requests
- Saves intermediate raw data for reproducibility

Usage:
    # Generate all time ranges for all levels
    python generate_all_levels_health_scores.py --all-ranges

    # Generate specific time range
    python generate_all_levels_health_scores.py --range 7d

    # Generate with custom delay between levels (default: 3 seconds)
    python generate_all_levels_health_scores.py --all-ranges --delay 5

    # Process only specific levels
    python generate_all_levels_health_scores.py --levels 1,3,5

Output:
- data/all_levels_raw_{timeRange}.csv    - Raw InfluxDB measurements
- data/all_levels_health_{timeRange}.csv - Final output with health index and scores

FAIR Algorithm Reference:
- Each AHU judged only against its own historical baseline (median + MAD)
- 70% level term + 30% trend term
- No fleet comparison - inherently fair across differently-sized AHUs

Sample Device Selection:
- Level 1:  e0101, e0105, e0111
- Level 2:  e0201, e0205, e0213
- Level 3:  e0301, e0307, e0401
- ... (2-3 devices per level)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import argparse
import time
import json

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models.schemas import AHU_LEVEL_CONFIG, get_devices_by_level
from core.influx_client import fetch_time_series


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# FAIR Algorithm Parameters
LEVEL_WEIGHT = 0.70   # "is it bad right now?"
TREND_WEIGHT = 0.30   # "is it getting worse?"

SENSITIVITY = {
    "energy_anomaly": 2.0,
    "pf_degradation": 2.5,
    "phase_imbalance": 2.0,
    "thd_drift": 2.0,
    "overload": 2.0,
}

SLOPE_SENS = 3.0
PF_DISCOUNT_THRESHOLD = 0.60
PF_DISCOUNT_FACTOR = 0.35

MIN_RSTD = {
    "delta_kwh": 0.05,
    "power_factor_avg": 0.008,
    "current_unbalance": 0.15,
    "composite_thd_24h": 0.15,
    "power_total": 0.05,
}

THD_ROLLING_H = 24
TREND_WINDOW_H = 168   # 7 days

# Sample device selection - updated to fetch all devices per level
SAMPLE_DEVICES = {
    1: get_devices_by_level(1),     # All 21 devices on Level 1
    2: get_devices_by_level(2),     # All 15 devices on Level 2
    3: get_devices_by_level(3),     # All 16 devices on Level 3
    4: get_devices_by_level(4),     # All 13 devices on Level 4
    5: get_devices_by_level(5),     # All 12 devices on Level 5
    6: get_devices_by_level(6),     # All 11 devices on Level 6
    7: get_devices_by_level(7),     # All 4 devices on Level 7
    8: get_devices_by_level(8),     # All 5 devices on Level 8
    9: get_devices_by_level(9),     # All 8 devices on Level 9
    10: get_devices_by_level(10),   # All 8 devices on Level 10
    11: get_devices_by_level(11),   # All 8 devices on Level 11
}

# Broad sample: all devices per level
BROAD_SAMPLE_DEVICES = {
    1: ['e0101', 'e0102', 'e0103', 'e0104', 'e0105', 'e0106', 'e0107', 'e0108', 'e0109', 'e0110', 'e0111', 'e0112', 'e0113', 'e0114', 'e0115', 'e0116', 'e0117', 'e0118', 'e0120', 'e0121', 'e0212'],
    2: ['e0201', 'e0202', 'e0203', 'e0204', 'e0205', 'e0206', 'e0207', 'e0208', 'e0209', 'e0213', 'e0214', 'e0215', 'e0216', 'e0217', 'e0218'],
    3: ['e0210', 'e0211', 'e0301', 'e0303', 'e0304', 'e0306', 'e0307', 'e0308', 'e0311', 'e0312', 'e0313', 'e0314', 'e0315', 'e0401', 'e0402', 'e0423'],
    4: ['e0403', 'e0404', 'e0406', 'e0407', 'e0408', 'e0409', 'e0411', 'e0412', 'e0413', 'e0414', 'e0415', 'e0416', 'e0419'],
    5: ['e0501', 'e0502', 'e0503', 'e0504', 'e0505', 'e0506', 'e0507', 'e0508', 'e0509', 'e0510', 'e0511', 'e0622'],
    6: ['e0602', 'e0603', 'e0604', 'e0605', 'e0606', 'e0607', 'e0611', 'e0625', 'e0626', 'e0627', 'e0628'],
    7: ['e0701', 'e0702', 'e0703', 'e0704'],
    8: ['e0801', 'e0802', 'e0803', 'e0804', 'e0805'],
    9: ['e0901', 'e0902', 'e0903', 'e0904', 'e0905', 'e0906', 'e0907', 'e0908'],
    10: ['e1001', 'e1002', 'e1003', 'e1004', 'e1005', 'e1006', 'e1007', 'e1008'],
    11: ['e1101', 'e1102', 'e1103', 'e1104', 'e1105', 'e1106', 'e1107', 'e1108'],
}

# Time range mapping
TIME_RANGE_MAP = {
    "24h": "last_24h",
    "7d": "last_7d",
    "30d": "last_30d",
}

# Output paths
DATA_DIR = "/Users/rdmasia/wach-insight/data"


# ──────────────────────────────────────────────────────────────────────────────
# SCORING FUNCTIONS (FAIR METHOD)
# ──────────────────────────────────────────────────────────────────────────────

def robust_params(values):
    """Compute robust location (median) and scale (1.4826 × MAD)."""
    v = values[~np.isnan(values)]
    if len(v) < 3:
        median = float(np.nanmedian(values)) if len(values) > 0 else 0.0
        return median, MIN_RSTD.get('default', 0.01)
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    rstd = max(1.4826 * mad, MIN_RSTD.get('default', 0.01))
    return med, rstd


def sigmoid(x):
    x = max(-500, min(500, x))
    return 1.0 / (1.0 + np.exp(-x))


def sigmoid_score(raw):
    raw = max(-500.0, min(500.0, float(raw)))
    s = sigmoid(raw) * 2.0 - 1.0
    return float(np.clip(s, 0.0, 1.0))


def ols_slope(values):
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 3:
        return 0.0
    i_arr = np.arange(n, dtype=float)
    num = n * np.dot(i_arr, v) - i_arr.sum() * v.sum()
    denom = n * np.dot(i_arr, i_arr) - i_arr.sum() ** 2
    return float(num / denom) if denom != 0 else 0.0


def clamp01(x):
    return float(np.clip(x, 0.0, 1.0))


def score_energy_anomaly(delta_kwh, ahu_median_delta, ahu_rstd_delta, hist_delta_series):
    """Score 1 · Energy Anomaly (weight 15%)"""
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
    slope_n = float(np.clip(ols_slope(hist_delta_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)


def score_pf_degradation(pf, power, ahu_median_pf, ahu_rstd_pf, hist_pf_series):
    """Score 2 · PF Degradation (weight 25%)"""
    if pf is None or np.isnan(pf):
        return 0.0, np.nan
    if ahu_median_pf is None or np.isnan(ahu_median_pf):
        return 0.0, np.nan
    rstd = max(ahu_rstd_pf, MIN_RSTD["power_factor_avg"])
    if rstd <= 0:
        return 0.0, np.nan
    z = (ahu_median_pf - pf) / rstd
    lv = sigmoid_score(z * SENSITIVITY["pf_degradation"])
    slope_n = float(np.clip(ols_slope(hist_pf_series) / rstd, -10, 10))
    tr = sigmoid_score(max(0.0, -slope_n) * SLOPE_SENS)
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    if (power is not None and not np.isnan(power)
        and ahu_median_pf > 0
        and power < PF_DISCOUNT_THRESHOLD * ahu_median_pf):
        score *= PF_DISCOUNT_FACTOR
    return clamp01(score), round(z, 3)


def score_phase_imbalance(unbal, ahu_median_unbal, ahu_rstd_unbal, hist_unbal_series):
    """Score 3 · Phase Imbalance (weight 25%)"""
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
    """Score 4 · THD Drift (weight 15%)"""
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
    """Score 5 · Overload (weight 20%)"""
    if power is None or np.isnan(power):
        return 0.0, np.nan
    if ahu_median_power is None or np.isnan(ahu_median_power):
        return 0.0, np.nan
    if ahu_p95_power is None or np.isnan(ahu_p95_power) or ahu_p95_power <= 0:
        return 0.0, np.nan
    rstd = max(ahu_rstd_power, MIN_RSTD["power_total"])
    power_ratio = power / ahu_p95_power
    demand = max(0.0, power_ratio - 0.85)
    score_A = sigmoid_score(demand * 8.0)
    z = (power - ahu_median_power) / rstd
    score_B = sigmoid_score(z * 1.5)
    slope_n = float(np.clip(ols_slope(hist_power_series) / rstd, -10, 10))
    score_C = sigmoid_score(max(0.0, slope_n) * SLOPE_SENS)
    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score), round(z, 3)


def calculate_health_index(risk_scores):
    """health_index = 100 - penalty * 100"""
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
    """Map health index to tier."""
    if health_index >= 80:
        return "Healthy"
    elif health_index >= 60:
        return "Monitor"
    elif health_index >= 40:
        return "Maintenance Soon"
    else:
        return "Critical"


def get_severity(score, metric_name):
    """Map score to severity level."""
    if score >= 0.8:
        return "Critical"
    elif score >= 0.6:
        return "Attention Required"
    elif score >= 0.4:
        return "Monitor"
    else:
        return "Normal"


# ──────────────────────────────────────────────────────────────────────────────
# DATA PROCESSING
# ──────────────────────────────────────────────────────────────────────────────

def get_sample_devices_for_level(level):
    """Get sample devices for a specific level."""
    if level not in SAMPLE_DEVICES:
        print(f"  ⚠️  Level {level} not in sample configuration, using all devices")
        return get_devices_by_level(level)[:3]
    return SAMPLE_DEVICES[level]


def fetch_raw_metrics_for_levels(levels, time_range="all_time", delay=3):
    """
    Fetch raw metrics from InfluxDB for selected levels.
    
    Args:
        levels: List of level numbers [1, 2, 3, ...]
        time_range: Time range key (last_24h, last_7d, last_30d)
        delay: Seconds to wait between levels (default: 3)
    
    Returns:
        DataFrame with columns: timestamp, ahu_id, level, power_total,
                                energy_import, power_factor_avg, current_unbalance,
                                current_l1_thd, current_l3_thd
    """
    all_records = []
    
    available_devices = get_available_devices_for_time_range(time_range)
    
    for level in sorted(levels):
        # Get sample devices for this level
        level_devices = get_sample_devices_for_level(level)
        
        # Filter to only devices that exist in the data
        level_devices = [d for d in level_devices if d in available_devices]
        
        if not level_devices:
            print(f"  ⚠️  Level {level}: No devices found in data")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing Level {level}: {len(level_devices)} devices")
        print(f"  Devices: {', '.join(level_devices)}")
        
        # Fetch metrics for this level
        df_power = fetch_time_series(level_devices, "power_total", time_range)
        df_energy = fetch_time_series(level_devices, "energy_import", time_range)
        df_pf = fetch_time_series(level_devices, "power_factor_avg", time_range)
        df_unbalance = fetch_time_series(level_devices, "current_unbalance", time_range)
        df_thd_l1 = fetch_time_series(level_devices, "current_l1_thd", time_range)
        df_thd_l3 = fetch_time_series(level_devices, "current_l3_thd", time_range)
        
        if df_power.empty:
            print(f"  ⚠️  Level {level}: No power data available")
            continue
        
        # Combine metrics
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
                        "level": f"Level {level}",
                        "power_total": power,
                        "energy_import": energy,
                        "power_factor_avg": pf,
                        "current_unbalance": unbalance,
                        "current_l1_thd": thd_l1,
                        "current_l3_thd": thd_l3,
                    })
                except Exception as e:
                    # Skip individual errors, continue with others
                    continue
        
        if records:
            all_records.extend(records)
            print(f"  ✓ Level {level}: Collected {len(records)} records")
        else:
            print(f"  ⚠️  Level {level}: No records collected")
        
        # Delay before next level (avoid InfluxDB timeout)
        if level < max(levels):
            print(f"  ⏳ Waiting {delay} seconds before next level...")
            time.sleep(delay)
    
    # Create DataFrame
    if not all_records:
        print("\n❌ No data collected from any level!")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_records)
    df = df.sort_values(["timestamp", "ahu_id"]).reset_index(drop=True)
    
    return df


def get_available_devices_for_time_range(time_range):
    """Get list of devices that have data in the specified time range."""
    # Reuse logic from get_available_devices
    from core.influx_client import _get_client, ALLOWED_TIME_RANGES
    
    influx_start = ALLOWED_TIME_RANGES[time_range]
    bucket = "wach_bucket_3"
    
    # Query for any device with power_total data
    flux_query = f'''
    from(bucket: "{bucket}")
      |> range(start: {influx_start})
      |> filter(fn: (r) => r._measurement =~ /^wach_e\\d{{4}}_power_total$/)
      |> distinct(column: "_measurement")
      |> keep(columns: ["_value"])
    '''
    
    client = _get_client()
    try:
        tables = client.query_api().query(flux_query)
        
        devices = set()
        for table in tables:
            for record in table.records:
                measurement = record.get_value()
                if measurement and measurement.startswith("wach_"):
                    parts = measurement.split("_")
                    if len(parts) >= 2:
                        devices.add(parts[1])
        
        return sorted(list(devices))
    except Exception as e:
        print(f"[influx_client] get_available_devices failed: {e}")
        return []
    finally:
        client.close()


def compute_risk_scores_for_levels(df, save_intermediate=True):
    """
    Compute health scores from raw metrics DataFrame using FAIR per-AHU method.
    
    Args:
        df: Raw metrics DataFrame
        save_intermediate: Save intermediate results
    
    Returns:
        DataFrame with health scores and risk metrics
    """
    print("\n" + "="*60)
    print("Computing FAIR Health Scores (per-AHU baseline)")
    print("="*60)
    
    # Add composite THD
    if 'current_l1_thd' in df.columns and 'current_l3_thd' in df.columns:
        df['composite_thd'] = df[['current_l1_thd', 'current_l3_thd']].max(axis=1)
    else:
        df['composite_thd'] = np.nan
    
    # Compute 24h rolling mean of THD per AHU
    df['thd_24h_mean'] = (
        df.groupby('ahu_id')['composite_thd']
          .transform(lambda s: s.rolling(THD_ROLLING_H, min_periods=1).mean())
    )
    
    # Build per-AHU baselines
    print("\nComputing robust baselines (median + MAD)...")
    
    ahu_baselines = {}
    ahu_ids = sorted(df['ahu_id'].unique())
    
    for i, ahu_id in enumerate(ahu_ids):
        if (i+1) % 10 == 0:
            print(f"  [{i+1}/{len(ahu_ids)}] Processing {ahu_id}...")
        
        ahu_df = df[df['ahu_id'] == ahu_id].copy()
        ahu_df = ahu_df.sort_values('timestamp').reset_index(drop=True)
        
        # Compute statistics
        power_vals = ahu_df['power_total'].dropna().values
        power_median, power_rstd = robust_params(power_vals)
        
        energy_vals = ahu_df['energy_import'].dropna().values
        if len(energy_vals) >= 2:
            delta_vals = np.diff(energy_vals)
            delta_median, delta_rstd = robust_params(delta_vals)
        else:
            delta_median, delta_rstd = 0.0, MIN_RSTD["delta_kwh"]
        
        pf_vals = ahu_df['power_factor_avg'].dropna().values
        pf_median, pf_rstd = robust_params(pf_vals)
        
        unbal_vals = ahu_df['current_unbalance'].dropna().values
        unbal_median, unbal_rstd = robust_params(unbal_vals)
        
        thd_24h_vals = ahu_df['thd_24h_mean'].dropna().values
        thd_median, thd_rstd = robust_params(thd_24h_vals)
        
        ahu_baselines[ahu_id] = {
            "power_median": power_median,
            "power_rstd": power_rstd,
            "power_p95": float(np.nanpercentile(power_vals, 95)) if len(power_vals) > 0 else None,
            "power_p99": float(np.nanpercentile(power_vals, 99)) if len(power_vals) > 0 else None,
            "energy_median": delta_median,
            "energy_rstd": delta_rstd,
            "pf_median": pf_median,
            "pf_rstd": pf_rstd,
            "unbal_median": unbal_median,
            "unbal_rstd": unbal_rstd,
            "thd_median": thd_median,
            "thd_rstd": thd_rstd,
        }
    
    # Compute safety flags
    print("\nComputing static safety flags...")
    
    def compute_safety_flags(baseline, power_median, power_p95):
        flags = []
        
        # THD_CHRONIC_HIGH: median 24h-THD > 15%
        thd_med = baseline.get("thd_median")
        if thd_med is not None and thd_med > 15.0:
            flags.append("THD_CHRONIC_HIGH")
        
        # IMBALANCE_SEVERE: median unbalance > 30%
        unbal_med = baseline.get("unbal_median")
        if unbal_med is not None and unbal_med > 30.0:
            flags.append("IMBALANCE_SEVERE")
        
        # PF_CHRONIC_LOW: median PF < 0.50
        pf_med = baseline.get("pf_median")
        if pf_med is not None and pf_med < 0.50:
            flags.append("PF_CHRONIC_LOW")
        
        # OVERLOAD_CHRONIC: median power > 90% of own p95
        if (power_median is not None and power_p95 is not None
                and power_p95 > 0 and power_median / power_p95 > 0.90):
            flags.append("OVERLOAD_CHRONIC")
        
        return ",".join(flags) if flags else ""
    
    safety_flags = {}
    for ahu_id in ahu_ids:
        baseline = ahu_baselines[ahu_id]
        safety_flags[ahu_id] = compute_safety_flags(
            baseline,
            baseline.get("power_median"),
            baseline.get("power_p95")
        )
    
    # Process each AHU and compute scores
    print("\nComputing FAIR risk scores for all devices...")
    
    results = []
    
    # Group by timestamp, then process each device
    grouped = df.groupby('timestamp')
    
    for ts_idx, (ts, ts_df) in enumerate(grouped):
        if (ts_idx + 1) % 100 == 0:
            print(f"  Processing timestamp {ts_idx+1}/{len(grouped)}...")
        
        for _, row in ts_df.iterrows():
            ahu_id = row['ahu_id']
            baseline = ahu_baselines[ahu_id]
            
            # Get values
            power_current = float(row['power_total']) if pd.notna(row['power_total']) else None
            energy_current = float(row['energy_import']) if pd.notna(row['energy_import']) else None
            pf_current = float(row['power_factor_avg']) if pd.notna(row['power_factor_avg']) else None
            unbalance_current = float(row['current_unbalance']) if pd.notna(row['current_unbalance']) else None
            thd_24h = float(row['thd_24h_mean']) if pd.notna(row['thd_24h_mean']) else None
            
            # Compute delta_kwh from previous row in current AHU's time series
            ahu_df = df[df['ahu_id'] == ahu_id].copy()
            ahu_df = ahu_df.sort_values('timestamp').reset_index(drop=True)
            
            # Find current row position and get previous energy value
            curr_pos = ahu_df[ahu_df['timestamp'] == row['timestamp']].index.tolist()
            delta_kwh = None
            if curr_pos and curr_pos[0] > 0:
                prev_energy = ahu_df.loc[curr_pos[0] - 1, 'energy_import']
                curr_energy = row['energy_import']
                delta_kwh = float(curr_energy - prev_energy)
                if delta_kwh < 0:
                    delta_kwh = None
            
            # Get historical series for trend (last TREND_WINDOW_H points from AHU's full data)
            start_idx = max(0, len(ahu_df) - TREND_WINDOW_H)
            hist_df = ahu_df.iloc[start_idx:]
            
            # Re-compute values from hist_df
            a_power = hist_df['power_total'].values.astype(float)
            a_energy = hist_df['energy_import'].values.astype(float)
            a_pf = hist_df['power_factor_avg'].values.astype(float)
            a_unbal = hist_df['current_unbalance'].values.astype(float)
            a_thd24 = hist_df['thd_24h_mean'].values.astype(float)
            
            # Compute delta_kwh series for trend window
            a_delta = np.empty(len(hist_df), dtype=float)
            a_delta[:] = np.nan
            if len(a_energy) >= 2:
                for j in range(1, len(a_delta)):
                    diff = a_energy[j] - a_energy[j-1]
                    a_delta[j] = diff if diff >= 0 else np.nan
            
            # Compute scores
            energy_score, z_energy = score_energy_anomaly(
                delta_kwh,
                baseline["energy_median"],
                baseline["energy_rstd"],
                a_delta if len(a_delta) >= 2 else np.array([])
            )
            
            pf_score, z_pf = score_pf_degradation(
                pf_current, power_current,
                baseline["pf_median"], baseline["pf_rstd"],
                a_pf if len(a_pf) >= 2 else np.array([])
            )
            
            unbal_score, z_unbal = score_phase_imbalance(
                unbalance_current,
                baseline["unbal_median"],
                baseline["unbal_rstd"],
                a_unbal if len(a_unbal) >= 2 else np.array([])
            )
            
            thd_score, z_thd = score_thd_drift(
                thd_24h,
                baseline["thd_median"],
                baseline["thd_rstd"],
                a_thd24 if len(a_thd24) >= 2 else np.array([])
            )
            
            overload_score, z_overload = score_overload(
                power_current,
                baseline["power_median"],
                baseline["power_rstd"],
                baseline["power_p95"],
                a_power if len(a_power) >= 2 else np.array([])
            )
            
            # Compute health index
            risk_scores = {
                "energy_anomaly": round(energy_score, 4),
                "pf_degradation": round(pf_score, 4),
                "phase_imbalance": round(unbal_score, 4),
                "thd_drift": round(thd_score, 4),
                "overload": round(overload_score, 4),
            }
            
            health_index = calculate_health_index(risk_scores)
            tier = get_health_tier(health_index)
            
            # Build result row
            results.append({
                "timestamp": row['timestamp'],
                "ahu_id": ahu_id,
                "level": row.get('level', f"Level {ahu_id[1:3]}"),
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
                "data_quality_flag": 0 if thd_24h is not None and not np.isnan(thd_24h) else 1,
                "safety_flags": safety_flags.get(ahu_id, ""),
                "z_energy": round(z_energy, 3) if z_energy is not None else None,
                "z_pf": round(z_pf, 3) if z_pf is not None else None,
                "z_imbalance": round(z_unbal, 3) if z_unbal is not None else None,
                "z_thd": round(z_thd, 3) if z_thd is not None else None,
                "z_overload": round(z_overload, 3) if z_overload is not None else None,
            })
    
    return pd.DataFrame(results)


def generate_all_levels_health_csv(levels, time_range="all_time", output_dir=None):
    """
    Generate health scores for selected levels.
    
    Args:
        levels: List of level numbers
        time_range: Time range key (last_24h, last_7d, last_30d)
        output_dir: Output directory for CSV files
    """
    if output_dir is None:
        output_dir = DATA_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Time range mapping
    time_range_key = TIME_RANGE_MAP.get(time_range, time_range)
    
    # Output paths
    raw_path = os.path.join(output_dir, f"all_levels_raw_{time_range}.csv")
    health_path = os.path.join(output_dir, f"all_levels_health_{time_range}.csv")
    
    # Fetch raw data
    print("="*60)
    print(f"Generating Health Data for Levels {levels}")
    print(f"Time range: {time_range} ({time_range_key})")
    print("="*60)
    
    df_raw = fetch_raw_metrics_for_levels(levels, time_range=time_range_key, delay=3)
    
    if df_raw.empty:
        print("\n❌ No data available!")
        return pd.DataFrame()
    
    # Save raw data
    df_raw.to_csv(raw_path, index=False)
    print(f"\n✓ Saved raw metrics: {raw_path} ({len(df_raw)} rows)")
    print(f"  Levels: {sorted(df_raw['level'].unique().tolist())}")
    print(f"  Devices: {df_raw['ahu_id'].nunique()}")
    
    # Compute health scores
    df_scores = compute_risk_scores_for_levels(df_raw)
    
    # Sort and save
    df_scores = df_scores.sort_values(["timestamp", "ahu_id"]).reset_index(drop=True)
    df_scores.to_csv(health_path, index=False)
    
    print(f"\n✓ Saved {len(df_scores)} records to {health_path}")
    print(f"  Columns: {', '.join(df_scores.columns.tolist()[:10])}...")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    
    total_ahus = df_scores['ahu_id'].nunique()
    print(f"  Total AHUs: {total_ahus}")
    print(f"  Hours of data: {df_scores['timestamp'].nunique()}")
    
    health_min = df_scores['health_index'].min()
    health_max = df_scores['health_index'].max()
    print(f"  Health Index range: [{health_min:.1f}, {health_max:.1f}]")
    
    print(f"\n  Tier Distribution:")
    for tier in ["Healthy", "Monitor", "Maintenance Soon", "Critical"]:
        count = len(df_scores[df_scores['tier'] == tier])
        pct = 100 * count / len(df_scores)
        print(f"    {tier}: {count} ({pct:.1f}%)")
    
    # Level breakdown
    print(f"\n  By Level:")
    for level in sorted(df_scores['level'].unique()):
        level_data = df_scores[df_scores['level'] == level]
        print(f"    {level}: {len(level_data)} records, {level_data['ahu_id'].nunique()} devices")
    
    return df_scores


def generate_all_time_ranges(levels, output_dir=None):
    """Generate health scores for all time ranges: 24h, 7d, 30d"""
    if output_dir is None:
        output_dir = DATA_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    time_ranges = [
        ("24h", "last_24h"),
        ("7d", "last_7d"),
        ("30d", "last_30d"),
    ]
    
    for range_name, range_key in time_ranges:
        print(f"\n{'='*60}")
        print(f"  Generating for {range_name} ({range_key})")
        print('='*60)
        
        df_scores = generate_all_levels_health_csv(
            levels, 
            time_range=range_name,
            output_dir=output_dir
        )
        
        if df_scores.empty:
            print(f"  ⚠️  No data for {range_name}")
            continue
        
        # Summary stats
        print(f"\n  Health Index: [{df_scores['health_index'].min():.1f}, {df_scores['health_index'].max():.1f}]")
        print(f"  Tiers: {dict(df_scores['tier'].value_counts())}")


def generate_anomaly_summary(df_scores, output_dir=None):
    """
    Generate anomaly summary report.
    
    For each AHU, identify:
    - Current values (latest timestamp)
    - Z-scores for all 5 metrics
    - Health tier
    - Safety flags
    """
    if output_dir is None:
        output_dir = DATA_DIR
    
    print("\n" + "="*60)
    print("Generating Anomaly Summary Report")
    print("="*60)
    
    # Get latest timestamp
    latest_ts = df_scores['timestamp'].max()
    latest_data = df_scores[df_scores['timestamp'] == latest_ts].copy()
    
    # Build anomaly report
    anomalies = []
    
    for _, row in latest_data.iterrows():
        ahu_id = row['ahu_id']
        
        # Get z-scores
        z_scores = {
            "energy": row.get('z_energy'),
            "pf": row.get('z_pf'),
            "unbalance": row.get('z_imbalance'),
            "thd": row.get('z_thd'),
            "overload": row.get('z_overload'),
        }
        
        # Identify anomalies (|z| > 2 or score > 0.5)
        anomaly_list = []
        
        for metric, z in z_scores.items():
            score = row.get(f'{metric}_anomaly') or row.get(f'{metric}')
            if score is None:
                continue
            
            # Convert score key to metric name
            if metric == "pf":
                metric_name = "pf_degradation"
            elif metric == "unbalance":
                metric_name = "phase_imbalance"
            else:
                metric_name = f"{metric}_anomaly" if metric != "overload" else "overload"
            
            score_val = row.get(metric_name) or score
            severity = get_severity(score_val, metric)
            
            if z is not None and (abs(z) > 2.0 or score_val > 0.5):
                anomaly_list.append({
                    "metric": metric_name,
                    "score": round(score_val, 3),
                    "z_score": round(z, 3),
                    "severity": severity,
                })
        
        # Safety flags
        safety_flags = row.get('safety_flags', '')
        if isinstance(safety_flags, str) and safety_flags:
            safety_list = [f for f in safety_flags.split(',') if f]
        else:
            safety_list = []
        
        anomaly_record = {
            "ahu_id": ahu_id,
            "level": row.get('level', 'Unknown'),
            "health_index": round(row['health_index'], 1),
            "tier": row.get('tier', 'Unknown'),
            "current_values": {
                "power_total": round(row['power_total'], 2) if pd.notna(row.get('power_total')) else None,
                "power_factor": round(row['power_factor'], 3) if pd.notna(row.get('power_factor')) else None,
                "unbalance_pct": round(row['unbalance_pct'], 2) if pd.notna(row.get('unbalance_pct')) else None,
                "thd_24h": round(row['thd_24h'], 2) if pd.notna(row.get('thd_24h')) else None,
            },
            "anomalies": anomaly_list,
            "safety_flags": safety_list if isinstance(safety_list, list) else [],
        }
        
        anomalies.append(anomaly_record)
    
    # Sort by health index (lowest first = most critical)
    anomalies.sort(key=lambda x: x['health_index'])
    
    # Convert latest_ts to string for JSON serialization
    if isinstance(latest_ts, pd.Timestamp):
        latest_ts_str = str(latest_ts)
    else:
        latest_ts_str = str(latest_ts)

    # Generate report
    report = {
        "generated_at": datetime.now().isoformat(),
        "timestamp": latest_ts_str,
        "total_ahus": len(anomalies),
        "tier_distribution": {},
        "anomalies": anomalies,
    }
    
    # Tier distribution
    for tier in ["Critical", "Maintenance Soon", "Monitor", "Healthy"]:
        count = sum(1 for a in anomalies if a['tier'] == tier)
        report["tier_distribution"][tier] = count
    
    # Save report
    # Format timestamp for filename (convert to string if needed)
    latest_ts_str = str(latest_ts) if not isinstance(latest_ts, str) else latest_ts
    ts_for_filename = latest_ts_str.replace(':', '-').replace('T', '_')
    report_path = os.path.join(output_dir, f"anomaly_summary_{ts_for_filename}.json")
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Saved anomaly summary: {report_path}")
    print(f"  Total AHUs analyzed: {len(anomalies)}")
    
    # Print summary
    print(f"\n  Tier Distribution:")
    for tier, count in report["tier_distribution"].items():
        print(f"    {tier}: {count}")
    
    # Count devices with anomalies
    devices_with_anomalies = sum(1 for a in anomalies if len(a['anomalies']) > 0)
    print(f"\n  Devices with anomalies: {devices_with_anomalies}/{len(anomalies)}")
    
    # Critical devices
    critical = [a for a in anomalies if a['tier'] == 'Critical']
    print(f"  Critical devices: {len(critical)}")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Generate FAIR health scores for AHU fleet (all levels)"
    )
    
    parser.add_argument(
        "--levels",
        type=str,
        default="all",
        help="Comma-separated list of levels (e.g., '1,3,5' or 'all')"
    )
    
    parser.add_argument(
        "--range",
        type=str,
        default=None,
        help="Time range: 24h, 7d, 30d (default: all ranges)"
    )
    
    parser.add_argument(
        "--all-ranges", 
        action="store_true",
        help="Generate for all time ranges (24h, 7d, 30d)"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        default=None,
        help="Output directory for CSV files"
    )
    
    parser.add_argument(
        "--anomaly-summary",
        action="store_true",
        help="Generate anomaly summary report"
    )
    
    parser.add_argument(
        "--delay",
        type=int,
        default=3,
        help="Seconds to wait between levels (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Parse levels
    if args.levels == "all":
        levels = list(range(1, 12))  # Levels 1-11
    else:
        levels = [int(l) for l in args.levels.split(',')]
    
    print(f"Levels to process: {levels}")
    print(f"Delay between levels: {args.delay} seconds")
    
    # Generate for all ranges
    if args.all_ranges:
        generate_all_time_ranges(levels, output_dir=args.output)
    
    # Generate for specific range
    elif args.range:
        generate_all_levels_health_csv(
            levels,
            time_range=args.range,
            output_dir=args.output
        )
    
    # Default: generate all ranges
    else:
        generate_all_time_ranges(levels, output_dir=args.output)
    
    # Generate anomaly summary if requested
    if args.anomaly_summary or args.all_ranges or args.range:
        # Load the last generated file
        output_dir = args.output or DATA_DIR
        
        # Find latest health file
        import glob
        health_files = sorted(glob.glob(os.path.join(output_dir, "all_levels_health_*.csv")))
        
        if health_files:
            latest_file = health_files[-1]
            print(f"\nLoading {latest_file} for anomaly analysis...")
            
            df_scores = pd.read_csv(latest_file, parse_dates=['timestamp'])
            generate_anomaly_summary(df_scores, output_dir=output_dir)


if __name__ == "__main__":
    main()
