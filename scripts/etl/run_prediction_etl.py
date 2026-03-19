#!/usr/bin/env python3
"""
run_prediction_etl.py
─────────────────────
Prediction ETL Pipeline for AHU Energy Forecasting

This script implements a 3-step ETL process:
1. EXTRACT: Fetch E(t), E(t−24h), E(t−168h), E(t−336h) from InfluxDB
2. TRANSFORM: Compute ŷ(t) and Δkwh per AHU
3. LOAD: Append results to predictions.csv

Formula:
  ŷ(t)   = (E(t−24h) + E(t−168h) + E(t−336h)) / 3
  Δkwh   = E(t) − ŷ(t)

Usage:
    python scripts/run_prediction_etl.py
    python scripts/run_prediction_etl.py --output custom_predictions.csv
    python scripts/run_prediction_etl.py --dry-run
    python scripts/run_prediction_etl.py --level 1           # Test Level 1 only
    python scripts/run_prediction_etl.py --level all         # All levels

Output:
    data/predictions.csv - Energy predictions with actual vs predicted values
"""

import sys
import os
import argparse
from datetime import datetime, timezone

# Add backend to path for imports (scripts/etl → .. → scripts → .. → backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pandas as pd
import numpy as np

# Import prediction data fetcher
from core.influx_client import fetch_prediction_data, get_available_devices

# Add models for AHU level config
from models.schemas import (
    AHU_LEVEL_CONFIG,
    get_devices_by_level,
    DEVICE_TO_LEVEL
)


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, "predictions.csv")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: EXTRACT - Fetch Prediction Data
# ──────────────────────────────────────────────────────────────────────────────

def extract_prediction_data(device_ids, reference_time=None):
    """
    Step 1: Fetch energy values at t, t-1h, t-24h, t-25h, t-168h, t-169h, t-336h, t-337h.

    Args:
        device_ids: List of AHU IDs to fetch
        reference_time: Reference timestamp (defaults to now)

    Returns:
        DataFrame with columns including hourly deltas needed for energy anomaly
    """
    print("\n" + "="*70)
    print("STEP 1: EXTRACT - Fetching Prediction Data from InfluxDB")
    print("="*70)

    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
        print(f"[INFO] Using current time: {reference_time.isoformat()}")

    try:
        # Fetch prediction data
        raw_data = fetch_prediction_data(device_ids, reference_time)

        if not raw_data:
            print("[ERROR] No data retrieved from InfluxDB!")
            return None

        # Convert to DataFrame
        records = []
        for ahu_id, values in raw_data.items():
            record = {
                'ahu_id': ahu_id,
                'energy_current': values.get('energy_current'),
                'yesterday_kwh': values.get('yesterday_kwh'),
                'last_week_kwh': values.get('last_week_kwh'),
                'two_weeks_kwh': values.get('two_weeks_kwh')
            }
            records.append(record)

        df = pd.DataFrame(records)

        if df.empty:
            print("[ERROR] No prediction data retrieved!")
            return None

        # Determine timestamp from energy_current (if available)
        # For now, use reference_time as the prediction timestamp
        df['timestamp'] = reference_time.isoformat()

        print(f"[OK] Retrieved prediction data for {len(df)} AHUs")
        print(f"    Columns: {list(df.columns)}")

        # Show sample of fetched values
        print("\n    Sample data:")
        for i, row in df.head(3).iterrows():
            print(f"      {row['ahu_id']}: current={row['energy_current']:.2f}, "
                  f"yesterday={row['yesterday_kwh']:.2f}, "
                  f"last_week={row['last_week_kwh']:.2f}, "
                  f"two_weeks={row['two_weeks_kwh']:.2f}")

        return df

    except Exception as e:
        print(f"[ERROR] Failed to fetch prediction data: {e}")
        import traceback
        traceback.print_exc()
        return None


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: TRANSFORM - Compute Predictions and Delta
# ──────────────────────────────────────────────────────────────────────────────

def transform_predictions(df_raw):
    """
    Step 2: Compute predicted energy (ŷ), hourly deltas, and energy anomaly.

    NEW Formula:
      hourly_delta(t)     = E(t) - E(t-1h)
      predicted_delta(t)  = (δ(t−24h) + δ(t−168h) + δ(t−336h)) / 3
      energy_anomaly      = hourly_delta(t) - predicted_delta(t)

    Where δ(t−nh) = E(t−nh) - E(t−nh-1h)

    Args:
        df_raw: DataFrame with energy values from Step 1

    Returns:
        DataFrame with added columns: hourly_delta, predicted_delta, energy_anomaly
    """
    print("\n" + "="*70)
    print("STEP 2: TRANSFORM - Computing Predictions")
    print("="*70)

    if df_raw is None or df_raw.empty:
        print("[ERROR] No raw data to transform!")
        return None

    # Make a copy to avoid modifying original
    df = df_raw.copy()

    # ── Compute Hourly Deltas (actual energy consumed in the hour) ─────────────
    def compute_hourly_delta(row, current_col, prev_col):
        """Compute δ = E(current) - E(previous_hour)."""
        current = row.get(current_col)
        prev = row.get(prev_col)

        if current is None or np.isnan(current):
            return None
        if prev is None or np.isnan(prev):
            return None

        return float(current - prev)

    # Hourly delta at current time
    df['hourly_delta'] = df.apply(lambda row: compute_hourly_delta(row, 'energy_current', 'energy_t_minus_1h'), axis=1)

    # Hourly deltas at historical points
    df['delta_yesterday'] = df.apply(lambda row: compute_hourly_delta(row, 'yesterday_kwh', 'yesterday_minus_1h'), axis=1)
    df['delta_last_week'] = df.apply(lambda row: compute_hourly_delta(row, 'last_week_kwh', 'last_week_minus_1h'), axis=1)
    df['delta_two_weeks'] = df.apply(lambda row: compute_hourly_delta(row, 'two_weeks_kwh', 'two_weeks_minus_1h'), axis=1)

    # ── Compute Predicted Delta (average of historical hourly deltas) ─────────
    def compute_predicted_delta(row):
        """Compute ŷ_δ(t) = avg(δ(t−24h), δ(t−168h), δ(t−336h))."""
        values = [
            row.get('delta_yesterday'),
            row.get('delta_last_week'),
            row.get('delta_two_weeks')
        ]
        # Filter out None/NaN values
        valid_values = [v for v in values if v is not None and not np.isnan(v)]
        if len(valid_values) == 0:
            return None
        return float(np.mean(valid_values))

    def count_delta_slots(row):
        """Count how many delta slots have valid data."""
        values = [
            row.get('delta_yesterday'),
            row.get('delta_last_week'),
            row.get('delta_two_weeks')
        ]
        valid_count = sum(1 for v in values if v is not None and not np.isnan(v))
        return valid_count

    # Apply predicted delta formula
    df['predicted_delta'] = df.apply(compute_predicted_delta, axis=1)

    # Count available delta slots
    df['available_delta_slots'] = df.apply(count_delta_slots, axis=1)

    # Mark insufficient history (< 3 delta slots means data < 2 weeks)
    df['insufficient_history'] = df['available_delta_slots'] < 3

    # ── Compute Energy Anomaly (deviation of hourly delta from predicted) ─────
    def compute_energy_anomaly(row):
        """Compute energy_anomaly = hourly_delta - predicted_delta."""
        actual_delta = row.get('hourly_delta')
        predicted = row.get('predicted_delta')

        if actual_delta is None or np.isnan(actual_delta):
            return None
        if predicted is None or np.isnan(predicted):
            return None

        return float(actual_delta - predicted)

    df['energy_anomaly'] = df.apply(compute_energy_anomaly, axis=1)

    # Add level column from AHU ID using reverse mapping
    def get_level(ahu_id):
        """Get level string from AHU_ID using DEVICE_TO_LEVEL mapping."""
        return DEVICE_TO_LEVEL.get(ahu_id, "Unknown")

    # Apply level to dataframe
    df['level'] = df['ahu_id'].apply(get_level)

    # Reorder columns for cleaner output
    col_order = [
        'timestamp', 'ahu_id', 'level',
        'energy_current', 'hourly_delta', 'predicted_delta', 'energy_anomaly',
        'yesterday_kwh', 'delta_yesterday',
        'last_week_kwh', 'delta_last_week',
        'two_weeks_kwh', 'delta_two_weeks',
        'available_delta_slots', 'insufficient_history'
    ]
    df = df[[c for c in col_order if c in df.columns]]

    # Print summary statistics
    print(f"\n[OK] Computed predictions for {len(df)} AHUs")
    print("\n    Summary Statistics:")

    # Energy current stats
    if df['energy_current'].notna().any():
        ec_mean = df['energy_current'].mean()
        ec_std = df['energy_current'].std()
        print(f"      Energy Current: {ec_mean:.2f} kWh (σ={ec_std:.2f})")

    # Hourly delta stats
    if df['hourly_delta'].notna().any():
        hd_mean = df['hourly_delta'].mean()
        hd_std = df['hourly_delta'].std()
        print(f"      Hourly Delta:     {hd_mean:.2f} kWh (σ={hd_std:.2f})")

    # Predicted delta stats
    if df['predicted_delta'].notna().any():
        pred_mean = df['predicted_delta'].mean()
        pred_std = df['predicted_delta'].std()
        print(f"      Predicted (ŷ_δ):  {pred_mean:.2f} kWh (σ={pred_std:.2f})")

    # Energy anomaly stats
    if df['energy_anomaly'].notna().any():
        anom_mean = df['energy_anomaly'].mean()
        anom_std = df['energy_anomaly'].std()
        print(f"      Energy Anomaly:   {anom_mean:.2f} kWh (σ={anom_std:.2f})")

    # Count devices with valid predictions
    valid_pred = df['predicted_delta'].notna().sum()
    print(f"\n      Devices with valid prediction: {valid_pred}/{len(df)}")

    # Count devices where actual > predicted (positive energy anomaly)
    positive_anomaly = (df['energy_anomaly'] > 0).sum()
    if valid_pred > 0:
        print(f"      Devices above prediction: {positive_anomaly} ({100*positive_anomaly/valid_pred:.1f}%)")

    # Insufficient history summary
    insufficient_count = df['insufficient_history'].sum()
    sufficient_count = len(df) - insufficient_count
    print(f"\n      Historical data quality:")
    print(f"        Sufficient (≥3 slots): {sufficient_count} ({100*sufficient_count/len(df):.1f}%)")
    print(f"        Insufficient (<3 slots): {insufficient_count} ({100*insufficient_count/len(df):.1f}%)")

    return df


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3: LOAD - Write to CSV
# ──────────────────────────────────────────────────────────────────────────────

def load_to_csv(df_predictions, output_path=None, dry_run=False):
    """
    Step 3: Append predictions to CSV file.

    Args:
        df_predictions: DataFrame with prediction results
        output_path: Path to output CSV file
        dry_run: If True, don't write file

    Returns:
        Number of rows written
    """
    print("\n" + "="*70)
    print("STEP 3: LOAD - Writing to predictions.csv")
    print("="*70)

    if output_path is None:
        output_path = OUTPUT_FILE

    # Ensure directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    if dry_run:
        print("[DRY RUN] Would write to:", output_path)
        print(f"[OK] Preview of {len(df_predictions)} rows:")
        print("\n    First 5 rows:")
        for i, row in df_predictions.head(5).iterrows():
            print(f"      {row['ahu_id']}: E={row.get('energy_current', 'N/A'):.2f}, "
                  f"δ={row.get('hourly_delta', 'N/A'):.2f}, "
                  f"ŷ_δ={row.get('predicted_delta', 'N/A'):.2f}, "
                  f"Δ={row.get('energy_anomaly', 'N/A'):.2f}")
        return len(df_predictions)

    # Determine if file exists and needs header
    file_exists = os.path.exists(output_path)

    # Define columns in order (new format with hourly deltas)
    required_cols = [
        "timestamp", "ahu_id", "level",
        "energy_current", "hourly_delta", "predicted_delta", "energy_anomaly",
        "yesterday_kwh", "delta_yesterday",
        "last_week_kwh", "delta_last_week",
        "two_weeks_kwh", "delta_two_weeks",
        "available_delta_slots", "insufficient_history"
    ]

    # Reorder columns
    df_output = df_predictions[[c for c in required_cols if c in df_predictions.columns]]

    # Always overwrite existing file
    mode = 'w'
    header = True

    try:
        df_output.to_csv(output_path, mode=mode, header=header, index=False)

        print(f"[OK] Overwritten CSV with {len(df_output)} rows: {output_path}")

        return len(df_output)

    except Exception as e:
        print(f"[ERROR] Failed to write CSV: {e}")
        import traceback
        traceback.print_exc()
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# VALIDATION FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def validate_level_results(df_results: pd.DataFrame, level_num: int) -> bool:
    """
    Validate that all devices for a level are present in results.
    
    Args:
        df_results: DataFrame with prediction results
        level_num: Level number (1-11)
        
    Returns:
        True if all devices match, False otherwise
    """
    from models.schemas import get_devices_by_level
    
    expected_device_ids = get_devices_by_level(level_num)
    actual_device_ids = df_results['ahu_id'].unique().tolist()
    
    expected_count = len(expected_device_ids)
    actual_count = len(actual_device_ids)
    
    # Sort for comparison
    expected_set = set(expected_device_ids)
    actual_set = set(actual_device_ids)
    
    missing = sorted(list(expected_set - actual_set))
    extra = sorted(list(actual_set - expected_set))
    
    status = "[PASS]" if actual_count == expected_count else "[FAIL]"
    print(f"\n  {status} Level {level_num}: {actual_count}/{expected_count} devices")
    
    if missing:
        print(f"  [WARN] Missing devices: {missing}")
    if extra:
        print(f"  [WARN] Extra devices: {extra}")
    
    # Count insufficient history
    if 'insufficient_history' in df_results.columns:
        insufficient_count = df_results['insufficient_history'].sum()
        sufficient_count = len(df_results) - insufficient_count
        print(f"  [INFO] Data quality:")
        print(f"    Sufficient (≥3 slots): {sufficient_count}")
        print(f"    Insufficient (<3 slots): {insufficient_count}")
    
    return actual_count == expected_count


# ──────────────────────────────────────────────────────────────────────────────
# MAIN ETL PIPELINE
# ──────────────────────────────────────────────────────────────────────────────

def run_prediction_etl(level_filter=None, output_path=None, dry_run=False, scheduled=False):
    """
    Run the complete prediction ETL pipeline.

    Args:
        level_filter: Optional level number (1-11) to filter devices
        output_path: Custom output path
        dry_run: If True, don't write to CSV
        scheduled: If True, run in scheduled mode (quiet output)

    Returns:
        DataFrame with prediction results
    """
    # Step 1: Extract
    if not scheduled:
        print("\n" + "="*70)
        print("PREDICTION ETL PIPELINE")
        print("="*70)

    # Determine device IDs
    if level_filter is not None:
        if level_filter not in AHU_LEVEL_CONFIG:
            print(f"[ERROR] Invalid level {level_filter}")
            return None
        device_ids = AHU_LEVEL_CONFIG[level_filter]["device_ids"]
        print(f"\n[INFO] Processing Level {level_filter} ({len(device_ids)} AHUs)")
    else:
        # Get all devices from AHU_LEVEL_CONFIG
        device_ids = []
        for level_config in AHU_LEVEL_CONFIG.values():
            device_ids.extend(level_config["device_ids"])
        print(f"\n[INFO] Processing all levels ({len(device_ids)} AHUs)")

    # Step 1: EXTRACT
    df_raw = extract_prediction_data(device_ids)
    if df_raw is None or df_raw.empty:
        print("[ERROR] Extract phase failed!")
        return None

    # Step 2: TRANSFORM
    df_predictions = transform_predictions(df_raw)
    if df_predictions is None or df_predictions.empty:
        print("[ERROR] Transform phase failed!")
        return None

    # Step 3: LOAD
    rows_written = load_to_csv(df_predictions, output_path, dry_run)

    # Determine actual output path
    if output_path is None:
        actual_output = OUTPUT_FILE
    else:
        actual_output = output_path

    # Validate results per level
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    all_valid = True
    if level_filter is not None:
        # Single level mode - validate that specific level
        all_valid = validate_level_results(df_predictions, level_filter)
    else:
        # All levels mode - validate each level separately
        for level_num in sorted(AHU_LEVEL_CONFIG.keys()):
            level_devices = AHU_LEVEL_CONFIG[level_num]["device_ids"]
            df_level = df_predictions[df_predictions['ahu_id'].isin(level_devices)]
            if not validate_level_results(df_level, level_num):
                all_valid = False
    
    # Summary
    print("\n" + "="*70)
    if dry_run:
        print("[DRY RUN] No file was written (--dry-run flag set)")
    else:
        if all_valid:
            print(f"[OK] ETL Complete: {rows_written} rows written to {actual_output}")
            print("[OK] All levels passed validation")
        else:
            print(f"[ERROR] ETL completed but some devices are missing from results")
            return None
        
        # Overall insufficient history summary
        if 'insufficient_history' in df_predictions.columns:
            total = len(df_predictions)
            insufficient = df_predictions['insufficient_history'].sum()
            sufficient = total - insufficient
            print(f"\n[OK] Overall Data Quality:")
            print(f"  Sufficient (≥3 slots): {sufficient}/{total} ({100*sufficient/total:.1f}%)")
            print(f"  Insufficient (<3 slots): {insufficient}/{total} ({100*insufficient/total:.1f}%)")
    
    print("="*70)

    return df_predictions


# ──────────────────────────────────────────────────────────────────────────────
# COMMAND-LINE INTERFACE
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Prediction ETL Pipeline for AHU Energy Forecasting"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Custom output CSV path"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Run ETL without writing to CSV"
    )
    parser.add_argument(
        "--level", "-l",
        type=str,
        default=None,
        help="Level number (1-11) or 'all' for all levels"
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run in scheduled mode (quiet output, automatic settings)"
    )

    args = parser.parse_args()

    # Parse level filter
    level_filter = None
    if args.level is not None:
        if args.level.lower() == "all":
            level_filter = None
        else:
            try:
                level_filter = int(args.level)
                if level_filter < 1 or level_filter > 11:
                    print("[ERROR] Level must be between 1 and 11")
                    sys.exit(1)
            except ValueError:
                print(f"[ERROR] Invalid level value: {args.level}")
                sys.exit(1)

    # Set default output path if not specified
    if args.output is None:
        args.output = OUTPUT_FILE

    # Run ETL
    result = run_prediction_etl(
        level_filter=level_filter,
        output_path=args.output,
        dry_run=args.dry_run,
        scheduled=args.scheduled
    )

    if result is None:
        sys.exit(1)

    # Print summary (only in interactive mode)
    if not args.scheduled:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
    else:
        # In scheduled mode, print minimal summary
        # Use energy_anomaly column (renamed from old delta_kwh)
        print(f"[INFO] Devices: {len(result)} | Predictions: {result['predicted_delta'].notna().sum()} | Avg anomaly: {result['energy_anomaly'].mean():.2f} kWh")


if __name__ == "__main__":
    main()
