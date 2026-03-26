#!/usr/bin/env python3
"""
history_generator.py — Full Historical ETL Pipeline (One-Shot)

Generates complete historical data from earliest available timestamp to latest:
1. Prediction ETL (generates predictions.csv)
2. Health Scoring ETL (uses predictions for health scores)

This is a one-shot script - it runs once and exits (no scheduling).

Usage:
    python3 scripts/history_generator.py
    python3 scripts/history_generator.py --level all --verbose

Output:
    data/predictions.csv       - Energy predictions with actual vs predicted values
    data/health_all_levels.csv - Health scores with tiers and safety flags

Author: WACH Insight Team
"""

import sys
import os
import time
import argparse
from datetime import datetime, timezone, timedelta

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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "predictions.csv")
HEALTH_FILE = os.path.join(DATA_DIR, "health_all_levels.csv")
HOURLY_FILE = os.path.join(DATA_DIR, "health_hourly.csv")

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


def _fetch_full_history(
    devices: list,
    metric: str,
    start_dt: datetime,
    end_dt: datetime,
    batch_days: int = 30,
    device_batch_size: int = 20,
) -> pd.DataFrame:
    """
    Fetch metric data for all devices from start_dt to end_dt by splitting the
    time range into windows of batch_days days and device groups of
    device_batch_size.  Concatenates and deduplicates all windows before
    returning a single DataFrame indexed by UTC time.
    """
    from core.influx_client import fetch_time_series_window

    total_days = max(1, (end_dt - start_dt).days)
    total_windows = math.ceil(total_days / batch_days)
    dev_chunks = [
        devices[i:i + device_batch_size]
        for i in range(0, len(devices), device_batch_size)
    ]
    total_batches = len(dev_chunks)
    frames = []
    window_start = start_dt
    window_num = 0
    total_rows_fetched = 0

    log_info(f"  [{metric}] starting: {total_windows} windows × {total_batches} device-batches "
             f"= {total_windows * total_batches} queries | "
             f"{len(devices)} devices | {start_dt.date()} → {end_dt.date()}")

    while window_start < end_dt:
        window_end = min(window_start + timedelta(days=batch_days), end_dt)
        window_num += 1
        window_rows = 0
        window_ok = 0
        window_fail = 0
        window_empty = 0

        log_info(f"  [{metric}] window {window_num}/{total_windows}: "
                 f"{window_start.date()} → {window_end.date()} "
                 f"({(window_end - window_start).days}d, {total_batches} batches)")

        for di, chunk in enumerate(dev_chunks):
            batch_label = f"batch {di + 1}/{total_batches}"
            devices_preview = ",".join(chunk[:3]) + (f"+{len(chunk)-3}" if len(chunk) > 3 else "")
            for attempt in range(3):
                try:
                    df_chunk = fetch_time_series_window(chunk, metric, window_start, window_end)
                    if not df_chunk.empty:
                        rows = len(df_chunk)
                        frames.append(df_chunk)
                        window_rows += rows
                        window_ok += 1
                        log_info(f"    [{metric}] w{window_num} {batch_label} ({devices_preview}): "
                                 f"OK — {rows} rows, {len(df_chunk.columns)} devices")
                    else:
                        window_empty += 1
                        log_info(f"    [{metric}] w{window_num} {batch_label} ({devices_preview}): "
                                 f"EMPTY — no data in this range")
                    break
                except Exception as e:
                    if attempt < 2:
                        wait = 15 * (2 ** attempt)  # 15s, 30s
                        log_error(
                            f"    [{metric}] w{window_num} {batch_label} ({devices_preview}): "
                            f"FAIL attempt {attempt + 1}/3 — {type(e).__name__}: {e} "
                            f"— retrying in {wait}s"
                        )
                        time.sleep(wait)
                    else:
                        window_fail += 1
                        log_error(
                            f"    [{metric}] w{window_num} {batch_label} ({devices_preview}): "
                            f"FAIL all 3 attempts — {type(e).__name__}: {e}"
                        )

        total_rows_fetched += window_rows
        status_parts = [f"{window_ok} ok"]
        if window_empty:
            status_parts.append(f"{window_empty} empty")
        if window_fail:
            status_parts.append(f"{window_fail} FAILED")
        log_info(f"  [{metric}] window {window_num}/{total_windows} done: "
                 f"{window_rows} rows ({', '.join(status_parts)}) | "
                 f"running total: {total_rows_fetched} rows")

        window_start = window_end

    if not frames:
        log_error(f"  [{metric}] RESULT: 0 rows — all {total_windows * total_batches} queries returned empty/failed")
        return pd.DataFrame()

    combined = pd.concat(frames, axis=0)
    # Merge rows that share a timestamp (happens when multiple device batches cover
    # the same time window — each batch has different columns, same timestamps).
    # groupby.first() picks the first non-NaN value per column per timestamp,
    # which correctly stitches device-batch columns back together.
    combined = combined.groupby(combined.index).first().sort_index()
    log_info(f"  [{metric}] RESULT: {len(combined)} rows × {len(combined.columns)} devices "
             f"| span {combined.index[0].date()} → {combined.index[-1].date()}")
    return combined


def sigmoid_score(raw: float) -> float:
    """Convert raw value to [0, 1] using sigmoid transformation."""
    raw = max(-500.0, min(500.0, float(raw)))
    s = 1.0 / (1.0 + math.exp(-raw))
    return max(0.0, min(1.0, s * 2.0 - 1.0))


def compute_ahu_health_score(
    ahu_id: str,
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
        # Energy Anomaly — normalize delta_kwh against daily energy variation std
        energy_score = 0.5
        ahu_energy = df_energy.get(ahu_id)
        if ahu_energy is not None and pd.notna(energy_anomaly_val) and ahu_energy.notna().sum() > 24:
            hist_energy = ahu_energy.dropna()
            hist_daily = hist_energy.diff().dropna()
            daily_std = max(float(hist_daily.std()), 1.0)
            z_score = float(energy_anomaly_val) / daily_std
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


def run_prediction_etl_historical(
    start_time: datetime,
    end_time: datetime = None,
    devices: list = None,
    batch_days: int = 30,
) -> pd.DataFrame:
    """
    Run Prediction ETL for full historical period.

    NEW Formula:
      hourly_delta(t)     = E(t) - E(t-1h)
      predicted_delta(t)  = (δ(t−24h) + δ(t−168h) + δ(t−336h)) / 3
      energy_anomaly      = hourly_delta(t) - predicted_delta(t)

    Where δ(t−nh) = E(t−nh) - E(t−nh-1h)

    Args:
        start_time:  Earliest data timestamp (UTC-aware datetime).
        end_time:    Latest data timestamp (defaults to now).
        devices:     Optional device list; defaults to all devices.
        batch_days:  Width of each InfluxDB time-fetch window in days.

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

    # Columns for predictions output (new format with hourly deltas)
    columns = [
        'timestamp', 'ahu_id', 'level',
        'energy_current', 'hourly_delta', 'predicted_delta', 'energy_anomaly',
        'yesterday_kwh', 'delta_yesterday',
        'last_week_kwh', 'delta_last_week',
        'two_weeks_kwh', 'delta_two_weeks'
    ]

    all_predictions = []

    # Fetch energy_import across the full history in time-batched windows
    log_info(f"Fetching energy_import for {len(devices)} devices "
             f"from {start_time.date()} → {end_time.date()} "
             f"(batch_days={batch_days})...")

    try:
        df = _fetch_full_history(devices, 'energy_import', start_time, end_time, batch_days)

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

                # Get values at t, t-24h, t-168h, t-336h and their t-1h counterparts
                energy_current = df[device_id].loc[ts]

                # Calculate historical offsets
                ts_24h = ts - pd.Timedelta(hours=24)
                ts_168h = ts - pd.Timedelta(weeks=1)
                ts_336h = ts - pd.Timedelta(weeks=2)
                
                # Also get t-1h offsets for hourly delta calculation
                ts_1h = ts - pd.Timedelta(hours=1)
                ts_25h = ts - pd.Timedelta(hours=25)
                ts_169h = ts - pd.Timedelta(weeks=1, hours=1)
                ts_337h = ts - pd.Timedelta(weeks=2, hours=1)

                # Get values at those offsets (Series.get works; .loc.get does not)
                series = df[device_id]
                energy_t_minus_1h = series.get(ts_1h, None)
                yesterday_kwh = series.get(ts_24h, None)
                yesterday_minus_1h = series.get(ts_25h, None)
                last_week_kwh = series.get(ts_168h, None)
                last_week_minus_1h = series.get(ts_169h, None)
                two_weeks_kwh = series.get(ts_336h, None)
                two_weeks_minus_1h = series.get(ts_337h, None)

                # Compute hourly deltas
                hourly_delta = None
                if energy_current is not None and not pd.isna(energy_current) and \
                   energy_t_minus_1h is not None and not pd.isna(energy_t_minus_1h):
                    hourly_delta = float(energy_current - energy_t_minus_1h)

                # Compute historical hourly deltas
                delta_yesterday = None
                if yesterday_kwh is not None and not pd.isna(yesterday_kwh) and \
                   yesterday_minus_1h is not None and not pd.isna(yesterday_minus_1h):
                    delta_yesterday = float(yesterday_kwh - yesterday_minus_1h)

                delta_last_week = None
                if last_week_kwh is not None and not pd.isna(last_week_kwh) and \
                   last_week_minus_1h is not None and not pd.isna(last_week_minus_1h):
                    delta_last_week = float(last_week_kwh - last_week_minus_1h)

                delta_two_weeks = None
                if two_weeks_kwh is not None and not pd.isna(two_weeks_kwh) and \
                   two_weeks_minus_1h is not None and not pd.isna(two_weeks_minus_1h):
                    delta_two_weeks = float(two_weeks_kwh - two_weeks_minus_1h)

                # Compute predicted delta (average of historical hourly deltas)
                valid_deltas = [v for v in [delta_yesterday, delta_last_week, delta_two_weeks] 
                               if v is not None and not pd.isna(v)]
                predicted_delta = float(np.mean(valid_deltas)) if valid_deltas else None

                # Compute energy anomaly
                energy_anomaly = None
                if hourly_delta is not None and predicted_delta is not None:
                    energy_anomaly = float(hourly_delta - predicted_delta)

                # Build row
                row = {
                    'timestamp': ts,
                    'ahu_id': device_id,
                    'level': DEVICE_TO_LEVEL.get(device_id, 'N/A'),
                    'energy_current': float(energy_current) if pd.notna(energy_current) else None,
                    'hourly_delta': float(hourly_delta) if hourly_delta is not None else None,
                    'predicted_delta': float(predicted_delta) if predicted_delta is not None else None,
                    'energy_anomaly': float(energy_anomaly) if energy_anomaly is not None else None,
                    'yesterday_kwh': float(yesterday_kwh) if pd.notna(yesterday_kwh) else None,
                    'delta_yesterday': float(delta_yesterday) if delta_yesterday is not None else None,
                    'last_week_kwh': float(last_week_kwh) if pd.notna(last_week_kwh) else None,
                    'delta_last_week': float(delta_last_week) if delta_last_week is not None else None,
                    'two_weeks_kwh': float(two_weeks_kwh) if pd.notna(two_weeks_kwh) else None,
                    'delta_two_weeks': float(delta_two_weeks) if delta_two_weeks is not None else None
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


def run_health_etl_historical(
    predictions_df: pd.DataFrame,
    start_dt: datetime = None,
    end_dt: datetime = None,
    batch_days: int = 30,
) -> pd.DataFrame:
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
        start_dt:       Start of data window (used for time-batched fetches)
        end_dt:         End of data window (defaults to now)
        batch_days:     Width of each InfluxDB time-fetch window in days

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
        'raw_power_total', 'raw_energy_import', 'raw_hourly_delta',
        'raw_predicted_delta', 'raw_energy_anomaly_raw',
        'raw_power_factor_avg', 'raw_current_unbalance', 'raw_composite_thd',
        # New per-phase columns
        'raw_apparent_power_total',
        'raw_current_l1', 'raw_current_l2', 'raw_current_l3',
        'raw_volts_l1_n', 'raw_volts_l2_n', 'raw_volts_l3_n',
        'raw_current_l1_thd', 'raw_current_l3_thd',
        'raw_volts_l1_thd', 'raw_volts_l2_thd', 'raw_volts_l3_thd',
        'raw_nema_voltage_imbalance',
        'raw_p95_current',
        'safety_flags'
    ]

    all_health_records = []

    if end_dt is None:
        end_dt = datetime.now(timezone.utc)
    if start_dt is None:
        # Fall back to 30-day window if caller didn't provide start
        start_dt = end_dt - timedelta(days=30)

    # Fetch all metrics for ALL devices across the full history window
    log_info(f"Fetching all metrics from InfluxDB "
             f"({start_dt.date()} → {end_dt.date()}, batch_days={batch_days})...")

    devices_with_data = predictions_df['ahu_id'].unique()
    devices_list = list(devices_with_data)

    def _fh(metric):
        return _fetch_full_history(devices_list, metric, start_dt, end_dt, batch_days).sort_index()

    # Fetch all 16 metrics concurrently — each call creates its own InfluxDB
    # connection so parallel execution is safe.
    from concurrent.futures import ThreadPoolExecutor, as_completed

    METRICS = [
        'power_total', 'energy_import', 'power_factor_avg', 'current_unbalance',
        'current_l1_thd', 'current_l3_thd', 'apparent_power_total',
        'current_l1', 'current_l2', 'current_l3',
        'volts_l1_n', 'volts_l2_n', 'volts_l3_n',
        'volts_l1_thd', 'volts_l2_thd', 'volts_l3_thd',
    ]

    log_info(f"Launching {len(METRICS)} metric fetches with max 3 concurrent "
             f"InfluxDB connections ({len(devices_list)} devices, "
             f"{start_dt.date()} → {end_dt.date()})...")

    metric_dfs = {}
    metrics_ok = []
    metrics_empty = []
    metrics_failed = []

    # Limit to 3 concurrent InfluxDB metric fetches — firing all 16 at once
    # overwhelms the remote server and causes connection failures for all of them.
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_fh, m): m for m in METRICS}
        for future in as_completed(futures):
            m = futures[future]
            try:
                df = future.result()
                metric_dfs[m] = df
                if df.empty:
                    metrics_empty.append(m)
                    log_error(f"  [METRIC] {m}: EMPTY — 0 rows returned")
                else:
                    metrics_ok.append(m)
                    log_info(f"  [METRIC] {m}: OK — {len(df)} rows, {len(df.columns)} devices")
            except Exception as e:
                metrics_failed.append(m)
                log_error(f"  [METRIC] {m}: FAILED — {type(e).__name__}: {e}")
                metric_dfs[m] = pd.DataFrame()

    log_info(f"Metric fetch summary: {len(metrics_ok)}/{len(METRICS)} succeeded, "
             f"{len(metrics_empty)} empty, {len(metrics_failed)} failed")
    if metrics_empty:
        log_error(f"  Empty metrics: {', '.join(metrics_empty)}")
    if metrics_failed:
        log_error(f"  Failed metrics: {', '.join(metrics_failed)}")

    # Abort guard: if power_total returned no data, InfluxDB was unreachable.
    # Writing health scores computed from empty DataFrames produces garbage — stop.
    if metric_dfs.get('power_total', pd.DataFrame()).empty:
        log_error(
            "ABORT: power_total fetch returned no data — InfluxDB unreachable "
            f"for window {start_dt.date()} → {end_dt.date()}. "
            "Skipping health score computation to avoid writing garbage data."
        )
        return pd.DataFrame(columns=health_columns)

    df_power          = metric_dfs['power_total']
    df_energy         = metric_dfs['energy_import']
    df_pf             = metric_dfs['power_factor_avg']
    df_unbalance      = metric_dfs['current_unbalance']
    df_l1_thd         = metric_dfs['current_l1_thd']
    df_l3_thd         = metric_dfs['current_l3_thd']
    df_apparent_power = metric_dfs['apparent_power_total']
    df_current_l1     = metric_dfs['current_l1']
    df_current_l2     = metric_dfs['current_l2']
    df_current_l3     = metric_dfs['current_l3']
    df_volts_l1_n     = metric_dfs['volts_l1_n']
    df_volts_l2_n     = metric_dfs['volts_l2_n']
    df_volts_l3_n     = metric_dfs['volts_l3_n']
    df_volts_l1_thd   = metric_dfs['volts_l1_thd']
    df_volts_l2_thd   = metric_dfs['volts_l2_thd']
    df_volts_l3_thd   = metric_dfs['volts_l3_thd']

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

    log_info(f"Computing health scores for {len(devices)} devices...")

    # Process each device — iterate ALL timestamps (not just latest)
    for idx, ahu_id in enumerate(devices):
        processed = idx + 1
        device_data_preview = predictions_df[predictions_df['ahu_id'] == ahu_id]
        ts_count = len(device_data_preview)
        has_power = not df_power.empty and ahu_id in df_power.columns
        has_pf = not df_pf.empty and ahu_id in df_pf.columns
        log_info(f"  [{processed:3d}/{len(devices)}] {ahu_id}: "
                 f"{ts_count} timestamps | "
                 f"power={'YES' if has_power else 'NO'} "
                 f"pf={'YES' if has_pf else 'NO'}")

        # Get ALL rows for this device sorted by timestamp
        device_data = predictions_df[predictions_df['ahu_id'] == ahu_id].sort_values('timestamp')

        if device_data.empty:
            continue

        # Per-AHU P95 of max-phase current
        p95_current = None
        try:
            currents = []
            for df_c in [df_current_l1, df_current_l2, df_current_l3]:
                if not df_c.empty and ahu_id in df_c.columns:
                    currents.append(df_c[ahu_id].dropna())
            if currents:
                max_current = pd.concat(currents, axis=1).max(axis=1).dropna()
                if len(max_current) >= 3:
                    p95_current = float(max_current.quantile(0.95))
        except Exception:
            p95_current = None

        for _, row in device_data.iterrows():
            ts = row['timestamp']
            level_val = str(row.get('level', 'Level 1'))
            
            # Get raw values from predictions for plotting
            hourly_delta_val = row.get('hourly_delta')
            predicted_delta_val = row.get('predicted_delta')
            energy_anomaly_raw = row.get('energy_anomaly')

            # Look up raw metric values at this timestamp using .asof()
            current_power = _asof_value(df_power, ahu_id, ts)
            current_pf = _asof_value(df_pf, ahu_id, ts)
            current_unbalance = _asof_value(df_unbalance, ahu_id, ts)
            current_energy = _asof_value(df_energy, ahu_id, ts)

            # New per-phase lookups
            apparent_power = _asof_value(df_apparent_power, ahu_id, ts)
            current_l1     = _asof_value(df_current_l1,     ahu_id, ts)
            current_l2     = _asof_value(df_current_l2,     ahu_id, ts)
            current_l3     = _asof_value(df_current_l3,     ahu_id, ts)
            volts_l1_n     = _asof_value(df_volts_l1_n,     ahu_id, ts)
            volts_l2_n     = _asof_value(df_volts_l2_n,     ahu_id, ts)
            volts_l3_n     = _asof_value(df_volts_l3_n,     ahu_id, ts)
            volts_l1_thd   = _asof_value(df_volts_l1_thd,   ahu_id, ts)
            volts_l2_thd   = _asof_value(df_volts_l2_thd,   ahu_id, ts)
            volts_l3_thd   = _asof_value(df_volts_l3_thd,   ahu_id, ts)
            # current_l1_thd and current_l3_thd already fetched as l1/l3 above
            current_l1_thd = _asof_value(df_l1_thd, ahu_id, ts)
            current_l3_thd = _asof_value(df_l3_thd, ahu_id, ts)

            # NEMA voltage imbalance (%)
            nema_voltage_imbalance = None
            if all(v is not None for v in [volts_l1_n, volts_l2_n, volts_l3_n]):
                v_avg = (volts_l1_n + volts_l2_n + volts_l3_n) / 3.0
                if v_avg > 0:
                    v_max_dev = max(abs(volts_l1_n - v_avg), abs(volts_l2_n - v_avg), abs(volts_l3_n - v_avg))
                    nema_voltage_imbalance = round(100.0 * v_max_dev / v_avg, 3)

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

            # Compute health score using energy_anomaly (from predictions)
            try:
                result = compute_ahu_health_score(
                    ahu_id=ahu_id,
                    energy_anomaly_val=energy_anomaly_raw,
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
                if current_pf < 0.85:
                    safety_flags.append('PF_CHRONIC_LOW')

            record = {
                'timestamp': ts,
                'ahu_id': ahu_id,
                'level': level_val,
                'health_index': result['health_index'],
                'tier': result['health_tier'],
                'energy_anomaly': round(risk_scores.get('energy_anomaly', 0) * 100, 2),
                'pf_degradation': round(risk_scores.get('power_factor', 0) * 100, 2),
                'phase_imbalance': round(risk_scores.get('phase_imbalance', 0) * 100, 2),
                'thd_drift': round(risk_scores.get('thd_drift', 0) * 100, 2),
                'overload': round(risk_scores.get('overload', 0) * 100, 2),
                'raw_power_total': current_power,
                'raw_energy_import': current_energy,
                # Raw values for energy anomaly score derivation
                'raw_hourly_delta': float(hourly_delta_val) if hourly_delta_val is not None else None,
                'raw_predicted_delta': float(predicted_delta_val) if predicted_delta_val is not None else None,
                'raw_energy_anomaly_raw': float(energy_anomaly_raw) if energy_anomaly_raw is not None else None,
                'raw_power_factor_avg': current_pf,
                'raw_current_unbalance': current_unbalance,
                'raw_composite_thd': current_composite_thd,
                'raw_apparent_power_total': apparent_power,
                'raw_current_l1': current_l1,
                'raw_current_l2': current_l2,
                'raw_current_l3': current_l3,
                'raw_volts_l1_n': volts_l1_n,
                'raw_volts_l2_n': volts_l2_n,
                'raw_volts_l3_n': volts_l3_n,
                'raw_current_l1_thd': current_l1_thd,
                'raw_current_l3_thd': current_l3_thd,
                'raw_volts_l1_thd': volts_l1_thd,
                'raw_volts_l2_thd': volts_l2_thd,
                'raw_volts_l3_thd': volts_l3_thd,
                'raw_nema_voltage_imbalance': nema_voltage_imbalance,
                'raw_p95_current': p95_current,
                'safety_flags': ';'.join(safety_flags) if safety_flags else ''
            }

            all_health_records.append(record)
            _stats['health_scores_computed'] += 1

        records_for_device = len([r for r in all_health_records if r['ahu_id'] == ahu_id])
        log_info(f"    → {ahu_id} done: {records_for_device} health records written")
        _stats['devices_processed'] += 1

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
    """Save health scores to CSV, overwriting any existing data."""
    log_info(f"Saving health scores to {HEALTH_FILE}...")
    if health_df.empty:
        log_error("No data to save!")
        return False
    os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)
    health_df.to_csv(HEALTH_FILE, index=False)
    log_info(f"Wrote {len(health_df)} records to health_all_levels.csv (overwrite)")
    return True


def save_hourly_scores(health_df: pd.DataFrame):
    """Save hourly health scores to CSV, overwriting any existing data."""
    log_info(f"Saving hourly health scores to {HOURLY_FILE}...")
    if health_df.empty:
        log_error("No data to save!")
        return False
    os.makedirs(os.path.dirname(HOURLY_FILE), exist_ok=True)
    health_df.to_csv(HOURLY_FILE, index=False)
    log_info(f"Wrote {len(health_df)} records to health_hourly.csv (overwrite)")
    return True


def main():
    """Main entry point - runs ETL pipeline once."""
    start_time = datetime.now()
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

    parser.add_argument(
        '--batch-days',
        type=int,
        default=30,
        help="Width of each InfluxDB time-fetch window in days (default: 30)"
    )

    args = parser.parse_args()

    if args.dry_run:
        log_info("=" * 70)
        log_info("DRY-RUN MODE - Showing plan only")
        log_info("=" * 70)
        log_info("Step 1: Prediction ETL")
        log_info(f"  - Query InfluxDB for earliest available data timestamp")
        log_info(f"  - Fetch energy_import in {args.batch_days}-day batches from earliest → now")
        log_info(f"  - Compute hourly_delta(t) = E(t) - E(t-1h)")
        log_info(f"  - Compute predicted_delta(t) = avg(δ(t−24h), δ(t−168h), δ(t−336h))")
        log_info(f"  - Compute energy_anomaly = hourly_delta(t) − predicted_delta(t)")
        log_info(f"  - Output: data/predictions.csv")
        log_info("")
        log_info("Step 2: Health Scoring ETL")
        log_info(f"  - Fetch all 16 raw metrics in {args.batch_days}-day batches")
        log_info(f"  - Compute FAIR health scores for all devices")
        log_info(f"  - Apply safety flags for engineering audit")
        log_info(f"  - Output: data/health_all_levels.csv + data/health_hourly.csv")
        log_info("")
        devices = get_all_devices()
        log_info(f"Estimated devices to process: {len(devices)} AHUs across all levels")
        log_info("")
        return

    # Start ETL
    run_start = datetime.now()

    log_info("=" * 70)
    log_info("WACH Insight Historical ETL Pipeline")
    log_info("=" * 70)
    log_info(f"Started at: {run_start.isoformat()}")
    log_info(f"Level filter: {args.level}")
    log_info(f"Batch window: {args.batch_days} days")

    devices = get_all_devices()
    if args.level != 'all':
        level_num = int(args.level)
        devices = get_devices_by_level(level_num)

    log_info(f"Devices to process: {len(devices)} AHUs")

    # Discover the earliest available data timestamp in InfluxDB
    from core.influx_client import get_earliest_data_timestamp
    log_info("")
    log_info("Querying InfluxDB for earliest available data timestamp...")
    earliest_ts = get_earliest_data_timestamp()
    if earliest_ts is None:
        log_info("Could not determine earliest timestamp; defaulting to 365 days ago")
        earliest_ts = datetime.now(timezone.utc) - timedelta(days=365)
    else:
        log_info(f"Earliest data found: {earliest_ts.isoformat()}")

    end_ts = datetime.now(timezone.utc)
    total_days = (end_ts - earliest_ts).days
    log_info(f"Full history span: {total_days} days "
             f"({earliest_ts.date()} → {end_ts.date()})")

    # Step 1: Prediction ETL
    log_info("")
    log_info("Phase 1: Running Prediction ETL")
    log_info("-" * 50)

    predictions_df = run_prediction_etl_historical(
        start_time=earliest_ts,
        end_time=end_ts,
        devices=devices,
        batch_days=args.batch_days,
    )

    if predictions_df.empty:
        log_error("Prediction ETL produced no data!")
    else:
        save_predictions(predictions_df)

    # Step 2: Health Scoring ETL
    log_info("")
    log_info("Phase 2: Running Health Scoring ETL")
    log_info("-" * 50)

    health_df = run_health_etl_historical(
        predictions_df,
        start_dt=earliest_ts,
        end_dt=end_ts,
        batch_days=args.batch_days,
    )

    if health_df.empty:
        log_error("Health Scoring ETL produced no data!")
    else:
        save_health_scores(health_df)
        save_hourly_scores(health_df)

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
