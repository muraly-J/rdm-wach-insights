"""
core/healthdb.py
────────────────
DuckDB-backed Health Database.

Stores hourly FAIR health scores for all AHUs.
Column names mirror data/health_hourly.csv exactly.

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
import duckdb
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'healthdb.duckdb'
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS health_hourly (
    timestamp                  TIMESTAMPTZ NOT NULL,
    ahu_id                     VARCHAR     NOT NULL,
    level                      INTEGER     NOT NULL,
    health_index               FLOAT,
    tier                       VARCHAR,
    energy_anomaly             FLOAT,
    pf_degradation             FLOAT,
    phase_imbalance            FLOAT,
    thd_drift                  FLOAT,
    overload                   FLOAT,
    raw_power_total            FLOAT,
    raw_energy_import          FLOAT,
    raw_hourly_delta           FLOAT,
    raw_predicted_delta        FLOAT,
    raw_energy_anomaly_raw     FLOAT,
    raw_power_factor_avg       FLOAT,
    raw_current_unbalance      FLOAT,
    raw_composite_thd          FLOAT,
    raw_apparent_power_total   FLOAT,
    raw_current_l1             FLOAT,
    raw_current_l2             FLOAT,
    raw_current_l3             FLOAT,
    raw_volts_l1_n             FLOAT,
    raw_volts_l2_n             FLOAT,
    raw_volts_l3_n             FLOAT,
    raw_current_l1_thd         FLOAT,
    raw_current_l3_thd         FLOAT,
    raw_volts_l1_thd           FLOAT,
    raw_volts_l2_thd           FLOAT,
    raw_volts_l3_thd           FLOAT,
    raw_nema_voltage_imbalance FLOAT,
    raw_p95_current            FLOAT,
    safety_flags               VARCHAR DEFAULT '',
    PRIMARY KEY (timestamp, ahu_id)
);
CREATE INDEX IF NOT EXISTS idx_ahu_time   ON health_hourly (ahu_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_level_time ON health_hourly (level, timestamp);
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

    # ── Write ──────────────────────────────────────────────────────────────────

    def upsert(self, df: pd.DataFrame) -> int:
        """
        Insert or replace rows. df must contain all schema columns.
        Returns number of rows written.
        """
        with self._conn(write=True) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO health_hourly SELECT * FROM df"
            )
        return len(df)

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_latest_snapshot(
        self,
        ahu_ids: Optional[list] = None,
        level: Optional[int] = None,
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
        ahu_ids: Optional[list] = None,
        level: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        metrics: Optional[list] = None,
    ) -> pd.DataFrame:
        """
        Return rows within a time window, optionally filtered by device/level.
        metrics: list of column names to return (None = all columns).
        Capped at 5000 rows to prevent overloading the context window.
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
        query = f"""
            SELECT {col_clause}
            FROM health_hourly
            {where}
            ORDER BY timestamp DESC
            LIMIT 5000
        """
        with self._conn() as conn:
            return conn.execute(query, params).df()

    def get_ranking(
        self,
        level: Optional[int],
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
        if level is not None:
            query = f"""
                SELECT ahu_id, level, health_index, {metric}, timestamp
                FROM health_hourly
                WHERE level = ?
                QUALIFY ROW_NUMBER() OVER (PARTITION BY ahu_id ORDER BY timestamp DESC) = 1
                ORDER BY {metric} {direction}
                LIMIT ?
            """
            params = [level, n]
        else:
            query = f"""
                SELECT ahu_id, level, health_index, {metric}, timestamp
                FROM health_hourly
                QUALIFY ROW_NUMBER() OVER (PARTITION BY ahu_id ORDER BY timestamp DESC) = 1
                ORDER BY {metric} {direction}
                LIMIT ?
            """
            params = [n]
        with self._conn() as conn:
            return conn.execute(query, params).df()

    def get_latest_timestamp(self) -> Optional[datetime]:
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
