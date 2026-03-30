# Chatbot V2 Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the chatbot's CSV-based context-stuffing with a DuckDB Health DB, five callable tools, and a heuristic thinking-mode classifier.

**Architecture:** The ETL pipeline writes FAIR-scored health data to `data/healthdb.duckdb` (DuckDB, embedded). The chat endpoint drops all pre-loaded context injection and instead gives Qwen3 five tool definitions; the model calls them on demand. A lightweight query classifier prepends `/think` or `/no_think` to each message before it reaches the model.

**Tech Stack:** Python 3.11, DuckDB, FastAPI, OpenAI SDK (tool calling), pytest, pandas

---

## Schema Note

The actual CSV column for device IDs is `ahu_id` (not `device_id` as in the design spec). The DuckDB schema uses `ahu_id` to match the CSV exactly, simplifying migration. The `safety_flags` column is a single `VARCHAR` containing comma-separated flag names (e.g. `"THD_CHRONIC_HIGH,PF_CHRONIC_LOW"`), not separate booleans.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/core/healthdb.py` | DuckDB connection, schema creation, all query methods |
| Create | `backend/core/query_classifier.py` | Heuristic think/fast classifier |
| Create | `backend/tools/__init__.py` | Package marker |
| Create | `backend/tools/tool_registry.py` | OpenAI-format tool definitions + async dispatcher |
| Create | `backend/tools/health_tools.py` | Tool handler implementations |
| Create | `scripts/etl/migrate_csv_to_duckdb.py` | One-time CSV → DuckDB migration |
| Create | `backend/tests/test_healthdb.py` | HealthDB unit tests |
| Create | `backend/tests/test_query_classifier.py` | Classifier unit tests |
| Create | `backend/tests/test_tool_registry.py` | Tool dispatcher unit tests |
| Modify | `scripts/etl/run_health_etl.py` | Add `save_health_duckdb()` step after CSV save |
| Modify | `backend/llm/qwen_client.py` | Add `generate_with_tools()` method |
| Modify | `backend/routes/chat.py` | Replace context-stuffing with tool loop + classifier |
| Modify | `backend/requirements.txt` | Add `duckdb>=1.0.0` |

---

## Task 1: DuckDB dependency + HealthDB schema

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/core/healthdb.py`
- Create: `backend/tests/test_healthdb.py`

- [ ] **Step 1.1: Write the failing test**

```python
# backend/tests/test_healthdb.py
import os
import sys
import pytest
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.healthdb import HealthDB


@pytest.fixture
def db(tmp_path):
    """Fresh in-file HealthDB for each test."""
    return HealthDB(str(tmp_path / "test.duckdb"))


def test_schema_created(db):
    """Tables and indexes are created on init."""
    result = db._conn().execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name='health_hourly'"
    ).fetchone()
    assert result is not None, "health_hourly table should exist"


def test_upsert_and_count(db):
    """upsert() inserts rows; duplicate primary keys replace."""
    df = pd.DataFrame([{
        "timestamp": pd.Timestamp("2026-03-01 00:00:00", tz="UTC"),
        "ahu_id": "e0101", "level": 1,
        "health_index": 85.0, "tier": "Healthy",
        "energy_anomaly": 0.0, "pf_degradation": 0.0,
        "phase_imbalance": 0.0, "thd_drift": 0.0, "overload": 0.0,
        "raw_power_total": 10.0, "raw_energy_import": 100.0,
        "raw_hourly_delta": 1.0, "raw_predicted_delta": 1.0,
        "raw_energy_anomaly_raw": 0.0, "raw_power_factor_avg": 0.92,
        "raw_current_unbalance": 1.0, "raw_composite_thd": 2.0,
        "raw_apparent_power_total": 11.0,
        "raw_current_l1": 5.0, "raw_current_l2": 5.0, "raw_current_l3": 5.0,
        "raw_volts_l1_n": 230.0, "raw_volts_l2_n": 230.0, "raw_volts_l3_n": 230.0,
        "raw_current_l1_thd": 2.0, "raw_current_l3_thd": 2.0,
        "raw_volts_l1_thd": 1.0, "raw_volts_l2_thd": 1.0, "raw_volts_l3_thd": 1.0,
        "raw_nema_voltage_imbalance": 0.5, "raw_p95_current": 6.0,
        "safety_flags": "",
    }])
    rows = db.upsert(df)
    assert rows == 1

    # Upsert same primary key with updated value
    df2 = df.copy()
    df2["health_index"] = 70.0
    db.upsert(df2)

    result = db._conn().execute(
        "SELECT health_index FROM health_hourly WHERE ahu_id='e0101'"
    ).fetchone()
    assert result[0] == pytest.approx(70.0), "Duplicate PK should update value"
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_healthdb.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.healthdb'`

- [ ] **Step 1.3: Add duckdb to requirements.txt**

Add this line to `backend/requirements.txt`:
```
duckdb>=1.0.0
```

Install it:
```bash
cd backend && pip install duckdb>=1.0.0
```

- [ ] **Step 1.4: Create `backend/core/healthdb.py`**

```python
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
        ahu_ids: Optional[list[str]] = None,
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
        ahu_ids: Optional[list[str]] = None,
        level: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        metrics: Optional[list[str]] = None,
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
        base_cols = "timestamp, ahu_id, level"
        extra_cols = (", " + ", ".join(metrics)) if metrics else ", *"
        # When metrics specified, select only those + identity columns
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
        level: int,
        metric: str,
        n: int = 5,
        order: str = "asc",
    ) -> pd.DataFrame:
        """
        Rank AHUs within a level by metric using their latest reading.
        order: 'asc' = worst first (lowest value), 'desc' = best first.
        """
        direction = "ASC" if order == "asc" else "DESC"
        query = f"""
            SELECT ahu_id, level, health_index, {metric}, timestamp
            FROM health_hourly
            WHERE level = ?
            QUALIFY ROW_NUMBER() OVER (PARTITION BY ahu_id ORDER BY timestamp DESC) = 1
            ORDER BY {metric} {direction}
            LIMIT ?
        """
        with self._conn() as conn:
            return conn.execute(query, [level, n]).df()

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
            return ts
        return None
```

- [ ] **Step 1.5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_healthdb.py -v
```

Expected output:
```
tests/test_healthdb.py::test_schema_created PASSED
tests/test_healthdb.py::test_upsert_and_count PASSED
```

- [ ] **Step 1.6: Commit**

```bash
git add backend/requirements.txt backend/core/healthdb.py backend/tests/test_healthdb.py
git commit -m "feat(healthdb): add DuckDB health database with schema and upsert"
```

---

## Task 2: HealthDB query method tests

**Files:**
- Modify: `backend/tests/test_healthdb.py` (add query tests)

- [ ] **Step 2.1: Add query tests to `backend/tests/test_healthdb.py`**

Append these tests to the existing file:

```python
# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_row(ahu_id: str, level: int, timestamp: str, health_index: float) -> dict:
    return {
        "timestamp": pd.Timestamp(timestamp, tz="UTC"),
        "ahu_id": ahu_id, "level": level,
        "health_index": health_index, "tier": "Healthy",
        "energy_anomaly": 0.1, "pf_degradation": 0.2,
        "phase_imbalance": 0.1, "thd_drift": 0.05, "overload": 0.0,
        "raw_power_total": 10.0, "raw_energy_import": 100.0,
        "raw_hourly_delta": 1.0, "raw_predicted_delta": 1.0,
        "raw_energy_anomaly_raw": 0.0, "raw_power_factor_avg": 0.92,
        "raw_current_unbalance": 1.0, "raw_composite_thd": 2.0,
        "raw_apparent_power_total": 11.0,
        "raw_current_l1": 5.0, "raw_current_l2": 5.0, "raw_current_l3": 5.0,
        "raw_volts_l1_n": 230.0, "raw_volts_l2_n": 230.0, "raw_volts_l3_n": 230.0,
        "raw_current_l1_thd": 2.0, "raw_current_l3_thd": 2.0,
        "raw_volts_l1_thd": 1.0, "raw_volts_l2_thd": 1.0, "raw_volts_l3_thd": 1.0,
        "raw_nema_voltage_imbalance": 0.5, "raw_p95_current": 6.0,
        "safety_flags": "",
    }


@pytest.fixture
def db_with_data(tmp_path):
    db = HealthDB(str(tmp_path / "test.duckdb"))
    rows = [
        _make_row("e0101", 1, "2026-03-27 00:00:00", 85.0),
        _make_row("e0101", 1, "2026-03-27 01:00:00", 83.0),  # latest for e0101
        _make_row("e0102", 1, "2026-03-27 00:00:00", 60.0),
        _make_row("e0102", 1, "2026-03-27 01:00:00", 58.0),  # latest for e0102
        _make_row("e0201", 2, "2026-03-27 01:00:00", 90.0),  # level 2
    ]
    db.upsert(pd.DataFrame(rows))
    return db


def test_get_latest_snapshot_all(db_with_data):
    """Returns one row per AHU (latest timestamp)."""
    result = db_with_data.get_latest_snapshot()
    assert len(result) == 3  # e0101, e0102, e0201
    e0101 = result[result["ahu_id"] == "e0101"].iloc[0]
    assert e0101["health_index"] == pytest.approx(83.0)


def test_get_latest_snapshot_by_level(db_with_data):
    """Filter to one level returns only that level's AHUs."""
    result = db_with_data.get_latest_snapshot(level=1)
    assert set(result["ahu_id"].tolist()) == {"e0101", "e0102"}


def test_get_latest_snapshot_by_ahu_ids(db_with_data):
    """Filter to specific AHU IDs."""
    result = db_with_data.get_latest_snapshot(ahu_ids=["e0101"])
    assert len(result) == 1
    assert result.iloc[0]["ahu_id"] == "e0101"


def test_get_time_range_all(db_with_data):
    """Returns all rows for a device across timestamps."""
    result = db_with_data.get_time_range(ahu_ids=["e0101"])
    assert len(result) == 2


def test_get_time_range_with_start_filter(db_with_data):
    """Start filter excludes earlier rows."""
    result = db_with_data.get_time_range(
        ahu_ids=["e0101"],
        start="2026-03-27T01:00:00Z"
    )
    assert len(result) == 1
    assert result.iloc[0]["health_index"] == pytest.approx(83.0)


def test_get_time_range_metrics_filter(db_with_data):
    """Requesting specific metrics returns only those columns + identity columns."""
    result = db_with_data.get_time_range(
        ahu_ids=["e0101"],
        metrics=["health_index", "pf_degradation"]
    )
    assert "health_index" in result.columns
    assert "pf_degradation" in result.columns
    assert "raw_power_total" not in result.columns


def test_get_ranking_worst_first(db_with_data):
    """asc order returns lowest health_index first (worst AHU first)."""
    result = db_with_data.get_ranking(level=1, metric="health_index", n=2, order="asc")
    assert result.iloc[0]["ahu_id"] == "e0102"  # 58.0 < 83.0


def test_get_ranking_best_first(db_with_data):
    """desc order returns highest health_index first."""
    result = db_with_data.get_ranking(level=1, metric="health_index", n=2, order="desc")
    assert result.iloc[0]["ahu_id"] == "e0101"


def test_get_latest_timestamp(db_with_data):
    """Returns the most recent timestamp across all rows."""
    ts = db_with_data.get_latest_timestamp()
    assert ts is not None
    assert ts.year == 2026
    assert ts.month == 3
    assert ts.day == 27
    assert ts.hour == 1


def test_get_latest_timestamp_empty_db(tmp_path):
    """Returns None when DB is empty."""
    db = HealthDB(str(tmp_path / "empty.duckdb"))
    assert db.get_latest_timestamp() is None
```

- [ ] **Step 2.2: Run tests**

```bash
cd backend && python -m pytest tests/test_healthdb.py -v
```

Expected: all 12 tests pass.

- [ ] **Step 2.3: Commit**

```bash
git add backend/tests/test_healthdb.py
git commit -m "test(healthdb): add comprehensive query method tests"
```

---

## Task 3: ETL write step

**Files:**
- Modify: `scripts/etl/run_health_etl.py`

- [ ] **Step 3.1: Find the save step in `run_health_etl.py`**

Open `scripts/etl/run_health_etl.py` and find the function `save_hourly_health` (around line 979). This is where the ETL currently writes `health_hourly.csv`.

- [ ] **Step 3.2: Add `save_health_duckdb()` function**

Add this function immediately before `save_hourly_health()` in `run_health_etl.py`:

```python
def save_health_duckdb(results_df: pd.DataFrame, dry_run: bool = False) -> None:
    """
    Append/replace computed health scores into data/healthdb.duckdb.

    Called after save_health_csv() as step 3c in the ETL pipeline.
    Idempotent — safe to re-run (upsert on PRIMARY KEY (timestamp, ahu_id)).
    """
    import sys
    import os
    # Add backend to path so we can import HealthDB from the ETL process
    backend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from core.healthdb import HealthDB

    if dry_run:
        print("[DRY-RUN] Would write to healthdb.duckdb (skipping)")
        return

    print("STEP 3c: LOAD - Writing to healthdb.duckdb")
    try:
        db = HealthDB()

        # Rename output columns to match DuckDB schema
        # ETL uses 'device_id'; CSV/DuckDB uses 'ahu_id'
        df = results_df.rename(columns={"device_id": "ahu_id"}) if "device_id" in results_df.columns else results_df.copy()

        # Select only schema columns (drop any extra ETL columns)
        schema_cols = [
            "timestamp", "ahu_id", "level", "health_index", "tier",
            "energy_anomaly", "pf_degradation", "phase_imbalance",
            "thd_drift", "overload", "raw_power_total", "raw_energy_import",
            "raw_hourly_delta", "raw_predicted_delta", "raw_energy_anomaly_raw",
            "raw_power_factor_avg", "raw_current_unbalance", "raw_composite_thd",
            "raw_apparent_power_total", "raw_current_l1", "raw_current_l2",
            "raw_current_l3", "raw_volts_l1_n", "raw_volts_l2_n", "raw_volts_l3_n",
            "raw_current_l1_thd", "raw_current_l3_thd", "raw_volts_l1_thd",
            "raw_volts_l2_thd", "raw_volts_l3_thd", "raw_nema_voltage_imbalance",
            "raw_p95_current", "safety_flags",
        ]
        available = [c for c in schema_cols if c in df.columns]
        missing = [c for c in schema_cols if c not in df.columns]
        if missing:
            for col in missing:
                df[col] = None  # fill missing columns with NULL
        df = df[schema_cols]

        rows = db.upsert(df)
        print(f"[OK] Upserted {rows} rows to healthdb.duckdb")
    except Exception as e:
        print(f"[ERROR] healthdb write failed: {e}")
        # Non-fatal — ETL continues, CSV is still written
```

- [ ] **Step 3.3: Call `save_health_duckdb()` in the ETL pipeline**

In `run_health_etl.py`, find the call to `save_hourly_health(...)` inside `run_etl_pipeline()`. Add the DuckDB call immediately after it:

```python
    # Existing call (keep it)
    save_hourly_health(results_df, output_path=output_hourly)

    # NEW: also write to DuckDB
    save_health_duckdb(results_df, dry_run=dry_run)
```

- [ ] **Step 3.4: Manual smoke test**

```bash
cd /path/to/wach-insight
python scripts/etl/run_health_etl.py --level 1 --dry-run
```

Expected output includes: `[DRY-RUN] Would write to healthdb.duckdb (skipping)`

Then test a real write (requires InfluxDB access):
```bash
python scripts/etl/run_health_etl.py --level 1
# Check for: [OK] Upserted N rows to healthdb.duckdb
```

- [ ] **Step 3.5: Commit**

```bash
git add scripts/etl/run_health_etl.py
git commit -m "feat(etl): write health scores to healthdb.duckdb alongside CSV"
```

---

## Task 4: Migration script

**Files:**
- Create: `scripts/etl/migrate_csv_to_duckdb.py`

- [ ] **Step 4.1: Create `scripts/etl/migrate_csv_to_duckdb.py`**

```python
#!/usr/bin/env python3
"""
migrate_csv_to_duckdb.py
────────────────────────
One-time migration: load data/health_hourly.csv → data/healthdb.duckdb.

Usage:
    python scripts/etl/migrate_csv_to_duckdb.py

Idempotent — safe to re-run. Uses INSERT OR REPLACE so existing rows are
updated and no duplicates are created.

Output:
    Prints rows imported, AHU count, date range covered.
"""
import os
import sys
import pandas as pd

# Add backend to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))

from core.healthdb import HealthDB

CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'health_hourly.csv')
BATCH_SIZE = 10_000


def migrate():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] CSV not found: {CSV_PATH}")
        sys.exit(1)

    print(f"Reading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])

    # Ensure timestamp is tz-aware UTC
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    total_rows = len(df)
    print(f"  Rows in CSV: {total_rows:,}")
    print(f"  AHUs: {df['ahu_id'].nunique()}")
    print(f"  Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")

    db = HealthDB()
    imported = 0
    for start in range(0, total_rows, BATCH_SIZE):
        batch = df.iloc[start:start + BATCH_SIZE]
        db.upsert(batch)
        imported += len(batch)
        pct = imported / total_rows * 100
        print(f"  [{pct:5.1f}%] {imported:,} / {total_rows:,} rows", end="\r")

    print(f"\n[OK] Migration complete — {imported:,} rows imported to data/healthdb.duckdb")

    # Verify
    ts = db.get_latest_timestamp()
    snapshot = db.get_latest_snapshot()
    print(f"  Verification: latest timestamp = {ts}, AHUs in DB = {len(snapshot)}")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 4.2: Run the migration**

```bash
python scripts/etl/migrate_csv_to_duckdb.py
```

Expected output (approximate):
```
Reading data/health_hourly.csv ...
  Rows in CSV: 2,041,920
  AHUs: 121
  Date range: 2026-01-01 00:00:00+00:00 → 2026-03-27 03:00:00+00:00
  [100.0%] 2,041,920 / 2,041,920 rows
[OK] Migration complete — 2,041,920 rows imported to data/healthdb.duckdb
  Verification: latest timestamp = 2026-03-27 03:00:00+00:00, AHUs in DB = 121
```

- [ ] **Step 4.3: Commit**

```bash
git add scripts/etl/migrate_csv_to_duckdb.py
git commit -m "feat(etl): add one-time CSV to DuckDB migration script"
```

---

## Task 5: Query classifier

**Files:**
- Create: `backend/core/query_classifier.py`
- Create: `backend/tests/test_query_classifier.py`

- [ ] **Step 5.1: Write the failing tests**

```python
# backend/tests/test_query_classifier.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.query_classifier import classify_query_complexity


def test_short_status_query_is_fast():
    assert classify_query_complexity("What is the health of e0101?", []) == "fast"


def test_list_query_is_fast():
    assert classify_query_complexity("Show me level 3 devices", []) == "fast"


def test_is_device_query_is_fast():
    assert classify_query_complexity("Is e0301 healthy?", []) == "fast"


def test_how_many_query_is_fast():
    assert classify_query_complexity("How many devices are critical?", []) == "fast"


def test_why_question_is_think():
    assert classify_query_complexity("Why is e0101 showing high THD?", []) == "think"


def test_compare_question_is_think():
    assert classify_query_complexity("Compare level 3 and level 5 health scores", []) == "think"


def test_analyse_question_is_think():
    assert classify_query_complexity("Analyse the power factor trend for e0201 over time", []) == "think"


def test_recommend_question_is_think():
    assert classify_query_complexity("What should I do about the overload on level 2?", []) == "think"


def test_root_cause_question_is_think():
    assert classify_query_complexity("What is the root cause of the phase imbalance?", []) == "think"


def test_three_devices_is_think():
    assert classify_query_complexity("Compare e0101 e0102 and e0103 health scores", []) == "think"


def test_two_levels_is_think():
    assert classify_query_complexity("How does level 3 compare to level 5?", []) == "think"


def test_long_history_with_long_message_is_think():
    history = [{"role": "user"}, {"role": "assistant"}] * 3  # 6 turns
    msg = "Tell me more about what is happening with the energy anomaly scores across the building"
    assert classify_query_complexity(msg, history) == "think"


def test_long_history_with_short_message_is_fast():
    history = [{"role": "user"}, {"role": "assistant"}] * 3  # 6 turns
    msg = "What is the score?"
    assert classify_query_complexity(msg, history) == "fast"
```

- [ ] **Step 5.2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_query_classifier.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.query_classifier'`

- [ ] **Step 5.3: Create `backend/core/query_classifier.py`**

```python
"""
core/query_classifier.py
────────────────────────
Heuristic classifier: decides whether a user query needs Qwen3 chain-of-thought
reasoning (/think) or can be answered quickly (/no_think).

Returns "think" or "fast". Adds ~1ms. No external calls.
"""
import re
from typing import Literal

_THINK_KEYWORDS = re.compile(
    r"\b(why|cause|causes|reason|reasons|explain|analyse|analyze|analysis|"
    r"compare|versus|\bvs\b|trend|over time|pattern|recommend|recommendation|"
    r"should i|what should|root cause|diagnose|investigate|worsening|"
    r"worsen|deteriorat|forecast|predict|prediction|next week|next month|"
    r"breakdown|deep.?dive|summary of)\b",
    re.IGNORECASE,
)

_FAST_PATTERNS = [
    re.compile(r"^what (is|are) (the )?(health|status|score|tier)", re.IGNORECASE),
    re.compile(r"^(show|list|give) me .{0,50}$", re.IGNORECASE),
    re.compile(r"^is e\d{4}", re.IGNORECASE),
    re.compile(r"^how many", re.IGNORECASE),
    re.compile(r"^(what|which) (level|floor|department)", re.IGNORECASE),
]

_DEVICE_ID_RE = re.compile(r"\be\d{4}\b")
_LEVEL_RE = re.compile(r"\blevel\s*\d+\b", re.IGNORECASE)


def classify_query_complexity(
    message: str,
    history: list[dict],
) -> Literal["think", "fast"]:
    """
    Classify a user query as needing deep reasoning or a fast response.

    Args:
        message: The raw user message.
        history: Full conversation history (list of {"role": ..., ...} dicts).

    Returns:
        "think" or "fast"
    """
    msg = message.strip()
    msg_lower = msg.lower()

    # Short messages with no think keywords → fast
    if len(msg) < 60 and not _THINK_KEYWORDS.search(msg_lower):
        return "fast"

    # Fast regex patterns — check before think keywords
    for pattern in _FAST_PATTERNS:
        if pattern.match(msg):
            return "fast"

    # Think keywords present
    if _THINK_KEYWORDS.search(msg_lower):
        return "think"

    # Three or more device IDs → comparative analysis
    if len(_DEVICE_ID_RE.findall(msg)) >= 3:
        return "think"

    # Two or more level references → cross-level comparison
    if len(_LEVEL_RE.findall(msg)) >= 2:
        return "think"

    # Mid-deep conversation + long message → likely a follow-up analysis
    if len(history) >= 6 and len(msg) > 80:
        return "think"

    return "fast"
```

- [ ] **Step 5.4: Run tests**

```bash
cd backend && python -m pytest tests/test_query_classifier.py -v
```

Expected: all 13 tests pass.

- [ ] **Step 5.5: Commit**

```bash
git add backend/core/query_classifier.py backend/tests/test_query_classifier.py
git commit -m "feat(classifier): add heuristic think/fast query complexity classifier"
```

---

## Task 6: Tool definitions and dispatcher

**Files:**
- Create: `backend/tools/__init__.py`
- Create: `backend/tools/tool_registry.py`
- Create: `backend/tests/test_tool_registry.py`

- [ ] **Step 6.1: Write the failing tests**

```python
# backend/tests/test_tool_registry.py
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.tool_registry import TOOLS, dispatch_tool


def test_tools_list_has_five_entries():
    assert len(TOOLS) == 5


def test_all_tools_have_required_fields():
    for tool in TOOLS:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]


def test_tool_names_are_correct():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == {
        "query_health_scores",
        "query_live_readings",
        "query_ranking",
        "query_financial_impact",
        "search_docs",
    }


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_error():
    result = await dispatch_tool("nonexistent_tool", {})
    assert "error" in result
    assert "nonexistent_tool" in result["error"]
```

- [ ] **Step 6.2: Run to verify failure**

```bash
cd backend && pip install pytest-asyncio && python -m pytest tests/test_tool_registry.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.tool_registry'`

- [ ] **Step 6.3: Create `backend/tools/__init__.py`**

```python
# tools/__init__.py
```

- [ ] **Step 6.4: Create `backend/tools/tool_registry.py`**

```python
"""
tools/tool_registry.py
──────────────────────
OpenAI-format tool definitions and async dispatcher.

TOOLS: list of dicts in OpenAI function-calling schema.
dispatch_tool(name, args): routes a tool call to its handler.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_health_scores",
            "description": (
                "Query FAIR health scores and component scores for AHUs from the Health DB. "
                "Use for: health index trends, component breakdowns (energy anomaly, PF, phase imbalance, "
                "THD, overload), safety flag history, comparing devices over a time range. "
                "Returns rows with timestamp, health_index, tier, and all FAIR component scores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ahu_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Device IDs to query, e.g. ['e0101', 'e0102']. Omit for all devices in level.",
                    },
                    "level": {
                        "type": "integer",
                        "description": "Floor level (1–11). Filters to AHUs on that level.",
                    },
                    "start": {
                        "type": "string",
                        "description": "Start of time range in ISO format, e.g. '2026-03-22T00:00:00Z'. Omit for latest snapshot.",
                    },
                    "end": {
                        "type": "string",
                        "description": "End of time range in ISO format. Omit for now.",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Columns to return. Omit for all. Options: health_index, tier, "
                            "energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload, "
                            "raw_power_factor_avg, raw_current_unbalance, raw_composite_thd, safety_flags"
                        ),
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_live_readings",
            "description": (
                "Get the most recent sensor readings from InfluxDB: power total, power factor, "
                "current THD, voltage per phase, current per phase. "
                "Use when asked about current/right-now status, live conditions, or real-time values."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ahu_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Device IDs to fetch. Omit for all devices in level.",
                    },
                    "level": {
                        "type": "integer",
                        "description": "Filter to a specific floor level (1–11).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_ranking",
            "description": (
                "Rank AHUs within a level by a health metric using their latest readings. "
                "Use for: 'worst devices', 'top N by PF', 'which AHUs need attention', best/worst comparisons."
            ),
            "parameters": {
                "type": "object",
                "required": ["level", "metric"],
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Floor level to rank within (1–11).",
                    },
                    "metric": {
                        "type": "string",
                        "description": (
                            "Metric to rank by: health_index, energy_anomaly, pf_degradation, "
                            "phase_imbalance, thd_drift, overload, raw_power_factor_avg, "
                            "raw_current_unbalance, raw_composite_thd"
                        ),
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of results to return (default 5).",
                    },
                    "order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "'asc' = lowest first (worst for health_index), 'desc' = highest first.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_financial_impact",
            "description": (
                "Get financial impact analysis for a level: excess energy cost (RM), "
                "power factor penalty (RM), maintenance risk exposure (RM), and the top "
                "cost-contributing AHUs. Use when asked about costs, financial impact, or RM values."
            ),
            "parameters": {
                "type": "object",
                "required": ["level"],
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Floor level to analyse (1–11).",
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["24h", "7d", "30d"],
                        "description": "Time window for cost calculation (default '7d').",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": (
                "Search technical documentation about AHU components, electrical health indicators, "
                "FAIR scoring methodology, and maintenance guidance. "
                "Use when asked 'why', 'what causes X', 'how does X work', 'what is X', "
                "or any question needing domain/technical knowledge rather than live data."
            ),
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query.",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of document chunks to return (default 3, max 8).",
                    },
                },
            },
        },
    },
]


async def dispatch_tool(name: str, args: dict) -> dict[str, Any]:
    """
    Route a tool call by name to its handler.
    Returns a plain dict (serialised to JSON and fed back to the model).
    """
    from tools.health_tools import (
        handle_query_health_scores,
        handle_query_live_readings,
        handle_query_ranking,
        handle_query_financial_impact,
        handle_search_docs,
    )

    handlers = {
        "query_health_scores":    handle_query_health_scores,
        "query_live_readings":    handle_query_live_readings,
        "query_ranking":          handle_query_ranking,
        "query_financial_impact": handle_query_financial_impact,
        "search_docs":            handle_search_docs,
    }
    handler = handlers.get(name)
    if handler is None:
        logger.warning(f"dispatch_tool: unknown tool '{name}'")
        return {"error": f"Unknown tool: {name}"}

    try:
        return await handler(**args)
    except Exception as e:
        logger.error(f"dispatch_tool: tool '{name}' raised {e}", exc_info=True)
        return {"error": f"Tool '{name}' failed: {str(e)}"}
```

- [ ] **Step 6.5: Run tests**

```bash
cd backend && python -m pytest tests/test_tool_registry.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 6.6: Commit**

```bash
git add backend/tools/__init__.py backend/tools/tool_registry.py backend/tests/test_tool_registry.py
git commit -m "feat(tools): add OpenAI tool definitions and dispatcher"
```

---

## Task 7: Tool handler implementations

**Files:**
- Create: `backend/tools/health_tools.py`
- Create: `backend/tests/test_tool_handlers.py`

- [ ] **Step 7.1: Write failing tests**

```python
# backend/tests/test_tool_handlers.py
import os
import sys
import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.asyncio
async def test_query_health_scores_returns_dict():
    """handle_query_health_scores returns a dict with a 'rows' key."""
    mock_db = MagicMock()
    mock_db.get_latest_snapshot.return_value = pd.DataFrame([{
        "ahu_id": "e0101", "level": 1, "health_index": 85.0,
        "tier": "Healthy", "timestamp": pd.Timestamp("2026-03-27", tz="UTC"),
    }])

    with patch("tools.health_tools._get_db", return_value=mock_db):
        from tools.health_tools import handle_query_health_scores
        result = await handle_query_health_scores(level=1)

    assert "rows" in result
    assert isinstance(result["rows"], list)
    assert result["rows"][0]["ahu_id"] == "e0101"


@pytest.mark.asyncio
async def test_query_ranking_returns_dict():
    """handle_query_ranking returns a dict with a 'ranking' key."""
    mock_db = MagicMock()
    mock_db.get_ranking.return_value = pd.DataFrame([
        {"ahu_id": "e0102", "level": 1, "health_index": 58.0,
         "timestamp": pd.Timestamp("2026-03-27", tz="UTC")},
        {"ahu_id": "e0101", "level": 1, "health_index": 83.0,
         "timestamp": pd.Timestamp("2026-03-27", tz="UTC")},
    ])

    with patch("tools.health_tools._get_db", return_value=mock_db):
        from tools.health_tools import handle_query_ranking
        result = await handle_query_ranking(level=1, metric="health_index")

    assert "ranking" in result
    assert result["ranking"][0]["ahu_id"] == "e0102"


@pytest.mark.asyncio
async def test_search_docs_returns_dict():
    """handle_search_docs returns a dict with a 'documents' key."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=["Doc chunk 1", "Doc chunk 2"])

    with patch("tools.health_tools._get_retriever", return_value=mock_retriever):
        from tools.health_tools import handle_search_docs
        result = await handle_search_docs(query="what causes high THD")

    assert "documents" in result
    assert len(result["documents"]) == 2


@pytest.mark.asyncio
async def test_search_docs_no_retriever_returns_empty():
    """handle_search_docs returns empty list when RAG not configured."""
    with patch("tools.health_tools._get_retriever", return_value=None):
        from tools.health_tools import handle_search_docs
        result = await handle_search_docs(query="any query")

    assert result == {"documents": [], "note": "No documents indexed in RAG."}
```

- [ ] **Step 7.2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_tool_handlers.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.health_tools'`

- [ ] **Step 7.3: Create `backend/tools/health_tools.py`**

```python
"""
tools/health_tools.py
─────────────────────
Handler implementations for the five chat tools.

Each handler is called by dispatch_tool() in tool_registry.py.
Handlers receive keyword arguments matching the tool's parameter schema.
Each returns a plain Python dict serialisable to JSON.
"""
import logging
from typing import Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


# ── Lazy singletons ────────────────────────────────────────────────────────────

_db_instance = None
_retriever_instance = None


def _get_db():
    """Return the shared HealthDB instance (read-only for API process)."""
    global _db_instance
    if _db_instance is None:
        from core.healthdb import HealthDB
        _db_instance = HealthDB()
    return _db_instance


def _get_retriever():
    """Return the RAG retriever, or None if ChromaDB not configured."""
    global _retriever_instance
    if _retriever_instance is None:
        try:
            import os
            from rag.vector_store import VectorStore
            from rag.retriever import Retriever
            chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
            collection = os.getenv("RAG_COLLECTION", "wach_docs")
            store = VectorStore(persist_dir=chroma_dir, collection_name=collection)
            if store.count == 0:
                return None
            _retriever_instance = Retriever(vector_store=store)
        except Exception:
            return None
    return _retriever_instance


# ── Helpers ────────────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-serialisable list of dicts."""
    return df.where(pd.notna(df), None).to_dict(orient="records")


# ── Handlers ───────────────────────────────────────────────────────────────────

async def handle_query_health_scores(
    ahu_ids: Optional[list[str]] = None,
    level: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    metrics: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Query FAIR health scores from DuckDB.
    Returns latest snapshot when no time range given; time-series otherwise.
    """
    db = _get_db()
    if start or end:
        df = db.get_time_range(ahu_ids=ahu_ids, level=level, start=start, end=end, metrics=metrics)
        query_type = "time_range"
    else:
        df = db.get_latest_snapshot(ahu_ids=ahu_ids, level=level)
        query_type = "latest_snapshot"

    if df.empty:
        return {"rows": [], "note": "No health data found for the given filters."}

    # Serialise timestamps to ISO strings
    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].astype(str)

    return {
        "query_type": query_type,
        "row_count": len(df),
        "rows": _df_to_records(df),
    }


async def handle_query_live_readings(
    ahu_ids: Optional[list[str]] = None,
    level: Optional[int] = None,
) -> dict[str, Any]:
    """
    Fetch latest sensor readings from InfluxDB.
    """
    try:
        from core.influx_client import fetch_latest_hourly_data
        from models.schemas import AHU_LEVEL_CONFIG

        if ahu_ids:
            devices_filter = ahu_ids
        elif level is not None:
            level_key = f"level_{level}"
            devices_filter = AHU_LEVEL_CONFIG.get(level_key, {}).get("devices", [])
        else:
            devices_filter = None

        df = await fetch_latest_hourly_data(devices_filter=devices_filter)
        if df is None or (hasattr(df, 'empty') and df.empty):
            return {"readings": [], "note": "No live readings available."}

        if hasattr(df, 'to_dict'):
            if "timestamp" in df.columns:
                df["timestamp"] = df["timestamp"].astype(str)
            return {"reading_count": len(df), "readings": _df_to_records(df)}

        return {"readings": [], "note": "Unexpected data format from InfluxDB."}
    except Exception as e:
        logger.warning(f"handle_query_live_readings failed: {e}")
        return {"readings": [], "error": str(e)}


async def handle_query_ranking(
    level: int,
    metric: str,
    n: int = 5,
    order: str = "asc",
) -> dict[str, Any]:
    """
    Rank AHUs by metric within a level.
    """
    db = _get_db()
    df = db.get_ranking(level=level, metric=metric, n=n, order=order)

    if df.empty:
        return {"ranking": [], "note": f"No data for level {level}."}

    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].astype(str)

    return {
        "level": level,
        "metric": metric,
        "order": order,
        "ranking": _df_to_records(df),
    }


async def handle_query_financial_impact(
    level: int,
    time_range: str = "7d",
) -> dict[str, Any]:
    """
    Compute financial impact for a level using the existing risk engine.
    """
    try:
        from routes.financial_impact import _compute_impact
        result = await _compute_impact(level=level, time_range=time_range)
        return result if isinstance(result, dict) else {"data": result}
    except Exception as e:
        logger.warning(f"handle_query_financial_impact failed: {e}")
        return {"error": str(e), "note": "Financial impact data unavailable."}


async def handle_search_docs(
    query: str,
    k: int = 3,
) -> dict[str, Any]:
    """
    Search RAG knowledge base for relevant document chunks.
    """
    retriever = _get_retriever()
    if retriever is None:
        return {"documents": [], "note": "No documents indexed in RAG."}

    try:
        k = min(k, 8)  # cap at 8
        snippets = await retriever.retrieve(query, top_k=k)
        return {"query": query, "documents": snippets or []}
    except Exception as e:
        logger.warning(f"handle_search_docs failed: {e}")
        return {"documents": [], "error": str(e)}
```

- [ ] **Step 7.4: Run tests**

```bash
cd backend && python -m pytest tests/test_tool_handlers.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 7.5: Commit**

```bash
git add backend/tools/health_tools.py backend/tests/test_tool_handlers.py
git commit -m "feat(tools): add tool handler implementations backed by HealthDB and InfluxDB"
```

---

## Task 8: QwenClient tool-calling loop

**Files:**
- Modify: `backend/llm/qwen_client.py`

- [ ] **Step 8.1: Add `generate_with_tools` method to `QwenClient`**

Add the following method to the `QwenClient` class in `backend/llm/qwen_client.py`, after the existing `generate_chat_response` method:

```python
    async def generate_with_tools(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        tool_dispatcher,
        max_tool_rounds: int = 5,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
    ) -> str:
        """
        Agentic tool-calling loop.

        Sends messages + tool definitions to the model. If the model issues
        tool_calls, executes them via tool_dispatcher and feeds results back.
        Repeats until the model produces a final text response or max_tool_rounds
        is reached.

        Args:
            system_prompt: Lean system prompt (no pre-loaded data).
            messages: Conversation history in OpenAI format
                      [{"role": "user"|"assistant", "content": str}, ...].
            tools: List of tool definitions in OpenAI function-calling schema.
            tool_dispatcher: Async callable(name: str, args: dict) -> dict.
            max_tool_rounds: Safety cap on tool-call iterations.
            temperature: Sampling temperature.
            max_output_tokens: Max tokens for final response.

        Returns:
            Final assistant response string with <think> blocks stripped.
        """
        import json
        full_messages = [{"role": "system", "content": system_prompt}] + list(messages)

        for round_num in range(max_tool_rounds + 1):
            is_final_round = (round_num == max_tool_rounds)

            # On the final round, send without tools so the model must answer
            call_tools = tools if not is_final_round else []

            loop = asyncio.get_event_loop()
            try:
                kwargs = dict(
                    model=self._model,
                    messages=full_messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                )
                if call_tools:
                    kwargs["tools"] = call_tools
                    kwargs["tool_choice"] = "auto"

                response = await loop.run_in_executor(
                    None,
                    partial(self._client.chat.completions.create, **kwargs),
                )
            except Exception as e:
                logger.warning(f"LM Studio unreachable: {e}")
                return "Local LM Studio is not available in this environment."

            choice = response.choices[0]
            tool_calls = getattr(choice.message, "tool_calls", None)

            # No tool calls → final answer
            if not tool_calls:
                content = choice.message.content or ""
                return _strip_think(content)

            # Append assistant message (with tool_calls) to history
            full_messages.append({
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Execute each tool call and append results
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = await tool_dispatcher(tc.function.name, args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                })

        # Should not reach here (final round sends without tools)
        return "I was unable to complete the analysis."
```

- [ ] **Step 8.2: Manual smoke test**

Start LM Studio with Qwen3, then run from the `backend/` directory:

```bash
cd backend && python3 -c "
import asyncio
from llm.qwen_client import QwenClient
from tools.tool_registry import TOOLS, dispatch_tool

async def test():
    client = QwenClient()
    result = await client.generate_with_tools(
        system_prompt='You are a helpful assistant.',
        messages=[{'role': 'user', 'content': '/no_think What is 2 + 2?'}],
        tools=TOOLS,
        tool_dispatcher=dispatch_tool,
    )
    print('Result:', result)

asyncio.run(test())
"
```

Expected: the model answers without calling any tools (simple math question).

- [ ] **Step 8.3: Commit**

```bash
git add backend/llm/qwen_client.py
git commit -m "feat(llm): add generate_with_tools() agentic tool-calling loop to QwenClient"
```

---

## Task 9: Chat route refactor

**Files:**
- Modify: `backend/routes/chat.py`

This is the final integration step. It replaces the 1,244-line context-stuffing implementation with the new tool-based flow. **Do a full read of `chat.py` before starting.**

- [ ] **Step 9.1: Read current `backend/routes/chat.py` in full**

Run the existing tests to capture the baseline:
```bash
cd backend && python -m pytest tests/test_chat_endpoint.py tests/test_chat_history.py -v 2>&1 | head -40
```

- [ ] **Step 9.2: Replace `backend/routes/chat.py` with the new implementation**

```python
"""
routes/chat.py
──────────────
AI-powered chat endpoint — V2 (agentic tool-use).

POST /api/chat
  Request:  { message: str, history?: list, context?: dict }
  Response: { reply: str, navigate: dict|null, thinking_mode: str }

Architecture:
  1. classify_query_complexity() → "think" or "fast"
  2. Prepend /think or /no_think to message
  3. Lean system prompt + 5 tool definitions → QwenClient.generate_with_tools()
  4. Model calls tools on demand (HealthDB, InfluxDB, RAG, financial)
  5. Return final reply + thinking_mode indicator
"""

import logging
import os
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from llm.client_factory import get_chat_client
from models.schemas import ChatHistoryItem
from config import get_building_name, get_department
from core.query_classifier import classify_query_complexity
from tools.tool_registry import TOOLS, dispatch_tool

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatHistoryItem]] = None
    context: Optional[dict] = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        if len(v) > 1000:
            raise ValueError("message must be 1000 characters or fewer")
        return v


# ── System prompt ──────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    building = get_building_name()
    department = get_department()
    return f"""You are WACH AI, an AHU health assistant for {building} ({department}).

You monitor Air Handling Units (AHUs) across 11 building levels (Level 1–Level 11), totalling 121 AHUs.
Device IDs follow the format e[LEVEL][NN], e.g. e0101 (Level 1, unit 01) through e1108 (Level 11, unit 08).

## Health Scoring (FAIR)
Health Index: 0–100 scale.
- Healthy (80–100): Normal operation
- Monitor (60–79): Watch closely
- Maintenance (40–59): Schedule maintenance
- Critical (0–39): Immediate intervention required

FAIR component penalty weights:
- Energy Anomaly (15%): Unusual energy consumption
- Power Factor Degradation (25%): Poor reactive power management
- Phase Imbalance (25%): Unequal current across phases
- THD Drift (15%): Total Harmonic Distortion increase
- Overload (20%): Power demand exceeding rated capacity

Power quality targets: power factor >0.85, voltage THD <5% (IEEE 519), current unbalance <2% (NEMA MG-1).

Financial impact categories:
- Excess Energy Cost: kWh above baseline × TNB tariff
- Power Factor Penalty: TNB surcharge of 1.5% per 0.01 below PF 0.85
- Maintenance Risk: emergency repair premium for AHUs with health index < 60

## Instructions
- Use the provided tools to retrieve data. Never guess device readings or fabricate values.
- Cite which devices and time ranges your data covers.
- If a tool returns no data, say so explicitly — do not invent numbers.
- Use markdown formatting. No emojis.
- Be concise and actionable. Use tables for comparisons.
"""


# ── History conversion ─────────────────────────────────────────────────────────

def _to_openai_messages(history: list[ChatHistoryItem]) -> list[dict]:
    """Convert ChatHistoryItem list to OpenAI-format messages."""
    messages = []
    for item in history:
        role = "assistant" if item.role in ("model", "assistant") else "user"
        content = item.parts[0] if isinstance(item.parts, list) else item.parts
        messages.append({"role": role, "content": content})
    return messages


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@router.post("")
async def chat(body: ChatRequest):
    history = body.history or []
    history_messages = _to_openai_messages(history)

    # 1. Classify complexity → choose thinking mode
    thinking_mode = classify_query_complexity(body.message, history_messages)
    prefix = "/think " if thinking_mode == "think" else "/no_think "
    user_content = prefix + body.message

    # 2. Build messages list for tool loop
    messages = history_messages + [{"role": "user", "content": user_content}]

    # 3. Generate response using tool-augmented generation
    try:
        client = get_chat_client()
        reply = await client.generate_with_tools(
            system_prompt=_build_system_prompt(),
            messages=messages,
            tools=TOOLS,
            tool_dispatcher=dispatch_tool,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    return {
        "reply": reply,
        "navigate": None,
        "thinking_mode": thinking_mode,
    }
```

- [ ] **Step 9.3: Run the test suite**

```bash
cd backend && python -m pytest tests/ -v --ignore=tests/test_history_generator.py -x 2>&1 | tail -30
```

Some existing tests that relied on the context-injection functions will fail — that is expected. The key tests to check are:

- `tests/test_chat_endpoint.py` — should pass (endpoint shape unchanged)
- `tests/test_query_classifier.py` — should pass
- `tests/test_healthdb.py` — should pass
- `tests/test_tool_registry.py` — should pass
- `tests/test_tool_handlers.py` — should pass

If `test_chat_endpoint.py` fails, check whether it mocks `generate_chat_response` — update mocks to patch `generate_with_tools` instead.

- [ ] **Step 9.4: Update `thinking_mode` in API response (add to frontend)**

In `frontend/src/store/useAppStore.ts` or wherever the chat API response is consumed, the response now includes `thinking_mode: "think" | "fast"`. This can be used to show a small badge on responses. No code change is required now — the field is additive and ignored by the current frontend.

- [ ] **Step 9.5: Manual end-to-end test**

Start the backend:
```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

Test a fast query:
```bash
curl -s -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the health of level 3?"}' | python3 -m json.tool
```

Expected response shape:
```json
{
  "reply": "...",
  "navigate": null,
  "thinking_mode": "fast"
}
```

Test a think query:
```bash
curl -s -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Why is the power factor on level 3 deteriorating and what should I do?"}' | python3 -m json.tool
```

Expected: `"thinking_mode": "think"` in response.

- [ ] **Step 9.6: Commit**

```bash
git add backend/routes/chat.py
git commit -m "feat(chat): replace context-stuffing with agentic tool-use + thinking toggle"
```

---

## Task 10: ETL GitHub Actions — add DuckDB to LFS and commit step

**Files:**
- Modify: `.github/workflows/etl-scheduler.yml`
- Modify: `.gitattributes`

The ETL now writes `data/healthdb.duckdb`. The GitHub Actions workflow needs to commit it.

- [ ] **Step 10.1: Add healthdb.duckdb to Git LFS**

```bash
# Track the DuckDB file in LFS
echo "data/healthdb.duckdb filter=lfs diff=lfs merge=lfs -text" >> .gitattributes
git add .gitattributes
```

- [ ] **Step 10.2: Update the commit step in `.github/workflows/etl-scheduler.yml`**

Find the "Commit updated CSVs" step and update `git add` to include the DuckDB file:

```yaml
      - name: Commit updated data files
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/predictions.csv data/health_all_levels.csv data/health_hourly.csv data/healthdb.duckdb
          if git diff --staged --quiet; then
            echo "No data changes to commit."
          else
            git commit -m "chore(data): update ETL outputs [skip ci]"
            git pull --rebase
            git push
          fi
```

- [ ] **Step 10.3: Commit**

```bash
git add .gitattributes .github/workflows/etl-scheduler.yml
git commit -m "chore(ci): track healthdb.duckdb in LFS and commit from ETL workflow"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| DuckDB schema mirrors CSV columns | Task 1 |
| `get_latest_snapshot`, `get_time_range`, `get_ranking`, `get_latest_timestamp`, `upsert` | Tasks 1–2 |
| ETL `save_health_duckdb()` step | Task 3 |
| One-time migration script | Task 4 |
| Heuristic classifier (`classify_query_complexity`) | Task 5 |
| Five tool definitions in OpenAI schema | Task 6 |
| Tool handlers backed by HealthDB/InfluxDB/RAG | Task 7 |
| `generate_with_tools()` loop, max 5 rounds | Task 8 |
| `chat.py` refactor — lean system prompt, tool loop | Task 9 |
| `thinking_mode` in API response | Task 9 |
| ETL CI workflow commits DuckDB file | Task 10 |

All spec requirements covered. No gaps found.

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency check:**
- `HealthDB.get_latest_snapshot(ahu_ids=..., level=...)` — used consistently in Task 2 tests and Task 7 handler
- `dispatch_tool(name, args)` — defined Task 6, called Task 8 ✓
- `classify_query_complexity(message, history)` — defined Task 5, called Task 9 ✓
- `generate_with_tools(system_prompt, messages, tools, tool_dispatcher)` — defined Task 8, called Task 9 ✓
- API response shape `{reply, navigate, thinking_mode}` — defined Task 9 ✓
