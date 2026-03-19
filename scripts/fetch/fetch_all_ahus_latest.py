#!/usr/bin/env python3
"""
fetch_all_ahus_latest.py
──────────────────────────
Fetch latest hourly data for all AHUs across all 11 levels from InfluxDB.

Usage:
    python fetch_all_ahus_latest.py [--output <filename.csv>]
    python fetch_all_ahus_latest.py --metrics power_total,energy_import,power_factor_avg

Output:
    data/all_ahus_latest_hourly.csv
"""

import sys
import os
import argparse
from datetime import datetime

# Add backend to path for imports (scripts/fetch → .. → scripts → .. → backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from core.influx_client import fetch_latest_hourly_data


def main():
    parser = argparse.ArgumentParser(
        description="Fetch latest hourly data for all AHUs across all 11 levels"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="all_ahus_latest_hourly.csv",
        help="Output CSV filename (default: all_ahus_latest_hourly.csv)"
    )
    parser.add_argument(
        "--metrics",
        "-m",
        default=None,
        help="Comma-separated list of metrics to fetch (default: all available)"
    )

    args = parser.parse_args()

    # Determine output directory
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)

    output_path = os.path.join(data_dir, args.output)

    # Parse metrics if provided
    metrics_to_fetch = None
    if args.metrics:
        metrics_to_fetch = [m.strip() for m in args.metrics.split(",")]

    print("=" * 70)
    print("Fetch Latest Hourly Data for All AHUs")
    print("=" * 70)
    print(f"Output: {output_path}")
    if metrics_to_fetch:
        print(f"Metrics: {', '.join(metrics_to_fetch)}")
    else:
        print("Metrics: Default (power_total, energy_import, power_factor_avg, current_unbalance, current_l1_thd, current_l3_thd)")
        print("         composite_thd will be computed as max(current_l1_thd, current_l3_thd)")
    print("=" * 70)

    # Fetch data
    try:
        df = fetch_latest_hourly_data(metrics_to_fetch=metrics_to_fetch)

        if df.empty:
            print("[ERROR] No data retrieved!")
            sys.exit(1)

        # Save to CSV
        df.to_csv(output_path, index=False)
        print(f"\nSaved {len(df)} AHU readings to: {output_path}")

        # Print summary
        print("\n" + "-" * 70)
        print("Summary")
        print("-" * 70)

        # Count by level
        from models.schemas import AHU_LEVEL_CONFIG

        for level in sorted(AHU_LEVEL_CONFIG.keys()):
            level_prefix = f"e{str(level).zfill(2)}"
            level_count = len(df[df["ahu_id"].str.startswith(level_prefix)])
            print(f"  Level {level}: {level_count} AHUs")

        total_ahus = sum(len(config["device_ids"]) for config in AHU_LEVEL_CONFIG.values())
        print(f"\n  Total AHUs available: {total_ahus}")
        print(f"  AHUs with data: {len(df)}")

        # Show sample data
        print("\n" + "-" * 70)
        print("Sample Data (first 10 rows)")
        print("-" * 70)
        print(df.head(10).to_string(index=False))

        # Show data quality
        print("\n" + "-" * 70)
        print("Data Quality Check")
        print("-" * 70)

        metrics = ["power_total", "energy_import", "power_factor_avg",
                   "current_unbalance", "composite_thd"]

        for metric in metrics:
            if metric in df.columns:
                null_count = df[metric].isna().sum()
                total = len(df)
                pct = 100 * null_count / total
                non_null = df[metric].dropna()
                if len(non_null) > 0:
                    min_val = non_null.min()
                    max_val = non_null.max()
                    print(f"  {metric:25s}: {total - null_count}/{total} values "
                          f"(min={min_val:.2f}, max={max_val:.2f})")
                else:
                    print(f"  {metric:25s}: No values (all NaN)")
            else:
                print(f"  {metric:25s}: Not fetched")

        print("\n" + "=" * 70)
        print("Done!")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Failed to fetch data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
