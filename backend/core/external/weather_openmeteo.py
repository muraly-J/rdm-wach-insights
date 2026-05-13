from __future__ import annotations

"""
core/external/weather_openmeteo.py
──────────────────────────────────
Open-meteo weather adapter with DuckDB read-through cache.

Public API
----------
    fetch_weather(lat, lon, start, end, cache_db=None) -> pd.DataFrame
        Returns hourly weather with columns: ["ts", "oat", "oah", "ghi"].

Exceptions
----------
    OpenMeteoError              — base class for HTTP errors from open-meteo
    OpenMeteoRateLimitError     — raised on HTTP 429

CLI (backfill)
--------------
    python -m backend.core.external.weather_openmeteo backfill \\
        --start 2025-01-01 --end 2026-05-13
"""

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb
import httpx
import pandas as pd

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# open-meteo variable → internal column name
_VAR_MAP = {
    "temperature_2m": "oat",
    "relative_humidity_2m": "oah",
    "shortwave_radiation": "ghi",
}

# DuckDB cache schema
# TIMESTAMPTZ so DuckDB stores the UTC offset; we always SET TimeZone='UTC' on
# each connection to guarantee consistent round-trip behaviour regardless of the
# host's local timezone.
_CACHE_DDL = """
CREATE TABLE IF NOT EXISTS weather_cache (
    lat DOUBLE NOT NULL,
    lon DOUBLE NOT NULL,
    ts  TIMESTAMPTZ NOT NULL,
    oat DOUBLE,
    oah DOUBLE,
    ghi DOUBLE,
    PRIMARY KEY (lat, lon, ts)
);
"""

_SET_UTC = "SET TimeZone = 'UTC'"

# Rounding precision for lat/lon to prevent float-noise cache fragmentation
_COORD_PRECISION = 4


# ── Exceptions ────────────────────────────────────────────────────────────────


class OpenMeteoError(Exception):
    """Base exception for open-meteo HTTP errors."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"open-meteo HTTP {status_code}: {message}")
        self.status_code = status_code


class OpenMeteoRateLimitError(OpenMeteoError):
    """Raised when open-meteo returns HTTP 429 Too Many Requests."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _today_utc() -> date:
    """Return today's date in UTC. Monkeypatch-able for tests."""
    return datetime.now(timezone.utc).date()


def _default_cache_db() -> Path:
    return settings.data_dir / "weather_cache.duckdb"


def _round_coord(value: float) -> float:
    return round(value, _COORD_PRECISION)


def _init_cache(db_path: Path) -> None:
    """Ensure the cache table exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(_SET_UTC)
        conn.execute(_CACHE_DDL)


def _fetch_from_api(
    url: str,
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> pd.DataFrame:
    """
    Call an open-meteo endpoint and return a DataFrame with columns
    ["ts", "oat", "oah", "ghi"].

    Raises OpenMeteoRateLimitError on 429, OpenMeteoError on other 4xx/5xx.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(_VAR_MAP.keys()),
        "timezone": "UTC",
    }

    logger.debug("open-meteo fetch: url=%s start=%s end=%s", url, start, end)

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, params=params)

    if resp.status_code == 429:
        raise OpenMeteoRateLimitError(429, resp.text)
    if resp.status_code >= 400:
        raise OpenMeteoError(resp.status_code, resp.text)

    data = resp.json()
    hourly = data["hourly"]

    df = pd.DataFrame(
        {
            "ts": pd.to_datetime(hourly["time"], utc=True),
            "oat": pd.array(hourly["temperature_2m"], dtype="Float64"),
            "oah": pd.array(hourly["relative_humidity_2m"], dtype="Float64"),
            "ghi": pd.array(hourly["shortwave_radiation"], dtype="Float64"),
        }
    )
    # Cast to plain float64 so DuckDB inserts work cleanly
    for col in ("oat", "oah", "ghi"):
        df[col] = df[col].astype("float64")

    return df[["ts", "oat", "oah", "ghi"]]


def _query_cache(
    db_path: Path,
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    """Return cached rows for (lat, lon) in [start, end] (inclusive)."""
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(_SET_UTC)
        df = conn.execute(
            """
            SELECT ts, oat, oah, ghi
            FROM   weather_cache
            WHERE  lat = ?
              AND  lon = ?
              AND  ts  >= ?
              AND  ts  <= ?
            ORDER  BY ts
            """,
            [lat, lon, start, end],
        ).fetchdf()

    if df.empty:
        return df

    # DuckDB returns TIMESTAMPTZ — normalise to UTC-aware pandas dtype
    if df["ts"].dt.tz is None:
        df["ts"] = df["ts"].dt.tz_localize("UTC")
    else:
        df["ts"] = df["ts"].dt.tz_convert("UTC")

    return df


def _cached_timestamps(
    db_path: Path,
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
) -> set[pd.Timestamp]:
    """Return the set of timestamps already in the cache for (lat, lon, range)."""
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(_SET_UTC)
        rows = conn.execute(
            """
            SELECT ts
            FROM   weather_cache
            WHERE  lat = ?
              AND  lon = ?
              AND  ts  >= ?
              AND  ts  <= ?
            """,
            [lat, lon, start, end],
        ).fetchall()
    # DuckDB TIMESTAMPTZ with SET TimeZone='UTC' returns tz-aware datetimes
    result = set()
    for (r,) in rows:
        if hasattr(r, "tzinfo") and r.tzinfo is not None:
            result.add(pd.Timestamp(r).tz_convert("UTC"))
        else:
            result.add(pd.Timestamp(r, tz="UTC"))
    return result


def _insert_into_cache(
    db_path: Path,
    lat: float,
    lon: float,
    df: pd.DataFrame,
) -> int:
    """
    Bulk-insert rows into weather_cache. Skips rows already present (idempotent).
    Returns count of newly inserted rows.

    Rows where ALL of oat, oah, ghi are NaN are dropped (useless cache entries).
    Duplicate timestamps within the input are deduplicated (keep last).
    """
    if df.empty:
        return 0

    # Drop within-batch timestamp duplicates
    df = df.drop_duplicates(subset=["ts"], keep="last")

    # Drop rows where ALL weather values are NaN — nothing useful to cache
    all_nan_mask = df["oat"].isna() & df["oah"].isna() & df["ghi"].isna()
    df = df[~all_nan_mask]

    if df.empty:
        return 0

    # Build a typed view DataFrame with lat/lon columns added
    insert_df = df[["ts", "oat", "oah", "ghi"]].copy()
    insert_df["lat"] = lat
    insert_df["lon"] = lon

    with duckdb.connect(str(db_path)) as conn:
        conn.execute(_SET_UTC)

        before = conn.execute(
            "SELECT COUNT(*) FROM weather_cache WHERE lat = ? AND lon = ?",
            [lat, lon],
        ).fetchone()[0]

        # Bulk insert; skip rows that violate the PRIMARY KEY constraint
        conn.execute(
            """
            INSERT OR IGNORE INTO weather_cache (lat, lon, ts, oat, oah, ghi)
            SELECT lat, lon, ts, oat, oah, ghi FROM insert_df
            """
        )

        after = conn.execute(
            "SELECT COUNT(*) FROM weather_cache WHERE lat = ? AND lon = ?",
            [lat, lon],
        ).fetchone()[0]

    return after - before


# ── Public API ────────────────────────────────────────────────────────────────


def fetch_weather(
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
    cache_db: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Fetch hourly weather for a geographic location over a time range.

    Parameters
    ----------
    lat, lon : float
        Geographic coordinates. Rounded to 4 decimal places internally.
    start, end : datetime
        Inclusive UTC timestamps. Both must be timezone-aware.
    cache_db : Path, optional
        Path to the DuckDB cache file. Defaults to
        ``settings.data_dir / "weather_cache.duckdb"``.

    Returns
    -------
    pd.DataFrame
        Columns: ``["ts", "oat", "oah", "ghi"]``
        ``ts`` is ``datetime64[ns, UTC]``. Rows are ordered by ``ts``.
    """
    db_path = cache_db or _default_cache_db()
    lat = _round_coord(lat)
    lon = _round_coord(lon)

    # Normalise to UTC-aware
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    _init_cache(db_path)

    today = _today_utc()

    # Determine boundary dates
    start_date = start.date()
    end_date = end.date()

    # Check what's already cached
    cached_ts = _cached_timestamps(db_path, lat, lon, start, end)

    # Build list of hour timestamps that need fetching
    all_hours = pd.date_range(start=start, end=end, freq="h", tz="UTC")
    missing = [h for h in all_hours if h not in cached_ts]

    if missing:
        # Determine which API(s) to call based on the boundary
        missing_dates = sorted({h.date() for h in missing})
        archive_dates = [d for d in missing_dates if d < today]
        forecast_dates = [d for d in missing_dates if d >= today]

        fetched_frames: list[pd.DataFrame] = []

        if archive_dates:
            arc_start = archive_dates[0]
            arc_end = archive_dates[-1]
            arc_df = _fetch_from_api(ARCHIVE_URL, lat, lon, arc_start, arc_end)
            # Filter to only missing timestamps
            arc_df = arc_df[arc_df["ts"].isin(set(missing))]
            fetched_frames.append(arc_df)

        if forecast_dates:
            fc_start = forecast_dates[0]
            fc_end = forecast_dates[-1]
            fc_df = _fetch_from_api(FORECAST_URL, lat, lon, fc_start, fc_end)
            fc_df = fc_df[fc_df["ts"].isin(set(missing))]
            fetched_frames.append(fc_df)

        if fetched_frames:
            combined = pd.concat(fetched_frames, ignore_index=True)
            _insert_into_cache(db_path, lat, lon, combined)

    # Read the full requested range from cache
    result = _query_cache(db_path, lat, lon, start, end)
    return result.reset_index(drop=True)[["ts", "oat", "oah", "ghi"]]


# ── CLI (backfill) ────────────────────────────────────────────────────────────


def _backfill(start_str: str, end_str: str) -> tuple[int, int]:
    """
    Backfill weather data for the hospital location.

    Returns (new_rows, total_rows).
    """
    # Round ONCE so COUNT queries and fetch_weather use the same key
    lat = _round_coord(settings.hospital_lat)
    lon = _round_coord(settings.hospital_lon)

    start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(end_str).replace(hour=23, tzinfo=timezone.utc)

    db_path = _default_cache_db()
    _init_cache(db_path)

    # Count rows before
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(_SET_UTC)
        before = conn.execute(
            "SELECT COUNT(*) FROM weather_cache WHERE lat = ? AND lon = ? AND ts >= ? AND ts <= ?",
            [lat, lon, start, end],
        ).fetchone()[0]

    df = fetch_weather(lat=lat, lon=lon, start=start, end=end, cache_db=db_path)
    total_rows = len(df)

    # Count rows after
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(_SET_UTC)
        after = conn.execute(
            "SELECT COUNT(*) FROM weather_cache WHERE lat = ? AND lon = ? AND ts >= ? AND ts <= ?",
            [lat, lon, start, end],
        ).fetchone()[0]

    new_rows = after - before
    return new_rows, total_rows


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Open-meteo weather adapter CLI",
        prog="python -m backend.core.external.weather_openmeteo",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backfill_parser = subparsers.add_parser("backfill", help="Backfill weather cache")
    backfill_parser.add_argument(
        "--start",
        required=True,
        metavar="YYYY-MM-DD",
        help="Start date (inclusive)",
    )
    backfill_parser.add_argument(
        "--end",
        required=True,
        metavar="YYYY-MM-DD",
        help="End date (inclusive)",
    )

    args = parser.parse_args()

    if args.command == "backfill":
        try:
            new_rows, total_rows = _backfill(args.start, args.end)
        except OpenMeteoError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Backfilled {total_rows} hours; cached {new_rows} new rows.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
