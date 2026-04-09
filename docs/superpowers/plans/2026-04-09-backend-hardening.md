# Backend Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 backend issues identified in the external review: data freshness metadata, metric registry consolidation, LLM circuit breaker, and rate limiter abstraction.

**Architecture:** Each phase is independent and produces a commit. Phase 1 adds ETL heartbeat tracking + API metadata + frontend indicator. Phase 2 restructures `ALLOWED_METRICS_WITH_UNITS` and rewrites the query parser. Phase 3 adds a circuit breaker state machine to `QwenClient`. Phase 4 extracts the rate limiter behind a protocol.

**Tech Stack:** Python 3.11+ / FastAPI / DuckDB / Pydantic / React + TypeScript + Zustand + Tailwind

**Spec:** `docs/superpowers/specs/2026-04-09-backend-hardening-design.md`

---

## File Map

### Phase 1: Data Freshness
| File | Action | Responsibility |
|------|--------|----------------|
| `backend/core/healthdb.py` | Modify | Add `etl_runs` table, `record_etl_start()`, `record_etl_complete()`, `get_last_sync()` |
| `backend/tests/test_healthdb.py` | Modify | Tests for ETL heartbeat and `get_last_sync()` |
| `scripts/etl/run_health_etl.py` | Modify | Call heartbeat methods around pipeline |
| `backend/routes/dashboard.py` | Modify | Inject `metadata` into trend, ranking, summary responses |
| `frontend/src/components/DataFreshnessIndicator.tsx` | Create | Render "Data as of X ago" |
| `frontend/src/App.tsx` | Modify | Pass metadata to indicator component |

### Phase 2: Metric Registry
| File | Action | Responsibility |
|------|--------|----------------|
| `backend/models/schemas.py` | Modify | Restructure `ALLOWED_METRICS_WITH_UNITS`, add `resolve_metric()` |
| `backend/tests/test_schemas.py` | Create | Tests for `resolve_metric()` and registry structure |
| `backend/llm/translator.py` | Modify | Rewrite `_parse_query_rules` using `resolve_metric()` |
| `backend/tests/test_translator.py` | Modify | Add regression tests for new parser |

### Phase 3: Circuit Breaker
| File | Action | Responsibility |
|------|--------|----------------|
| `backend/llm/circuit_breaker.py` | Create | `CircuitBreaker` class + `LLMUnavailableError` |
| `backend/tests/test_circuit_breaker.py` | Create | State transition tests |
| `backend/llm/qwen_client.py` | Modify | Wrap calls through breaker |
| `backend/routes/chat.py` | Modify | Catch `LLMUnavailableError` |
| `backend/routes/query.py` | Modify | Catch `LLMUnavailableError` when LLM enabled |

### Phase 4: Rate Limiter
| File | Action | Responsibility |
|------|--------|----------------|
| `backend/middleware/rate_limiter.py` | Create | `RateLimiter` protocol + `InMemoryRateLimiter` + factory |
| `backend/tests/test_rate_limiter.py` | Create | Limit enforcement tests |
| `backend/routes/query.py` | Modify | Replace inline rate limiter with import |

---

## Task 1: ETL Heartbeat Table in HealthDB

**Files:**
- Modify: `backend/core/healthdb.py:36-189` (schema + class)
- Test: `backend/tests/test_healthdb.py`

- [ ] **Step 1: Write failing tests for ETL heartbeat**

Add to `backend/tests/test_healthdb.py`:

```python
def test_etl_runs_table_created(db):
    """etl_runs table exists after HealthDB init."""
    result = db._conn().execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name='etl_runs'"
    ).fetchone()
    assert result is not None, "etl_runs table should exist"


def test_record_etl_start_and_complete(db):
    """record_etl_start creates a running row; record_etl_complete updates it."""
    run_id = db.record_etl_start(level=1)
    assert run_id is not None

    # Check it's in 'running' state
    row = db._conn().execute(
        "SELECT status, completed_at, rows_written FROM etl_runs WHERE run_id = ?",
        [run_id],
    ).fetchone()
    assert row[0] == "running"
    assert row[1] is None  # completed_at is NULL
    assert row[2] is None  # rows_written is NULL

    # Complete it
    db.record_etl_complete(run_id, status="success", rows_written=42)

    row = db._conn().execute(
        "SELECT status, completed_at, rows_written FROM etl_runs WHERE run_id = ?",
        [run_id],
    ).fetchone()
    assert row[0] == "success"
    assert row[1] is not None  # completed_at is set
    assert row[2] == 42


def test_get_last_sync_returns_metadata(db):
    """get_last_sync returns data_as_of and sync_age_seconds."""
    run_id = db.record_etl_start(level=None)
    db.record_etl_complete(run_id, status="success", rows_written=10)

    meta = db.get_last_sync()
    assert "data_as_of" in meta
    assert "sync_age_seconds" in meta
    assert meta["sync_age_seconds"] >= 0


def test_get_last_sync_empty_db(db):
    """get_last_sync returns None fields when no ETL has run."""
    meta = db.get_last_sync()
    assert meta["data_as_of"] is None
    assert meta["sync_age_seconds"] is None


def test_get_last_sync_ignores_failed_runs(db):
    """get_last_sync only considers successful runs."""
    run_id = db.record_etl_start(level=None)
    db.record_etl_complete(run_id, status="failed", rows_written=0)

    meta = db.get_last_sync()
    assert meta["data_as_of"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_healthdb.py::test_etl_runs_table_created tests/test_healthdb.py::test_record_etl_start_and_complete tests/test_healthdb.py::test_get_last_sync_returns_metadata tests/test_healthdb.py::test_get_last_sync_empty_db tests/test_healthdb.py::test_get_last_sync_ignores_failed_runs -v`

Expected: FAIL — `record_etl_start` and `get_last_sync` don't exist yet.

- [ ] **Step 3: Add etl_runs schema and methods to HealthDB**

In `backend/core/healthdb.py`, add the table schema constant after `_PREDICTIONS_SCHEMA_SQL` (after line 55):

```python
_ETL_RUNS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS etl_runs (
    run_id        INTEGER PRIMARY KEY DEFAULT nextval('etl_runs_seq'),
    started_at    TIMESTAMPTZ NOT NULL,
    completed_at  TIMESTAMPTZ,
    status        VARCHAR NOT NULL DEFAULT 'running',
    rows_written  INTEGER,
    level         INTEGER
);
"""

_ETL_RUNS_SEQ_SQL = "CREATE SEQUENCE IF NOT EXISTS etl_runs_seq START 1;"
```

In `_ensure_schema` method (line 181), add after the existing `conn.execute` calls:

```python
conn.execute(_ETL_RUNS_SEQ_SQL)
conn.execute(_ETL_RUNS_SCHEMA_SQL)
```

Add these methods to the `HealthDB` class after `get_latest_timestamp` (after line 326):

```python
# ── ETL Heartbeat ─────────────────────────────────────────────────────

def record_etl_start(self, level: int | None = None) -> int:
    """Record the start of an ETL run. Returns the run_id."""
    with self._conn(write=True) as conn:
        result = conn.execute(
            "INSERT INTO etl_runs (started_at, status, level) "
            "VALUES (now(), 'running', ?) RETURNING run_id",
            [level],
        ).fetchone()
    return result[0]

def record_etl_complete(
    self, run_id: int, status: str = "success", rows_written: int = 0
) -> None:
    """Update an ETL run with completion status."""
    with self._conn(write=True) as conn:
        conn.execute(
            "UPDATE etl_runs SET completed_at = now(), status = ?, rows_written = ? "
            "WHERE run_id = ?",
            [status, rows_written, run_id],
        )

def get_last_sync(self) -> dict:
    """
    Returns metadata about the most recent successful ETL run.

    Returns:
        {"data_as_of": ISO8601 string or None, "sync_age_seconds": int or None}
    """
    with self._conn() as conn:
        row = conn.execute(
            "SELECT completed_at FROM etl_runs "
            "WHERE status = 'success' "
            "ORDER BY completed_at DESC LIMIT 1"
        ).fetchone()

    if row is None or row[0] is None:
        return {"data_as_of": None, "sync_age_seconds": None}

    completed = row[0]
    if hasattr(completed, 'tzinfo') and completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    age = int((now - completed).total_seconds())
    return {
        "data_as_of": completed.isoformat(),
        "sync_age_seconds": age,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_healthdb.py -v`

Expected: All tests pass, including the 5 new ones.

- [ ] **Step 5: Commit**

```bash
git add backend/core/healthdb.py backend/tests/test_healthdb.py
git commit -m "feat: add ETL heartbeat table and get_last_sync to HealthDB"
```

---

## Task 2: Wire ETL Script to Heartbeat

**Files:**
- Modify: `scripts/etl/run_health_etl.py:1033-1129` (run_etl_pipeline function)

- [ ] **Step 1: Add heartbeat calls to run_etl_pipeline**

In `scripts/etl/run_health_etl.py`, add an import near the top (after the existing `from core.influx_client` import at line 36):

```python
from core.healthdb import HealthDB
```

In `run_etl_pipeline` (line 1033), add heartbeat recording. After the `results` dict initialization (after line 1065), add:

```python
# Record ETL start in heartbeat table
heartbeat_db = HealthDB()
etl_run_id = heartbeat_db.record_etl_start(level=level)
```

Before the final `return results` at line 1129, add the completion recording. Replace the block from `return results` (line 1129) with:

```python
    # Record ETL completion
    heartbeat_db.record_etl_complete(
        etl_run_id,
        status=results["status"],
        rows_written=results["rows_loaded"],
    )

    return results
```

Also wrap the entire pipeline body in a try/except to catch crashes, so we record failures. After the `etl_run_id` assignment, wrap the STEP 1-4 block:

```python
try:
    # STEP 1: EXTRACT
    # ... (existing code through to final summary)
except Exception as e:
    heartbeat_db.record_etl_complete(etl_run_id, status="failed", rows_written=0)
    print(f"[ERROR] ETL pipeline failed: {e}")
    results["status"] = "error"
    return results
```

- [ ] **Step 2: Verify ETL still runs**

Run: `cd scripts/etl && python run_health_etl.py --dry-run --level 1`

Expected: Pipeline completes with status "success". No errors about missing tables.

- [ ] **Step 3: Commit**

```bash
git add scripts/etl/run_health_etl.py
git commit -m "feat: wire ETL pipeline to heartbeat table"
```

---

## Task 3: Inject Metadata into Dashboard API Responses

**Files:**
- Modify: `backend/routes/dashboard.py:49-130` (ranking), `132-297` (trend), `452-666` (summary)

- [ ] **Step 1: Add metadata helper import and function**

At the top of `backend/routes/dashboard.py`, add after the existing imports (after line 27):

```python
from core.healthdb import HealthDB
```

Add a module-level helper after the `FLAG_LABELS` dict (after line 34):

```python
def _get_metadata() -> dict:
    """Get data freshness metadata for API responses."""
    try:
        db = HealthDB()
        return db.get_last_sync()
    except Exception:
        return {"data_as_of": None, "sync_age_seconds": None}
```

- [ ] **Step 2: Add metadata to ranking response**

In `dashboard_ranking` (line 49), modify the return dict (line 117) to include metadata:

```python
        return {
            "level": level,
            "time_range": time_range,
            "snapshot_time": datetime.now().isoformat(),
            "metadata": _get_metadata(),
            "best": best_list,
            "worst": worst_list,
        }
```

- [ ] **Step 3: Add metadata to trend response**

In `dashboard_trend` (line 132), modify the return dict (line 274) to include metadata:

```python
        return {
            "level": level,
            "range": range,
            "metadata": _get_metadata(),
            "ahus": [a["device_id"] for a in assessments],
            "series": series,
            "latest_snapshot": {
                a["device_id"]: round(a["health_index"], 1)
                for a in assessments
            },
            "safety_flags": {
                a["device_id"]: [
                    {"flag_id": f.strip(), "label": FLAG_LABELS.get(f.strip(), "Safety Issue"), "severity": "High" if f.strip() in ["THD_CHRONIC_HIGH", "OVERLOAD_CHRONIC"] else ("Moderate" if f.strip() == "PF_CHRONIC_LOW" else "High")}
                    for f in a.get("safety_flags", "").split(",")
                    if f.strip()
                ]
                for a in assessments
            }
        }
```

- [ ] **Step 4: Add metadata to summary response**

In `dashboard_summary` (line 452), modify the return dict (line 655) to include metadata:

```python
        return {
            "level": level,
            "range": range,
            "device_id": ahu_id,
            "metadata": _get_metadata(),
            "summaries": summaries
        }
```

- [ ] **Step 5: Verify endpoints return metadata**

Run: `cd backend && python -c "from core.healthdb import HealthDB; db = HealthDB(); print(db.get_last_sync())"`

Expected: Prints `{'data_as_of': ..., 'sync_age_seconds': ...}` (values depend on whether ETL has run).

- [ ] **Step 6: Commit**

```bash
git add backend/routes/dashboard.py
git commit -m "feat: inject data freshness metadata into dashboard API responses"
```

---

## Task 4: Frontend Data Freshness Indicator

**Files:**
- Create: `frontend/src/components/DataFreshnessIndicator.tsx`
- Modify: `frontend/src/App.tsx:132-155` (ranking fetch)

- [ ] **Step 1: Create the DataFreshnessIndicator component**

Create `frontend/src/components/DataFreshnessIndicator.tsx`:

```tsx
interface DataFreshnessIndicatorProps {
  dataAsOf: string | null;
}

function formatTimeAgo(isoString: string): string {
  const then = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export default function DataFreshnessIndicator({ dataAsOf }: DataFreshnessIndicatorProps) {
  if (!dataAsOf) return null;

  return (
    <span className="text-xs text-gray-500 font-mono">
      Data as of {formatTimeAgo(dataAsOf)}
    </span>
  );
}
```

- [ ] **Step 2: Wire the indicator into App.tsx**

In `frontend/src/App.tsx`, add state for metadata. Near the other `useState` declarations (around line 85), add:

```tsx
const [dataAsOf, setDataAsOf] = React.useState<string | null>(null);
```

In the ranking fetch effect (line 132), update the `.then` callback to also capture metadata:

```tsx
    fetchDashboardRanking(selectedLevel, apiRange)
      .then((data: any) => {
        // Capture data freshness metadata
        if (data.metadata?.data_as_of) {
          setDataAsOf(data.metadata.data_as_of);
        }
        const allDevices = [...(data.best ?? []), ...(data.worst ?? [])];
        // ... rest of existing code unchanged
```

Add the import at the top of `App.tsx`:

```tsx
import DataFreshnessIndicator from './components/DataFreshnessIndicator';
```

Render the indicator somewhere visible in the dashboard area. Find the dashboard section where the level selector or time range selector is rendered, and add after it:

```tsx
<DataFreshnessIndicator dataAsOf={dataAsOf} />
```

The exact placement depends on the component tree — place it near the `LevelSelectorBar` or the time range controls so it's visible but unobtrusive.

- [ ] **Step 3: Verify in browser**

Run: `cd frontend && npm run dev`

Expected: After selecting a level, "Data as of X ago" appears subtly in the dashboard area. If no ETL has run (metadata is null), nothing renders.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DataFreshnessIndicator.tsx frontend/src/App.tsx
git commit -m "feat: add data freshness indicator to dashboard"
```

---

## Task 5: Restructure Metric Registry in schemas.py

**Files:**
- Modify: `backend/models/schemas.py:16-86` (ALLOWED_METRICS_WITH_UNITS) and `430-458` (utility functions)
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing tests for the new registry shape and resolve_metric**

Create `backend/tests/test_schemas.py`:

```python
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_registry_is_dict_of_dicts():
    """Each metric entry should be a dict with unit, description, aliases."""
    from models.schemas import ALLOWED_METRICS_WITH_UNITS
    for key, entry in ALLOWED_METRICS_WITH_UNITS.items():
        assert isinstance(entry, dict), f"{key}: expected dict, got {type(entry)}"
        assert "unit" in entry, f"{key}: missing 'unit'"
        assert "description" in entry, f"{key}: missing 'description'"
        assert "aliases" in entry, f"{key}: missing 'aliases'"
        assert isinstance(entry["aliases"], list), f"{key}: aliases should be a list"


def test_allowed_metrics_list_matches_keys():
    """ALLOWED_METRICS should be the list of keys from the registry."""
    from models.schemas import ALLOWED_METRICS, ALLOWED_METRICS_WITH_UNITS
    assert set(ALLOWED_METRICS) == set(ALLOWED_METRICS_WITH_UNITS.keys())


def test_get_metric_unit():
    """get_metric_unit reads from new dict structure."""
    from models.schemas import get_metric_unit
    assert get_metric_unit("power_total") == "kW"
    assert get_metric_unit("energy_import") == "kWh"
    assert get_metric_unit("nonexistent") == ""


def test_get_metric_description():
    """get_metric_description reads from new dict structure."""
    from models.schemas import get_metric_description
    assert "active power" in get_metric_description("power_total").lower()
    assert get_metric_description("nonexistent") == ""


def test_resolve_metric_exact_key():
    """Exact metric key name matches."""
    from models.schemas import resolve_metric
    assert resolve_metric("show power_total for e0101") == "power_total"


def test_resolve_metric_alias():
    """Natural language alias matches."""
    from models.schemas import resolve_metric
    assert resolve_metric("show energy consumption for level 3") == "energy_import"


def test_resolve_metric_multi_word_priority():
    """Multi-word alias 'apparent power' matches before single-word 'power'."""
    from models.schemas import resolve_metric
    assert resolve_metric("apparent power for e0101") == "apparent_power_total"


def test_resolve_metric_no_match():
    """Returns None when no metric matches."""
    from models.schemas import resolve_metric
    assert resolve_metric("what is the weather") is None


@pytest.mark.parametrize("text,expected", [
    ("show phase imbalance for e0101", "current_unbalance"),
    ("voltage unbalance level 3", "volts_unbalance"),
    ("thd l3 for e0101", "current_l3_thd"),
    ("energy usage level 5", "energy_import"),
    ("voltage readings e0201", "volts_l_n_avg"),
    ("show reactive power", "reactive_power_total"),
    ("power factor for e0101", "power_factor_avg"),
    ("current for level 1", "current_avg"),
])
def test_resolve_metric_aliases(text, expected):
    """All aliases from the old metric_map should resolve correctly."""
    from models.schemas import resolve_metric
    assert resolve_metric(text) == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_schemas.py -v`

Expected: FAIL — `resolve_metric` doesn't exist, registry is still tuples.

- [ ] **Step 3: Restructure ALLOWED_METRICS_WITH_UNITS**

In `backend/models/schemas.py`, replace lines 16-81 (the `ALLOWED_METRICS_WITH_UNITS` dict). Change from tuples to dicts with aliases:

```python
ALLOWED_METRICS_WITH_UNITS = {
    # POWER (kW, kVAR, kVA)
    "power_total": {
        "unit": "kW",
        "description": "Total active power across all phases",
        "aliases": ["power", "total power", "active power"],
    },
    "power_l1": {
        "unit": "kW",
        "description": "Active power Phase L1",
        "aliases": [],
    },
    "power_l2": {
        "unit": "kW",
        "description": "Active power Phase L2",
        "aliases": [],
    },
    "power_l3": {
        "unit": "kW",
        "description": "Active power Phase L3",
        "aliases": [],
    },
    "power_demand": {
        "unit": "kW",
        "description": "Rolling average demand",
        "aliases": [],
    },
    "max_power_demand": {
        "unit": "kW",
        "description": "Peak demand recorded",
        "aliases": ["peak demand"],
    },
    "apparent_power_total": {
        "unit": "kVA",
        "description": "Total apparent power",
        "aliases": ["apparent power"],
    },
    "apparent_power_l1": {
        "unit": "kVA",
        "description": "Apparent power Phase L1",
        "aliases": [],
    },
    "apparent_power_l2": {
        "unit": "kVA",
        "description": "Apparent power Phase L2",
        "aliases": [],
    },
    "apparent_power_l3": {
        "unit": "kVA",
        "description": "Apparent power Phase L3",
        "aliases": [],
    },
    "apparent_power_demand": {
        "unit": "kVA",
        "description": "Apparent power demand",
        "aliases": [],
    },
    "reactive_power_total": {
        "unit": "kVAR",
        "description": "Total reactive power",
        "aliases": ["reactive power"],
    },
    "reactive_power_l1": {
        "unit": "kVAR",
        "description": "Reactive power Phase L1",
        "aliases": [],
    },
    "reactive_power_l2": {
        "unit": "kVAR",
        "description": "Reactive power Phase L2",
        "aliases": [],
    },
    "reactive_power_l3": {
        "unit": "kVAR",
        "description": "Reactive power Phase L3",
        "aliases": [],
    },
    "reactive_power_demand": {
        "unit": "kVAR",
        "description": "Reactive power demand",
        "aliases": [],
    },
    # ENERGY (kWh, kVARh, kVAh)
    "energy_import": {
        "unit": "kWh",
        "description": "Energy consumed from grid",
        "aliases": ["energy", "energy consumption", "energy usage", "energy import"],
    },
    "energy_export": {
        "unit": "kWh",
        "description": "Energy sent to grid",
        "aliases": [],
    },
    "reactive_energy_import": {
        "unit": "kVARh",
        "description": "Reactive energy consumed",
        "aliases": [],
    },
    "reactive_energy_export": {
        "unit": "kVARh",
        "description": "Reactive energy sent to grid",
        "aliases": [],
    },
    "apparent_energy": {
        "unit": "kVAh",
        "description": "Total apparent energy",
        "aliases": [],
    },
    # CURRENT (A)
    "current_avg": {
        "unit": "A",
        "description": "Average current across phases",
        "aliases": ["current"],
    },
    "current_l1": {
        "unit": "A",
        "description": "Current Phase L1",
        "aliases": [],
    },
    "current_l2": {
        "unit": "A",
        "description": "Current Phase L2",
        "aliases": [],
    },
    "current_l3": {
        "unit": "A",
        "description": "Current Phase L3",
        "aliases": [],
    },
    # CURRENT THD (%)
    "current_l1_thd": {
        "unit": "%",
        "description": "Current THD Phase L1",
        "aliases": ["thd", "thd l1"],
    },
    "current_l3_thd": {
        "unit": "%",
        "description": "Current THD Phase L3",
        "aliases": ["thd l3"],
    },
    # VOLTAGE (V)
    "volts_l_n_avg": {
        "unit": "V",
        "description": "Phase-to-neutral voltage average",
        "aliases": ["voltage", "voltage readings"],
    },
    "volts_l_l_avg": {
        "unit": "V",
        "description": "Phase-to-phase voltage average",
        "aliases": [],
    },
    "volts_l1_n": {
        "unit": "V",
        "description": "Phase L1 to neutral voltage",
        "aliases": [],
    },
    "volts_l2_n": {
        "unit": "V",
        "description": "Phase L2 to neutral voltage",
        "aliases": [],
    },
    "volts_l3_n": {
        "unit": "V",
        "description": "Phase L3 to neutral voltage",
        "aliases": [],
    },
    "volts_l1_l2": {
        "unit": "V",
        "description": "Phase L1 to L2 voltage",
        "aliases": [],
    },
    "volts_l2_l3": {
        "unit": "V",
        "description": "Phase L2 to L3 voltage",
        "aliases": [],
    },
    "volts_l3_l1": {
        "unit": "V",
        "description": "Phase L3 to L1 voltage",
        "aliases": [],
    },
    # THD (%)
    "volts_l1_thd": {
        "unit": "%",
        "description": "Voltage THD Phase L1",
        "aliases": [],
    },
    "volts_l2_thd": {
        "unit": "%",
        "description": "Voltage THD Phase L2",
        "aliases": [],
    },
    "volts_l3_thd": {
        "unit": "%",
        "description": "Voltage THD Phase L3",
        "aliases": [],
    },
    # POWER FACTOR (unitless, -1 to 1)
    "power_factor_avg": {
        "unit": "",
        "description": "Power factor average (unitless ratio -1 to 1)",
        "aliases": ["power factor"],
    },
    "power_factor_l1": {
        "unit": "",
        "description": "Power factor Phase L1 (unitless ratio -1 to 1)",
        "aliases": [],
    },
    "power_factor_l2": {
        "unit": "",
        "description": "Power factor Phase L2 (unitless ratio -1 to 1)",
        "aliases": [],
    },
    "power_factor_l3": {
        "unit": "",
        "description": "Power factor Phase L3 (unitless ratio -1 to 1)",
        "aliases": [],
    },
    # FREQUENCY (Hz)
    "freq": {
        "unit": "Hz",
        "description": "System frequency",
        "aliases": ["frequency"],
    },
    # UNBALANCE (%)
    "current_unbalance": {
        "unit": "%",
        "description": "Current unbalance percentage",
        "aliases": ["unbalance", "phase imbalance", "phase unbalance", "current imbalance"],
    },
    "volts_unbalance": {
        "unit": "%",
        "description": "Voltage unbalance percentage",
        "aliases": ["voltage unbalance", "voltage imbalance"],
    },
    # OTHER
    "digital_input_1_and_2": {
        "unit": "",
        "description": "Binary status inputs",
        "aliases": [],
    },
}
```

- [ ] **Step 4: Update ALLOWED_METRICS, get_metric_unit, get_metric_description**

In `backend/models/schemas.py`, the `ALLOWED_METRICS` line (currently line 86) stays the same — `list(ALLOWED_METRICS_WITH_UNITS.keys())` works with both shapes.

Update `get_metric_unit` (around line 441):

```python
def get_metric_unit(metric: str) -> str:
    entry = ALLOWED_METRICS_WITH_UNITS.get(metric)
    if entry is None:
        return ""
    return entry["unit"]
```

Update `get_metric_description` (around line 456):

```python
def get_metric_description(metric: str) -> str:
    entry = ALLOWED_METRICS_WITH_UNITS.get(metric)
    if entry is None:
        return ""
    return entry["description"]
```

- [ ] **Step 5: Add resolve_metric function**

Add after the `ALLOWED_METRICS` line in `backend/models/schemas.py`:

```python
# ── Metric alias resolver ────────────────────────────────────────────────────

def _build_alias_lookup() -> dict[str, str]:
    """
    Build reverse lookup: alias string -> metric key.
    Sorted longest-first so multi-word aliases match before single-word.
    """
    lookup: dict[str, str] = {}
    # First pass: add all metric key names themselves
    for key in ALLOWED_METRICS_WITH_UNITS:
        lookup[key] = key
    # Second pass: add aliases (longer aliases inserted first for priority)
    pairs: list[tuple[str, str]] = []
    for key, entry in ALLOWED_METRICS_WITH_UNITS.items():
        for alias in entry["aliases"]:
            pairs.append((alias.lower(), key))
    # Sort by alias length descending — longest match wins
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    for alias, key in pairs:
        if alias not in lookup:  # don't override metric key names
            lookup[alias] = key
    return lookup


_ALIAS_LOOKUP: dict[str, str] = _build_alias_lookup()
# Sorted by length descending for substring matching
_ALIAS_KEYS_BY_LENGTH: list[str] = sorted(_ALIAS_LOOKUP.keys(), key=len, reverse=True)


def resolve_metric(text: str) -> str | None:
    """
    Resolve a natural-language query text to a metric key.

    Matching strategy:
      1. Exact metric key match (e.g., "power_total" in text)
      2. Longest alias substring match (multi-word before single-word)

    Returns the metric key string, or None if no match.
    """
    text_lower = text.lower()
    for alias in _ALIAS_KEYS_BY_LENGTH:
        if alias in text_lower:
            return _ALIAS_LOOKUP[alias]
    return None
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_schemas.py -v`

Expected: All tests pass.

- [ ] **Step 7: Run existing tests to verify no regressions**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All existing tests pass — particularly `test_translator.py::test_metric_patterns` which validates alias resolution.

- [ ] **Step 8: Commit**

```bash
git add backend/models/schemas.py backend/tests/test_schemas.py
git commit -m "feat: restructure metric registry with aliases and add resolve_metric"
```

---

## Task 6: Rewrite _parse_query_rules to Use resolve_metric

**Files:**
- Modify: `backend/llm/translator.py:120-379` (_parse_query_rules)
- Modify: `backend/tests/test_translator.py`

- [ ] **Step 1: Add regression test for edge cases before rewriting**

Add to `backend/tests/test_translator.py`:

```python
def test_ranking_query_all_levels():
    """'rank all devices by energy' should produce ranking with empty device_ids."""
    from llm.translator import _parse_query_rules
    from models.schemas import QueryType
    q, err = _parse_query_rules("rank all devices by energy")
    assert err is None
    assert q.query_type == QueryType.ranking


def test_top_n_extraction():
    """'top 5 devices by power level 3' should set top_n=5."""
    from llm.translator import _parse_query_rules
    q, err = _parse_query_rules("top 5 devices by power level 3")
    assert err is None
    assert q.top_n == 5


def test_time_range_month():
    """'energy for e0101 this month' should set time_range to last_30d."""
    from llm.translator import _parse_query_rules
    q, err = _parse_query_rules("energy for e0101 this month")
    assert err is None
    assert q.time_range == "last_30d"
```

- [ ] **Step 2: Run new + existing tests (should pass with old code)**

Run: `cd backend && python -m pytest tests/test_translator.py -v`

Expected: All pass (new tests validate behavior the old parser already handles).

- [ ] **Step 3: Rewrite _parse_query_rules**

Replace `_parse_query_rules` in `backend/llm/translator.py` (lines 120-379) with:

```python
def _parse_query_rules(user_query: str) -> tuple[Union[StructuredQuery, None], Union[str, None]]:
    """
    Rule-based query parser (production path when ENABLE_LLM=false).

    Uses resolve_metric() from schemas.py for metric resolution.
    """
    import re
    from models.schemas import QueryType, AHU_LEVEL_CONFIG, resolve_metric

    query_lower = user_query.lower().strip()

    # ── Extract device IDs (e0101, e0202, etc.) ──────────────────────────────
    devices = re.findall(r'\be\d{4}\b', query_lower)

    # ── Extract levels (e.g., "level 3", "level 03") ────────────────────────
    level_pattern = r'levels?\s+(.+?)(?:\bfor\b|$)'
    level_matches = re.findall(level_pattern, query_lower)
    levels_expanded: list[str] = []
    for match in level_matches:
        for level_str in re.findall(r'\b(0?[1-9]|1[01])\b', match):
            level_num = int(level_str)
            if 1 <= level_num <= 11:
                levels_expanded.append(f"{level_num:02d}")

    # ── Resolve metric via registry ──────────────────────────────────────────
    resolved = resolve_metric(query_lower)
    default_metric = resolved if resolved else "power_total"

    # ── Extract time range ───────────────────────────────────────────────────
    if 'today' in query_lower or '24h' in query_lower:
        default_time_range = "last_24h"
    elif 'week' in query_lower or '7d' in query_lower:
        default_time_range = "last_7d"
    elif 'month' in query_lower or '30 days' in query_lower or 'past 30 days' in query_lower or 'last 30d' in query_lower:
        default_time_range = "last_30d"
    elif 'all time' in query_lower or 'entire' in query_lower:
        default_time_range = "all_time"
    else:
        default_time_range = "last_7d"

    # ── Determine query type ─────────────────────────────────────────────────
    is_ranking = any(word in query_lower for word in [
        'rank', 'top', 'compare', 'worst', 'lowest', 'highest',
        'devices have', 'comparison', 'comparing'
    ])

    prediction_keywords = {
        'predict', 'forecast', 'next', 'upcoming', 'future',
        'ahead', 'will', 'tomorrow', 'expect', 'projection', 'estimate', 'spike'
    }
    is_prediction = any(kw in query_lower for kw in prediction_keywords)

    health_index_keywords = {
        'health index', 'health score', 'fair score', 'ahu score',
        'health trend', 'score trend', 'overall health'
    }
    is_health_index = any(kw in query_lower for kw in health_index_keywords)

    if is_health_index:
        query_type = QueryType.health_index
    elif is_prediction:
        query_type = QueryType.prediction
    elif is_ranking:
        query_type = QueryType.ranking
    else:
        query_type = QueryType.time_series

    # ── Auto-upgrade to ranking: metric + level, no devices, no time intent ──
    time_keywords = {
        'today', '24h', 'week', '7d', 'month', '30 days',
        'all time', 'entire', 'trend', 'over time', 'history', 'past'
    }
    has_time_intent = any(kw in query_lower for kw in time_keywords)

    if (
        query_type == QueryType.time_series
        and levels_expanded
        and not devices
        and resolved is not None
        and not has_time_intent
    ):
        query_type = QueryType.ranking

    # ── Determine top_n for ranking ──────────────────────────────────────────
    top_n = None
    if query_type == QueryType.ranking:
        top_n_match = re.search(r'top\s+(\d+)', query_lower)
        if top_n_match:
            top_n = int(top_n_match.group(1))
        elif any(word in query_lower for word in ['all', 'every', 'whole']):
            top_n = None
        elif 'compare' in query_lower and not any(word in query_lower for word in ['top', 'highest', 'lowest', 'best', 'worst']):
            top_n = None
        else:
            top_n = 10

    # ── Confidence gate ──────────────────────────────────────────────────────
    understood_anything = (
        bool(devices)
        or bool(levels_expanded)
        or is_ranking
        or is_prediction
        or is_health_index
        or resolved is not None
    )

    if not understood_anything:
        return None, (
            "I couldn't understand that query. Try asking something like: "
            "'show power for e0101', 'top 10 AHUs by energy level 3', "
            "'forecast power for level 5', or 'health index level 2'."
        )

    # ── Build device_ids ─────────────────────────────────────────────────────
    device_ids: list[str] = []

    # Expand levels to device IDs
    if levels_expanded and not devices:
        for level_str in levels_expanded:
            level_int = int(level_str)
            if level_int in AHU_LEVEL_CONFIG:
                device_ids.extend(AHU_LEVEL_CONFIG[level_int]['device_ids'])
        device_ids = list(dict.fromkeys(device_ids))  # deduplicate

    # Handle "all devices/levels" for ranking
    if query_type == QueryType.ranking:
        has_all_levels = any(phrase in query_lower for phrase in [
            'all levels', 'across all', 'all ahus', 'all devices',
            'every level', 'entire building', 'building-wide'
        ])
        if has_all_levels and not levels_expanded:
            device_ids = []  # empty means "all" for ranking

    # Fall back to explicit device IDs or default
    if not device_ids and not (query_type == QueryType.ranking and not levels_expanded and not devices):
        device_ids = devices if devices else ["e0101"]

    try:
        return StructuredQuery(
            query_type=query_type,
            device_ids=device_ids,
            metric=default_metric,
            time_range=default_time_range,
            top_n=top_n,
        ), None
    except Exception as e:
        return None, f"Could not parse query: {user_query}. Error: {e}"
```

- [ ] **Step 4: Run all translator tests**

Run: `cd backend && python -m pytest tests/test_translator.py -v`

Expected: All tests pass — including the parametrized `test_metric_patterns` that validates alias resolution.

- [ ] **Step 5: Run full backend test suite**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/llm/translator.py backend/tests/test_translator.py
git commit -m "refactor: rewrite _parse_query_rules to use metric registry"
```

---

## Task 7: Circuit Breaker

**Files:**
- Create: `backend/llm/circuit_breaker.py`
- Create: `backend/tests/test_circuit_breaker.py`

- [ ] **Step 1: Write failing tests for circuit breaker state transitions**

Create `backend/tests/test_circuit_breaker.py`:

```python
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from llm.circuit_breaker import CircuitBreaker, LLMUnavailableError


@pytest.fixture
def breaker():
    """Breaker with low thresholds for fast testing."""
    return CircuitBreaker(failure_threshold=2, cooldown_seconds=1)


def test_starts_closed(breaker):
    """Breaker starts in CLOSED state."""
    assert breaker.state == "closed"


def test_success_keeps_closed(breaker):
    """Successful call keeps breaker closed."""
    breaker.record_success()
    assert breaker.state == "closed"


def test_failures_trip_to_open(breaker):
    """After failure_threshold consecutive failures, state becomes OPEN."""
    breaker.record_failure()
    assert breaker.state == "closed"
    breaker.record_failure()
    assert breaker.state == "open"


def test_open_state_raises(breaker):
    """check_state raises LLMUnavailableError when OPEN."""
    breaker.record_failure()
    breaker.record_failure()
    with pytest.raises(LLMUnavailableError):
        breaker.check_state()


def test_success_resets_failure_count(breaker):
    """A success resets the consecutive failure counter."""
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert breaker.state == "closed"  # only 1 consecutive failure


def test_open_transitions_to_half_open_after_cooldown(breaker):
    """After cooldown expires, state becomes HALF_OPEN."""
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == "open"

    time.sleep(1.1)  # cooldown is 1 second
    assert breaker.state == "half_open"


def test_half_open_success_closes(breaker):
    """Success in HALF_OPEN transitions to CLOSED."""
    breaker.record_failure()
    breaker.record_failure()
    time.sleep(1.1)
    assert breaker.state == "half_open"

    breaker.record_success()
    assert breaker.state == "closed"


def test_half_open_failure_reopens(breaker):
    """Failure in HALF_OPEN transitions back to OPEN."""
    breaker.record_failure()
    breaker.record_failure()
    time.sleep(1.1)
    assert breaker.state == "half_open"

    breaker.record_failure()
    assert breaker.state == "open"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_circuit_breaker.py -v`

Expected: FAIL — `circuit_breaker` module doesn't exist.

- [ ] **Step 3: Implement CircuitBreaker**

Create `backend/llm/circuit_breaker.py`:

```python
"""
llm/circuit_breaker.py
──────────────────────
Lightweight circuit breaker for LLM calls.

States: CLOSED → OPEN → HALF_OPEN → CLOSED (or back to OPEN).
Prevents repeated 60-second timeouts when LM Studio is down.
"""

import os
import time
import threading


class LLMUnavailableError(Exception):
    """Raised when the circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    In-memory circuit breaker with three states.

    Args:
        failure_threshold: Consecutive failures to trip the breaker.
        cooldown_seconds: How long OPEN state lasts before probing.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        cooldown_seconds: float | None = None,
    ):
        self._failure_threshold = failure_threshold or int(
            os.getenv("LLM_FAILURE_THRESHOLD", "3")
        )
        self._cooldown_seconds = cooldown_seconds or float(
            os.getenv("LLM_COOLDOWN_SECONDS", "300")
        )
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._consecutive_failures < self._failure_threshold:
                return "closed"
            # Breaker has been tripped
            if self._opened_at is None:
                return "open"
            elapsed = time.time() - self._opened_at
            if elapsed >= self._cooldown_seconds:
                return "half_open"
            return "open"

    def check_state(self) -> None:
        """Raise LLMUnavailableError if the breaker is OPEN."""
        s = self.state
        if s == "open":
            raise LLMUnavailableError(
                "AI is temporarily unavailable, please try again in a few minutes."
            )
        # half_open and closed: allow the call through

    def record_success(self) -> None:
        """Record a successful call. Resets failure counter."""
        with self._lock:
            self._consecutive_failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        """Record a failed call. May trip the breaker."""
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._opened_at = time.time()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_circuit_breaker.py -v`

Expected: All 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/llm/circuit_breaker.py backend/tests/test_circuit_breaker.py
git commit -m "feat: add circuit breaker for LLM calls"
```

---

## Task 8: Integrate Circuit Breaker into QwenClient and Routes

**Files:**
- Modify: `backend/llm/qwen_client.py:30-42` (init) and `58-72`, `96-109`, `163-169` (call sites)
- Modify: `backend/routes/chat.py:86-95`
- Modify: `backend/routes/query.py:195-207`

- [ ] **Step 1: Add breaker to QwenClient**

In `backend/llm/qwen_client.py`, add import at the top (after line 9):

```python
from llm.circuit_breaker import CircuitBreaker, LLMUnavailableError
```

In `QwenClient.__init__` (line 33), add after `self._model = get_lms_model()` (line 41):

```python
        self._breaker = CircuitBreaker()
```

In `generate_text` (line 44), wrap the `try`/`except` block (lines 58-72). Replace:

```python
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(
                    self._client.chat.completions.create,
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                ),
            )
            return _strip_think(response.choices[0].message.content)
        except Exception as e:
            logger.warning(f"LM Studio unreachable: {e}")
            return "Local LM Studio is not available in this environment."
```

With:

```python
        self._breaker.check_state()
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(
                    self._client.chat.completions.create,
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                ),
            )
            self._breaker.record_success()
            return _strip_think(response.choices[0].message.content)
        except LLMUnavailableError:
            raise
        except Exception as e:
            self._breaker.record_failure()
            logger.warning(f"LM Studio unreachable: {e}")
            raise LLMUnavailableError(f"LM Studio unreachable: {e}")
```

Apply the same pattern to `generate_chat_response` (lines 96-109) and the inner try/except in `generate_with_tools` (lines 152-169). For `generate_with_tools`, add `self._breaker.check_state()` before the loop starts (before line 145), add `self._breaker.record_success()` after a successful response with no tool calls (before line 177's `return`), and change the generic exception handler to record failure and re-raise as `LLMUnavailableError`.

- [ ] **Step 2: Catch LLMUnavailableError in chat route**

In `backend/routes/chat.py`, add import (after line 20):

```python
from llm.circuit_breaker import LLMUnavailableError
```

Replace the exception handler at line 94-95:

```python
    except LLMUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="AI is temporarily unavailable, please try again in a few minutes."
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")
```

- [ ] **Step 3: Catch LLMUnavailableError in query route**

In `backend/routes/query.py`, add import (after line 24):

```python
from llm.circuit_breaker import LLMUnavailableError
```

In `handle_query` (line 182), add a catch for `LLMUnavailableError` in the LLM translation try/except (lines 195-207). After `try:` and before the generic `except Exception as e:`:

```python
    except LLMUnavailableError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "AI is temporarily unavailable, please try again in a few minutes.",
                "suggestion": "The system will automatically retry. Please wait a moment."
            }
        )
```

- [ ] **Step 4: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All tests pass. The chat endpoint test should still work (QwenClient is typically mocked in tests).

- [ ] **Step 5: Commit**

```bash
git add backend/llm/qwen_client.py backend/routes/chat.py backend/routes/query.py
git commit -m "feat: integrate circuit breaker into QwenClient and route handlers"
```

---

## Task 9: Rate Limiter Protocol and InMemoryRateLimiter

**Files:**
- Create: `backend/middleware/rate_limiter.py`
- Create: `backend/tests/test_rate_limiter.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_rate_limiter.py`:

```python
import os
import sys
import time
import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from middleware.rate_limiter import InMemoryRateLimiter


def test_allows_under_limit():
    """Requests under the limit should pass without error."""
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.1")
    # 3 requests = at the limit, should still pass


def test_blocks_over_limit():
    """Requests over the limit should raise HTTPException 429."""
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.1")
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("192.168.1.1")
    assert exc_info.value.status_code == 429


def test_different_keys_independent():
    """Different IPs should have independent limits."""
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.2")  # different IP, should pass


def test_window_resets():
    """After the window expires, the limit resets."""
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=1)
    limiter.check("192.168.1.1")
    with pytest.raises(HTTPException):
        limiter.check("192.168.1.1")

    time.sleep(1.1)  # wait for window to expire
    limiter.check("192.168.1.1")  # should pass now
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rate_limiter.py -v`

Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement rate limiter**

Create `backend/middleware/rate_limiter.py`:

```python
"""
middleware/rate_limiter.py
─────────────────────────
Rate limiter abstraction. Ships with InMemoryRateLimiter;
swap to Redis later by implementing the same protocol.
"""

import os
import time
from collections import defaultdict
from typing import Protocol

from fastapi import HTTPException


class RateLimiter(Protocol):
    def check(self, key: str) -> None:
        """Raise HTTPException(429) if rate limit exceeded."""
        ...


class InMemoryRateLimiter:
    """Sliding-window rate limiter using in-memory storage."""

    def __init__(self, max_requests: int, window_seconds: int):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.time()
        hits = [t for t in self._store[key] if now - t < self._window_seconds]
        hits.append(now)
        self._store[key] = hits
        if len(hits) > self._max_requests:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests. Please wait a moment before trying again."
                },
            )


def get_rate_limiter() -> RateLimiter:
    """Factory — returns configured InMemoryRateLimiter."""
    return InMemoryRateLimiter(
        max_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
        window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rate_limiter.py -v`

Expected: All 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/rate_limiter.py backend/tests/test_rate_limiter.py
git commit -m "feat: add rate limiter protocol and InMemoryRateLimiter"
```

---

## Task 10: Replace Inline Rate Limiter in query.py

**Files:**
- Modify: `backend/routes/query.py:34-48` (remove inline code), `182-187` (update usage)

- [ ] **Step 1: Remove inline rate limiter and wire the new one**

In `backend/routes/query.py`, remove the inline rate limiter code (lines 34-48):

Remove:
```python
# ── Rate limiter (in-memory, per IP) ────────────────────────────────────────
_rate_store: dict = defaultdict(list)
RATE_LIMIT        = 20   # requests
RATE_WINDOW       = 60   # seconds

def _check_rate_limit(ip: str) -> None:
    now  = time.time()
    hits = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    hits.append(now)
    _rate_store[ip] = hits
    if len(hits) > RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={"error": "Too many requests. Please wait a moment before trying again."}
        )
```

Also remove the unused imports that were only needed by the inline limiter: `defaultdict` from `collections` (line 14) and `time` (line 11) — but check if `time` is used elsewhere first. (`time` is not used elsewhere in query.py, so it can be removed. `uuid`, `re`, `logging` are still used.)

Add the import at the top:

```python
from middleware.rate_limiter import get_rate_limiter
```

Add after the imports:

```python
_limiter = get_rate_limiter()
```

In `handle_query` (line 182), replace `_check_rate_limit(client_ip)` (line 187) with:

```python
    _limiter.check(client_ip)
```

- [ ] **Step 2: Run security tests**

Run: `cd backend && python -m pytest tests/test_security.py -v`

Expected: All pass (rate limiting behavior is preserved).

- [ ] **Step 3: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/query.py
git commit -m "refactor: replace inline rate limiter with RateLimiter protocol"
```

---

## Task 11: Final Verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest tests/ -v --tb=short`

Expected: All tests pass.

- [ ] **Step 2: Start backend and verify API responses include metadata**

Run: `cd backend && python main.py`

Then in another terminal:
```bash
curl -s http://localhost:8081/api/dashboard/ranking?level=1\&time_range=last_7d | python -m json.tool | grep -A3 metadata
```

Expected: Response includes `"metadata": {"data_as_of": ..., "sync_age_seconds": ...}`.

- [ ] **Step 3: Start frontend and verify freshness indicator**

Run: `cd frontend && npm run dev`

Open `http://localhost:3000`, select a level. Verify "Data as of X ago" text appears.

- [ ] **Step 4: Final commit (if any fixups needed)**

Only if previous steps required changes. Otherwise, all commits from Tasks 1-10 cover everything.
