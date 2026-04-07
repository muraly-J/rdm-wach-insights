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
    numeric_cols = [c for c in df.select_dtypes(include='number').columns if c not in group_keys]
    text_cols = [c for c in df.columns if c not in group_keys + ['timestamp'] + numeric_cols]
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


def _db() -> HealthDB:
    return HealthDB(_DB_PATH) if _DB_PATH else HealthDB()


def _get_df(
    level: Optional[int] = None,
    ahu_ids: Optional[list] = None,
    time_range: str = "7d",
) -> pd.DataFrame:
    """
    Fetch rows from DuckDB, filtered by level / ahu_ids / time window.
    For 30d, collapses hourly rows to daily averages (same as csv_reader).
    """
    db = _db()
    latest_ts = db.get_latest_timestamp()
    if latest_ts is None:
        return pd.DataFrame()

    delta = _RANGE_DELTA.get(time_range, _RANGE_DELTA["7d"])
    start = (latest_ts - delta).isoformat()

    # 30d queries need full data for accurate daily resampling — no row cap
    row_limit = None if time_range == "30d" else 5000
    df = db.get_time_range(level=level, ahu_ids=ahu_ids, start=start, limit=row_limit)
    if df.empty:
        return df

    # Normalize to UTC so .isoformat() always emits +00:00 (matches csv_reader behavior)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    if time_range == "30d":
        df = _resample_to_daily(df)

    return df.sort_values("timestamp")


# ── Public API ─────────────────────────────────────────────────────────────────

def get_health_index_series(
    level: int,
    device_id: Optional[str],
    time_range: str,
) -> list[dict]:
    """Returns [{id, name, label, department, area, data: [{timestamp, value}]}]"""
    ahu_ids = [device_id] if device_id else None
    df = _get_df(level=level, ahu_ids=ahu_ids, time_range=time_range)
    if df.empty:
        return []

    labels = _load_ahu_labels()
    result = []
    for ahu_id, group in df.groupby("ahu_id"):
        meta = labels.get(str(ahu_id), {})
        result.append({
            "id": ahu_id,
            "name": ahu_id,
            "label": meta.get("label", ""),
            "department": meta.get("department", ""),
            "area": meta.get("area", ""),
            "data": [
                {"timestamp": row["timestamp"].isoformat(), "value": round(float(row["health_index"]), 2)}
                for _, row in group.iterrows()
                if pd.notna(row["health_index"])
            ],
        })
    return result


def get_score_breakdown(level: int, time_range: str) -> list[dict]:
    """Returns [{id, name, label, department, scores: {col: {current, trend, data}}}]"""
    df = _get_df(level=level, time_range=time_range)
    if df.empty:
        return []

    labels = _load_ahu_labels()
    result = []
    for ahu_id, group in df.groupby("ahu_id"):
        scores = {}
        for col in SCORE_COLUMNS:
            if col not in group.columns:
                continue
            series = group[["timestamp", col]].dropna(subset=[col])
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
        result.append({
            "id": ahu_id,
            "name": ahu_id,
            "label": meta.get("label", ""),
            "department": meta.get("department", ""),
            "scores": scores,
        })
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
