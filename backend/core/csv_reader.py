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

SCORE_COLUMNS = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload']

# Score → (raw column, unit)
SCORE_RAW_MAP = {
    'energy_anomaly':  ('raw_energy_import',     'kWh'),
    'pf_degradation':  ('raw_power_factor_avg',   ''),
    'phase_imbalance': ('raw_current_unbalance',  '%'),
    'thd_drift':       ('raw_composite_thd',      '%'),
    'overload':        ('raw_power_total',         'kW'),
}

RANGE_DELTA = {
    '24h': timedelta(hours=24),
    '7d':  timedelta(days=7),
    '30d': timedelta(days=30),
}


def _load_csv() -> pd.DataFrame:
    """Load CSV; return empty DataFrame if missing."""
    if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0:
        return pd.DataFrame()
    return pd.read_csv(CSV_PATH, parse_dates=['timestamp'])


def _filter_time_range(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    delta = RANGE_DELTA.get(time_range, RANGE_DELTA['7d'])
    cutoff = datetime.now(timezone.utc) - delta
    ts = pd.to_datetime(df['timestamp'], utc=True)
    return df[ts >= cutoff]


def _ahu_name(device_id: str, level: int) -> str:
    return f"AHU-L{level}-{device_id[-2:]}"


def get_health_index_series(level: int, device_id: str | None, time_range: str) -> list[dict]:
    """
    Returns [{device: {id, name, level}, data: [{timestamp, value}]}]
    for all devices on the level (or just device_id if specified).
    """
    df = _load_csv()
    if df.empty:
        return []
    df = df[df['level'] == f"Level {level}"]
    if device_id:
        df = df[df['ahu_id'] == device_id]
    df = _filter_time_range(df, time_range).sort_values('timestamp')

    result = []
    for ahu_id, group in df.groupby('ahu_id'):
        result.append({
            'id': ahu_id,
            'name': _ahu_name(ahu_id, level),
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
    df = _load_csv()
    if df.empty:
        return []
    df = df[df['level'] == f"Level {level}"]
    df = _filter_time_range(df, time_range).sort_values('timestamp')

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
        result.append({'id': ahu_id, 'name': _ahu_name(ahu_id, level), 'scores': scores})
    return result


def get_raw_score_relationship(device_id: str, time_range: str) -> dict:
    """
    Returns {score_name: {rawMetric, rawUnit, rawData, scoreData}}
    """
    df = _load_csv()
    if df.empty:
        return {}
    df = df[df['ahu_id'] == device_id]
    df = _filter_time_range(df, time_range).sort_values('timestamp')
    if df.empty:
        return {}

    result = {}
    for score_col, (raw_col, raw_unit) in SCORE_RAW_MAP.items():
        if score_col not in df.columns or raw_col not in df.columns:
            continue
        sub = df[['timestamp', score_col, raw_col]].dropna(subset=[score_col, raw_col])
        if sub.empty:
            continue
        result[score_col] = {
            'rawMetric': raw_col,
            'rawUnit': raw_unit,
            'rawData': [
                {'timestamp': r['timestamp'].isoformat(), 'value': round(float(r[raw_col]), 4)}
                for _, r in sub.iterrows()
            ],
            'scoreData': [
                {'timestamp': r['timestamp'].isoformat(), 'value': round(float(r[score_col]), 2)}
                for _, r in sub.iterrows()
            ],
        }
    return result
