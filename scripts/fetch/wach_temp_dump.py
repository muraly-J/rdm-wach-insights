#!/usr/bin/env python3
"""
wach_temp_dump.py — Pull bacnet_points from InfluxDB `wach_temp` bucket
into DuckDB at <repo_root>/wach_temp_data.db, downsampled to 1h mean.

Modes:
  --backfill        Full pull from earliest data to now (idempotent upsert).
  --incremental     Resume from max(time) in DB; default mode.

Schema:
  temp_hourly(time TIMESTAMP, item VARCHAR, value DOUBLE, PRIMARY KEY(time,item))
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import duckdb
import pandas as pd
from influxdb_client import InfluxDBClient

INFLUX_URL = os.environ.get("WACH_TEMP_URL", "http://172.17.84.201:8086")
INFLUX_TOKEN = os.environ.get("WACH_TEMP_TOKEN")
INFLUX_ORG = os.environ.get("WACH_TEMP_ORG", "wach")
INFLUX_BUCKET = os.environ.get("WACH_TEMP_BUCKET", "wach_temp")

if not INFLUX_TOKEN:
    print("[wach_temp_dump] ERROR: WACH_TEMP_TOKEN env var not set", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.environ.get("WACH_TEMP_DB", os.path.join(REPO_ROOT, "wach_temp_data.db"))

CHUNK_DAYS = 1
DEFAULT_BACKFILL_FLOOR = "2026-02-19T00:00:00Z"


def log(msg: str) -> None:
    print(f"[wach_temp_dump] {datetime.now().isoformat(timespec='seconds')} {msg}", flush=True)


def ensure_db(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS temp_hourly (
            time  TIMESTAMP NOT NULL,
            item  VARCHAR   NOT NULL,
            value DOUBLE,
            PRIMARY KEY (time, item)
        );
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_temp_hourly_item ON temp_hourly(item);")


def db_max_time(con: duckdb.DuckDBPyConnection) -> datetime | None:
    row = con.execute("SELECT max(time) FROM temp_hourly").fetchone()
    if row and row[0]:
        ts = row[0]
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return None


def find_earliest(qapi) -> datetime:
    flux = (
        f'from(bucket:"{INFLUX_BUCKET}") '
        '|> range(start:-10y) '
        '|> first() '
        '|> keep(columns:["_time"]) '
        '|> group() '
        '|> min(column:"_time")'
    )
    tables = qapi.query(flux)
    for t in tables:
        for rec in t.records:
            ts = rec.get_time()
            return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(DEFAULT_BACKFILL_FLOOR.replace("Z", "+00:00"))


def fetch_chunk(qapi, start: datetime, stop: datetime) -> pd.DataFrame:
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    stop_iso = stop.strftime("%Y-%m-%dT%H:%M:%SZ")
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start_iso}, stop: {stop_iso})
      |> filter(fn: (r) => r._measurement == "bacnet_points" and r._field == "value")
      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
      |> keep(columns: ["_time", "item", "_value"])
    '''
    df = qapi.query_data_frame(flux)
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()
    if df.empty:
        return pd.DataFrame(columns=["time", "item", "value"])
    df = df.rename(columns={"_time": "time", "_value": "value"})
    df = df[["time", "item", "value"]].dropna(subset=["time", "item"])
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert("UTC").dt.tz_localize(None)
    return df


def upsert(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    con.register("staging", df)
    con.execute(
        """
        INSERT INTO temp_hourly (time, item, value)
        SELECT time, item, value FROM staging
        ON CONFLICT (time, item) DO UPDATE SET value = excluded.value;
        """
    )
    con.unregister("staging")
    return len(df)


def run(start: datetime, stop: datetime) -> int:
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=300_000)
    qapi = client.query_api()
    con = duckdb.connect(DB_PATH)
    ensure_db(con)

    total = 0
    cur = start.replace(minute=0, second=0, microsecond=0)
    stop = stop.replace(minute=0, second=0, microsecond=0)
    while cur < stop:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), stop)
        attempt = 0
        while True:
            try:
                df = fetch_chunk(qapi, cur, nxt)
                rows = upsert(con, df)
                total += rows
                log(f"chunk {cur.date()}..{nxt.date()} rows={rows} total={total}")
                break
            except Exception as e:
                attempt += 1
                if attempt >= 4:
                    log(f"FAIL chunk {cur}..{nxt}: {e}")
                    raise
                wait = 2 ** attempt
                log(f"retry {attempt} chunk {cur}..{nxt} in {wait}s ({e})")
                time.sleep(wait)
        cur = nxt

    con.close()
    client.close()
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true", help="Full backfill from earliest")
    ap.add_argument("--since", help="ISO timestamp override (e.g. 2026-02-19T00:00:00Z)")
    args = ap.parse_args()

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=120_000)
    qapi = client.query_api()
    con = duckdb.connect(DB_PATH)
    ensure_db(con)
    last = db_max_time(con)
    con.close()

    if args.since:
        start = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    elif args.backfill or last is None:
        start = find_earliest(qapi)
        log(f"earliest in bucket: {start.isoformat()}")
    else:
        start = last + timedelta(hours=1)
        log(f"resuming from db max: {last.isoformat()}")
    client.close()

    stop = datetime.now(timezone.utc)
    if start >= stop:
        log("up-to-date, nothing to do")
        return 0

    log(f"pulling {start.isoformat()} -> {stop.isoformat()} into {DB_PATH}")
    total = run(start, stop)
    log(f"done. inserted/updated rows: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
