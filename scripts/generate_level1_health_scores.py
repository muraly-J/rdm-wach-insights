#!/usr/bin/env python3
"""
generate_level1_hourly_data.py
───────────────────────────────
Two-step process:
1. FETCH_RAW: Pull raw metrics from InfluxDB and save to intermediate CSV
2. COMPUTE_SCORES: Load raw data, apply risk formulas, generate health scores

This way we can:
- Fetch raw data once (expensive), then regenerate scores quickly
- Store both raw and processed data for future use

Usage:
    # Step 1: Fetch raw data (only need to run when data changes)
    python generate_level1_hourly_data.py --fetch
    
    # Step 2: Compute scores from raw data (can run multiple times)
    python generate_level1_hourly_data.py --compute
    
    # Or both at once
    python generate_level1_hourly_data.py

Output:
- data/level1_raw_metrics.csv - Raw InfluxDB measurements
- data/level1_hourly_health.csv - Final output with health index and scores
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import argparse

# Import from backend
sys.path.insert(0, '/Users/rdmasia/wach-insight')

from backend.core.risk_engine import (
    sigmoid_score,
    power_factor_risk_score,
    phase_imbalance_risk_score,
    thd_risk_score,
    overload_risk_score,
    calculate_ahu_health_index,
)
from backend.core.influx_client import fetch_time_series, get_available_devices
from backend.models.schemas import ALLOWED_DEVICES


def fetch_raw_metrics(level: int = 1, time_range: str = "all_time"):
    """
    Fetch raw metrics from InfluxDB for all AHUs on a level.
    
    Returns DataFrame with columns:
        timestamp, ahu_id, power_total, energy_import,
        power_factor_avg, current_unbalance, current_l1_thd, current_l3_thd
    """
    import math
    
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


def compute_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute health scores from raw metrics DataFrame using FAIR per-AHU method.

    For each row (ahu_id at timestamp):
    - Calculate baseline values from ALL data for that AHU
    - Compute fleet-wide percentiles for absolute scoring
    - Compare current values to baselines using blended z-score + percentile approach
    """
    import math

    print("Computing risk scores (FAIR method)...")

    def calc_slope(series):
        """Calculate normalized 7-day slope."""
        if len(series) < 7:
            return 0.0
        y = series.dropna().values
        if len(y) < 2:
            return 0.0
        try:
            x = list(range(len(y)))
            x_mean = sum(x) / len(x)
            y_mean = sum(y) / len(y)
            numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
            denominator = sum((xi - x_mean) ** 2 for xi in x)
            if denominator == 0:
                return 0.0
            slope = numerator / denominator
            value_range = max(y) - min(y) if max(y) != min(y) else 1.0
            return slope / value_range if value_range > 0 else 0.0
        except:
            return 0.0

    def calc_sigmoid(raw_score):
        """Apply sigmoid transformation to get score in [0, 1]."""
        if raw_score > 500:
            return 1.0
        if raw_score < -500:
            return 0.0
        return 1.0 / (1.0 + math.exp(-raw_score))

    def calc_sigmoid_score(raw):
        """Convert raw penalty to [0, 1] using sigmoid transformation."""
        raw = max(-500.0, min(500.0, float(raw)))
        s = calc_sigmoid(raw) * 2.0 - 1.0
        return max(0.0, min(1.0, s))

    # Compute fleet-wide statistics for absolute scoring
    print("  Computing fleet-wide percentiles...")
    
    # Composite THD
    df["composite_thd"] = df[["current_l1_thd", "current_l3_thd"]].max(axis=1)
    
    fleet_stats = {}
    for col, key in [
        ("current_unbalance", "unbalance"),
        ("composite_thd", "thd"),
        ("power_factor_avg", "pf"),
        ("energy_import", "delta_kwh"),  # Use energy for overload comparison
    ]:
        vals = df[col].dropna()
        if len(vals) >= 2:
            fleet_stats[key] = {
                "p5": float(np.percentile(vals, 5)) if len(vals) > 0 else 0,
                "median": float(np.percentile(vals, 50)) if len(vals) > 0 else 0,
                "p95": float(np.percentile(vals, 95)) if len(vals) > 0 else 1,
            }
        else:
            fleet_stats[key] = {"p5": 0, "median": 0, "p95": 1}
    
    # Add composite_thd stats specifically
    composite_vals = df["composite_thd"].dropna()
    fleet_stats["composite_thd"] = {
        "p5": float(np.percentile(composite_vals, 5)) if len(composite_vals) > 0 else 0,
        "median": float(np.percentile(composite_vals, 50)) if len(composite_vals) > 0 else 0,
        "p95": float(np.percentile(composite_vals, 95)) if len(composite_vals) > 0 else 1,
    }
    
    # Minimum std values to avoid division by zero
    MIN_STD_POWER = 0.05
    MIN_STD_PF = 0.005
    MIN_STD_UNBAL = 0.10
    MIN_STD_THD = 0.10
    
    # Load discount thresholds
    PF_LOAD_DISCOUNT_THRESHOLD = 0.60
    PF_LOAD_DISCOUNT_FACTOR = 0.65

    # Process each AHU separately
    results = []
    ahu_ids = df['ahu_id'].unique()

    for i, ahu_id in enumerate(sorted(ahu_ids)):
        if i % 5 == 0:
            print(f"  [{i+1}/{len(ahu_ids)}] Processing {ahu_id}...")

        ahu_df = df[df['ahu_id'] == ahu_id].copy()

        # Compute per-AHU baselines
        power_values = ahu_df['power_total'].dropna()
        energy_values = ahu_df['energy_import'].dropna()
        pf_values = ahu_df['power_factor_avg'].dropna()
        unbalance_values = ahu_df['current_unbalance'].dropna()
        composite_thd_values = ahu_df['composite_thd'].dropna()

        # Per-AHU statistics
        power_mean = float(power_values.mean()) if len(power_values) > 0 else None
        power_std = float(max(power_values.std(), MIN_STD_POWER)) if len(power_values) > 1 else MIN_STD_POWER
        power_p95 = float(energy_values.quantile(0.95)) if len(energy_values) > 0 else None
        
        energy_mean = float(energy_values.mean()) if len(energy_values) > 0 else None
        energy_std = float(max(energy_values.std(), MIN_STD_POWER)) if len(energy_values) > 1 else MIN_STD_POWER
        
        pf_mean = float(pf_values.mean()) if len(pf_values) > 0 else None
        pf_std = float(max(pf_values.std(), MIN_STD_PF)) if len(pf_values) > 1 else MIN_STD_PF
        
        unbalance_mean = float(unbalance_values.mean()) if len(unbalance_values) > 0 else None
        unbalance_std = float(max(unbalance_values.std(), MIN_STD_UNBAL)) if len(unbalance_values) > 1 else MIN_STD_UNBAL
        
        thd_mean = float(composite_thd_values.mean()) if len(composite_thd_values) > 0 else None
        thd_std = float(max(composite_thd_values.std(), MIN_STD_THD)) if len(composite_thd_values) > 1 else MIN_STD_THD

        for _, row in ahu_df.iterrows():
            ts = row['timestamp']

            # Get current values
            power_current = row.get('power_total')
            energy_current = row.get('energy_import')
            pf_current = row.get('power_factor_avg')
            unbalance_current = row.get('current_unbalance')
            composite_thd = float(row.get('composite_thd')) if pd.notna(row.get('composite_thd')) else None

            # ---------------------- ENERGY ANOMALY (60% relative + 40% absolute) ----------------------
            # For energy, use delta_kwh (hourly consumption)
            delta_kwh = None
            if pd.notna(energy_current) and len(energy_values) > 0:
                # Simple delta from current value - in real scenario would be computed before
                pass
            
            energy_anomaly = 0.5
            if pd.notna(energy_current) and energy_mean is not None and energy_std > 0:
                z = (float(energy_current) - float(energy_mean)) / float(energy_std)
                raw = 0.6 * abs(z) + 0.4 * max(0, z)
                energy_anomaly = calc_sigmoid_score(raw)

            # ---------------------- PF DEGRADATION (60% relative + 40% absolute) ----------------------
            pf_risk = 0.5
            if pd.notna(pf_current) and pf_mean is not None and pf_std > 0:
                # RELATIVE: how many SDs below own mean? (lower PF = worse, so flip z)
                z_score = (float(pf_current) - float(pf_mean)) / float(pf_std)
                z_score = -z_score  # Flip: below mean = penalty
                raw_relative = max(0, z_score * 2.5)
                
                # ABSOLUTE: fleet-calibrated
                fs = fleet_stats["pf"]
                denom = fs["median"] - fs["p5"]
                raw_absolute = max(0, (fs["median"] - float(pf_current)) / denom) if denom > 0 else 0.0
                
                # Blend
                pf_risk = 0.60 * calc_sigmoid_score(raw_relative) + 0.40 * raw_absolute

                # LOAD DISCOUNT: if below 60% of own mean power, discount by 65%
                if (pd.notna(power_current) and power_mean is not None 
                    and power_mean > 0 
                    and float(power_current) < PF_LOAD_DISCOUNT_THRESHOLD * float(power_mean)):
                    pf_risk *= (1.0 - PF_LOAD_DISCOUNT_FACTOR)

            # ---------------------- PHASE IMBALANCE (60% relative + 40% absolute) ----------------------
            imbalance_risk = 0.5
            if pd.notna(unbalance_current) and unbalance_mean is not None and unbalance_std > 0:
                # RELATIVE: how many SDs above own mean?
                z_score = (float(unbalance_current) - float(unbalance_mean)) / float(unbalance_std)
                raw_relative = z_score * 2.0
                
                # ABSOLUTE: where does this sit in fleet distribution?
                fs = fleet_stats["unbalance"]
                denom = fs["p95"] - fs["median"]
                raw_absolute = max(0, (float(unbalance_current) - fs["median"]) / denom) if denom > 0 else 0.0
                
                # Blend
                imbalance_risk = 0.60 * calc_sigmoid_score(raw_relative) + 0.40 * raw_absolute

            # ---------------------- THD DRIFT (60% relative + 40% absolute) ----------------------
            thd_risk = 0.5
            if pd.notna(composite_thd) and thd_mean is not None and thd_std > 0:
                # RELATIVE: how many SDs above own mean?
                z_score = (float(composite_thd) - float(thd_mean)) / float(thd_std)
                raw_relative = z_score * 2.0
                
                # ABSOLUTE: where does this sit in fleet distribution?
                fs = fleet_stats["thd"]
                denom = fs["p95"] - fs["median"]
                raw_absolute = max(0, (float(composite_thd) - fs["median"]) / denom) if denom > 0 else 0.0
                
                # Blend
                thd_risk = 0.60 * calc_sigmoid_score(raw_relative) + 0.40 * raw_absolute

            # ---------------------- OVERLOAD (60% relative + 40% absolute) ----------------------
            overload_risk = 0.5
            if pd.notna(power_current) and power_p95 is not None and power_p95 > 0:
                # RELATIVE: how far above own p95 ceiling?
                power_ratio = float(power_current) / float(power_p95)
                demand_term = max(0.0, power_ratio - 0.85)
                rel_score = calc_sigmoid_score(demand_term * 8.0)

                # Also include z-score of current power vs own mean
                if power_mean is not None:
                    std_approx = max(abs(power_mean) * 0.15, MIN_STD_POWER)
                    z_pwr = (float(power_current) - float(power_mean)) / std_approx
                    rel_score = max(0.0, min(1.0, 0.7 * rel_score + 0.3 * calc_sigmoid_score(z_pwr * 1.5)))

                # ABSOLUTE: fleet context
                fs = fleet_stats["delta_kwh"]
                denom = fs["p95"] - fs["median"]
                abs_score = max(0, (float(power_current) - fs["median"]) / denom) if denom > 0 else 0.0

                # Blend
                overload_risk = 0.60 * rel_score + 0.40 * abs_score

            # Calculate health index
            risk_scores = {
                "energy_anomaly": round(energy_anomaly, 4),
                "pf_degradation": round(pf_risk, 4),
                "phase_imbalance": round(imbalance_risk, 4),
                "thd_drift": round(thd_risk, 4),
                "overload": round(overload_risk, 4),
            }

            # health_index = 100 - weighted_penalty * 100
            penalty = (0.15 * risk_scores["energy_anomaly"] +
                      0.25 * risk_scores["pf_degradation"] +
                      0.25 * risk_scores["phase_imbalance"] +
                      0.15 * risk_scores["thd_drift"] +
                      0.20 * risk_scores["overload"])
            health_index = round(max(0, min(100, 100.0 - penalty * 100.0)), 1)

            level_str = f"Level {row.get('level', 1)}"

            results.append({
                "timestamp": ts,
                "ahu_id": ahu_id,
                "level": level_str,
                "health_index": health_index,
                "energy_anomaly": risk_scores["energy_anomaly"],
                "pf_degradation": risk_scores["pf_degradation"],
                "phase_imbalance": risk_scores["phase_imbalance"],
                "thd_drift": risk_scores["thd_drift"],
                "overload": risk_scores["overload"],
            })

    return pd.DataFrame(results)


def generate_level1_hourly_csv(output_path: str = None, raw_output_path: str = None,
                                time_range_days: int = 365):
    """
    Generate Level 1 hourly health data.
    
    Args:
        output_path: Final output CSV (default: data/level1_hourly_health.csv)
        raw_output_path: Raw metrics CSV (default: data/level1_raw_metrics.csv)
        time_range_days: How many days of history to fetch
    
    Returns:
        DataFrame with health scores
    """
    if output_path is None:
        output_path = "/Users/rdmasia/wach-insight/data/level1_hourly_health.csv"
    if raw_output_path is None:
        raw_output_path = "/Users/rdmasia/wach-insight/data/level1_raw_metrics.csv"
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Determine time range string
    if time_range_days >= 365:
        time_range = "all_time"
    else:
        time_range = f"last_{time_range_days}d"
    
    print("=" * 60)
    print(f"Generating Level 1 Hourly Health Data")
    print(f"Time range: {time_range} ({time_range_days} days)")
    print("=" * 60)
    
    # Step 1: Fetch raw metrics
    print("\n[Step 1] Fetching raw metrics from InfluxDB...")
    df_raw = fetch_raw_metrics(level=1, time_range=time_range)
    
    if df_raw.empty:
        print("No data available!")
        return pd.DataFrame()
    
    # Save raw metrics
    df_raw.to_csv(raw_output_path, index=False)
    print(f"  Saved raw metrics: {raw_output_path} ({len(df_raw)} rows)")
    
    # Step 2: Compute risk scores
    print("\n[Step 2] Computing health scores...")
    df_scores = compute_risk_scores(df_raw)
    
    # Save final output
    df_scores = df_scores.sort_values(["timestamp", "ahu_id"]).reset_index(drop=True)
    df_scores.to_csv(output_path, index=False)
    
    print(f"\n✓ Saved {len(df_scores)} records to {output_path}")
    print(f"  Columns: {', '.join(df_scores.columns.tolist())}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Total AHUs: {len(df_scores['ahu_id'].unique())}")
    print(f"  Hours of data: {len(df_scores['timestamp'].unique())}")
    print(f"  Health Index range: [{df_scores['health_index'].min():.1f}, {df_scores['health_index'].max():.1f}]")
    print(f"  Energy Anomaly range: [{df_scores['energy_anomaly'].min():.4f}, {df_scores['energy_anomaly'].max():.4f}]")
    print(f"  PF Degradation range: [{df_scores['pf_degradation'].min():.4f}, {df_scores['pf_degradation'].max():.4f}]")
    
    return df_scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Level 1 hourly health data")
    parser.add_argument("--fetch-only", action="store_true",
                       help="Only fetch raw data, don't compute scores")
    parser.add_argument("--compute-only", action="store_true",
                       help="Only compute scores from existing raw data")
    parser.add_argument("--days", type=int, default=365,
                       help="Number of days of history to fetch (default: 365)")
    parser.add_argument("--output", type=str, default=None,
                       help="Output CSV path for scores")
    parser.add_argument("--raw-output", type=str, default=None,
                       help="Output CSV path for raw metrics")
    
    args = parser.parse_args()
    
    if args.compute_only:
        # Load raw data and compute scores
        raw_path = args.raw_output or "/Users/rdmasia/wach-insight/data/level1_raw_metrics.csv"
        if os.path.exists(raw_path):
            print(f"Loading raw data from {raw_path}...")
            df_raw = pd.read_csv(raw_path, parse_dates=['timestamp'])
            df_scores = compute_risk_scores(df_raw)
            output_path = args.output or "/Users/rdmasia/wach-insight/data/level1_hourly_health.csv"
            df_scores.to_csv(output_path, index=False)
            print(f"Saved scores to {output_path}")
        else:
            print(f"Raw data not found at {raw_path}. Run with --fetch-only first.")
    else:
        # Generate everything
        df = generate_level1_hourly_csv(
            output_path=args.output,
            raw_output_path=args.raw_output,
            time_range_days=args.days
        )
    
    print("\nDone!")
