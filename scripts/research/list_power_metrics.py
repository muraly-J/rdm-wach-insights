"""One-off: enumerate all power-meter fields in InfluxDB with sample ranges.

Output: prints CSV-like rows to stdout for paste into the metric inventory doc.
Columns: field_name, unit_guess, sample_min, sample_max, sample_count

Usage:
    cd backend && python ../scripts/research/list_power_metrics.py
"""

from __future__ import annotations

import os
import sys

# Ensure backend/ is on the path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from config import get_influx_bucket, get_influx_org, get_influx_token, get_influx_url  # noqa: E402
from influxdb_client import InfluxDBClient  # noqa: E402

INFLUX_URL = get_influx_url()
INFLUX_TOKEN = get_influx_token()
INFLUX_ORG = get_influx_org()
INFLUX_BUCKET = get_influx_bucket()

# Measurements follow pattern wach_{device_id}_{metric}.
# The metrics we care about (from influx_client.py fetch_time_series default list):
METRICS = [
    "power_total",
    "energy_import",
    "power_factor_avg",
    "current_unbalance",
    "current_l1_thd",
    "current_l3_thd",
]
LOOKBACK = "-7d"

# Build Flux regex: /^wach_e\d{4}_metric$/
FLUX_REGEX = "^wach_e\\d{4}_(" + "|".join(METRICS) + ")$"


def build_schema_query() -> str:
    return (
        'import "influxdata/influxdb/schema"\n'
        f'schema.fieldKeys(\n'
        f'    bucket: "{INFLUX_BUCKET}",\n'
        f'    predicate: (r) => r._measurement =~ /{FLUX_REGEX}/,\n'
        f'    start: {LOOKBACK},\n'
        f')'
    )


def build_count_query(field: str) -> str:
    return (
        f'from(bucket: "{INFLUX_BUCKET}")\n'
        f'    |> range(start: {LOOKBACK})\n'
        f'    |> filter(fn: (r) => r._measurement =~ /{FLUX_REGEX}/ and r._field == "{field}")\n'
        f'    |> count()\n'
    )


def build_min_query(field: str) -> str:
    return (
        f'from(bucket: "{INFLUX_BUCKET}")\n'
        f'    |> range(start: {LOOKBACK})\n'
        f'    |> filter(fn: (r) => r._measurement =~ /{FLUX_REGEX}/ and r._field == "{field}")\n'
        f'    |> min()\n'
    )


def build_max_query(field: str) -> str:
    return (
        f'from(bucket: "{INFLUX_BUCKET}")\n'
        f'    |> range(start: {LOOKBACK})\n'
        f'    |> filter(fn: (r) => r._measurement =~ /{FLUX_REGEX}/ and r._field == "{field}")\n'
        f'    |> max()\n'
    )


def main() -> int:
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    fields: list[str] = []
    for table in query_api.query(build_schema_query()):
        for record in table.records:
            fields.append(record.get_value())

    print("field_name,unit_guess,sample_min,sample_max,sample_count")
    for f in sorted(fields):
        # Count
        cnt = 0
        for table in query_api.query(build_count_query(f)):
            for rec in table.records:
                cnt = int(rec.values.get("_count", 0))

        # Min
        mn = "?"
        for table in query_api.query(build_min_query(f)):
            for rec in table.records:
                mn = rec.values.get("_value", "?")

        # Max
        mx = "?"
        for table in query_api.query(build_max_query(f)):
            for rec in table.records:
                mx = rec.values.get("_value", "?")

        unit = _unit_guess(f)
        print(f"{f},{unit},{mn},{mx},{cnt}")

    client.close()
    return 0


def _unit_guess(field: str) -> str:
    f = field.lower()
    if "kwh" in f or "energy" in f:
        return "kWh"
    if "kw" in f or "power" in f:
        return "kW"
    if "voltage" in f or f.endswith("_v"):
        return "V"
    if "current" in f or f.endswith("_a") or f.endswith("_amp"):
        return "A"
    if "pf" in f or "power_factor" in f:
        return "ratio"
    if "thd" in f:
        return "%"
    if "freq" in f or "hz" in f:
        return "Hz"
    if "temp" in f:
        return "°C"
    return "?"


if __name__ == "__main__":
    sys.exit(main())
