#!/usr/bin/env python3
"""
build_hourly_csv.py
────────────────────
Derive data/health_hourly.csv from data/health_all_levels.csv.

Filters to the last 3 days of hourly data for the 24h dashboard chart.

Output columns (from health_all_levels.csv):
    timestamp, ahu_id, level, health_index, tier,
    energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload,
    raw_power_total, raw_energy_import, raw_hourly_delta,
    raw_predicted_delta, raw_energy_anomaly_raw, raw_power_factor_avg,
    raw_current_unbalance, raw_composite_thd

Usage:
    python3 scripts/etl/build_hourly_csv.py

Pre-requisite:
    data/health_all_levels.csv must exist (run history_generator.py first).

Output:
    data/health_hourly.csv
"""
import os
import sys
from datetime import datetime, timezone, timedelta
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SOURCE = os.path.join(DATA_DIR, "health_all_levels.csv")
OUTPUT = os.path.join(DATA_DIR, "health_hourly.csv")

KEEP_DAYS = 3  # matches csv_reader.py RANGE_DELTA['24h']


def main():
    if not os.path.exists(SOURCE):
        print(f"[ERROR] Source not found: {SOURCE}")
        print("Run scripts/etl/history_generator.py first.")
        sys.exit(1)

    print(f"Reading {SOURCE} ...")
    df = pd.read_csv(SOURCE, parse_dates=["timestamp"])
    print(f"  Loaded {len(df):,} rows, {df['ahu_id'].nunique()} AHUs")

    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    ts = pd.to_datetime(df["timestamp"], utc=True)
    df_filtered = df[ts >= cutoff].copy()
    print(f"  Filtered to last {KEEP_DAYS} days: {len(df_filtered):,} rows")

    if df_filtered.empty:
        print("[WARNING] No data in last 3 days — writing full dataset instead")
        df_filtered = df.copy()

    df_filtered.to_csv(OUTPUT, index=False)
    print(f"[OK] Written to {OUTPUT}")
    print(f"     Rows: {len(df_filtered):,}, AHUs: {df_filtered['ahu_id'].nunique()}")


if __name__ == "__main__":
    main()
