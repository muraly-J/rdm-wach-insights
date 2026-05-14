from __future__ import annotations

"""
core/etl/feature_builder.py
────────────────────────────
Hourly AHU feature engineering pipeline.

Public API
----------
    build_features(ahu_id, start, end, *, provider, ...) -> pd.DataFrame

The returned DataFrame conforms to ``models.feature_schema.AHUFeatureRow``
(one row per hour in [start, end)) and is persisted to a DuckDB cache at
``settings.data_dir / "ahu_features.duckdb"`` unless ``persist=False``.

Architecture
------------
This module has ZERO imports from InfluxDB or open-meteo.  All external data
is injected via the ``RawTelemetryProvider`` Protocol and the optional
``weather`` DataFrame argument.
"""

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Literal

import duckdb
import pandas as pd

from config import settings
from core.external.holidays_my import is_holiday as _default_is_holiday
from core.logger import get_logger
from models.feature_schema import AHUFeatureRow

logger = get_logger(__name__)

# ── AHU ID validation ─────────────────────────────────────────────────────────

_AHU_ID_RE = re.compile(r"^e\d{4}$")


def _build_all_device_ids() -> frozenset[str]:
    """Build the set of all valid AHU IDs from AHU_LEVEL_CONFIG at import time."""
    from models.schemas import AHU_LEVEL_CONFIG  # noqa: PLC0415

    ids: set[str] = set()
    for level_conf in AHU_LEVEL_CONFIG.values():
        ids.update(level_conf["device_ids"])
    return frozenset(ids)


_ALL_DEVICE_IDS: frozenset[str] = _build_all_device_ids()


def _validate_ahu_id(ahu_id: str) -> None:
    """Raise ValueError if *ahu_id* is not a valid, known AHU device ID."""
    if not _AHU_ID_RE.match(ahu_id):
        raise ValueError(
            f"Invalid AHU ID format: {ahu_id!r}. Must match ^e\\d{{4}}$."
        )
    if ahu_id not in _ALL_DEVICE_IDS:
        raise ValueError(
            f"AHU ID {ahu_id!r} is not in AHU_LEVEL_CONFIG. "
            "Only known device IDs are accepted."
        )


# ── DuckDB helpers ────────────────────────────────────────────────────────────

_SET_UTC = "SET TimeZone = 'UTC'"

# DDL for the ahu_features table.
# IMPORTANT: must remain byte-equivalent (modulo whitespace) to
# backend/data/migrations/0002_ahu_features.duckdb.sql.
# The two are intentionally maintained as a pair: this tuple is used at
# runtime; the .sql file is the human-readable migration artefact.
_AHU_FEATURES_DDL_STATEMENTS: tuple[str, ...] = (
    """
CREATE TABLE IF NOT EXISTS ahu_features (
    ahu_id                          TEXT NOT NULL,
    ts                              TIMESTAMP NOT NULL,
    hourly_energy_kwh               DOUBLE,
    total_tons                      DOUBLE,
    sat                             DOUBLE,
    sat_minus_rat                   DOUBLE,
    rat                             DOUBLE,
    rah                             DOUBLE,
    co2                             DOUBLE,
    wst                             DOUBLE,
    wrt                             DOUBLE,
    wst_minus_wrt                   DOUBLE,
    oat                             DOUBLE,
    oah                             DOUBLE,
    ghi                             DOUBLE,
    rat_sp                          DOUBLE,
    co2_sp                          DOUBLE,
    rah_sp                          DOUBLE,
    dsp_sp                          DOUBLE,
    dsp                             DOUBLE,
    dsp_dev                         DOUBLE,
    fa_dmpr                         DOUBLE,
    fa_dmpr_min                     DOUBLE,
    mvlv                            DOUBLE,
    mcvlv                           DOUBLE,
    oct                             BOOLEAN,
    am                              BOOLEAN,
    vsd_fb                          DOUBLE,
    vsd_ctrl                        DOUBLE,
    vsd_dev                         DOUBLE,
    fltr                            BOOLEAN,
    sts                             BOOLEAN,
    dp                              DOUBLE,
    runtime                         INTEGER,
    power_factor_avg                DOUBLE,
    hour_of_day                     INTEGER NOT NULL,
    day_of_week                     INTEGER NOT NULL,
    is_weekend                      BOOLEAN NOT NULL,
    is_holiday                      BOOLEAN NOT NULL,
    energy_lag_1h                   DOUBLE,
    energy_lag_24h                  DOUBLE,
    energy_lag_168h                 DOUBLE,
    energy_rolling_24h_mean         DOUBLE,
    total_tons_rolling_24h_mean     DOUBLE,
    oat_rolling_24h_mean            DOUBLE,
    PRIMARY KEY (ahu_id, ts)
)
""",
    "CREATE INDEX IF NOT EXISTS idx_ahu_features_ts ON ahu_features (ts)",
)


def _open(cache_db: Path) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection with the session timezone set to UTC."""
    conn = duckdb.connect(str(cache_db))
    conn.execute(_SET_UTC)
    return conn


def _init_cache(db_path: Path) -> None:
    """Ensure ahu_features table and index exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _open(db_path) as conn:
        for stmt in _AHU_FEATURES_DDL_STATEMENTS:
            conn.execute(stmt)


def _default_cache_db() -> Path:
    return settings.data_dir / "ahu_features.duckdb"


# ── Column order expected by AHUFeatureRow ────────────────────────────────────

_FEATURE_COLUMNS: list[str] = list(AHUFeatureRow.model_fields.keys())


# ── Main feature builder ──────────────────────────────────────────────────────


def build_features(
    ahu_id: str,
    start: datetime,
    end: datetime,
    *,
    provider: object,  # RawTelemetryProvider — untyped to avoid circular imports
    cache_db: Path | None = None,
    weather: pd.DataFrame | None = None,
    holidays_fn: Callable[[date], bool] | None = None,
    am_policy: Literal["drop_for_training", "keep_with_flag"] = "drop_for_training",
    persist: bool = True,
) -> pd.DataFrame:
    """Build an hourly feature DataFrame for one AHU over [start, end).

    Parameters
    ----------
    ahu_id : str
        AHU device identifier.  Must match ``^e\\d{4}$`` and be present in
        ``AHU_LEVEL_CONFIG``.
    start, end : datetime
        Half-open interval [start, end) in UTC.  Timezone-naive datetimes
        are treated as UTC.
    provider : RawTelemetryProvider
        Injected telemetry source (use ``FakeTelemetryProvider`` in tests,
        ``InfluxTelemetryProvider`` in production).
    cache_db : Path, optional
        DuckDB file path for the persistent cache.  Defaults to
        ``settings.data_dir / "ahu_features.duckdb"``.
    weather : pd.DataFrame, optional
        Pre-fetched weather with columns ``["ts", "oat", "oah", "ghi"]``.
        When ``None``, ``core.external.weather_openmeteo.fetch_weather`` is
        called automatically.
    holidays_fn : Callable[[date], bool], optional
        Function that returns True for public holidays.  When ``None``,
        ``core.external.holidays_my.is_holiday`` is used.
    am_policy : {"drop_for_training", "keep_with_flag"}
        ``drop_for_training`` — drop rows where ``am==1`` or ``sts==0``.
        ``keep_with_flag``    — keep all rows; callers filter themselves.
    persist : bool
        When True (default), persist the resulting rows to DuckDB.

    Returns
    -------
    pd.DataFrame
        Columns match ``AHUFeatureRow.model_fields.keys()``, one row per hour.
    """
    # ── Step 1: validate AHU ID ────────────────────────────────────────────────
    _validate_ahu_id(ahu_id)

    # ── Normalise timestamps to UTC ───────────────────────────────────────────
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    # ── Step 2: fetch telemetry ────────────────────────────────────────────────
    tele = provider.fetch_hourly(ahu_id, start, end)  # type: ignore[union-attr]
    tele = tele.sort_values("ts").reset_index(drop=True)

    # Ensure ts is UTC-aware
    if tele["ts"].dt.tz is None:
        tele["ts"] = tele["ts"].dt.tz_localize("UTC")
    else:
        tele["ts"] = tele["ts"].dt.tz_convert("UTC")

    # ── Step 3: fetch weather ─────────────────────────────────────────────────
    if weather is None:
        from core.external.weather_openmeteo import fetch_weather  # noqa: PLC0415

        weather = fetch_weather(
            settings.hospital_lat,
            settings.hospital_lon,
            start,
            end,
        )

    # Normalise weather ts to UTC-aware
    wx = weather.copy()
    if wx["ts"].dt.tz is None:
        wx["ts"] = wx["ts"].dt.tz_localize("UTC")
    else:
        wx["ts"] = wx["ts"].dt.tz_convert("UTC")

    # ── Step 4: left-merge weather onto telemetry on ts ───────────────────────
    df = tele.merge(wx[["ts", "oat", "oah", "ghi"]], on="ts", how="left")

    # ── Step 5: holiday flag ──────────────────────────────────────────────────
    _hol_fn = holidays_fn if holidays_fn is not None else _default_is_holiday
    df["is_holiday"] = df["ts"].apply(lambda t: bool(_hol_fn(t.date())))

    # ── Step 6: derived columns ───────────────────────────────────────────────
    df["sat_minus_rat"] = df["sat"] - df["rat"]
    df["wst_minus_wrt"] = df["wst"] - df["wrt"]
    df["dsp_dev"] = df["dsp"] - df["dsp_sp"]
    df["vsd_dev"] = df["vsd_fb"] - df["vsd_ctrl"]

    # ── Step 7: target (energy_import_kwh is already the hourly delta) ────────
    df["hourly_energy_kwh"] = df["energy_import_kwh"]

    # ── Step 8: lag features ───────────────────────────────────────────────────
    df["energy_lag_1h"] = df["hourly_energy_kwh"].shift(1)
    df["energy_lag_24h"] = df["hourly_energy_kwh"].shift(24)
    df["energy_lag_168h"] = df["hourly_energy_kwh"].shift(168)

    # ── Step 9: rolling means (trailing 24h, min 12 periods) ─────────────────
    df["energy_rolling_24h_mean"] = (
        df["hourly_energy_kwh"].rolling(window=24, min_periods=12).mean()
    )
    df["total_tons_rolling_24h_mean"] = (
        df["total_tons"].rolling(window=24, min_periods=12).mean()
    )
    df["oat_rolling_24h_mean"] = (
        df["oat"].rolling(window=24, min_periods=12).mean()
    )

    # ── Step 10: temporal features ────────────────────────────────────────────
    df["hour_of_day"] = df["ts"].dt.hour
    df["day_of_week"] = df["ts"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"] >= 5

    # ── Step 11: apply am_policy ──────────────────────────────────────────────
    if am_policy == "drop_for_training":
        # Convert before filtering to handle float 0/1 representations
        sts_drop = (df["sts"].astype(float) == 0.0) | df["sts"].isna()
        am_drop = df["am"].astype(float) == 1.0
        df = df[~sts_drop & ~am_drop].reset_index(drop=True)

    # ── Step 12: type coercions ───────────────────────────────────────────────
    # Discrete signals → bool
    for col in ("sts", "am", "oct", "fltr"):
        df[col] = df[col].astype(float).map(lambda v: bool(v) if not pd.isna(v) else False).astype(bool)

    # Temporal booleans → bool (guaranteed non-null)
    df["is_weekend"] = df["is_weekend"].astype(bool)
    df["is_holiday"] = df["is_holiday"].astype(bool)

    # Integer columns
    df["runtime"] = df["runtime"].fillna(0).round().astype(int)
    df["hour_of_day"] = df["hour_of_day"].astype(int)
    df["day_of_week"] = df["day_of_week"].astype(int)

    # All other numeric columns stay float (NaN → None semantically)

    # ── Add identity columns ──────────────────────────────────────────────────
    df["ahu_id"] = ahu_id

    # ── Step 13: reorder to match AHUFeatureRow column order ─────────────────
    df = df[_FEATURE_COLUMNS].reset_index(drop=True)

    # ── Persist to DuckDB ─────────────────────────────────────────────────────
    if persist:
        db_path = cache_db if cache_db is not None else _default_cache_db()
        _init_cache(db_path)
        _persist(df, ahu_id, db_path)

    return df


# ── DuckDB persistence ────────────────────────────────────────────────────────


def _persist(df: pd.DataFrame, ahu_id: str, db_path: Path) -> int:
    """
    Insert rows from *df* into ahu_features.  INSERT OR IGNORE is used so
    re-running on the same (ahu_id, ts) range inserts 0 new rows.

    Returns the count of newly inserted rows.
    """
    if df.empty:
        return 0

    # Prepare insert DataFrame: convert tz-aware ts to naive UTC for TIMESTAMP
    insert_df = df.copy()
    if insert_df["ts"].dt.tz is not None:
        insert_df["ts"] = insert_df["ts"].dt.tz_convert("UTC").dt.tz_localize(None)

    with _open(db_path) as conn:
        before = conn.execute(
            "SELECT COUNT(*) FROM ahu_features WHERE ahu_id = ?",
            [ahu_id],
        ).fetchone()[0]

        conn.execute(
            """
            INSERT OR IGNORE INTO ahu_features
            SELECT * FROM insert_df
            """
        )

        after = conn.execute(
            "SELECT COUNT(*) FROM ahu_features WHERE ahu_id = ?",
            [ahu_id],
        ).fetchone()[0]

    new_rows = after - before
    logger.info(
        "ahu_features persist: ahu_id=%s new_rows=%d total_rows=%d",
        ahu_id,
        new_rows,
        after,
    )
    return new_rows
