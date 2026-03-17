"""
csv_reader.py
─────────────
Reads health_all_levels.csv and formats data for API endpoints.

CSV columns used:
  timestamp, ahu_id, level, health_index, tier,
  energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload,
  raw_power_total, raw_energy_import, raw_power_factor_avg,
  raw_current_unbalance, raw_composite_thd
"""

import os
import pandas as pd
from datetime import datetime, timedelta, timezone

CSV_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'health_all_levels.csv'
)

HOURLY_CSV_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'health_hourly.csv'
)

DAILY_CSV_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'health_daily.csv'
)

SCORE_COLUMNS = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload', 'health_index']

# Score → (raw column, unit)
# Note: For energy_anomaly, the raw metric is hourly_delta (energy consumed in one hour)
#       not cumulative energy_import. The score derivation plot shows hourly_delta vs energy_anomaly.
SCORE_RAW_MAP = {
    'energy_anomaly':  ('raw_hourly_delta',      'kWh'),
    'pf_degradation':  ('raw_power_factor_avg',   ''),
    'phase_imbalance': ('raw_current_unbalance',  '%'),
    'thd_drift':       ('raw_composite_thd',      '%'),
    'overload':        ('raw_power_total',         'kW'),
}

# Debug logging flag - set to True for detailed diagnostics
DEBUG_MODE = os.getenv('CSV_DEBUG', 'false').lower() == 'true'


def _debug_csv_state(time_range: str) -> dict:
    """Debug helper to log CSV state for diagnostics."""
    if not DEBUG_MODE:
        return {}
    df = _load_csv(time_range=time_range)
    return {
        'path': os.path.abspath(CSV_PATH),
        'row_count': len(df),
        'columns': list(df.columns) if not df.empty else [],
        'time_range': time_range,
    }

# Time range window for filtering CSV data
# For hourly data: exact 24 hours (no interpolation needed)
# For daily data: range with matching number of days
RANGE_DELTA = {
    '24h': timedelta(hours=24),  # hourly data — exact 24 hours
    '7d':  timedelta(days=7),
    '30d': timedelta(days=30),
}

_AHU_LABELS: dict[str, dict] = {}


def _load_ahu_labels() -> dict[str, dict]:
    """Load docs/ahu_relationships.tsv → {device_id: {label, department, area}}."""
    global _AHU_LABELS
    if _AHU_LABELS:
        return _AHU_LABELS
    tsv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'ahu_relationships.tsv')
    if not os.path.exists(tsv_path):
        return {}
    df = pd.read_csv(tsv_path, sep='\t')
    for _, row in df.iterrows():
        device_id = str(row.get('device_id', '')).strip()
        if device_id:
            _AHU_LABELS[device_id] = {
                'label': str(row.get('AHU Label', '')).strip(),
                'department': str(row.get('Department Name', '')).strip(),
                'area': str(row.get('Area Name', '')).strip(),
            }
    return _AHU_LABELS


def _resample_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse hourly rows into one representative row per device per calendar day.

    Strategy: group by (ahu_id, level, date) and take the MEAN of all numeric
    columns. Text columns (tier, safety_flags) take the last value of the day.
    This produces the same schema as health_daily.csv so downstream functions
    need no changes.
    """
    if df.empty:
        return df

    df = df.copy()
    df['_date'] = pd.to_datetime(df['timestamp'], utc=True).dt.normalize()

    group_keys = ['ahu_id', 'level', '_date']
    # Identify numeric vs text columns (excluding group keys and timestamp)
    numeric_cols = [
        c for c in df.select_dtypes(include='number').columns
        if c not in group_keys
    ]
    text_cols = [
        c for c in df.columns
        if c not in group_keys + ['timestamp'] + numeric_cols
    ]

    agg: dict = {c: 'mean' for c in numeric_cols}
    agg.update({c: 'last' for c in text_cols})

    daily = df.groupby(group_keys).agg(agg).reset_index()
    daily = daily.rename(columns={'_date': 'timestamp'})
    return daily


def _load_csv(time_range: str = "7d") -> pd.DataFrame:
    """
    Load the appropriate CSV for the requested time range.

    24h → health_hourly.csv  (~24 hourly rows per device)
    7d  → health_hourly.csv  (~168 hourly rows per device)
    30d → health_hourly.csv resampled to daily (~30 rows per device,
          using the most recently generated data)

    Falls back to health_daily.csv / health_all_levels.csv if hourly CSV
    is unavailable.
    """
    hourly_ok = os.path.exists(HOURLY_CSV_PATH) and os.path.getsize(HOURLY_CSV_PATH) > 0

    if time_range in ("24h", "7d"):
        path = HOURLY_CSV_PATH if hourly_ok else (
            DAILY_CSV_PATH if os.path.exists(DAILY_CSV_PATH) else CSV_PATH
        )
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return pd.DataFrame()
        return pd.read_csv(path, parse_dates=['timestamp'])

    # 30d — load hourly and resample to daily for the most current data
    if hourly_ok:
        df = pd.read_csv(HOURLY_CSV_PATH, parse_dates=['timestamp'])
        return _resample_to_daily(df)

    # fallback to pre-built daily CSV
    path = DAILY_CSV_PATH if os.path.exists(DAILY_CSV_PATH) else CSV_PATH
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=['timestamp'])


def _filter_time_range(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    delta = RANGE_DELTA.get(time_range, RANGE_DELTA['7d'])
    ts = pd.to_datetime(df['timestamp'], utc=True)
    # Use the latest available timestamp as the reference so that ranges
    # always return data even when the CSV hasn't been regenerated recently.
    reference = ts.max() if not ts.empty else pd.Timestamp.now(tz='UTC')
    cutoff = reference - delta
    return df[ts >= cutoff]


def get_health_index_series(level: int, device_id: str | None, time_range: str) -> list[dict]:
    """
    Returns [{id, name, label, department, area, data: [{timestamp, value}]}]
    for all devices on the level (or just device_id if specified).
    """
    df = _load_csv(time_range=time_range)
    if df.empty:
        return []
    df = df[df['level'] == f"Level {level}"]
    if device_id:
        df = df[df['ahu_id'] == device_id]
    df = _filter_time_range(df, time_range).sort_values('timestamp')

    labels = _load_ahu_labels()
    result = []
    for ahu_id, group in df.groupby('ahu_id'):
        meta = labels.get(str(ahu_id), {})
        result.append({
            'id': ahu_id,
            'name': ahu_id,
            'label': meta.get('label', ''),
            'department': meta.get('department', ''),
            'area': meta.get('area', ''),
            'data': [
                {'timestamp': row['timestamp'].isoformat(), 'value': round(float(row['health_index']), 2)}
                for _, row in group.iterrows()
                if pd.notna(row['health_index'])
            ],
        })
    return result


def get_score_breakdown(level: int, time_range: str) -> list[dict]:
    """
    Returns [{id, name, scores: {energy_anomaly: {current, trend, data}, ...}}]
    """
    df = _load_csv(time_range=time_range)
    if df.empty:
        return []
    df = df[df['level'] == f"Level {level}"]
    df = _filter_time_range(df, time_range).sort_values('timestamp')

    labels = _load_ahu_labels()
    result = []
    for ahu_id, group in df.groupby('ahu_id'):
        scores = {}
        for col in SCORE_COLUMNS:
            if col not in group.columns:
                continue
            series = group[['timestamp', col]].dropna(subset=[col])
            if series.empty:
                continue
            values = series[col].astype(float)
            data_points = [
                {'timestamp': row['timestamp'].isoformat(), 'value': round(float(row[col]), 2)}
                for _, row in series.iterrows()
            ]
            current = round(float(values.iloc[-1]), 2)
            trend = round(float(values.iloc[-1] - values.iloc[0]), 2) if len(values) > 1 else 0.0
            scores[col] = {'current': current, 'trend': trend, 'data': data_points}
        meta = labels.get(str(ahu_id), {})
        result.append({
            'id': ahu_id,
            'name': ahu_id,
            'label': meta.get('label', ''),
            'department': meta.get('department', ''),
            'scores': scores,
        })
    return result


def get_raw_score_relationship(device_id: str, time_range: str) -> dict:
    """
    Returns {score_name: {rawMetric, rawUnit, rawData, predictedData, scoreData}}

    For energy_anomaly:
      - rawData: hourly_delta (raw energy consumed in the hour)
      - predictedData: predicted_delta (expected consumption based on historical averages)
      - scoreData: energy_anomaly score (computed deviation)

    For other scores, predictedData is None.

    Debug output logged when CSV_DEBUG=true environment variable is set.
    """
    df = _load_csv(time_range=time_range)
    if df.empty:
        if DEBUG_MODE:
            print(f"[DEBUG] get_raw_score_relationship: CSV empty for time_range={time_range}")
        return {}
    
    df = df[df['ahu_id'] == device_id]
    if DEBUG_MODE:
        print(f"[DEBUG] After device filter: {len(df)} rows")
    
    df = _filter_time_range(df, time_range).sort_values('timestamp')
    if DEBUG_MODE:
        print(f"[DEBUG] After time filter: {len(df)} rows")
    
    if df.empty:
        if DEBUG_MODE:
            print(f"[DEBUG] No data after filtering: device={device_id}, time_range={time_range}")
        return {}

    result = {}
    for score_col, (raw_col, raw_unit) in SCORE_RAW_MAP.items():
        # Skip if either column is missing
        if score_col not in df.columns:
            print(f"[WARN] Score column '{score_col}' missing from CSV (available: {list(df.columns)[:10]}...)")
            continue
        if raw_col not in df.columns:
            print(f"[WARN] Raw column '{raw_col}' missing from CSV")
            continue
        
        # Select only required columns
        sub = df[['timestamp', score_col, raw_col]].copy()

        # For energy_anomaly, also include predicted_delta for the third line
        predicted_data = None
        if score_col == 'energy_anomaly' and 'raw_predicted_delta' in df.columns:
            pred_sub = df[['timestamp', 'raw_predicted_delta']].copy()
            pred_sub = pred_sub.dropna(subset=['raw_predicted_delta'])
            if not pred_sub.empty:
                # Merge with score data on timestamp
                merged = sub[['timestamp']].merge(
                    pred_sub, on='timestamp', how='left'
                )
                predicted_data = [
                    {'timestamp': r['timestamp'].isoformat(), 'value': float(r['raw_predicted_delta'])}
                    for _, r in merged.iterrows()
                ]
        
        if DEBUG_MODE:
            print(f"[DEBUG] {score_col}: before dropna={len(sub)}")
        
        # Drop rows where either score or raw value is NaN
        sub = sub.dropna(subset=[score_col, raw_col])
        
        if sub.empty:
            print(f"[WARN] No valid pairs for {score_col}/{raw_col} after dropna")
            continue
        
        # Sort by timestamp (explicitly)
        sub = sub.sort_values('timestamp')
        
        result[score_col] = {
            'rawMetric': raw_col,
            'rawUnit': raw_unit,
            'rawData': [
                {'timestamp': r['timestamp'].isoformat(), 'value': float(r[raw_col])}
                for _, r in sub.iterrows()
            ],
            'predictedData': predicted_data,
            'scoreData': [
                {'timestamp': r['timestamp'].isoformat(), 'value': float(r[score_col])}
                for _, r in sub.iterrows()
            ],
        }
        
        if DEBUG_MODE:
            print(f"[DEBUG] {score_col}: after dropna={len(result[score_col]['rawData'])}")
    
    if DEBUG_MODE:
        print(f"[DEBUG] get_raw_score_relationship returned {len(result)} scores")
    return result
