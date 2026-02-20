"""
Test script for InfluxDB Client
Run from the project root: python3 backend/tests/test_influx.py

Requires valid INFLUX_URL, INFLUX_TOKEN in your .env file.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd

from backend.core.influx_client import fetch_time_series, fetch_ranking
from backend.models.schemas import ALLOWED_TIME_RANGES


if __name__ == "__main__":
    print("\n" + "="*50)
    print(" WACH INSIGHT - INFLUXDB CLIENT TEST ".center(50, "="))
    print("="*50)

    # 1. Test Ranking Query
    print(f"\n[Test 1] Fetching top 5 devices by power_total (last 24h)...")
    try:
        df_ranking = fetch_ranking(
            metric="power_total",
            time_range="last_24h",
            device_ids=[],  # All devices
            top_n=5
        )
        if not df_ranking.empty:
            print("DONE. Top Results:")
            print(df_ranking.to_string(index=False))
        else:
            print("DONE. (No data found for this period)")
    except Exception as e:
        print(f"FAILED: {e}")

    # 2. Test Time-Series Query
    print(f"\n[Test 2] Fetching time-series for e0101 (last 24h)...")
    try:
        df_ts = fetch_time_series(
            device_ids=["e0101"],
            metric="power_total",
            time_range="last_24h"
        )
        if not df_ts.empty:
            print(f"DONE. Received {len(df_ts)} rows.")
            print("Sample data (last 5 rows):")
            print(df_ts.tail())
        else:
            print("DONE. (No data found for this device/period)")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n" + "="*50)
    print(" TEST COMPLETE ".center(50, "="))
    print("="*50 + "\n")
