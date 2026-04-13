"""
db_reader.py
────────────
DuckDB-backed replacements for all csv_reader functions used by API routes.

Drop-in API:
  get_health_index_series(level, device_id, time_range) -> list[dict]
  get_score_breakdown(level, time_range)                -> list[dict]
  get_raw_score_relationship(device_id, time_range)     -> dict
  get_dataframe(level, time_range)                      -> pd.DataFrame

`time_range` values: "24h" | "7d" | "30d"
DuckDB `level` column is INTEGER (1-11), not "Level N" string.
"""

from __future__ import annotations

import os
import threading
from datetime import timedelta
from typing import Optional

import pandas as pd

from core.healthdb import HealthDB

# ---------------------------------------------------------------------------
# Inlined from csv_reader (no CSV I/O — pure constants and helpers)
# ---------------------------------------------------------------------------

SCORE_COLUMNS = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload', 'health_index']

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
    """Collapse hourly rows into one representative row per device per calendar day."""
    if df.empty:
        return df
    df = df.copy()
    df['_date'] = pd.to_datetime(df['timestamp'], utc=True).dt.normalize()
    group_keys = ['ahu_id', 'level', '_date']
    # is_on is a derived bool — exclude from generic averaging; caller restores it
    _skip = set(group_keys + ['timestamp', 'is_on'])
    numeric_cols = [c for c in df.select_dtypes(include='number').columns if c not in _skip]
    text_cols = [c for c in df.columns if c not in _skip and c not in numeric_cols]
    agg: dict = {c: 'mean' for c in numeric_cols}
    agg.update({c: 'last' for c in text_cols})
    daily = df.groupby(group_keys).agg(agg).reset_index()
    return daily.rename(columns={'_date': 'timestamp'})

# ---------------------------------------------------------------------------

# Override-able path for testing (monkeypatched in tests)
_DB_PATH: Optional[str] = None  # None → HealthDB uses its default path

_RANGE_DELTA: dict[str, timedelta] = {
    "24h": timedelta(hours=24),
    "7d":  timedelta(days=7),
    "30d": timedelta(days=30),
}

# Singleton cache: avoids creating multiple HealthDB instances (and concurrent
# write connections) on every request. Keyed by path so test monkeypatching works.
_DB_INSTANCES: dict = {}
_DB_LOCK = threading.Lock()


def _db() -> HealthDB:
    key = _DB_PATH
    if key not in _DB_INSTANCES:
        with _DB_LOCK:
            if key not in _DB_INSTANCES:  # double-checked
                _DB_INSTANCES[key] = HealthDB(_DB_PATH) if _DB_PATH else HealthDB()
    return _DB_INSTANCES[key]


def _get_df(
    level: Optional[int] = None,
    ahu_ids: Optional[list] = None,
    time_range: str = "7d",
) -> pd.DataFrame:
    """
    Fetch rows from DuckDB, filtered by level / ahu_ids / time window.
    For 30d, collapses hourly rows to daily averages (same as csv_reader).
    For "all", returns entire database from earliest to latest timestamp.
    """
    db = _db()
    latest_ts = db.get_latest_timestamp()
    if latest_ts is None:
        return pd.DataFrame()

    # Calculate time window from latest_ts working backwards
    # "24h" → last 24 hours from latest_ts
    # "7d"  → last 7 days from latest_ts
    # "30d" → last 30 days from latest_ts
    # "all" → entire database from earliest to latest
    if time_range == "all":
        start = None
    else:
        delta = _RANGE_DELTA.get(time_range, _RANGE_DELTA["7d"])
        start = (latest_ts - delta).isoformat()

    # Resolve level to its authoritative device list so cross-level devices
    # (e.g. e0212 stored with level=2 but belonging to Level 1) are included.
    # Only apply when no explicit ahu_ids are provided.
    db_level = None
    effective_ahu_ids = ahu_ids
    if level is not None and not ahu_ids:
        from models.schemas import AHU_LEVEL_CONFIG
        effective_ahu_ids = AHU_LEVEL_CONFIG.get(level, {}).get("device_ids")

    # Fetch all rows in the time window (no limit; we need complete data for aggregation)
    df = db.get_time_range(level=db_level, ahu_ids=effective_ahu_ids, start=start, limit=None)
    if df.empty:
        return df

    # Normalize to UTC so .isoformat() always emits +00:00 (matches csv_reader behavior)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Derive is_on BEFORE any resampling so the flag is available row-level
    current_cols = ["raw_current_l1", "raw_current_l2", "raw_current_l3"]
    if all(c in df.columns for c in current_cols):
        df["is_on"] = (
            (df["raw_current_l1"].fillna(0) >= 2)
            | (df["raw_current_l2"].fillna(0) >= 2)
            | (df["raw_current_l3"].fillna(0) >= 2)
        )

    if time_range == "30d":
        if "is_on" in df.columns:
            # Save true current status per device (most recent raw row) before filtering
            latest_status: pd.Series = df.groupby("ahu_id")["is_on"].last()
            # Daily averages should only reflect on-time hours
            df_active = df[df["is_on"]]
            df = _resample_to_daily(df_active if not df_active.empty else df)
            # Restore accurate current on/off per device after resample
            df["is_on"] = df["ahu_id"].map(latest_status)
        else:
            df = _resample_to_daily(df)

    return df.sort_values("timestamp")


# ── Public API ─────────────────────────────────────────────────────────────────

def get_level_devices(level: int) -> list[dict]:
    """
    Return [{id, label, department, area}] for a level from the static AHU config.
    No DuckDB required — always fast and reliable.
    """
    from models.schemas import AHU_LEVEL_CONFIG
    device_ids = AHU_LEVEL_CONFIG.get(level, {}).get("device_ids", [])
    labels = _load_ahu_labels()
    return [
        {
            "id": did,
            "label": labels.get(did, {}).get("label", ""),
            "department": labels.get(did, {}).get("department", ""),
            "area": labels.get(did, {}).get("area", ""),
        }
        for did in device_ids
    ]


def get_health_index_series(
    level: int,
    device_id: Optional[str],
    time_range: str,
) -> list[dict]:
    """Returns [{id, name, label, department, area, data: [{timestamp, value}]}]"""
    ahu_ids = [device_id] if device_id else None
    df = _get_df(level=level, ahu_ids=ahu_ids, time_range=time_range)
    if df.empty or "health_index" not in df.columns:
        return []

    labels = _load_ahu_labels()
    result = []
    for ahu_id, group in df.groupby("ahu_id"):
        meta = labels.get(str(ahu_id), {})
        # Include all data points (both on and off) so chart can grey out off-time sections
        entry: dict = {
            "id": ahu_id,
            "name": ahu_id,
            "label": meta.get("label", ""),
            "department": meta.get("department", ""),
            "area": meta.get("area", ""),
            "data": [
                {
                    "timestamp": row["timestamp"].isoformat(),
                    "value": round(float(row["health_index"]), 2),
                    "is_on": bool(row["is_on"]) if "is_on" in group.columns else True
                }
                for _, row in group.iterrows()
                if pd.notna(row["health_index"])
            ],
        }
        # is_on reflects the most recent raw reading (before any filtering)
        if "is_on" in group.columns:
            entry["is_on"] = bool(group["is_on"].iloc[-1])
        result.append(entry)
    return result


def get_score_breakdown(level: int, time_range: str) -> list[dict]:
    """Returns [{id, name, label, department, scores: {col: {current, trend, data}}}]"""
    df = _get_df(level=level, time_range=time_range)
    if df.empty:
        return []

    labels = _load_ahu_labels()
    result = []
    for ahu_id, group in df.groupby("ahu_id"):
        # Only compute scores from on-time rows; fall back to all rows if none qualify
        if "is_on" in group.columns:
            active = group[group["is_on"]]
            score_group = active if not active.empty else group
        else:
            score_group = group
        scores = {}
        for col in SCORE_COLUMNS:
            if col not in score_group.columns:
                continue
            series = score_group[["timestamp", col]].dropna(subset=[col])
            if series.empty:
                continue
            values = series[col].astype(float)
            data_points = [
                {"timestamp": row["timestamp"].isoformat(), "value": round(float(row[col]), 2)}
                for _, row in series.iterrows()
            ]
            current = round(float(values.iloc[-1]), 2)
            trend = round(float(values.iloc[-1] - values.iloc[0]), 2) if len(values) > 1 else 0.0
            scores[col] = {"current": current, "trend": trend, "data": data_points}
        meta = labels.get(str(ahu_id), {})
        entry: dict = {
            "id": ahu_id,
            "name": ahu_id,
            "label": meta.get("label", ""),
            "department": meta.get("department", ""),
            "scores": scores,
        }
        if "is_on" in group.columns:
            entry["is_on"] = bool(group["is_on"].iloc[-1])
        result.append(entry)
    return result


def get_raw_score_relationship(device_id: str, time_range: str) -> dict:
    """Returns {score_name: {series, scoreData, referenceLines}}"""
    df = _get_df(ahu_ids=[device_id], time_range=time_range)
    if df.empty:
        return {}

    REFERENCE_LINES = {
        "thd_drift": [{"value": 5.0, "label": "IEEE 519: 5%", "color": "#FFB020"}],
    }

    result = {}
    for score_col, series_defs in SCORE_SERIES_MAP.items():
        if score_col not in df.columns:
            continue
        score_sub = df[["timestamp", score_col]].dropna(subset=[score_col])
        if score_sub.empty:
            continue
        score_data = [
            {"timestamp": r["timestamp"].isoformat(), "value": round(float(r[score_col]), 2)}
            for _, r in score_sub.iterrows()
        ]
        series_out = []
        for s in series_defs:
            col = s["col"]
            if col not in df.columns:
                continue
            sub = df[["timestamp", col]].dropna(subset=[col])
            if sub.empty:
                continue
            entry = {
                "col": col,
                "label": s["label"],
                "unit": s["unit"],
                "style": s["style"],
                "data": [
                    {"timestamp": r["timestamp"].isoformat(), "value": float(r[col])}
                    for _, r in sub.iterrows()
                ],
            }
            if "group" in s:
                entry["group"] = s["group"]
            series_out.append(entry)
        if not series_out:
            continue
        result[score_col] = {
            "series": series_out,
            "scoreData": score_data,
            "referenceLines": REFERENCE_LINES.get(score_col, []),
        }
    return result


def _get_raw_rows(ahu_id: str, time_range: str) -> pd.DataFrame:
    """
    Fetch raw (non-resampled) rows for a single AHU, bypassing the 30d daily
    aggregation in _get_df so that per-row is_on transitions are preserved.
    """
    db = _db()
    latest_ts = db.get_latest_timestamp()
    if latest_ts is None:
        return pd.DataFrame()

    delta = _RANGE_DELTA.get(time_range, _RANGE_DELTA["7d"])
    start = (latest_ts - delta).isoformat()

    df = db.get_time_range(level=None, ahu_ids=[ahu_id], start=start, limit=None)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    current_cols = ["raw_current_l1", "raw_current_l2", "raw_current_l3"]
    if all(c in df.columns for c in current_cols):
        df["is_on"] = (
            (df["raw_current_l1"].fillna(0) >= 2)
            | (df["raw_current_l2"].fillna(0) >= 2)
            | (df["raw_current_l3"].fillna(0) >= 2)
        )

    return df.sort_values("timestamp").reset_index(drop=True)


def get_off_periods(ahu_id: str, time_range: str) -> list[dict]:
    """
    Returns contiguous off-period intervals for a single AHU.
    Each dict has {"start": <iso str>, "end": <iso str>}.
    """
    from models.schemas import ALLOWED_DEVICES
    if ahu_id not in ALLOWED_DEVICES:
        return []

    rows = _get_raw_rows(ahu_id, time_range)
    if rows.empty or "is_on" not in rows.columns:
        return []

    # rows is already filtered to ahu_id and sorted by _get_raw_rows
    periods: list[dict] = []
    in_off = False
    start_ts = None

    for _, row in rows.iterrows():
        if not row["is_on"] and not in_off:
            in_off = True
            start_ts = row["timestamp"]
        elif row["is_on"] and in_off:
            in_off = False
            periods.append({
                "start": start_ts.isoformat(),
                "end": row["timestamp"].isoformat(),
            })

    # Close an open off-period at the last data point
    if in_off and start_ts is not None:
        periods.append({
            "start": start_ts.isoformat(),
            "end": rows["timestamp"].iloc[-1].isoformat(),
        })

    return periods


def get_dataframe(
    level: Optional[int] = None,
    time_range: str = "7d",
) -> pd.DataFrame:
    """
    Returns a DataFrame of health records from DuckDB.
    Equivalent to csv_reader._load_csv() + _filter_time_range() combined.

    IMPORTANT: `level` column is INTEGER (1-11), not "Level N" string.
    Callers that previously did df[df['level'] == 'Level N'] must use
    df[df['level'] == N] (integer).
    """
    return _get_df(level=level, time_range=time_range)
