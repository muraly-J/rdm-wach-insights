#!/usr/bin/env python3
"""
fetch_level1_raw_data.py
───────────────────────────
Fetch raw metrics from InfluxDB for Level 1 AHUs and save to Parquet.

This script:
1. Fetches raw time series data for all Level 1 devices
2. Saves to Parquet format (columnar, compressed, memory-efficient)

Output:
- data/level1_raw_metrics.parquet - Raw InfluxDB measurements

Usage:
    python fetch_level1_raw_data.py --days 365
    python fetch_level1_raw_data.py --all-time

The Parquet file can then be used by process_health_scores.py

Strategy: For large ranges (>7 days), fetch in 7-day chunks with small delays
to avoid overwhelming InfluxDB (since only last_24h, last_7d, last_30d, all_time
are allowed time ranges).
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import time
import math

# Add backend to path for imports (scripts/fetch → .. → scripts → .. → backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from core.influx_client import fetch_time_series, get_available_devices


def fetch_level1_raw_data_chunk(level1_devices, start_date, end_date):
    """
    Fetch metrics for a date range chunk using last_7d (max allowed).
    
    Since InfluxClient only allows specific time ranges (last_24h, last_7d,
    last_30d, all_time), we always use last_7d for chunked fetching and
    manually filter the results by date range.
    
    Args:
        level1_devices: List of device IDs
        start_date: Start datetime for the chunk
        end_date: End datetime for the chunk
    
    Returns:
        DataFrame with raw metrics for this chunk
    """
    # Always use last_7d since that's the largest allowed chunk
    time_range = "last_7d"
    
    records = []
    
    # Fetch each metric with retry logic
    metrics_to_fetch = [
        ("power_total", "Power"),
        ("energy_import", "Energy"),
        ("power_factor_avg", "PF"),
        ("current_unbalance", "Unbalance"),
        ("current_l1_thd", "THD L1"),
        ("current_l3_thd", "THD L3"),
    ]
    
    for metric, label in metrics_to_fetch:
        print(f"  Fetching {label} ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})...")
        df_metric = fetch_time_series(level1_devices, metric, time_range)
        
        if df_metric.empty:
            print(f"    No {label} data for this chunk")
            continue
        
        # Filter to date range since we're using last_7d
        df_metric_filtered = df_metric[
            (df_metric.index >= start_date.isoformat()) & 
            (df_metric.index <= end_date.isoformat())
        ]
        
        print(f"    Got {len(df_metric_filtered)} rows in date range (total: {len(df_metric)})")
        
        # Merge with existing records
        for ts in df_metric_filtered.index:
            for ahu_id in level1_devices:
                try:
                    value = float(df_metric_filtered.loc[ts, ahu_id]) if pd.notna(df_metric_filtered.loc[ts, ahu_id]) else None
                    
                    # Find existing record for this timestamp/ahu
                    found = False
                    for rec in records:
                        if rec["timestamp"] == ts.isoformat() and rec["ahu_id"] == ahu_id:
                            rec[f"{metric}"] = value
                            found = True
                            break
                    
                    if not found:
                        # Create new record with None for other metrics
                        rec = {
                            "timestamp": ts.isoformat(),
                            "ahu_id": ahu_id,
                        }
                        # Initialize all metrics to None
                        for m, _ in metrics_to_fetch:
                            rec[m] = None
                        rec[f"{metric}"] = value
                        records.append(rec)
                except Exception as e:
                    continue
    
    return pd.DataFrame(records)


def fetch_level1_raw_data(time_range: str = "all_time"):
    """
    Fetch raw metrics from InfluxDB for all Level 1 AHUs.
    
    For large ranges (>7 days), fetches in 7-day chunks with small delays
    to avoid overwhelming InfluxDB and triggering timeouts.

    Args:
        time_range: Data period to fetch ("last_24h", "last_7d", "last_30d", "all_time")

    Returns:
        DataFrame with columns: timestamp, ahu_id, power_total, energy_import,
                               power_factor_avg, current_unbalance, current_l1_thd, current_l3_thd
    """
    import math
    
    # Get all Level 1 devices (e01 prefix)
    available_devices = get_available_devices(time_range)
    level_prefix = "e01"
    level1_devices = [d for d in available_devices if d.startswith(level_prefix)]

    print(f"Level 1: Found {len(level1_devices)} devices")
    if not level1_devices:
        return pd.DataFrame()

    # Determine start date based on time_range
    end_date = datetime.now()
    
    if time_range == "last_24h":
        start_date = end_date - timedelta(days=1)
    elif time_range == "last_7d":
        start_date = end_date - timedelta(days=7)
    elif time_range == "last_30d":
        start_date = end_date - timedelta(days=30)
    elif time_range == "all_time":
        # For all-time, default to 365 days but fetch in 7-day chunks
        start_date = end_date - timedelta(days=365)
    else:
        # time_range is int days
        start_date = end_date - timedelta(days=time_range)
    
    # Get number of days to fetch
    total_days = (end_date - start_date).days
    
    print(f"  Total data range: {total_days} days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
    
    # Chunk size: 7 days (the maximum allowed by InfluxClient)
    chunk_size = 7
    
    if total_days > chunk_size:
        print(f"  Fetching in {chunk_size}-day chunks (total: {math.ceil(total_days/chunk_size)} chunks)...")
        
        all_dfs = []
        num_chunks = math.ceil(total_days / chunk_size)
        
        for i in range(num_chunks):
            # Calculate date range for this chunk
            chunk_start = start_date + timedelta(days=i*chunk_size)
            chunk_end = chunk_start + timedelta(days=chunk_size)
            
            print(f"  [{i+1}/{num_chunks}] Fetching {chunk_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}...")
            
            # Fetch with 7-day range
            chunk_df = fetch_level1_raw_data_chunk(level1_devices, chunk_start, chunk_end)
            
            if not chunk_df.empty:
                all_dfs.append(chunk_df)
                print(f"    Got {len(chunk_df)} rows from this chunk")
            else:
                print(f"    No data for this chunk")
            
            # Small delay between chunks (except last one)
            if i < num_chunks - 1:
                print(f"    Waiting 2 seconds before next chunk...")
                time.sleep(2)
        
        if not all_dfs:
            print("  No data available!")
            return pd.DataFrame()
        
        df = pd.concat(all_dfs, ignore_index=True)
    else:
        # Small range - fetch all at once using last_7d
        print("  Fetching raw time series data from InfluxDB...")
        df = fetch_level1_raw_data_chunk(level1_devices, start_date, end_date)
    
    if df.empty:
        print("  No records generated!")
        return df

    # Sort by timestamp then ahu_id
    df = df.sort_values(["timestamp", "ahu_id"]).reset_index(drop=True)

    print(f"  Total records: {len(df)}")

    return df


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Level 1 raw metrics from InfluxDB")
    parser.add_argument("--days", type=int, default=365,
                       help="Number of days to fetch (default: 365 for all-time)")
    parser.add_argument("--output", type=str, default=None,
                       help="Output Parquet path (default: data/level1_raw_metrics.parquet)")

    args = parser.parse_args()

    if args.days >= 365:
        time_range = "all_time"
    else:
        time_range = f"last_{args.days}d"

    print("=" * 60)
    print(f"Fetching Level 1 Raw Data")
    print(f"Time range: {time_range}")
    print("=" * 60)

    if args.output is None:
        output_path = "/Users/rdmasia/wach-insight/data/level1_raw_metrics.parquet"
    else:
        output_path = args.output

    # Ensure data directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Fetch data
    df = fetch_level1_raw_data(time_range=time_range)

    if df.empty:
        print("\nNo data to save!")
        return

    # Save to Parquet (columnar, compressed)
    print(f"\nSaving to {output_path}...")
    df.to_parquet(output_path, index=False, compression="snappy")

    file_size = os.path.getsize(output_path)
    print(f"  File size: {file_size:,} bytes")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {', '.join(df.columns.tolist())}")

    # Summary
    print(f"\nSummary:")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  AHUs: {len(df['ahu_id'].unique())}")

    # Also save CSV for easy inspection
    csv_path = output_path.replace('.parquet', '.csv')
    print(f"\nAlso saving CSV to {csv_path}...")
    df.to_csv(csv_path, index=False)

    print("\nDone!")


if __name__ == "__main__":
    main()
