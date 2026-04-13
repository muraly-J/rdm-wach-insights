from __future__ import annotations

"""
core/healthdb.py
────────────────
DuckDB-backed Health Database.

Stores hourly FAIR health scores for all AHUs.

Usage:
  db = HealthDB()                          # default path: data/healthdb.duckdb
  db = HealthDB('/tmp/test.duckdb')        # custom path (tests)
  db.upsert(df)                            # insert/replace rows
  db.get_latest_snapshot(level=3)          # latest row per AHU
  db.get_time_range('e0101', start, end)   # time-window slice
  db.get_ranking(level=3, metric='health_index', n=5, order='asc')
  db.get_latest_timestamp()                # for gap-fill scheduling
"""

import os
from datetime import datetime, timezone

import duckdb
import pandas as pd
from config import settings

# Use environment variable if set, else use settings.data_dir,
# customizable via HEALTH_DB_PATH environment variable
if settings.app_env != 'development':
    # Production (Railway): use /tmp which persists for the deployment lifetime
    _DEFAULT_DB_PATH = '/tmp/healthdb.duckdb'
else:
    # Local development: use data/ directory
    _DEFAULT_DB_PATH = str(settings.data_dir / 'healthdb.duckdb')

_PREDICTIONS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    timestamp       TIMESTAMPTZ NOT NULL,
    ahu_id          VARCHAR     NOT NULL,
    level           INTEGER     NOT NULL,
    energy_current  FLOAT,
    hourly_delta    FLOAT,
    predicted_delta FLOAT,
    energy_anomaly  FLOAT,
    yesterday_kwh   FLOAT,
    delta_yesterday FLOAT,
    last_week_kwh   FLOAT,
    delta_last_week FLOAT,
    two_weeks_kwh          FLOAT,
    delta_two_weeks        FLOAT,
    available_delta_slots  INTEGER,
    insufficient_history   BOOLEAN,
    PRIMARY KEY (timestamp, ahu_id)
);
"""

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS health_hourly (
    timestamp                       TIMESTAMPTZ NOT NULL,
    ahu_id                          VARCHAR     NOT NULL,
    level                           INTEGER     NOT NULL,
    -- FAIR health scores
    health_index                    FLOAT,
    tier                            VARCHAR,
    energy_anomaly                  FLOAT,
    pf_degradation                  FLOAT,
    phase_imbalance                 FLOAT,
    thd_drift                       FLOAT,
    overload                        FLOAT,
    -- Derived / computed columns (not direct InfluxDB reads)
    raw_hourly_delta                FLOAT,
    raw_predicted_delta             FLOAT,
    raw_energy_anomaly_raw          FLOAT,
    raw_composite_thd               FLOAT,
    raw_nema_voltage_imbalance      FLOAT,
    raw_p95_current                 FLOAT,
    -- All 46 raw InfluxDB metrics (prefixed raw_)
    raw_power_total                 FLOAT,
    raw_power_l1                    FLOAT,
    raw_power_l2                    FLOAT,
    raw_power_l3                    FLOAT,
    raw_power_demand                FLOAT,
    raw_max_power_demand            FLOAT,
    raw_apparent_power_total        FLOAT,
    raw_apparent_power_l1           FLOAT,
    raw_apparent_power_l2           FLOAT,
    raw_apparent_power_l3           FLOAT,
    raw_apparent_power_demand       FLOAT,
    raw_reactive_power_total        FLOAT,
    raw_reactive_power_l1           FLOAT,
    raw_reactive_power_l2           FLOAT,
    raw_reactive_power_l3           FLOAT,
    raw_reactive_power_demand       FLOAT,
    raw_energy_import               FLOAT,
    raw_energy_export               FLOAT,
    raw_reactive_energy_import      FLOAT,
    raw_reactive_energy_export      FLOAT,
    raw_apparent_energy             FLOAT,
    raw_current_avg                 FLOAT,
    raw_current_l1                  FLOAT,
    raw_current_l2                  FLOAT,
    raw_current_l3                  FLOAT,
    raw_current_l1_thd              FLOAT,
    raw_current_l3_thd              FLOAT,
    raw_current_unbalance           FLOAT,
    raw_power_factor_avg            FLOAT,
    raw_power_factor_l1             FLOAT,
    raw_power_factor_l2             FLOAT,
    raw_power_factor_l3             FLOAT,
    raw_freq                        FLOAT,
    raw_volts_l_n_avg               FLOAT,
    raw_volts_l_l_avg               FLOAT,
    raw_volts_l1_n                  FLOAT,
    raw_volts_l2_n                  FLOAT,
    raw_volts_l3_n                  FLOAT,
    raw_volts_l1_l2                 FLOAT,
    raw_volts_l2_l3                 FLOAT,
    raw_volts_l3_l1                 FLOAT,
    raw_volts_l1_thd                FLOAT,
    raw_volts_l2_thd                FLOAT,
    raw_volts_l3_thd                FLOAT,
    raw_volts_unbalance             FLOAT,
    raw_digital_input_1_and_2       FLOAT,
    safety_flags                    VARCHAR DEFAULT '',
    PRIMARY KEY (timestamp, ahu_id)
);
CREATE INDEX IF NOT EXISTS idx_ahu_time   ON health_hourly (ahu_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_level_time ON health_hourly (level, timestamp);
"""

# ALTER statements to migrate existing databases — safe to run repeatedly
# (DuckDB silently ignores ADD COLUMN if the column already exists via IF NOT EXISTS)
_MIGRATE_SCHEMA_SQL = """
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS health_index                 FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS tier                         VARCHAR;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_power_l1                 FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_power_l2                 FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_power_l3                 FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_power_demand             FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_max_power_demand         FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_apparent_power_l1        FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_apparent_power_l2        FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_apparent_power_l3        FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_apparent_power_demand    FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_reactive_power_total     FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_reactive_power_l1        FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_reactive_power_l2        FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_reactive_power_l3        FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_reactive_power_demand    FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_energy_export            FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_reactive_energy_import   FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_reactive_energy_export   FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_apparent_energy          FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_current_avg              FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_power_factor_l1          FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_power_factor_l2          FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_power_factor_l3          FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_freq                     FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_volts_l_n_avg            FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_volts_l_l_avg            FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_volts_l1_l2              FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_volts_l2_l3              FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_volts_l3_l1              FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_volts_unbalance          FLOAT;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS raw_digital_input_1_and_2   FLOAT;
"""


class HealthDB:
    """DuckDB-backed time-series store for AHU health scores."""

    def __init__(self, path: str = _DEFAULT_DB_PATH):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._ensure_schema()

    def _conn(self, write: bool = False) -> duckdb.DuckDBPyConnection:
        """Open a short-lived connection. Caller must close or use as context manager."""
        return duckdb.connect(self.path, read_only=not write)

    def _ensure_schema(self):
        with self._conn(write=True) as conn:
            conn.execute(_SCHEMA_SQL)
            conn.execute(_PREDICTIONS_SCHEMA_SQL)
            # Migrate existing DBs: add new columns (no-op if already present)
            for stmt in _MIGRATE_SCHEMA_SQL.strip().split(';'):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(stmt)

    # ── Write ──────────────────────────────────────────────────────────────────

    def upsert(self, df: pd.DataFrame) -> int:
        """
        Insert or replace rows. df may contain a subset of schema columns;
        missing columns are left as NULL. Returns number of rows written.
        """
        cols = ", ".join(df.columns.tolist())
        with self._conn(write=True) as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO health_hourly ({cols}) SELECT * FROM df"
            )
        return len(df)

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_latest_snapshot(
        self,
        ahu_ids: list | None = None,
        level: int | None = None,
    ) -> pd.DataFrame:
        """
        Return the most recent row per AHU.
        Filter by ahu_ids list and/or level.
        """
        conditions, params = [], []
        if ahu_ids:
            placeholders = ", ".join("?" * len(ahu_ids))
            conditions.append(f"ahu_id IN ({placeholders})")
            params.extend(ahu_ids)
        if level is not None:
            conditions.append("level = ?")
            params.append(level)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM health_hourly
            {where}
            QUALIFY ROW_NUMBER() OVER (PARTITION BY ahu_id ORDER BY timestamp DESC) = 1
            ORDER BY ahu_id
        """
        with self._conn() as conn:
            return conn.execute(query, params).df()

    def get_time_range(
        self,
        ahu_ids: list | None = None,
        level: int | None = None,
        start: str | None = None,
        end: str | None = None,
        metrics: list | None = None,
        limit: int | None = 5000,
    ) -> pd.DataFrame:
        """
        Return rows within a time window, optionally filtered by device/level.
        metrics: list of column names to return (None = all columns).
        limit: max rows to return (None = no cap; default 5000).
        """
        conditions, params = [], []
        if ahu_ids:
            placeholders = ", ".join("?" * len(ahu_ids))
            conditions.append(f"ahu_id IN ({placeholders})")
            params.extend(ahu_ids)
        if level is not None:
            conditions.append("level = ?")
            params.append(level)
        if start:
            conditions.append("timestamp >= ?")
            params.append(start)
        if end:
            conditions.append("timestamp <= ?")
            params.append(end)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        col_clause = (
            f"timestamp, ahu_id, level, {', '.join(metrics)}"
            if metrics else "*"
        )
        limit_clause = f"LIMIT {limit}" if limit is not None else ""
        query = f"""
            SELECT {col_clause}
            FROM health_hourly
            {where}
            ORDER BY timestamp ASC
            {limit_clause}
        """
        with self._conn() as conn:
            return conn.execute(query, params).df()

    def get_ranking(
        self,
        level: int | None,
        metric: str,
        n: int = 5,
        order: str = "asc",
    ) -> pd.DataFrame:
        """
        Rank AHUs by metric using their latest reading.
        level: floor to filter to (1–11), or None for all levels.
        order: 'asc' = worst first (lowest value), 'desc' = best first.
        """
        direction = "ASC" if order == "asc" else "DESC"
        # Include tier so callers don't have to infer it from the index value.
        select_cols = f"ahu_id, level, health_index, tier, {metric}, timestamp"
        if level is not None:
            query = f"""
                SELECT {select_cols}
                FROM health_hourly
                WHERE level = ?
                QUALIFY ROW_NUMBER() OVER (PARTITION BY ahu_id ORDER BY timestamp DESC) = 1
                ORDER BY {metric} {direction}
                LIMIT ?
            """
            params = [level, n]
        else:
            query = f"""
                SELECT {select_cols}
                FROM health_hourly
                QUALIFY ROW_NUMBER() OVER (PARTITION BY ahu_id ORDER BY timestamp DESC) = 1
                ORDER BY {metric} {direction}
                LIMIT ?
            """
            params = [n]
        with self._conn() as conn:
            return conn.execute(query, params).df()

    def get_latest_timestamp(self) -> datetime | None:
        """Return the most recent timestamp in the DB, or None if empty."""
        with self._conn() as conn:
            result = conn.execute(
                "SELECT MAX(timestamp) FROM health_hourly"
            ).fetchone()
        if result and result[0] is not None:
            ts = result[0]
            if hasattr(ts, 'tzinfo') and ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(timezone.utc)
        return None

    def upsert_predictions(self, df: pd.DataFrame) -> int:
        """Insert or replace prediction rows."""
        _PREDICTION_COLS = [
            "timestamp", "ahu_id", "level", "energy_current", "hourly_delta",
            "predicted_delta", "energy_anomaly", "yesterday_kwh", "delta_yesterday",
            "last_week_kwh", "delta_last_week", "two_weeks_kwh", "delta_two_weeks",
            "available_delta_slots", "insufficient_history",
        ]
        cols = [c for c in _PREDICTION_COLS if c in df.columns]
        col_list = ", ".join(cols)
        with self._conn(write=True) as conn:
            conn.register("sub", df[cols])
            conn.execute(
                f"INSERT OR REPLACE INTO predictions ({col_list}) SELECT * FROM sub"
            )
        return len(df)

    def get_all_predictions(
        self,
        ahu_ids: list | None = None,
    ) -> pd.DataFrame:
        """Return all prediction rows, optionally filtered by device."""
        conditions, params = [], []
        if ahu_ids:
            placeholders = ", ".join("?" * len(ahu_ids))
            conditions.append(f"ahu_id IN ({placeholders})")
            params.extend(ahu_ids)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._conn() as conn:
            return conn.execute(
                f"SELECT * FROM predictions {where} ORDER BY timestamp", params
            ).df()

    def get_latest_predictions(
        self,
        ahu_ids: list | None = None,
    ) -> pd.DataFrame:
        """Return the most recent prediction row per AHU."""
        conditions, params = [], []
        if ahu_ids:
            placeholders = ", ".join("?" * len(ahu_ids))
            conditions.append(f"ahu_id IN ({placeholders})")
            params.extend(ahu_ids)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM predictions
            {where}
            QUALIFY ROW_NUMBER() OVER (PARTITION BY ahu_id ORDER BY timestamp DESC) = 1
            ORDER BY ahu_id
        """
        with self._conn() as conn:
            return conn.execute(query, params).df()
