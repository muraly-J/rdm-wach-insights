"""
influx_client.py
────────────────
Handles all InfluxDB communication for WACH Insight.

Two public functions:
  fetch_time_series()  → for line-chart queries  (UC-1)
  fetch_ranking()      → for bar-chart queries   (UC-2)

Both return clean pandas DataFrames ready for the visualization layer.
"""

import os
import warnings
import pandas as pd
from influxdb_client import InfluxDBClient

from backend.models.schemas import ALLOWED_TIME_RANGES
from backend.config import get_influx_url, get_influx_token, get_influx_org, get_influx_bucket

warnings.filterwarnings("ignore")

_URL    = get_influx_url()
_TOKEN  = get_influx_token()
_ORG    = get_influx_org()
_BUCKET = get_influx_bucket()

import logging

logger = logging.getLogger(__name__)

# Resample granularity per time range — keeps charts readable
_RESAMPLE_MAP = {
    "last_24h":  "5min",
    "last_7d":   "1h",
    "last_30d":  "4h",
    "all_time":  "1d",
}


def _get_client() -> InfluxDBClient:
    return InfluxDBClient(url=_URL, token=_TOKEN, org=_ORG, timeout=18_000_000)


# ── Time-series query (single or multi device, one metric over time) ──────────

def fetch_time_series(
    device_ids: list[str],
    metric: str,
    time_range: str,
) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by time with one column per device_id.
    Columns are named after the device IDs (e.g. 'e0101').

    Example output:
                             e0101    e0206
        time
        2026-02-10 00:00:00  1200.5   980.2
        2026-02-10 00:05:00  1198.1   975.4
        ...
    """
    influx_start  = ALLOWED_TIME_RANGES[time_range]
    resample_freq = _RESAMPLE_MAP[time_range]
    devices_regex = "|".join(device_ids)

    flux_query = f'''
    from(bucket: "{_BUCKET}")
      |> range(start: {influx_start})
      |> filter(fn: (r) => r._measurement =~ /^wach_({devices_regex})_{metric}$/)
      |> pivot(rowKey:["_time"], columnKey: ["_measurement"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''

    return _execute_and_clean(flux_query, device_ids, metric, resample_freq)


# ── Ranking query (all devices, one metric, aggregated to a single value) ─────

def fetch_ranking(
    metric: str,
    time_range: str,
    device_ids: list[str],   # pass [] to query ALL devices; pass a subset to restrict
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns ['device_id', 'value'] sorted descending,
    limited to top_n rows.

    Example output:
        device_id    value
        e0505        2300.1
        e0101        2150.4
        ...
    """
    influx_start = ALLOWED_TIME_RANGES[time_range]

    # If no device filter → match all WACH devices with a broad regex
    if device_ids:
        devices_regex = "|".join(device_ids)
    else:
        devices_regex = r"e\d{4}"   # matches e0101 … e9999

    flux_query = f'''
    from(bucket: "{_BUCKET}")
      |> range(start: {influx_start})
      |> filter(fn: (r) => r._measurement =~ /^wach_({devices_regex})_{metric}$/)
      |> mean()
      |> group()
      |> sort(columns: ["_value"], desc: true)
      |> limit(n: {top_n})
    '''

    client = _get_client()
    try:
        tables = client.query_api().query(flux_query)

        rows = []
        for table in tables:
            for record in table.records:
                # Measurement name looks like "wach_e0101_power_total"
                # Extract device_id from the middle segment
                parts = record.get_measurement().split("_")
                # parts = ["wach", "e0101", "power", "total"] — device is always parts[1]
                device_id = parts[1] if len(parts) >= 2 else "unknown"
                rows.append({"device_id": device_id, "value": record.get_value()})

        if not rows:
            return pd.DataFrame(columns=["device_id", "value"])

        df = pd.DataFrame(rows)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])
        df = df.sort_values("value", ascending=False).head(top_n).reset_index(drop=True)
        return df

    except Exception as e:
        logger.error(f"fetch_ranking failed: {e}")
        return pd.DataFrame(columns=["device_id", "value"])
    finally:
        client.close()


# ── Shared helper ─────────────────────────────────────────────────────────────

def _execute_and_clean(
    flux_query: str,
    device_ids: list[str],
    metric: str,
    resample_freq: str,
) -> pd.DataFrame:
    client = _get_client()
    try:
        raw = client.query_api().query_data_frame(flux_query)

        if isinstance(raw, list):
            if not raw:
                return pd.DataFrame()
            df = pd.concat(raw, ignore_index=True)
        else:
            df = raw

        if df.empty:
            return pd.DataFrame()

        # Drop internal InfluxDB columns
        df = df.drop(
            columns=[c for c in df.columns if c.startswith("_") and c != "_time"],
            errors="ignore",
        )

        df = df.rename(columns={"_time": "time"})
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df = df.set_index("time")

        # Column names arrive as "wach_e0101_power_total" → extract device_id
        def _col_to_device(col: str) -> str:
            parts = col.split("_")
            return parts[1] if len(parts) >= 2 else col

        df.columns = [_col_to_device(c) for c in df.columns]

        # Keep only requested devices (safety guard against regex over-matching)
        if device_ids:
            df = df[[c for c in df.columns if c in device_ids]]

        df = df.apply(pd.to_numeric, errors="coerce")

        # Resample → mean per interval, forward-fill small gaps
        df = (
            df
            .resample(resample_freq)
            .mean()
            .ffill()
            .fillna(0)
        )

        return df

    except Exception as e:
        logger.error(f"query failed: {e}")
        return pd.DataFrame()
    finally:
        client.close()