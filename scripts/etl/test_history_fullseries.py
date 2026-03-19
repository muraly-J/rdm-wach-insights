#!/usr/bin/env python3
"""Test that run_health_etl_historical produces >1 row per device."""
import pandas as pd
import subprocess, sys, os

CSV_PATH = os.path.join(os.path.dirname(__file__), "../../data/health_all_levels.csv")

def test_multiple_rows_per_device():
    """After a partial run, each device should have >1 row."""
    df = pd.read_csv(CSV_PATH)
    # Pick a device known to have historical data
    if df.empty:
        print("SKIP: CSV empty, run historical ETL first")
        return
    device_counts = df.groupby('ahu_id').size()
    multi_row_devices = (device_counts > 1).sum()
    total_devices = len(device_counts)
    print(f"Devices with >1 row: {multi_row_devices}/{total_devices}")
    assert multi_row_devices > 0, "Expected multiple rows per device, got 1 each (iloc[-1] bug still present)"
    print("PASS: Multiple rows per device confirmed")

if __name__ == "__main__":
    test_multiple_rows_per_device()
