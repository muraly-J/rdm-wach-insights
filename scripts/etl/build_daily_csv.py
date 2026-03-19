#!/usr/bin/env python3
"""
build_daily_csv.py
───────────────────
Derive data/health_daily.csv from data/health_all_levels.csv.

Aggregates hourly rows to one daily mean per AHU per day.
Used for 7d and 30d dashboard charts.

Output columns:
    timestamp, ahu_id, level, health_index, tier,
    energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload,
    raw_power_total, raw_energy_import, raw_hourly_delta,
    raw_predicted_delta, raw_energy_anomaly_raw, raw_power_factor_avg,
    raw_current_unbalance, raw_composite_thd

Usage:
    python3 scripts/etl/build_daily_csv.py

Pre-requisite:
    data/health_all_levels.csv must exist (run history_generator.py first).

Output:
    data/health_daily.csv
"""
import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SOURCE = os.path.join(DATA_DIR, "health_all_levels.csv")
OUTPUT = os.path.join(DATA_DIR, "health_daily.csv")

SCORE_COLS = ["energy_anomaly", "pf_degradation", "phase_imbalance", "thd_drift", "overload"]

# Raw metric columns that should be included in daily output
RAW_METRIC_COLS = [
    "raw_power_total",
    "raw_energy_import",
    "raw_hourly_delta",      # NEW: raw hourly delta for energy anomaly score derivation
    "raw_predicted_delta",   # NEW: predicted hourly delta
    "raw_energy_anomaly_raw",# NEW: raw energy anomaly (before scoring normalization)
    "raw_power_factor_avg",
    "raw_current_unbalance",
    "raw_composite_thd",
]


def get_tier(index: float) -> str:
    if index >= 80:
        return "Healthy"
    elif index >= 60:
        return "Monitor"
    elif index >= 40:
        return "Maintenance Soon"
    return "Critical"


def main():
    if not os.path.exists(SOURCE):
        print(f"[ERROR] Source not found: {SOURCE}")
        print("Run scripts/etl/history_generator.py first.")
        sys.exit(1)

    print(f"Reading {SOURCE} ...")
    df = pd.read_csv(SOURCE, parse_dates=["timestamp"])
    print(f"  Loaded {len(df):,} rows, {df['ahu_id'].nunique()} AHUs")

    # Normalise to UTC, extract date (midnight UTC = start of that day)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.normalize()

    # Aggregate: mean per (date, ahu_id, level)
    # Include both score columns and raw metric columns
    agg_cols = {"health_index": "mean"}
    for col in SCORE_COLS:
        if col in df.columns:
            agg_cols[col] = "mean"
    
    # Include raw metric columns (use first value or mean since hourly precision is reduced)
    for col in RAW_METRIC_COLS:
        if col in df.columns:
            agg_cols[col] = "mean"

    daily = (
        df.groupby(["date", "ahu_id", "level"], as_index=False)
        .agg(agg_cols)
    )

    # Re-derive tier from daily mean health_index
    daily["tier"] = daily["health_index"].apply(get_tier)

    # Rename date → timestamp for csv_reader compatibility
    daily = daily.rename(columns={"date": "timestamp"})

    # Round numeric columns (include both scores and raw metrics)
    numeric_cols = ["health_index"] + SCORE_COLS + RAW_METRIC_COLS
    numeric_cols = [c for c in numeric_cols if c in daily.columns]
    daily[numeric_cols] = daily[numeric_cols].round(4)

    daily = daily.sort_values(["timestamp", "ahu_id"]).reset_index(drop=True)
    daily.to_csv(OUTPUT, index=False)

    print(f"[OK] Written to {OUTPUT}")
    print(f"     Rows: {len(daily):,}, Days: {daily['timestamp'].nunique()}, AHUs: {daily['ahu_id'].nunique()}")


if __name__ == "__main__":
    main()
