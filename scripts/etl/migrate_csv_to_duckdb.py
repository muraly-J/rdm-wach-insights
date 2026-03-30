#!/usr/bin/env python3
"""
migrate_csv_to_duckdb.py
────────────────────────
One-time migration: load data/health_hourly.csv → data/healthdb.duckdb.

Usage:
    python scripts/etl/migrate_csv_to_duckdb.py

Idempotent — safe to re-run. Uses INSERT OR REPLACE so existing rows are
updated and no duplicates are created.

Output:
    Prints rows imported, AHU count, date range covered.
"""
import os
import sys
import pandas as pd

# Add backend to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))

from core.healthdb import HealthDB

CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'health_hourly.csv')
BATCH_SIZE = 10_000


def migrate():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] CSV not found: {CSV_PATH}")
        sys.exit(1)

    print(f"Reading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])

    # Ensure timestamp is tz-aware UTC
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    total_rows = len(df)
    print(f"  Rows in CSV: {total_rows:,}")
    print(f"  AHUs: {df['ahu_id'].nunique()}")
    print(f"  Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")

    db = HealthDB()
    imported = 0
    for start in range(0, total_rows, BATCH_SIZE):
        batch = df.iloc[start:start + BATCH_SIZE]
        db.upsert(batch)
        imported += len(batch)
        pct = imported / total_rows * 100
        print(f"  [{pct:5.1f}%] {imported:,} / {total_rows:,} rows", end="\r")

    print(f"\n[OK] Migration complete — {imported:,} rows imported to data/healthdb.duckdb")

    # Verify
    ts = db.get_latest_timestamp()
    snapshot = db.get_latest_snapshot()
    print(f"  Verification: latest timestamp = {ts}, AHUs in DB = {len(snapshot)}")


if __name__ == "__main__":
    migrate()
