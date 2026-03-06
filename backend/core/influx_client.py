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
import math
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
from influxdb_client import InfluxDBClient

from models.schemas import ALLOWED_TIME_RANGES
from config import get_influx_url, get_influx_token, get_influx_org, get_influx_bucket

warnings.filterwarnings("ignore")

# Get config values - handle missing env vars gracefully
_URL    = get_influx_url()
_TOKEN  = get_influx_token() or ""  # Empty token will cause InfluxDB to fail, but we'll catch it
_ORG    = get_influx_org() or "wach"
_BUCKET = get_influx_bucket() or "wach_bucket_3"

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
        # When explicit device_ids are provided, respect top_n if specified
        if top_n is not None:
            query_limit = min(top_n, len(device_ids))
            use_limit = True
        else:
            query_limit = None
            use_limit = False  # Return all devices when no top_n specified
    else:
        devices_regex = r"e\d{4}"   # matches e0101 … e9999
        # When fetching ALL devices without filter, use a reasonable max
        query_limit = 50 if top_n is None else min(top_n, 50)
        use_limit = True

    # Build Flux query
    if not use_limit:
        flux_query = f'''
        from(bucket: "{_BUCKET}")
          |> range(start: {influx_start})
          |> filter(fn: (r) => r._measurement =~ /^wach_({devices_regex})_{metric}$/)
          |> mean()
          |> group()
          |> sort(columns: ["_value"], desc: true)
        '''
    else:
        flux_query = f'''
        from(bucket: "{_BUCKET}")
          |> range(start: {influx_start})
          |> filter(fn: (r) => r._measurement =~ /^wach_({devices_regex})_{metric}$/)
          |> mean()
          |> group()
          |> sort(columns: ["_value"], desc: true)
          |> limit(n: {query_limit})
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
        df = df.sort_values("value", ascending=False)
        # Only apply head() if top_n is specified, otherwise return all results
        if top_n is not None:
            df = df.head(top_n)
        df = df.reset_index(drop=True)
        return df

    except Exception as e:
        print(f"[influx_client] fetch_ranking failed: {e}")
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
        print(f"[influx_client] query failed: {e}")
        return pd.DataFrame()
    finally:
        client.close()


def get_available_devices(time_range: str = "last_30d") -> list[str]:
    """
    Get list of devices that have data in the specified time range.
    
    This is used by electrical-risk to avoid querying devices that don't exist
    or don't have data, which would cause timeouts.
    
    Args:
        time_range: Data period to check (last_24h, last_7d, last_30d, all_time)
        
    Returns:
        List of device IDs that have power_total data
    """
    influx_start = ALLOWED_TIME_RANGES[time_range]
    
    # Query for any device with power_total data
    flux_query = f'''
    from(bucket: "{_BUCKET}")
      |> range(start: {influx_start})
      |> filter(fn: (r) => r._measurement =~ /^wach_e\\d{{4}}_power_total$/)
      |> distinct(column: "_measurement")
      |> keep(columns: ["_value"])
    '''
    
    client = _get_client()
    try:
        tables = client.query_api().query(flux_query)
        
        devices = set()
        for table in tables:
            for record in table.records:
                measurement = record.get_value()
                # Extract device_id from measurement like "wach_e0101_power_total"
                if measurement and measurement.startswith("wach_"):
                    parts = measurement.split("_")
                    if len(parts) >= 2:
                        devices.add(parts[1])  # Already contains 'e0101'
        
        return sorted(list(devices))
    
    except Exception as e:
        print(f"[influx_client] get_available_devices failed: {e}")
        return []
    finally:
        client.close()


# ── Exact Slot Fetching for t-24h, t-168h, t-336h comparison ────────────────

def fetch_exact_slots(
    device_ids: list[str],
    metric: str,
    reference_time: datetime,
    slots_hours_ago: list[int]
) -> Dict[str, Dict[int, Optional[float]]]:
    """
    Fetch exact historical values at specific time slots (t-24h, t-168h, etc).

    This enables comparison of current value against specific historical points:
    - t:     Current hour
    - t-24h: Same hour yesterday
    - t-168h: Same hour last week (7 days ago)
    - t-336h: Two weeks ago (14 days ago)

    Args:
        device_ids: List of AHU IDs to fetch
        metric: Metric name (e.g., "power_total", "energy_import")
        reference_time: Current timestamp t
        slots_hours_ago: List of hours ago to fetch (e.g., [0, 24, 168, 336])

    Returns:
        Nested dict: {ahu_id: {hours_ago: value, ...}}
        Example: {"e0101": {0: 35.2, 24: 33.1, 168: 34.8, 336: 32.5}}

    Example usage:
        now = datetime.now(timezone.utc)
        slots = fetch_exact_slots(["e0101"], "power_total", now, [24, 168])
        # Compare current vs t-24h vs t-168h for trend detection
    """
    results = {ahu_id: {} for ahu_id in device_ids}

    if not device_ids:
        return results

    client = _get_client()
    try:
        for ahu_id in device_ids:
            for hours_ago in slots_hours_ago:
                # Calculate start and end time for exact slot
                # Fetch a narrow window around the target time (±30 min tolerance)
                start_time = reference_time - timedelta(hours=hours_ago + 1)
                end_time = reference_time - timedelta(hours=hours_ago)

                flux_query = f'''
                from(bucket: "{_BUCKET}")
                  |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                  |> filter(fn: (r) => r._measurement == "wach_{ahu_id}_{metric}")
                  |> mean()
                '''

                try:
                    tables = client.query_api().query(flux_query)
                    value = None
                    for table in tables:
                        for record in table.records:
                            val = record.get_value()
                            if val is not None and not math.isnan(float(val)):
                                value = float(val)
                                break

                    # If no result in 1-hour window, try broader search
                    if value is None:
                        broader_start = reference_time - timedelta(hours=hours_ago + 2)
                        broader_query = f'''
                        from(bucket: "{_BUCKET}")
                          |> range(start: {broader_start.isoformat()}, stop: {reference_time.isoformat()})
                          |> filter(fn: (r) => r._measurement == "wach_{ahu_id}_{metric}")
                          |> last()
                        '''
                        broader_tables = client.query_api().query(broader_query)
                        for table in broader_tables:
                            for record in table.records:
                                val = record.get_value()
                                if val is not None and not math.isnan(float(val)):
                                    value = float(val)
                                    break

                    results[ahu_id][hours_ago] = value

                except Exception as e:
                    print(f"[influx_client] Slot fetch failed for {ahu_id} @ t-{hours_ago}h: {e}")
                    results[ahu_id][hours_ago] = None

    except Exception as e:
        print(f"[influx_client] fetch_exact_slots failed: {e}")
    finally:
        client.close()

    return results


# ── Fetch Prediction Data for ETL (t, t-24h, t-168h, t-336h) ───────────────

def fetch_prediction_data(
    device_ids: list[str],
    reference_time: datetime = None,
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Fetch energy values at t, t-24h, t-168h, and t-336h for prediction ETL.

    This enables computation of:
      ŷ(t)   = (E(t−24h) + E(t−168h) + E(t−336h)) / 3
      Δkwh   = E(t) − ŷ(t)

    Args:
        device_ids: List of AHU IDs to fetch
        reference_time: Current timestamp t (defaults to now in UTC)

    Returns:
        Nested dict: {ahu_id: {
            'energy_current': E(t),
            'yesterday_kwh': E(t−24h),
            'last_week_kwh': E(t−168h),
            'two_weeks_kwh': E(t−336h)
        }}

    Example:
        now = datetime.now(timezone.utc)
        data = fetch_prediction_data(["e0101"], now)
        # Compute prediction: ŷ(t) = (yesterday + last_week + two_weeks) / 3
    """
    if reference_time is None:
        from datetime import timezone
        reference_time = datetime.now(timezone.utc)

    # Slots to fetch: current, t-24h, t-168h, t-336h
    slots_hours_ago = [0, 24, 168, 336]
    slot_labels = {
        0: 'energy_current',
        24: 'yesterday_kwh',
        168: 'last_week_kwh',
        336: 'two_weeks_kwh'
    }

    # Fetch using existing fetch_exact_slots
    raw_data = fetch_exact_slots(device_ids, "energy_import", reference_time, slots_hours_ago)

    # Transform to prediction format
    results = {}
    for ahu_id in device_ids:
        slot_values = raw_data.get(ahu_id, {})
        results[ahu_id] = {
            'energy_current': slot_values.get(0),
            'yesterday_kwh': slot_values.get(24),
            'last_week_kwh': slot_values.get(168),
            'two_weeks_kwh': slot_values.get(336)
        }

    return results


# ── Fetch Latest Hourly Data for All AHUs ────────────────────────────────────

def fetch_latest_hourly_data(
    metrics_to_fetch: list[str] = None,
    level_filter: int = None
) -> pd.DataFrame:
    """
    Fetch the latest hourly data point for each AHU across all levels or a specific level.

    This function queries InfluxDB to get the most recent reading for each
    metric for every AHU, then aggregates them into a single DataFrame.

    Args:
        metrics_to_fetch: List of metric names to fetch.
                         Default: ["power_total", "energy_import",
                                   "power_factor_avg", "current_unbalance",
                                   "current_l1_thd", "current_l3_thd"]
        level_filter: Optional level number (1-11) to fetch only specific level.
                     If None, fetches all levels.

    Returns:
        DataFrame with columns:
        - timestamp (latest reading time)
        - ahu_id
        - level (Building level 1-11)
        - All requested metrics

    Example:
        >>> df = fetch_latest_hourly_data()
        >>> print(f"Retrieved {len(df)} AHU readings")
        >>> # Fetch only Level 1
        >>> df = fetch_latest_hourly_data(level_filter=1)
    """
    if metrics_to_fetch is None:
        metrics_to_fetch = [
            "power_total",
            "energy_import",
            "power_factor_avg",
            "current_unbalance",
            "current_l1_thd",
            "current_l3_thd",
        ]

    from models.schemas import AHU_LEVEL_CONFIG

    # Determine which devices to fetch
    if level_filter is not None:
        if level_filter not in AHU_LEVEL_CONFIG:
            print(f"[influx_client] Error: Invalid level {level_filter}")
            return pd.DataFrame()
        device_ids = AHU_LEVEL_CONFIG[level_filter]["device_ids"]
        print(f"[influx_client] Fetching latest data for Level {level_filter} ({len(device_ids)} AHUs)...")
    else:
        all_devices = []
        for level_config in AHU_LEVEL_CONFIG.values():
            all_devices.extend(level_config["device_ids"])
        device_ids = all_devices
        print(f"[influx_client] Fetching latest data for {len(device_ids)} AHUs (all levels)...")

    print(f"[influx_client] Metrics: {', '.join(metrics_to_fetch)}")

    records = []

    client = _get_client()
    try:
        # Batch by level for better performance (avoids N+1 queries)
        levels_to_fetch = [level_filter] if level_filter else sorted(AHU_LEVEL_CONFIG.keys())
        
        for level_num in levels_to_fetch:
            # Skip if filtering by a specific level and this doesn't match
            if level_filter is not None and level_num != level_filter:
                continue
            
            level_devices = AHU_LEVEL_CONFIG[level_num]["device_ids"]
            
            # Build measurement regex for this level's devices
            devices_regex = "|".join([d.replace("e", "e") for d in level_devices])
            
            # Query each metric for this level
            for metric in metrics_to_fetch:
                flux_query = f'''
                from(bucket: "{_BUCKET}")
                  |> range(start: -7d)
                  |> filter(fn: (r) => r._measurement =~ /^wach_({devices_regex})_{metric}$/)
                  |> last()
                '''

                try:
                    tables = client.query_api().query(flux_query)
                    for table in tables:
                        for record in table.records:
                            measurement = record.get_measurement()
                            # Parse: wach_e0101_power_total -> e0101
                            parts = measurement.split("_")
                            if len(parts) >= 2:
                                ahu_id = parts[1]
                                val = record.get_value()

                                if val is not None and not math.isnan(float(val)):
                                    # Determine level from AHU ID
                                    level_code = ahu_id[1:3]  # "01" from "e0101"
                                    level = f"Level {int(level_code)}"

                                    records.append({
                                        "ahu_id": ahu_id,
                                        "level": level,
                                        "metric": metric,
                                        "value": float(val),
                                    })

                except Exception as e:
                    print(f"[influx_client] Query failed for {metric} (Level {level_num}): {e}")
                    continue

    except Exception as e:
        print(f"[influx_client] fetch_latest_hourly_data failed: {e}")
    finally:
        client.close()

    if not records:
        print("[influx_client] No data found!")
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Pivot to wide format (one row per AHU, one column per metric)
    df_wide = df.pivot_table(
        index=["ahu_id", "level"],
        columns="metric",
        values="value"
    ).reset_index()

    # Ensure all expected metrics are present
    for metric in metrics_to_fetch:
        if metric not in df_wide.columns:
            df_wide[metric] = None

    # Get timestamps from power_total data (has all AHUs)
    print("[influx_client] Fetching timestamps...")

    # Get the devices for this query (all or filtered)
    if level_filter is not None:
        devices_for_timestamps = AHU_LEVEL_CONFIG[level_filter]["device_ids"]
    else:
        devices_for_timestamps = all_devices

    # First, fetch power data with the relevant devices to get timestamps
    df_power = fetch_time_series(devices_for_timestamps, "power_total", "last_7d")
    
    # Extract timestamps from the last row of each AHU
    timestamps = {}
    for ahu_id in df_wide["ahu_id"]:
        if ahu_id in df_power.columns and not pd.isna(df_power[ahu_id].iloc[-1]):
            timestamps[ahu_id] = df_power.index[-1].isoformat()
        else:
            # Try to find a non-null value anywhere in the series
            non_null = df_power[ahu_id].dropna()
            if len(non_null) > 0:
                # Get timestamp of last non-null value
                last_valid_idx = non_null.index[-1]
                timestamps[ahu_id] = last_valid_idx.isoformat()
            else:
                timestamps[ahu_id] = None

    df_wide["timestamp"] = df_wide["ahu_id"].map(timestamps)

    # Compute composite_thd from max of L1 and L3 THD
    has_composite = False
    if "current_l1_thd" in df_wide.columns and "current_l3_thd" in df_wide.columns:
        df_wide["composite_thd"] = df_wide[["current_l1_thd", "current_l3_thd"]].max(axis=1)
        has_composite = True

    # Reorder columns for cleaner output
    col_order = ["timestamp", "ahu_id", "level"] + metrics_to_fetch
    if has_composite:
        col_order.append("composite_thd")
    df_wide = df_wide[[c for c in col_order if c in df_wide.columns]]

    print(f"[influx_client] Retrieved {len(df_wide)} AHU readings")

    return df_wide
