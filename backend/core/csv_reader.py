"""
csv_reader.py
─────────────
Reads health_all_levels.csv and formats data for API endpoints.

CSV columns used:
  timestamp, ahu_id, level, health_index, tier,
  energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload,
  raw_power_total, raw_energy_import, raw_power_factor_avg,
  raw_current_unbalance, raw_composite_thd,
  raw_hourly_delta, raw_predicted_delta,
  raw_volts_l1_n, raw_volts_l2_n, raw_volts_l3_n,
  raw_current_l1, raw_current_l2, raw_current_l3,
  raw_nema_voltage_imbalance,
  raw_current_l1_thd, raw_current_l3_thd,
  raw_volts_l1_thd, raw_volts_l2_thd, raw_volts_l3_thd,
  raw_apparent_power_total, raw_p95_current
"""

from __future__ import annotations

import os
import time
import pandas as pd
from datetime import datetime, timedelta, timezone

# In-memory CSV cache: path → (DataFrame, loaded_at_monotonic)
_CSV_CACHE: dict[str, tuple[pd.DataFrame, float]] = {}
_CSV_CACHE_TTL = 300  # seconds (5 minutes)


def _read_csv_cached(path: str) -> pd.DataFrame:
    """Read a CSV with a 5-minute in-memory cache to avoid repeated 156MB disk reads."""
    now = time.monotonic()
    cached = _CSV_CACHE.get(path)
    if cached is not None:
        df, loaded_at = cached
        if now - loaded_at < _CSV_CACHE_TTL:
            return df
    df = pd.read_csv(path, parse_dates=['timestamp'])
    _CSV_CACHE[path] = (df, now)
    return df

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

# Score → list of {col, label, unit, style, group?}
# style: "solid" | "dashed" | "bold" | "ref"
# group: optional grouping hint for the frontend
SCORE_SERIES_MAP: dict[str, list[dict]] = {
    "energy_anomaly": [
        {"col": "raw_hourly_delta",    "label": "Actual δ kWh",    "unit": "kWh", "style": "solid"},
        {"col": "raw_predicted_delta", "label": "Predicted δ kWh", "unit": "kWh", "style": "dashed"},
    ],
    "pf_degradation": [
        {"col": "raw_power_total",          "label": "Real Power",     "unit": "kW",  "style": "solid"},
        {"col": "raw_apparent_power_total", "label": "Apparent Power", "unit": "kVA", "style": "dashed"},
    ],
    "phase_imbalance": [
        {"col": "raw_volts_l1_n", "label": "V L1", "unit": "V", "style": "solid", "group": "voltage"},
        {"col": "raw_volts_l2_n", "label": "V L2", "unit": "V", "style": "solid", "group": "voltage"},
        {"col": "raw_volts_l3_n", "label": "V L3", "unit": "V", "style": "solid", "group": "voltage"},
        {"col": "raw_current_l1", "label": "I L1", "unit": "A", "style": "solid", "group": "current"},
        {"col": "raw_current_l2", "label": "I L2", "unit": "A", "style": "solid", "group": "current"},
        {"col": "raw_current_l3", "label": "I L3", "unit": "A", "style": "solid", "group": "current"},
        {"col": "raw_nema_voltage_imbalance", "label": "NEMA V Imbalance", "unit": "%", "style": "bold", "group": "imbalance"},
    ],
    "thd_drift": [
        {"col": "raw_current_l1_thd", "label": "I L1 THD", "unit": "%", "style": "solid",  "group": "current_thd"},
        {"col": "raw_current_l3_thd", "label": "I L3 THD", "unit": "%", "style": "solid",  "group": "current_thd"},
        {"col": "raw_volts_l1_thd",   "label": "V L1 THD", "unit": "%", "style": "dashed", "group": "voltage_thd"},
        {"col": "raw_volts_l2_thd",   "label": "V L2 THD", "unit": "%", "style": "dashed", "group": "voltage_thd"},
        {"col": "raw_volts_l3_thd",   "label": "V L3 THD", "unit": "%", "style": "dashed", "group": "voltage_thd"},
    ],
    "overload": [
        {"col": "raw_current_l1", "label": "I L1",     "unit": "A", "style": "solid", "group": "current"},
        {"col": "raw_current_l2", "label": "I L2",     "unit": "A", "style": "solid", "group": "current"},
        {"col": "raw_current_l3", "label": "I L3",     "unit": "A", "style": "solid", "group": "current"},
        {"col": "raw_p95_current","label": "P95 Peak", "unit": "A", "style": "ref",   "group": "threshold"},
    ],
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
        return _read_csv_cached(path)

    # 30d — load hourly and resample to daily for the most current data
    if hourly_ok:
        df = _read_csv_cached(HOURLY_CSV_PATH)
        return _resample_to_daily(df)

    # fallback to pre-built daily CSV
    path = DAILY_CSV_PATH if os.path.exists(DAILY_CSV_PATH) else CSV_PATH
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame()
    return _read_csv_cached(path)


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
    Returns {score_name: {series: [...], scoreData: [...], referenceLines: [...]}}

    Each series entry: {col, label, unit, style, group?, data: [{timestamp, value}]}
    referenceLines: optional [{value, label, color}] for chart annotations

    Score values in the CSV are stored in the 0-100 range and are returned as-is.
    """
    df = _load_csv(time_range=time_range)
    if df.empty:
        return {}

    df = df[df['ahu_id'] == device_id]
    df = _filter_time_range(df, time_range).sort_values('timestamp')

    if df.empty:
        return {}

    # Reference lines per score (static thresholds)
    REFERENCE_LINES = {
        "thd_drift": [{"value": 5.0, "label": "IEEE 519: 5%", "color": "#FFB020"}],
    }

    result = {}
    for score_col, series_defs in SCORE_SERIES_MAP.items():
        if score_col not in df.columns:
            continue

        # Build score time series (values already in 0-100 range)
        score_sub = df[['timestamp', score_col]].dropna(subset=[score_col])
        if score_sub.empty:
            continue
        score_data = [
            {'timestamp': r['timestamp'].isoformat(), 'value': round(float(r[score_col]), 2)}
            for _, r in score_sub.iterrows()
        ]

        # Build each raw series
        series_out = []
        for s in series_defs:
            col = s["col"]
            if col not in df.columns:
                # Column not yet in CSV (e.g. new ETL columns not yet run)
                continue
            sub = df[['timestamp', col]].dropna(subset=[col])
            if sub.empty:
                continue
            series_entry = {
                "col": col,
                "label": s["label"],
                "unit": s["unit"],
                "style": s["style"],
                "data": [
                    {'timestamp': r['timestamp'].isoformat(), 'value': float(r[col])}
                    for _, r in sub.iterrows()
                ],
            }
            if "group" in s:
                series_entry["group"] = s["group"]
            series_out.append(series_entry)

        if not series_out:
            # Fallback: skip score if no raw series data at all
            continue

        result[score_col] = {
            "series": series_out,
            "scoreData": score_data,
            "referenceLines": REFERENCE_LINES.get(score_col, []),
        }

    return result
