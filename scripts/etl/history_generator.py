#!/usr/bin/env python3
"""
history_generator.py — Full Historical ETL Pipeline (One-Shot)

Generates complete historical data from earliest available timestamp to latest:
1. Prediction ETL (generates predictions.csv)
2. Health Scoring ETL (uses predictions for health scores)

This is a one-shot script - it runs once and exits (no scheduling).

Usage:
    python scripts/history_generator.py
    python scripts/history_generator.py --level all --verbose

Output:
    data/predictions.csv       - Energy predictions with actual vs predicted values
    data/health_all_levels.csv - Health scores with tiers and safety flags

Author: WACH Insight Team
"""

import sys
import os
import argparse
from datetime import datetime, timezone

# Add backend to path for imports (scripts/etl → .. → scripts → .. → backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pandas as pd
import numpy as np
import math

# Import ETL components
from core.influx_client import (
    fetch_time_series,
    get_available_devices
)

# Add models for AHU level config
from models.schemas import (
    AHU_LEVEL_CONFIG,
    get_devices_by_level,
    DEVICE_TO_LEVEL
)


# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "predictions.csv")
HEALTH_FILE = os.path.join(DATA_DIR, "health_all_levels.csv")

# Statistics
_stats = {
    'devices_processed': 0,
    'predictions_generated': 0,
    'health_scores_computed': 0,
    'errors': []
}

# Health Index Weights (same as risk_engine.py)
HEALTH_INDEX_WEIGHTS = {
    "energy_anomaly": 0.15,
    "power_factor":   0.25,
    "phase_imbalance": 0.25,
    "thd_drift":      0.15,
    "overload":       0.20,
}


def log_info(message: str):
    """Print info message with timestamp."""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] INFO: {message}")


def log_error(message: str):
    """Print error message with timestamp."""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] ERROR: {message}")
    _stats['errors'].append(message)


def get_all_devices() -> list:
    """Get all device IDs across all levels."""
    devices = []
    for level_config in AHU_LEVEL_CONFIG.values():
        devices.extend(level_config['device_ids'])
    return sorted(devices)


def _fetch_batched(devices: list, metric: str, time_range: str, batch_size: int = 20) -> pd.DataFrame:
    """
    Batch fetch_time_series into groups of batch_size to avoid InfluxDB
    connection drops caused by oversized regex patterns.
    """
    chunks = [devices[i:i + batch_size] for i in range(0, len(devices), batch_size)]
    frames = []
    for i, chunk in enumerate(chunks):
        log_info(f"  Fetching {metric} batch {i + 1}/{len(chunks)} ({len(chunk)} devices)...")
        try:
            df_chunk = fetch_time_series(chunk, metric, time_range)
            if not df_chunk.empty:
                frames.append(df_chunk)
        except Exception as e:
            log_error(f"  Batch {i + 1} failed for {metric}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index()


def sigmoid_score(raw: float) -> float:
    """Convert raw value to [0, 1] using sigmoid transformation."""
    raw = max(-500.0, min(500.0, float(raw)))
    s = 1.0 / (1.0 + math.exp(-raw))
    return max(0.0, min(1.0, s * 2.0 - 1.0))


def compute_ahu_health_score(
    energy_anomaly_val: float,
    current_pf: float,
    current_power: float,
    current_unbalance: float,
    current_composite_thd: float,
    df_energy: pd.DataFrame,
    df_pf: pd.DataFrame,
    df_power: pd.DataFrame,
    df_unbalance: pd.DataFrame,
    df_l1_thd: pd.DataFrame,
    df_l3_thd: pd.DataFrame
) -> dict:
    """
    Compute FAIR health score for a single AHU.
    
    Returns dict with health_index, risk_scores, and tier.
    """
    try:
        # Energy Anomaly (uses delta_kwh)
        energy_score = 0.5
        ahu_energy = df_energy.get(ahu_id)
        if ahu_energy is not None and pd.notna(energy_anomaly_val) and ahu_energy.notna().sum() > 24:
            hist_energy = ahu_energy.dropna()
            energy_median = float(hist_energy.median())
            energy_mad = float((hist_energy - energy_median).abs().median())
            energy_std = max(1.4826 * energy_mad, 0.05)
            if energy_std > 0:
                z_score = (energy_anomaly_val - energy_median) / energy_std
                energy_score = sigmoid_score(z_score)
        
        # Power Factor Risk
        pf_score = 0.5
        ahu_pf = df_pf.get(ahu_id)
        if current_pf is not None and ahu_pf is not None and ahu_pf.notna().sum() > 24:
            hist_pf = ahu_pf.dropna()
            pf_mean = float(hist_pf.mean())
            pf_std = float(hist_pf.std())
            if pf_std > 0:
                z_score = (pf_mean - current_pf) / pf_std
                pf_score = sigmoid_score(z_score)
        
        # Phase Imbalance Risk
        imbalance_score = 0.5
        ahu_unbalance = df_unbalance.get(ahu_id)
        if current_unbalance is not None and ahu_unbalance is not None and ahu_unbalance.notna().sum() > 24:
            hist_unbalance = ahu_unbalance.dropna()
            unbalance_mean = float(hist_unbalance.mean())
            unbalance_std = float(hist_unbalance.std())
            if unbalance_std > 0:
                z_score = (current_unbalance - unbalance_mean) / unbalance_std
                imbalance_score = sigmoid_score(z_score)
        
        # THD Drift Risk
        thd_score = 0.5
        if current_composite_thd is not None:
            # Combine L1 and L3 THD
            all_thd = pd.concat([df_l1_thd.get(ahu_id), df_l3_thd.get(ahu_id)], axis=1)
            hist_thd = all_thd.max(axis=1).dropna()
            if len(hist_thd) > 24:
                thd_mean = float(hist_thd.mean())
                thd_std = float(hist_thd.std())
                if thd_std > 0:
                    z_score = (current_composite_thd - thd_mean) / thd_std
                    thd_score = sigmoid_score(z_score)
        
        # Overload Risk
        overload_score = 0.5
        ahu_power = df_power.get(ahu_id)
        if current_power is not None and ahu_power is not None and ahu_power.notna().sum() > 24:
            hist_power = ahu_power.dropna()
            power_p99 = float(hist_power.quantile(0.99))
            if power_p99 > 0:
                ratio = current_power / power_p99
                overload_score = sigmoid_score(ratio * 2 - 1)
        
        # Build risk scores dict
        risk_scores = {
            'energy_anomaly': energy_score,
            'power_factor': pf_score,
            'phase_imbalance': imbalance_score,
            'thd_drift': thd_score,
            'overload': overload_score
        }
        
        # Calculate health index: 100 - (weighted_sum * 100)
        weighted_sum = 0.0
        for metric, score in risk_scores.items():
            weight = HEALTH_INDEX_WEIGHTS.get(metric, 0)
            if score is None or np.isnan(score):
                score = 0.5
            weighted_sum += score * weight
        
        health_index = 100 - (weighted_sum * 100)
        health_index = max(0, min(100, health_index))
        
        # Determine tier
        if health_index >= 80:
            health_tier = 'Healthy'
        elif health_index >= 60:
            health_tier = 'Monitor'
        elif health_index >= 40:
            health_tier = 'Maintenance Soon'
        else:
            health_tier = 'Critical'
        
        return {
            'health_index': round(health_index, 2),
            'health_tier': health_tier,
            'risk_scores': risk_scores
        }
        
    except Exception as e:
        log_error(f"Error computing health score: {e}")
        return None


def run_prediction_etl_historical(start_time: datetime, end_time: datetime = None, devices: list = None) -> pd.DataFrame:
    """
    Run Prediction ETL for full historical period.

    Formula:
        ŷ(t)   = (E(t−24h) + E(t−168h) + E(t−336h)) / 3
        Δkwh   = E(t) − ŷ(t)

    Args:
        start_time: Start timestamp
        end_time: End timestamp
        devices: Optional list of device IDs to restrict processing (level filter)

    Returns:
        DataFrame with predictions and energy values
    """
    log_info("=" * 70)
    log_info("STEP 1: EXTRACT - Fetching Historical Energy Data")
    log_info("=" * 70)

    if end_time is None:
        end_time = datetime.now(timezone.utc)

    if devices is None:
        devices = get_all_devices()
    total_devices = len(devices)
    
    # Columns for predictions output
    columns = [
        'timestamp', 'ahu_id', 'level',
        'energy_current', 'yesterday_kwh', 'last_week_kwh', 'two_weeks_kwh',
        'predicted_energy', 'delta_kwh'
    ]
    
    all_predictions = []
    
    # Fetch energy_import in batches to avoid InfluxDB connection drops
    log_info(f"Fetching energy_import for {len(devices)} devices (batched)...")

    try:
        df = _fetch_batched(devices, 'energy_import', 'all_time')
        
        if df.empty:
            log_error("No energy data fetched!")
            return pd.DataFrame(columns=columns)
        
        log_info(f"Fetched {len(df)} rows of energy data")
        
        # Get timestamps that exist across all devices
        valid_timestamps = df.dropna(how='all').index
        
        log_info(f"Processing {len(valid_timestamps)} timestamps...")
        
        # Process each timestamp
        for ts_idx, ts in enumerate(valid_timestamps):
            if ts_idx % 100 == 0:
                log_info(f"  Timestamp {ts_idx + 1}/{len(valid_timestamps)}: {ts}")
            
            # For each device at this timestamp
            for device_id in devices:
                if device_id not in df.columns:
                    continue
                
                if pd.isna(df[device_id].loc[ts]):
                    continue
                
                # Get values at t, t-24h, t-168h, t-336h
                energy_current = df[device_id].loc[ts]
                
                # Calculate historical offsets
                ts_24h = ts - pd.Timedelta(hours=24)
                ts_168h = ts - pd.Timedelta(weeks=1)
                ts_336h = ts - pd.Timedelta(weeks=2)
                
                # Get values at those offsets (Series.get works; .loc.get does not)
                series = df[device_id]
                yesterday_kwh = series.get(ts_24h, None)
                last_week_kwh = series.get(ts_168h, None)
                two_weeks_kwh = series.get(ts_336h, None)
                
                # Compute prediction
                if all(v is not None and not pd.isna(v) for v in [
                    yesterday_kwh, last_week_kwh, two_weeks_kwh
                ]):
                    predicted_energy = (yesterday_kwh + last_week_kwh + two_weeks_kwh) / 3
                    delta_kwh = energy_current - predicted_energy
                else:
                    predicted_energy = None
                    delta_kwh = None
                
                # Build row
                row = {
                    'timestamp': ts,
                    'ahu_id': device_id,
                    'level': f"Level {DEVICE_TO_LEVEL.get(device_id, 'N/A')}",
                    'energy_current': float(energy_current) if pd.notna(energy_current) else None,
                    'yesterday_kwh': float(yesterday_kwh) if pd.notna(yesterday_kwh) else None,
                    'last_week_kwh': float(last_week_kwh) if pd.notna(last_week_kwh) else None,
                    'two_weeks_kwh': float(two_weeks_kwh) if pd.notna(two_weeks_kwh) else None,
                    'predicted_energy': float(predicted_energy) if pd.notna(predicted_energy) else None,
                    'delta_kwh': float(delta_kwh) if pd.notna(delta_kwh) else None
                }
                
                all_predictions.append(row)
                _stats['predictions_generated'] += 1
        
        log_info(f"Generated {len(all_predictions)} prediction records")
        
    except Exception as e:
        log_error(f"Error in ETL: {e}")
        import traceback
        traceback.print_exc()
    
    # Create DataFrame
    if not all_predictions:
        log_error("No predictions generated!")
        return pd.DataFrame(columns=columns)
    
    df_predictions = pd.DataFrame(all_predictions, columns=columns)
    df_predictions = df_predictions.sort_values(['timestamp', 'ahu_id'])
    
    log_info(f"Generated {len(df_predictions)} prediction records")
    
    return df_predictions


def run_health_etl_historical(predictions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run Health Scoring ETL using historical predictions.
    
    Computes FAIR health scores:
        - Energy Anomaly (15%)
        - Power Factor Degradation (25%)
        - Phase Imbalance (25%)
        - THD Drift (15%)
        - Overload (20%)
    
    Args:
        predictions_df: DataFrame from prediction ETL
        
    Returns:
        DataFrame with health scores and safety flags
    """
    log_info("=" * 70)
    log_info("STEP 2: TRANSFORM & LOAD - Computing Health Scores")
    log_info("=" * 70)
    
    # Get unique devices
    devices = predictions_df['ahu_id'].unique()
    
    log_info(f"Processing {len(devices)} devices...")
    
    # Health scoring columns — must match run_health_etl.py output format
    health_columns = [
        'timestamp', 'ahu_id', 'level',
        'health_index', 'tier',
        'energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload',
        'raw_power_total', 'raw_energy_import', 'raw_power_factor_avg',
        'raw_current_unbalance', 'raw_composite_thd',
        'safety_flags'
    ]

    all_health_records = []

    # Fetch all metrics for ALL devices
    log_info("Fetching all metrics from InfluxDB...")

    # Fetch energy at latest timestamp
    devices_with_data = predictions_df['ahu_id'].unique()

    # Fetch all metrics in batches to avoid InfluxDB connection drops
    devices_list = list(devices_with_data)
    df_power    = _fetch_batched(devices_list, 'power_total',      'all_time').sort_index()
    df_energy   = _fetch_batched(devices_list, 'energy_import',    'all_time').sort_index()
    df_pf       = _fetch_batched(devices_list, 'power_factor_avg', 'all_time').sort_index()
    df_unbalance = _fetch_batched(devices_list, 'current_unbalance', 'all_time').sort_index()
    df_l1_thd   = _fetch_batched(devices_list, 'current_l1_thd',   'all_time').sort_index()
    df_l3_thd   = _fetch_batched(devices_list, 'current_l3_thd',   'all_time').sort_index()

    def _asof_value(df, ahu_id, ts):
        """Look up nearest-prior value for ahu_id at timestamp ts."""
        if df.empty or ahu_id not in df.columns:
            return None
        s = df[ahu_id].dropna()
        if s.empty:
            return None
        try:
            val = s.asof(ts)
            return float(val) if pd.notna(val) else None
        except Exception:
            return float(s.iloc[-1]) if not s.empty else None

    # Process each device — iterate ALL timestamps (not just latest)
    for idx, ahu_id in enumerate(devices):
        processed = idx + 1
        log_info(f"Computing health scores for {ahu_id} ({processed}/{len(devices)})...")

        # Get ALL rows for this device sorted by timestamp
        device_data = predictions_df[predictions_df['ahu_id'] == ahu_id].sort_values('timestamp')

        if device_data.empty:
            continue

        for _, row in device_data.iterrows():
            ts = row['timestamp']
            level_val = str(row.get('level', 'Level 1'))
            energy_anomaly_val = row.get('delta_kwh')

            # Look up raw metric values at this timestamp using .asof()
            current_power = _asof_value(df_power, ahu_id, ts)
            current_pf = _asof_value(df_pf, ahu_id, ts)
            current_unbalance = _asof_value(df_unbalance, ahu_id, ts)
            current_energy = _asof_value(df_energy, ahu_id, ts)

            # Composite THD: average of L1 and L3
            l1 = _asof_value(df_l1_thd, ahu_id, ts)
            l3 = _asof_value(df_l3_thd, ahu_id, ts)
            if l1 is not None and l3 is not None:
                current_composite_thd = (l1 + l3) / 2
            elif l1 is not None:
                current_composite_thd = l1
            elif l3 is not None:
                current_composite_thd = l3
            else:
                current_composite_thd = None

            # Compute health score
            try:
                result = compute_ahu_health_score(
                    energy_anomaly_val=energy_anomaly_val,
                    current_pf=current_pf,
                    current_power=current_power,
                    current_unbalance=current_unbalance,
                    current_composite_thd=current_composite_thd,
                    df_energy=df_energy,
                    df_pf=df_pf,
                    df_power=df_power,
                    df_unbalance=df_unbalance,
                    df_l1_thd=df_l1_thd,
                    df_l3_thd=df_l3_thd
                )
            except Exception as e:
                log_error(f"Error computing health score for {ahu_id} at {ts}: {e}")
                continue

            if result is None:
                continue

            # Build record
            risk_scores = result['risk_scores']

            # Generate safety flags
            safety_flags = []
            if risk_scores.get('thd_drift', 0) >= 0.8:
                safety_flags.append('THD_CHRONIC_HIGH')
            if risk_scores.get('phase_imbalance', 0) >= 0.8:
                safety_flags.append('IMBALANCE_SEVERE')
            if risk_scores.get('power_factor', 0) >= 0.8 and current_pf is not None:
                if current_pf < 0.50:
                    safety_flags.append('PF_CHRONIC_LOW')

            record = {
                'timestamp': ts,
                'ahu_id': ahu_id,
                'level': level_val,
                'health_index': result['health_index'],
                'tier': result['health_tier'],
                'energy_anomaly': round(risk_scores.get('energy_anomaly', 0), 4),
                'pf_degradation': round(risk_scores.get('power_factor', 0), 4),
                'phase_imbalance': round(risk_scores.get('phase_imbalance', 0), 4),
                'thd_drift': round(risk_scores.get('thd_drift', 0), 4),
                'overload': round(risk_scores.get('overload', 0), 4),
                'raw_power_total': current_power,
                'raw_energy_import': current_energy,
                'raw_power_factor_avg': current_pf,
                'raw_current_unbalance': current_unbalance,
                'raw_composite_thd': current_composite_thd,
                'safety_flags': ';'.join(safety_flags) if safety_flags else ''
            }

            all_health_records.append(record)
            _stats['health_scores_computed'] += 1
    
    # Create DataFrame
    if not all_health_records:
        log_error("No health scores generated!")
        return pd.DataFrame(columns=health_columns)
    
    df_health = pd.DataFrame(all_health_records, columns=health_columns)
    df_health = df_health.sort_values(['timestamp', 'ahu_id'])
    
    log_info(f"Generated {len(df_health)} health records")
    
    return df_health


def save_predictions(predictions_df: pd.DataFrame):
    """Save predictions to CSV."""
    log_info(f"Saving predictions to {PREDICTIONS_FILE}...")
    
    if predictions_df.empty:
        log_error("No data to save!")
        return False
    
    os.makedirs(os.path.dirname(PREDICTIONS_FILE), exist_ok=True)
    predictions_df.to_csv(PREDICTIONS_FILE, index=False)
    log_info(f"Saved {len(predictions_df)} records to predictions.csv")
    
    return True


def save_health_scores(health_df: pd.DataFrame):
    """Append health scores to CSV, deduplicating on (timestamp, ahu_id)."""
    log_info(f"Saving health scores to {HEALTH_FILE}...")

    if health_df.empty:
        log_error("No data to save!")
        return False

    os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)

    if os.path.exists(HEALTH_FILE) and os.path.getsize(HEALTH_FILE) > 0:
        existing = pd.read_csv(HEALTH_FILE)
        existing_keys = set(zip(existing['timestamp'].astype(str), existing['ahu_id'].astype(str)))
        new_rows = health_df[
            ~health_df.apply(
                lambda r: (str(r['timestamp']), str(r['ahu_id'])) in existing_keys, axis=1
            )
        ]
        if new_rows.empty:
            log_info("No new rows to append (all already present)")
            return True
        new_rows.to_csv(HEALTH_FILE, mode='a', header=False, index=False)
        log_info(f"Appended {len(new_rows)} new records to health_all_levels.csv")
    else:
        health_df.to_csv(HEALTH_FILE, index=False)
        log_info(f"Created health_all_levels.csv with {len(health_df)} records")

    return True


def main():
    """Main entry point - runs ETL pipeline once."""
    parser = argparse.ArgumentParser(
        description="Full Historical ETL Pipeline (One-Shot)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/history_generator.py          # Run complete ETL
  python scripts/history_generator.py --dry-run  # Show what would run
  
Output:
  data/predictions.csv       - Energy predictions
  data/health_all_levels.csv - Health scores with tiers and safety flags
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would run without executing"
    )
    
    parser.add_argument(
        '--level',
        type=str,
        default='all',
        help="Level to process (1-11) or 'all' for all levels"
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Show verbose output"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        log_info("=" * 70)
        log_info("DRY-RUN MODE - Showing plan only")
        log_info("=" * 70)
        log_info("Step 1: Prediction ETL")
        log_info(f"  - Fetch energy_import data for all AHUs")
        log_info(f"  - Compute ŷ(t) = (E(t−24h) + E(t−168h) + E(t−336h)) / 3")
        log_info(f"  - Compute Δkwh = E(t) − ŷ(t)")
        log_info(f"  - Output: data/predictions.csv")
        log_info("")
        log_info("Step 2: Health Scoring ETL")
        log_info(f"  - Compute FAIR health scores for all devices")
        log_info(f"  - Apply safety flags for engineering audit")
        log_info(f"  - Output: data/health_all_levels.csv")
        log_info("")
        devices = get_all_devices()
        log_info(f"Estimated devices to process: {len(devices)} AHUs across all levels")
        log_info("")
        return
    
    # Start ETL
    start_time = datetime.now()
    
    log_info("=" * 70)
    log_info("WACH Insight Historical ETL Pipeline")
    log_info("=" * 70)
    log_info(f"Started at: {start_time.isoformat()}")
    log_info(f"Level filter: {args.level}")
    
    devices = get_all_devices()
    if args.level != 'all':
        level_num = int(args.level)
        devices = get_devices_by_level(level_num)
    
    log_info(f"Devices to process: {len(devices)} AHUs")
    
    # Step 1: Prediction ETL
    log_info("")
    log_info("Phase 1: Running Prediction ETL")
    log_info("-" * 50)
    
    predictions_df = run_prediction_etl_historical(
        start_time=datetime.now(timezone.utc) - pd.Timedelta(days=365),
        end_time=datetime.now(timezone.utc),
        devices=devices,
    )
    
    if predictions_df.empty:
        log_error("Prediction ETL produced no data!")
    else:
        save_predictions(predictions_df)
    
    # Step 2: Health Scoring ETL
    log_info("")
    log_info("Phase 2: Running Health Scoring ETL")
    log_info("-" * 50)
    
    health_df = run_health_etl_historical(predictions_df)
    
    if health_df.empty:
        log_error("Health Scoring ETL produced no data!")
    else:
        save_health_scores(health_df)
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    
    log_info("")
    log_info("=" * 70)
    log_info("ETL Pipeline Complete")
    log_info("=" * 70)
    log_info(f"Duration: {elapsed:.1f} seconds")
    log_info(f"Devices processed: {_stats['devices_processed']}")
    log_info(f"Predictions generated: {_stats['predictions_generated']}")
    log_info(f"Health scores computed: {_stats['health_scores_computed']}")
    
    if _stats['errors']:
        log_info(f"Errors encountered: {len(_stats['errors'])}")
        for err in _stats['errors'][:5]:
            log_error(f"  - {err}")
    
    return 0 if not _stats['errors'] else 1


if __name__ == "__main__":
    sys.exit(main())
