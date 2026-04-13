"""
charts.py
─────────
Converts pandas DataFrames from influx_client into Recharts-ready JSON payloads
and CSV strings for download.

Two public functions:
  build_line_chart()  → for time_series queries  (UC-1)
  build_bar_chart()   → for ranking queries       (UC-2)

Both return a ChartPayload dict that the FastAPI route sends directly to React.
"""

from typing import Any

import pandas as pd
from models.schemas import QueryType

# ── Recharts line chart (time series) ────────────────────────────────────────

def build_line_chart(
    df: pd.DataFrame,
    metric: str,
    time_range: str,
) -> dict[str, Any]:
    """
    Input:  DataFrame indexed by time, one column per device_id.
    Output: {
        "chart_type": "line",
        "metric": "power_total",
        "time_range": "last_7d",
        "device_ids": ["e0101"],
        "data": [{"time": "Feb 10 08:00", "e0101": 1200.5}, ...],
        "csv": "time,e0101\n2026-02-10 08:00:00,1200.5\n...",
    }
    """
    if df.empty:
        return _empty_payload("line", metric, time_range)

    device_ids: list[str] = list(df.columns)

    # Format timestamps based on time range — keeps x-axis labels readable
    label_format = _time_label_format(time_range)

    records = []
    for ts, row in df.iterrows():
        entry: dict[str, Any] = {"time": ts.strftime(label_format)}
        for device in device_ids:
            val = row.get(device)
            if pd.notna(val):
                entry[device] = round(float(val), 3)
            else:
                entry[device] = None
        records.append(entry)

    csv_str = _df_to_csv(df)

    return {
        "chart_type":  "line",
        "metric":      metric,
        "time_range":  time_range,
        "device_ids":  device_ids,
        "data":        records,
        "csv":         csv_str,
    }


# ── Recharts bar chart (ranking) ──────────────────────────────────────────────

def build_bar_chart(
    df: pd.DataFrame,
    metric: str,
    time_range: str,
    top_n: int | None = None,  # None means no limit (show all)
) -> dict[str, Any]:
    """
    Input:  DataFrame with columns ['device_id', 'value'], sorted descending.
    Output: {
        "chart_type": "bar",
        "metric": "power_total",
        "time_range": "last_30d",
        "data": [{"device_id": "e0405", "value": 2300.1}, ...],
        "csv": "device_id,value\ne0405,2300.1\n...",
    }
    """
    if df.empty:
        return _empty_payload("bar", metric, time_range)

    # If top_n is None or 0, show all devices (or up to a reasonable max)
    if top_n is None or top_n == 0:
        # Limit to reasonable number for visualization
        max_devices = 50
        df = df.head(max_devices).copy()
    else:
        df = df.head(top_n).copy()

    df["value"] = df["value"].round(3)

    records = df.to_dict(orient="records")
    csv_str = df.to_csv(index=False)

    return {
        "chart_type":  "bar",
        "metric":      metric,
        "time_range":  time_range,
        "data":        records,
        "csv":         csv_str,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _time_label_format(time_range: str) -> str:
    """Return a strftime format string appropriate for the time range granularity."""
    return {
        "last_24h":  "%H:%M",           # 08:05
        "last_7d":   "%b %d %H:%M",     # Feb 10 08:00
        "last_30d":  "%b %d",           # Feb 10
        "all_time":  "%b %Y",           # Feb 2025
    }.get(time_range, "%b %d %H:%M")


def _df_to_csv(df: pd.DataFrame) -> str:
    """Convert a time-indexed DataFrame to a CSV string with readable timestamps."""
    export = df.copy()
    export.index = export.index.strftime("%Y-%m-%d %H:%M:%S")
    export.index.name = "time"
    return export.to_csv()


def _empty_payload(chart_type: str, metric: str, time_range: str) -> dict[str, Any]:
    return {
        "chart_type":  chart_type,
        "metric":      metric,
        "time_range":  time_range,
        "device_ids":  [],
        "data":        [],
        "csv":         "",
        "empty":       True,
    }

# ── Unified entry point ───────────────────────────────────────────────────────

def build_chart(df: pd.DataFrame, structured: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatcher: takes a DataFrame and the StructuredQuery dict/object,
    calls the appropriate builder, and returns the Recharts-ready payload.
    """
    # handle both dict and object (pydantic)
    if hasattr(structured, 'query_type'):
        qtype      = structured.query_type
        metric     = structured.metric
        time_range = structured.time_range
        top_n      = getattr(structured, 'top_n', 10)
    else:
        qtype      = structured.get('query_type')
        metric     = structured.get('metric')
        time_range = structured.get('time_range')
        top_n      = structured.get('top_n', 10)

    if qtype == QueryType.prediction:
        return {
            "chart_type": "prediction",
            "redirect": "prediction_view",
            "message": "Use the prediction panel to see forecast data for this device.",
        }
    if qtype == QueryType.health_index:
        return {
            "chart_type": "health_index",
            "redirect": "health_index_view",
            "message": "Use the health index chart to see score trends.",
        }
    if qtype == 'time_series':
        return build_line_chart(df, metric, time_range)
    else:
        return build_bar_chart(df, metric, time_range, top_n)

