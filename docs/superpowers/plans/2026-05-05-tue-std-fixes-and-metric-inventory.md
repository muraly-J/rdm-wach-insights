# Tue — Scoring Std Fixes + 46-Metric Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the Mon audit's "Tuesday AM batch" fixes so all scores are **0–100, high = good** at the API boundary with a single converter utility; then enumerate every power-meter field in InfluxDB and write a 46-row metric inventory ready for Wed prototype work.

**Architecture:** Two halves.
- **AM**: Apply Mon `docs/audits/2026-05-04-scoring-audit.md` fix list. Add a single canonical converter in `backend/core/fair_health_scoring.py`. Push conversions to the API boundary (route layer). Strip scale/direction math from frontend components. Update tests.
- **PM**: Read-only inventory. Use `backend/core/influx_client.py` helpers + a one-off Flux schema query to enumerate fields, plus a sample-range pass over recent data. Output is a markdown matrix.

**Tech Stack:** Python 3.11 (FastAPI, pandas, numpy, InfluxDB client), TypeScript/React (Recharts), pytest, ruff. InfluxDB Cloud schema discovery via Flux `schema.fieldKeys()` / `import "influxdata/influxdb/schema"`.

**Inputs (must exist before starting):**
- `docs/audits/2026-05-04-scoring-audit.md` (Mon deliverable) — specifically the **Ranked Fix List → "Tuesday AM batch"** section.

**Existing context:**
- FAIR sub-scores live in `backend/core/fair_health_scoring.py` as `score_energy_anomaly`, `score_power_factor`, `score_phase_imbalance`, `score_thd_drift`, `score_overload`. Each currently returns 0–1 (see `clamp01` at `fair_health_scoring.py:278`).
- `calculate_health_index(scores: dict[str, float]) -> float` at `fair_health_scoring.py:580` produces the composite. Tests (`test_db_reader.py`, `test_watchman.py`, `test_tool_handlers.py`) already assert `health_index` on a 0–100 scale, so the composite is canonical; sub-scores are not.
- Recent commits already inverted FAIR sub-scores to high=good (`0dbb31c`, `4aa8c90`, `1f7d7db`). Direction should be correct; scale and conversion-site placement is the remaining work.

---

## File Structure

**Created:**
- `backend/core/score_normalize.py` — single canonical converter module (NEW)
- `docs/audits/2026-05-04-metric-inventory.md` — 46-row metric inventory (NEW)
- `scripts/research/list_power_metrics.py` — one-off InfluxDB schema enumerator (NEW)
- `backend/tests/test_score_normalize.py` — unit tests for the converter (NEW)

**Modified (only files named in Mon Fix List):**
- `backend/routes/health_scores.py` — apply normalize at response boundary
- `backend/routes/dashboard.py` — same
- `backend/core/fair_health_scoring.py` — re-export `to_canonical` for ergonomic import; no formula edits
- Frontend score-rendering components named in Mon audit (e.g. `HealthIndexChart.tsx`, `ScoreCard.tsx`, `CombinedScoresChart.tsx`, `components/dashboard/derivation/*`) — strip in-component scale/direction math
- `backend/tests/` — update assertions for any sub-score now at 0–100

**Read-only:**
- `docs/audits/2026-05-04-scoring-audit.md`
- `backend/core/influx_client.py`

---

### Task 1: Read the Mon audit and pin the Tuesday AM batch

**Files:**
- Read: `docs/audits/2026-05-04-scoring-audit.md`

- [ ] **Step 1: Open the audit and locate "Tuesday AM batch" cutoff**

Read top to bottom. Note exactly which fix entries fall above the cutoff. For each, capture:
- Target file + line range
- Field name(s) being normalized
- Tests to update

- [ ] **Step 2: Write a working list at top of this plan execution**

In your scratchpad (NOT in the plan file), write a numbered list of every fix in the Tuesday AM batch. Example:
```
1. Normalize FAIR sub-scores to 0-100 in /api/health-scores response (health_scores.py:42)
2. Remove `* 100` in HealthIndexChart.tsx:88
3. Update test_db_reader.py expectations for fairness sub-score
...
```
This list is the source of truth for Tasks 4–6 — do not invent additional changes.

- [ ] **Step 3: No commit (planning only)**

---

### Task 2: Create canonical converter with tests (TDD)

**Files:**
- Create: `backend/core/score_normalize.py`
- Create: `backend/tests/test_score_normalize.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_score_normalize.py`:

```python
import math

import pytest

from backend.core.score_normalize import to_canonical, from_canonical


class TestToCanonical:
    def test_zero_to_one_scale_high_good_passthrough(self):
        assert to_canonical(0.0, scale="0-1", direction="high-good") == 0.0
        assert to_canonical(1.0, scale="0-1", direction="high-good") == 100.0
        assert to_canonical(0.5, scale="0-1", direction="high-good") == 50.0

    def test_zero_to_one_scale_high_bad_inverts(self):
        assert to_canonical(0.0, scale="0-1", direction="high-bad") == 100.0
        assert to_canonical(1.0, scale="0-1", direction="high-bad") == 0.0
        assert to_canonical(0.25, scale="0-1", direction="high-bad") == 75.0

    def test_zero_to_hundred_high_good_passthrough(self):
        assert to_canonical(73.0, scale="0-100", direction="high-good") == 73.0

    def test_zero_to_hundred_high_bad_inverts(self):
        assert to_canonical(73.0, scale="0-100", direction="high-bad") == 27.0

    def test_clamps_above_range(self):
        assert to_canonical(1.5, scale="0-1", direction="high-good") == 100.0
        assert to_canonical(150.0, scale="0-100", direction="high-good") == 100.0

    def test_clamps_below_range(self):
        assert to_canonical(-0.2, scale="0-1", direction="high-good") == 0.0
        assert to_canonical(-5.0, scale="0-100", direction="high-good") == 0.0

    def test_none_returns_none(self):
        assert to_canonical(None, scale="0-1", direction="high-good") is None

    def test_nan_returns_none(self):
        assert to_canonical(float("nan"), scale="0-1", direction="high-good") is None

    def test_invalid_scale_raises(self):
        with pytest.raises(ValueError):
            to_canonical(0.5, scale="0-10", direction="high-good")

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            to_canonical(0.5, scale="0-1", direction="up")


class TestFromCanonical:
    def test_round_trip_zero_to_one_high_good(self):
        for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
            canonical = to_canonical(v, scale="0-1", direction="high-good")
            assert math.isclose(
                from_canonical(canonical, scale="0-1", direction="high-good"), v, abs_tol=1e-9
            )
```

- [ ] **Step 2: Run test, verify failure**

Run: `cd backend && python -m pytest tests/test_score_normalize.py -v`
Expected: `ModuleNotFoundError: No module named 'backend.core.score_normalize'` (or equivalent ImportError).

- [ ] **Step 3: Implement `score_normalize.py`**

Create `backend/core/score_normalize.py`:

```python
"""Canonical score representation: 0-100, high=good. Convert at API boundary only."""

from __future__ import annotations

import math
from typing import Literal, Optional

Scale = Literal["0-1", "0-100"]
Direction = Literal["high-good", "high-bad"]

_VALID_SCALES = ("0-1", "0-100")
_VALID_DIRECTIONS = ("high-good", "high-bad")


def _check(scale: str, direction: str) -> None:
    if scale not in _VALID_SCALES:
        raise ValueError(f"scale must be one of {_VALID_SCALES}, got {scale!r}")
    if direction not in _VALID_DIRECTIONS:
        raise ValueError(f"direction must be one of {_VALID_DIRECTIONS}, got {direction!r}")


def to_canonical(
    value: Optional[float], *, scale: Scale, direction: Direction
) -> Optional[float]:
    """Convert a raw score to canonical 0-100 high=good. None/NaN passthrough as None."""
    _check(scale, direction)
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if scale == "0-1":
        v = value * 100.0
    else:
        v = float(value)
    if direction == "high-bad":
        v = 100.0 - v
    return max(0.0, min(100.0, v))


def from_canonical(
    value: Optional[float], *, scale: Scale, direction: Direction
) -> Optional[float]:
    """Inverse of to_canonical. Used only for tests/round-trip validation."""
    _check(scale, direction)
    if value is None:
        return None
    v = float(value)
    if direction == "high-bad":
        v = 100.0 - v
    if scale == "0-1":
        v = v / 100.0
    return v
```

- [ ] **Step 4: Run test, verify pass**

Run: `cd backend && python -m pytest tests/test_score_normalize.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/score_normalize.py backend/tests/test_score_normalize.py
git commit -m "feat(scoring): add canonical 0-100 high-good converter with tests"
```

---

### Task 3: Wire converter into FAIR scoring module (re-export)

**Files:**
- Modify: `backend/core/fair_health_scoring.py`

- [ ] **Step 1: Add import + re-export at top of file (after existing imports)**

Add:

```python
from backend.core.score_normalize import to_canonical as _to_canonical_score

# Re-export for ergonomic call sites: from backend.core.fair_health_scoring import to_canonical
to_canonical = _to_canonical_score
```

Place immediately below the existing import block. Do NOT modify any `score_*` function or `calculate_health_index`.

- [ ] **Step 2: Run full backend tests to confirm no regression**

Run: `cd backend && python -m pytest tests/ -x --ignore=tests/e2e -q`
Expected: green (or same baseline as pre-change).

- [ ] **Step 3: Commit**

```bash
git add backend/core/fair_health_scoring.py
git commit -m "refactor(scoring): re-export canonical converter from fair module"
```

---

### Task 4: Apply API-boundary normalization (driven by Mon Fix List)

**Files:** Determined by Task 1 working list. Typically:
- Modify: `backend/routes/health_scores.py`
- Modify: `backend/routes/dashboard.py`

**For each fix in the Tuesday AM batch that targets a route handler, do one TDD cycle:**

- [ ] **Step 1: Write/update a failing test asserting canonical response**

For each affected route, add or modify a test in `backend/tests/test_<route>.py` asserting:
- Each score field is `>= 0.0` and `<= 100.0`
- A known-degraded fixture produces a score `< 50` (high=good direction)
- A known-healthy fixture produces a score `> 50`

Example skeleton (adapt field names to actual route output):

```python
def test_health_scores_endpoint_returns_canonical_zero_to_hundred(client):
    response = client.get("/api/health-scores")
    assert response.status_code == 200
    payload = response.json()
    for entry in payload:
        for field in ("health_index", "fairness", "availability", "integrity", "reliability"):
            v = entry.get(field)
            if v is None:
                continue
            assert 0.0 <= v <= 100.0, f"{field}={v} out of canonical range"
```

- [ ] **Step 2: Run, verify failure**

Run: `cd backend && python -m pytest tests/test_health_scores.py -v`
Expected: FAIL on at least one assertion if any sub-score is currently 0–1.

- [ ] **Step 3: Apply normalization in handler**

In each handler that emits a score field, replace direct value with:

```python
from backend.core.score_normalize import to_canonical

# inside handler, per score field
entry["fairness"] = to_canonical(raw_fairness, scale="0-1", direction="high-good")
```

Use the scale + direction recorded in the Mon Producer Matrix for that field. **Do not guess.**

- [ ] **Step 4: Run, verify pass**

Run: `cd backend && python -m pytest tests/test_health_scores.py tests/test_dashboard.py -v`
Expected: PASS.

- [ ] **Step 5: Commit per route file**

```bash
git add backend/routes/<route>.py backend/tests/test_<route>.py
git commit -m "fix(api): normalize <route> scores to canonical 0-100 high-good"
```

Repeat Steps 1–5 for each route in the Mon AM batch.

---

### Task 5: Strip frontend scale/direction math

**Files:** Determined by Task 1 working list. Typically:
- Modify: `frontend/src/components/dashboard/HealthIndexChart.tsx`
- Modify: `frontend/src/components/dashboard/ScoreCard.tsx`
- Modify: `frontend/src/components/dashboard/CombinedScoresChart.tsx`
- Modify: files under `frontend/src/components/dashboard/derivation/`

**For each frontend component flagged in the Mon Fix List as "math at consumer":**

- [ ] **Step 1: Identify the offending expression**

Search the file for any of: `* 100`, `/ 100`, `1 - `, `100 -`, `(1.0 -`, applied to a score field. The Mon audit Frontend Matrix → "Math done in component?" column tells you exactly where.

- [ ] **Step 2: Remove the math**

The API now returns canonical 0–100 high=good. Replace e.g.:

```tsx
// before
const display = score * 100;
const color = score < 0.3 ? 'red' : 'green';
```

```tsx
// after
const display = score;
const color = score < 30 ? 'red' : 'green';
```

Also adjust any Recharts `domain={[0, 1]}` to `domain={[0, 100]}` and any `tickFormatter` that multiplied by 100.

- [ ] **Step 3: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors. Fix type drift if any.

- [ ] **Step 4: Run frontend tests**

Run: `cd frontend && npm test -- --watchAll=false`
Expected: green. If any snapshot/test asserted on 0–1 values, update to 0–100.

- [ ] **Step 5: Manual smoke (one component at a time)**

Run dev stack:
```bash
cd backend && python main.py &
cd frontend && npm run dev
```
Open `http://localhost:3000`, navigate to the page rendering the modified component, confirm:
- Values look sane (no 5000% bars, no inverted color coding)
- Healthy AHU shows green; degraded AHU shows red

- [ ] **Step 6: Commit per component**

```bash
git add frontend/src/components/dashboard/<File>.tsx
git commit -m "refactor(frontend): strip scale/direction math from <Component>; consume canonical API"
```

Repeat for each component in the Mon AM batch.

---

### Task 6: AM verification gate

**Files:** none modified.

- [ ] **Step 1: Full backend test run**

Run: `cd backend && python -m pytest tests/ --ignore=tests/e2e -q`
Expected: green.

- [ ] **Step 2: Lint / format**

Run: `cd backend && ruff check . && ruff format --check .`
Expected: clean. Fix and recommit if needed.

- [ ] **Step 3: Frontend lint + type**

Run: `cd frontend && npm run lint && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 4: Manual API spot check**

Run: `cd backend && python main.py` then in another terminal:
```bash
curl -s http://localhost:8081/api/health-scores | python -c "
import json, sys
data = json.load(sys.stdin)
for e in data[:5]:
    for k, v in e.items():
        if isinstance(v, (int, float)) and 'score' in k or k in ('health_index','fairness','availability','integrity','reliability'):
            assert v is None or 0 <= v <= 100, f'{k}={v}'
print('OK', len(data), 'rows')
"
```
Expected: prints `OK <n> rows` with no AssertionError.

- [ ] **Step 5: AM checkpoint commit (if any uncommitted lint fixes)**

```bash
git add -A
git commit -m "chore: AM checkpoint after scoring std fixes"
```

---

### Task 7: Build power-meter metric enumerator script

**Files:**
- Create: `scripts/research/list_power_metrics.py`

- [ ] **Step 1: Create directory if missing**

```bash
mkdir -p scripts/research
```

- [ ] **Step 2: Write enumerator script**

Create `scripts/research/list_power_metrics.py`:

```python
"""One-off: enumerate all power-meter fields in InfluxDB with sample ranges.

Output: prints CSV-like rows to stdout for paste into the metric inventory doc.
Columns: field_name, unit_guess, sample_min, sample_max, sample_count, last_seen
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from backend.config import (
    INFLUX_BUCKET,
    INFLUX_ORG,
    INFLUX_TOKEN,
    INFLUX_URL,
)
from influxdb_client import InfluxDBClient

# Confirm bucket / measurement names against backend/core/influx_client.py before running.
MEASUREMENT = "power_meter"
LOOKBACK = "-7d"


SCHEMA_QUERY = f'''
import "influxdata/influxdb/schema"
schema.fieldKeys(
    bucket: "{INFLUX_BUCKET}",
    predicate: (r) => r._measurement == "{MEASUREMENT}",
    start: {LOOKBACK},
)
'''


SAMPLE_QUERY_TEMPLATE = '''
from(bucket: "{bucket}")
    |> range(start: {lookback})
    |> filter(fn: (r) => r._measurement == "{measurement}" and r._field == "{field}")
    |> group()
    |> reduce(
        identity: {{cnt: 0, mn: 1e18, mx: -1e18, last: 0.0}},
        fn: (r, accumulator) => ({{
            cnt: accumulator.cnt + 1,
            mn: if r._value < accumulator.mn then r._value else accumulator.mn,
            mx: if r._value > accumulator.mx then r._value else accumulator.mx,
            last: r._value,
        }}),
    )
'''


def main() -> int:
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    fields: list[str] = []
    for table in query_api.query(SCHEMA_QUERY):
        for record in table.records:
            fields.append(record.get_value())

    print("field_name,unit_guess,sample_min,sample_max,sample_count")
    for f in sorted(fields):
        q = SAMPLE_QUERY_TEMPLATE.format(
            bucket=INFLUX_BUCKET, lookback=LOOKBACK, measurement=MEASUREMENT, field=f
        )
        tables = query_api.query(q)
        if not tables or not tables[0].records:
            print(f"{f},?,?,?,0")
            continue
        rec = tables[0].records[0]
        cnt = rec.values.get("cnt", 0)
        mn = rec.values.get("mn", "?")
        mx = rec.values.get("mx", "?")
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
```

- [ ] **Step 3: Verify measurement name**

Open `backend/core/influx_client.py` (functions `fetch_time_series`, `fetch_ranking`). Find the actual measurement name(s) used (likely `power_meter`, `electrical`, or similar). If different, update `MEASUREMENT` in the script. If multiple measurements carry power data, change `MEASUREMENT` to a tuple and union the schema query.

- [ ] **Step 4: Run the script**

Run: `cd /Users/rdmasia/wach-insight && python -m scripts.research.list_power_metrics > /tmp/metrics.csv`
Expected: ~46 rows in `/tmp/metrics.csv`. If row count is wildly off (e.g. 5 or 200), debug:
- 5 rows: wrong measurement name; check `backend/core/influx_client.py` query bodies.
- 200 rows: measurement includes non-power tags; add a tag filter (e.g. `r.source == "power_meter"`).

- [ ] **Step 5: Commit script**

```bash
git add scripts/research/list_power_metrics.py
git commit -m "chore(research): add one-off InfluxDB power-meter field enumerator"
```

---

### Task 8: Map each field to current FAIR-score consumer

**Files:** none modified yet (research step).

- [ ] **Step 1: Build the consumer map by grep**

For each unique field name in `/tmp/metrics.csv`, run:

```bash
field=<field_name>
rg -l "$field" backend/core/fair_health_scoring.py backend/core/healthdb.py backend/core/risk_engine.py scripts/etl scripts/generate
```

Record per field which of `score_energy_anomaly`, `score_power_factor`, `score_phase_imbalance`, `score_thd_drift`, `score_overload`, `calculate_health_index`, or "unused" consumes it.

- [ ] **Step 2: Save mapping to a temp file**

Write a CSV `/tmp/metric_consumers.csv` with columns `field_name,consumer` (one row per field; comma-separated multiple consumers if needed).

- [ ] **Step 3: No commit (intermediate research artifact)**

---

### Task 9: Write the metric inventory doc

**Files:**
- Create: `docs/audits/2026-05-04-metric-inventory.md`

- [ ] **Step 1: Write doc skeleton**

Create `docs/audits/2026-05-04-metric-inventory.md`:

```markdown
# Power-Meter Metric Inventory — 2026-05-04

Source: 7-day window, measurement `power_meter` in InfluxDB bucket `<bucket>`.
Generated by `scripts/research/list_power_metrics.py` + manual mapping.

## Legend

- **Tech-rank (1–5)**: technician-relevance for AHU controller health.
  - 5: directly diagnostic of failure mode (e.g. severe overload, sustained PF collapse)
  - 4: strong indicator with mild noise
  - 3: useful in combination
  - 2: weak / often redundant
  - 1: niche or unreliable
- **Tag**: `keep` (already used, retain), `drop` (redundant or noisy), `promote` (currently unused but candidate for new score), `?` (needs Wed validation).

## Metrics

| Field name | Unit | Sample min | Sample max | Sample count (7d) | Current consumer | Tech-rank | Tag |
|------------|------|------------|------------|-------------------|------------------|-----------|-----|
```

- [ ] **Step 2: Populate rows from `/tmp/metrics.csv` + `/tmp/metric_consumers.csv`**

Merge the two CSVs into rows. For each field:
- Copy `field_name`, `unit_guess`, `sample_min`, `sample_max`, `sample_count`
- Set `Current consumer` from the consumer map (or `unused`)
- Tech-rank: assign best-guess based on standard HVAC power diagnostics (PF, current imbalance, THD, overload current = high; voltage harmonics, frequency = mid; energy totalization = low for transient health). Mark uncertain ones `?` for Wed.
- Tag:
  - In an existing FAIR score → `keep`
  - `unused` AND tech-rank ≥ 4 → `promote`
  - `unused` AND tech-rank ≤ 2 → `drop`
  - `unused` AND tech-rank = 3 OR rank `?` → `?`

- [ ] **Step 3: Add a summary block at the bottom**

```markdown
## Summary

- Total fields: <n>
- Currently consumed: <n>
- Unused: <n>
- Promote candidates: <list field names>
- Drop candidates: <list field names>
- Needs validation (Wed): <list field names>
```

- [ ] **Step 4: Verify row count**

Run: `grep -c '^|' docs/audits/2026-05-04-metric-inventory.md`
Expected: header + separator + ~46 = ~48 lines starting with `|`. Confirm 46 metric rows.

- [ ] **Step 5: Commit**

```bash
git add docs/audits/2026-05-04-metric-inventory.md
git commit -m "docs(audit): add 46-row power-meter metric inventory"
```

---

### Task 10: End-of-day verification

**Files:** none modified.

- [ ] **Step 1: Backend tests green**

Run: `cd backend && python -m pytest tests/ --ignore=tests/e2e -q`
Expected: pass.

- [ ] **Step 2: Frontend builds**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 3: API still serves canonical**

Repeat Task 6 Step 4 curl check. Expected: `OK <n> rows`.

- [ ] **Step 4: Inventory complete**

Confirm `docs/audits/2026-05-04-metric-inventory.md` has 46 metric rows and a populated Summary block.

- [ ] **Step 5: Push to remote**

```bash
git push origin main
```

(Skip push if user prefers manual gate. Verify branch first if not on `main`.)

---

## Verification (end of Tue)

- [ ] Single converter `backend/core/score_normalize.py` exists with passing tests covering 0-1, 0-100, both directions, clamping, None/NaN, invalid args.
- [ ] All routes in the Mon AM batch return scores in `[0, 100]` with high=good direction (curl + pytest both confirm).
- [ ] No frontend component listed in the Mon Frontend Matrix still does scale/direction math (grep `* 100`, `/ 100`, `1 - score`, `100 - score` returns no matches in scope).
- [ ] `docs/audits/2026-05-04-metric-inventory.md` lists ~46 power-meter fields with non-`?` `Current consumer` values, tech-rank, and tag.
- [ ] `scripts/research/list_power_metrics.py` runs end-to-end (or its failure mode is documented inline if InfluxDB is unreachable from dev machine).
- [ ] Backend ruff clean, frontend tsc clean, all tests green.

---

## Risks

- **Mon audit batch larger than expected**: if "Tuesday AM batch" exceeds half a day, defer the lower-severity items in the batch to Wed AM and protect the inventory work — Wed prototype depends on inventory, not on every fix.
- **InfluxDB measurement name not `power_meter`**: most likely failure mode for Task 7. Read `backend/core/influx_client.py` query bodies first; the script's `MEASUREMENT` constant is the only thing to change.
- **Field count != 46**: if the schema returns ≠46, surface the count + suspected reason in the inventory doc Summary; user said "I think we have a total of 46" — actual count is the source of truth.
- **Sub-score test churn**: tests that asserted on 0–1 sub-scores will fail until updated. Update assertions, do not loosen them (`abs(x - expected) < 0.5` is fine on 0–100; `< 0.005` is not).
