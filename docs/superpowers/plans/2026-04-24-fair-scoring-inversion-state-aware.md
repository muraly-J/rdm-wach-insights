# FAIR Scoring Inversion & State-Aware Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Invert the FAIR scoring engine from penalty-based (0=healthy) to health-based (0=critical, 100=healthy), add On/Off state detection to baselines and DuckDB, then surface `<StateBadge />` on every frontend health display.

**Architecture:** Three sequential phases — Phase 1 inverts scoring math in the library and ETL (self-contained, reviewable alone); Phase 2 adds state detection to the production ETL and adds confidence-decay to the HealthDB query layer; Phase 3 wires state badges into all five frontend components and updates the LLM prompt.

**Tech Stack:** Python 3.11 (FastAPI backend, DuckDB, numpy/pandas), TypeScript/React (Zustand, Tailwind v3), pytest, Jest/React Testing Library.

---

> **IMPORTANT DISCOVERY (read before starting):**
> The spec mentions `scripts/generate/generate_fair_health_scores.py` as the ETL, but the **production pipeline** that actually writes to DuckDB is `scripts/etl/run_health_etl.py`. This file already fetches `current_l1/l2/l3` from InfluxDB (lines 435, 650, 810-812). Phase 2 state detection goes into `run_health_etl.py`, not the generate script.
> `generate_fair_health_scores.py` only needs Phase 1 score inversions (it has its own scoring copies but writes CSVs, not DuckDB).

---

## File Map

| File | Change |
|------|--------|
| `backend/core/fair_health_scoring.py` | Invert 5 score functions + `calculate_health_index` + `get_severity` |
| `backend/tests/unit/test_fair_health_scoring.py` | Flip `calculate_health_index` assertions |
| `scripts/etl/run_health_etl.py` | Mirror score inversions; add `is_operational()`; filter baselines to On-rows; write `operational_state` + `last_on_timestamp` |
| `scripts/generate/generate_fair_health_scores.py` | Mirror score inversions only |
| `backend/core/healthdb.py` | Add `operational_state`/`last_on_timestamp` columns + migration; add confidence-decay to `get_latest_snapshot()` |
| `frontend/src/types/index.ts` | Add `OperationalState` type; extend `DeviceRank`, `AlertAHU`, `LevelHealthTile` |
| `frontend/src/components/shared/StateBadge.tsx` | New component |
| `frontend/src/components/dashboard/AHURankingsTable.tsx` | Add `operational_state?` to `AHURankRow`; render `<StateBadge />` |
| `frontend/src/components/dashboard/DeviceDetailCard.tsx` | Render `<StateBadge />` |
| `frontend/src/components/dashboard/LatestOverview.tsx` | Render `<StateBadge />` |
| `frontend/src/components/dashboard/AlertsModal.tsx` | Render `<StateBadge />` |
| `frontend/src/components/chat/cards/WorkOrderCard.tsx` | Render `<StateBadge />` |
| `backend/llm/prompts.py` | Add state mention instructions |

---

## Phase 1 — Score Inversion

### Task 1: Write Failing Tests for Inverted `calculate_health_index`

**Files:**
- Modify: `backend/tests/unit/test_fair_health_scoring.py`

The existing tests reflect **penalty** semantics (score=0 means no penalty → index=100). After inversion, score=0 means critical → index=0. Write the new tests first so they fail, driving the implementation.

- [ ] **Step 1: Open the test file and replace the `TestCalculateHealthIndex` class**

```python
# backend/tests/unit/test_fair_health_scoring.py
# Replace the existing TestCalculateHealthIndex class with:

class TestCalculateHealthIndex:
    def test_all_zero_health_scores_give_zero_index(self):
        """All scores = 0 (critical on every metric) → health index = 0."""
        scores = {k: 0.0 for k in HEALTH_INDEX_WEIGHTS}
        assert calculate_health_index(scores) == pytest.approx(0.0, abs=1e-6)

    def test_all_one_health_scores_give_100_index(self):
        """All scores = 1 (healthy on every metric) → health index = 100."""
        scores = {k: 1.0 for k in HEALTH_INDEX_WEIGHTS}
        assert calculate_health_index(scores) == pytest.approx(100.0, abs=1e-6)

    def test_single_component_health_energy_only(self):
        """Only energy_anomaly = 1 (healthy), rest = 0 → index = 15 (15% weight)."""
        scores = {k: 0.0 for k in HEALTH_INDEX_WEIGHTS}
        scores["energy_anomaly"] = 1.0
        assert calculate_health_index(scores) == pytest.approx(15.0, abs=1e-6)

    def test_weights_sum_to_one(self):
        """Sanity check: HEALTH_INDEX_WEIGHTS sum to exactly 1.0."""
        assert sum(HEALTH_INDEX_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/unit/test_fair_health_scoring.py::TestCalculateHealthIndex -v
```

Expected: `FAILED` — `calculate_health_index` still uses old penalty formula.

---

### Task 2: Invert Scoring in `backend/core/fair_health_scoring.py`

**Files:**
- Modify: `backend/core/fair_health_scoring.py`

Three changes: (A) each `score_*` function returns `1.0 - penalty` instead of `penalty`; (B) error/unknown fallbacks change from `0.0` to `0.5` for `score_power_factor`, `score_phase_imbalance`, `score_thd_drift`; (C) `calculate_health_index` becomes a weighted sum; (D) `get_severity` thresholds flip.

- [ ] **Step 1: Invert `score_energy_anomaly`**

Find the return at line ~354:
```python
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)
```
Replace with:
```python
    penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return 1.0 - penalty, round(z, 3)
```

- [ ] **Step 2: Invert `score_power_factor`**

Change all early `return 0.0, np.nan` lines to `return 0.5, np.nan`. Then find the return at the end of the function:
```python
    return clamp01(score), round(z, 3)
```
Replace with:
```python
    penalty = clamp01(score)
    return 1.0 - penalty, round(z, 3)
```

- [ ] **Step 3: Invert `score_phase_imbalance`**

Change all early `return 0.0, np.nan` lines to `return 0.5, np.nan`. Then find the return at the end:
```python
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)
```
Replace with:
```python
    penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return 1.0 - penalty, round(z, 3)
```

- [ ] **Step 4: Invert `score_thd_drift`**

Change all early `return 0.0, np.nan` lines to `return 0.5, np.nan`. Then find the return at the end:
```python
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3)
```
Replace with:
```python
    penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return 1.0 - penalty, round(z, 3)
```

- [ ] **Step 5: Invert `score_overload`**

Find all early `return 0.5, np.nan` lines — leave them at `0.5` (neutral, correct). Find the final return:
```python
    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score), round(z, 3)
```
Replace with:
```python
    penalty = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return 1.0 - clamp01(penalty), round(z, 3)
```

- [ ] **Step 6: Rewrite `calculate_health_index`**

```python
def calculate_health_index(scores: dict[str, float]) -> float:
    """
    health_index = clip(weighted_average(health_scores) × 100, 0, 100)

    All scores at 1 (healthy on every metric) → index = 100
    All scores at 0 (critical on every metric) → index = 0
    """
    health = sum(HEALTH_INDEX_WEIGHTS.get(k, 0) * score for k, score in scores.items())
    return float(np.clip(health * 100.0, 0.0, 100.0))
```

- [ ] **Step 7: Flip `get_severity` thresholds**

```python
def get_severity(score: float, risk_type: str) -> str:
    """Map health score to severity level. High score = healthy = Normal."""
    if score <= 0.2:
        return "Critical"
    elif score <= 0.4:
        return "Attention Required"
    elif score <= 0.6:
        return "Monitor"
    else:
        return "Normal"
```

- [ ] **Step 8: Run tests — should now pass**

```bash
cd backend && python -m pytest tests/unit/test_fair_health_scoring.py -v
```

Expected: All tests `PASS`.

---

### Task 3: Mirror Inversions in `scripts/etl/run_health_etl.py`

**Files:**
- Modify: `scripts/etl/run_health_etl.py`

This file has its own scoring copies that write to production DuckDB. Same inversion changes, but these functions return 4- or 5-tuples: `(score, z, lv, tr)` or `(score, z, A, B, C)`. Only the first element (score) flips.

- [ ] **Step 1: Invert `score_energy_anomaly` in run_health_etl.py**

Find (around line 200):
```python
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)
```
Replace with:
```python
    penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return 1.0 - penalty, round(z, 3), round(lv, 4), round(tr, 4)
```

- [ ] **Step 2: Invert `score_power_factor` in run_health_etl.py**

Change early `return 0.0, np.nan, np.nan, np.nan` to `return 0.5, np.nan, np.nan, np.nan`. Find the final return (around line 230):
```python
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)
```
Replace with:
```python
    penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return 1.0 - penalty, round(z, 3), round(lv, 4), round(tr, 4)
```

- [ ] **Step 3: Invert `score_phase_imbalance` in run_health_etl.py**

Change early `return 0.0, np.nan, np.nan, np.nan` to `return 0.5, np.nan, np.nan, np.nan`. Find the final return (around line 259):
```python
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)
```
Replace with:
```python
    penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return 1.0 - penalty, round(z, 3), round(lv, 4), round(tr, 4)
```

- [ ] **Step 4: Invert `score_thd_drift` in run_health_etl.py**

Change early `return 0.0, np.nan, np.nan, np.nan` to `return 0.5, np.nan, np.nan, np.nan`. Find the final return (around line 288):
```python
    score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return score, round(z, 3), round(lv, 4), round(tr, 4)
```
Replace with:
```python
    penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
    return 1.0 - penalty, round(z, 3), round(lv, 4), round(tr, 4)
```

- [ ] **Step 5: Invert `score_overload` in run_health_etl.py**

Leave `return 0.5, np.nan, np.nan, np.nan, np.nan` fallbacks unchanged. Find the final return (around line 336):
```python
    score = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return clamp01(score), round(z, 3), round(score_A, 4), round(score_B, 4), round(score_C, 4)
```
Replace with:
```python
    penalty = 0.50 * score_A + 0.30 * score_B + 0.20 * score_C
    return 1.0 - clamp01(penalty), round(z, 3), round(score_A, 4), round(score_B, 4), round(score_C, 4)
```

- [ ] **Step 6: Rewrite `calculate_health_index` in run_health_etl.py**

Find (around line 339):
```python
def calculate_health_index(scores):
    """..."""
    penalty = sum(HEALTH_INDEX_WEIGHTS.get(k, 0) * score for k, score in scores.items())
    return float(np.clip(100.0 - penalty * 100.0, 0.0, 100.0))
```
Replace with:
```python
def calculate_health_index(scores):
    """
    health_index = clip(weighted_average(health_scores) × 100, 0, 100)

    All scores at 1 (healthy on every metric) → index = 100
    All scores at 0 (critical on every metric) → index = 0
    """
    health = sum(HEALTH_INDEX_WEIGHTS.get(k, 0) * score for k, score in scores.items())
    return float(np.clip(health * 100.0, 0.0, 100.0))
```

- [ ] **Step 7: Mirror inversions in `generate_fair_health_scores.py`**

This file writes CSVs (not DuckDB) but has its own scoring copies. Apply the same four changes to `score_energy_anomaly`, `score_pf_degradation`, `score_phase_imbalance`, `score_thd_drift`, `score_overload`, and `calculate_health_index` in `scripts/generate/generate_fair_health_scores.py`. The functions there return 2-tuples `(score, z)`. Pattern is identical:

For each `score_*`: rename final local `score` to `penalty`, return `1.0 - penalty, z`. Change `0.0` fallbacks to `0.5` for pf, phase_imbalance, thd_drift. Rewrite `calculate_health_index` same as above.

- [ ] **Step 8: Commit Phase 1**

```bash
git add backend/core/fair_health_scoring.py \
        backend/tests/unit/test_fair_health_scoring.py \
        scripts/etl/run_health_etl.py \
        scripts/generate/generate_fair_health_scores.py
git commit -m "feat: invert FAIR scoring to health-based model (0=critical, 100=healthy)"
```

---

## Phase 2 — State-Aware Filtering

### Task 4: Add `is_operational()` + Filter Baselines in `run_health_etl.py`

**Files:**
- Modify: `scripts/etl/run_health_etl.py`

The production ETL already fetches `current_l1`, `current_l2`, `current_l3` from InfluxDB and has them available in every row (variable `current_l1/l2/l3` at line 650). No new InfluxDB queries needed.

- [ ] **Step 1: Add `is_operational()` helper after the constant definitions (around line 110)**

```python
# Operational state threshold — all three phases below this = Off
OPERATIONAL_THRESHOLD_A = 2.0

def is_operational(l1, l2, l3) -> bool:
    """True if AHU draws power on at least one phase. Unknown values = assume On."""
    if any(v is None or (isinstance(v, float) and np.isnan(v)) for v in [l1, l2, l3]):
        return True
    return not (l1 < OPERATIONAL_THRESHOLD_A and l2 < OPERATIONAL_THRESHOLD_A and l3 < OPERATIONAL_THRESHOLD_A)
```

- [ ] **Step 2: Filter `build_baselines()` to On-rows only**

Inside `build_baselines()` at the top of the `for ahu_id, grp in df.groupby("device_id"):` loop, add the filter immediately after `grp = grp.sort_values("timestamp")`:

```python
        # Filter to operational periods only for baseline computation
        if all(c in grp.columns for c in ["current_l1", "current_l2", "current_l3"]):
            on_mask = grp.apply(
                lambda r: is_operational(r["current_l1"], r["current_l2"], r["current_l3"]),
                axis=1,
            )
            grp_on = grp[on_mask]
        else:
            grp_on = grp  # fallback: no phase data, use all rows

        # Use grp_on for all baseline stats (replace grp with grp_on below)
```

Then replace every reference to `grp[col]` in the standard-metrics loop with `grp_on[col]`, and same for the THD 24h rolling series and max-phase-current computation. (The full-history `grp` is unchanged — only baseline stats use `grp_on`.)

Concretely: after adding `grp_on`, change the for-loop header from:
```python
        for col, min_r in [...]:
            vals = grp[col].dropna().values if col in grp.columns else np.array([])
```
to:
```python
        for col, min_r in [...]:
            vals = grp_on[col].dropna().values if col in grp_on.columns else np.array([])
```

And the THD section from `grp["composite_thd"]` to `grp_on["composite_thd"]`.

- [ ] **Step 3: Verify the function didn't break (manual dry-run check)**

Open a Python REPL and verify `is_operational` behaves correctly:
```python
import sys; sys.path.insert(0, 'backend')
# Simulate importing from the script
from scripts.etl.run_health_etl import is_operational  # adjust path if needed
assert is_operational(0.0, 0.0, 0.0) == False   # all below 2A = Off
assert is_operational(5.0, 0.0, 0.0) == True    # one phase active = On
assert is_operational(None, 0.0, 0.0) == True   # unknown = assume On
assert is_operational(float('nan'), 0.0, 0.0) == True
print("OK")
```

---

### Task 5: Write `operational_state` + `last_on_timestamp` to ETL Results

**Files:**
- Modify: `scripts/etl/run_health_etl.py`

- [ ] **Step 1: Pre-compute `last_on_timestamp` per AHU before the row loop**

In `transform_health_scores()`, before the `for idx, row in df_sorted.iterrows():` loop, add:

```python
    # Pre-compute last On timestamp per AHU
    last_on_ts: dict[str, str | None] = {}
    for ahu_id_key in df_sorted["device_id"].unique():
        ahu_rows = df_sorted[df_sorted["device_id"] == ahu_id_key].copy()
        if all(c in ahu_rows.columns for c in ["current_l1", "current_l2", "current_l3"]):
            on_rows = ahu_rows[ahu_rows.apply(
                lambda r: is_operational(
                    float(r["current_l1"]) if pd.notna(r.get("current_l1")) else None,
                    float(r["current_l2"]) if pd.notna(r.get("current_l2")) else None,
                    float(r["current_l3"]) if pd.notna(r.get("current_l3")) else None,
                ),
                axis=1,
            )]
            last_on_ts[ahu_id_key] = on_rows["timestamp"].max() if not on_rows.empty else None
        else:
            last_on_ts[ahu_id_key] = None
```

- [ ] **Step 2: Compute `operational_state` per row and add both fields to results dict**

Inside the row loop, after extracting `current_l1`, `current_l2`, `current_l3` (they're already in variables at line 650), compute state:

```python
        # Operational state for this row
        op_state = "On" if is_operational(current_l1, current_l2, current_l3) else "Off"
        row_last_on = last_on_ts.get(ahu_id)
```

Then in the `results.append({...})` dict, add these two fields at the end (before closing brace):

```python
            # === Operational State ===
            "operational_state":   op_state,
            "last_on_timestamp":   row_last_on,
```

---

### Task 6: Add Schema Migration + Confidence Decay to `healthdb.py`

**Files:**
- Modify: `backend/core/healthdb.py`

- [ ] **Step 1: Add new columns to `_SCHEMA_SQL` CREATE TABLE**

Inside the `_SCHEMA_SQL` string, add before the `PRIMARY KEY` line:
```sql
    operational_state   VARCHAR,
    last_on_timestamp   TIMESTAMPTZ,
```

- [ ] **Step 2: Add migration statements to `_MIGRATE_SCHEMA_SQL`**

Append to the end of `_MIGRATE_SCHEMA_SQL`:
```python
_MIGRATE_SCHEMA_SQL = """
...existing statements...
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS operational_state  VARCHAR;
ALTER TABLE health_hourly ADD COLUMN IF NOT EXISTS last_on_timestamp  TIMESTAMPTZ;
"""
```

- [ ] **Step 3: Add confidence decay to `get_latest_snapshot()`**

After `return conn.execute(query, params).df()`, apply the decay in Python (post-query):

```python
    def get_latest_snapshot(
        self,
        ahu_ids: list | None = None,
        level: int | None = None,
    ) -> pd.DataFrame:
        # ... existing query code ...
        with self._conn() as conn:
            df = conn.execute(query, params).df()

        if df.empty or "operational_state" not in df.columns:
            return df

        return self._apply_confidence_decay(df)

    def _apply_confidence_decay(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies confidence decay to Off AHUs based on time since last On state.

        | Now - last_on_timestamp | state returned  | health_index |
        |------------------------|-----------------|--------------|
        | ≤ 48h                  | "Off"           | last known   |
        | 48h – 168h             | "Off_Stale"     | last known   |
        | > 168h or null         | "Inactive"      | null         |
        """
        now = datetime.now(timezone.utc)
        df = df.copy()

        for i, row in df.iterrows():
            if row.get("operational_state") != "Off":
                continue  # On rows are returned as-is

            last_on = row.get("last_on_timestamp")
            if last_on is None or pd.isna(last_on):
                df.at[i, "operational_state"] = "Inactive"
                df.at[i, "health_index"] = None
                continue

            # Ensure timezone-aware
            if hasattr(last_on, "tzinfo") and last_on.tzinfo is None:
                last_on = last_on.replace(tzinfo=timezone.utc)

            elapsed_h = (now - last_on).total_seconds() / 3600.0

            if elapsed_h <= 48:
                pass  # keep "Off", keep health_index
            elif elapsed_h <= 168:
                df.at[i, "operational_state"] = "Off_Stale"
                # health_index unchanged
            else:
                df.at[i, "operational_state"] = "Inactive"
                df.at[i, "health_index"] = None

        return df
```

Make sure `from datetime import datetime, timezone` is already imported at the top of `healthdb.py` (it is — check line 5).

- [ ] **Step 4: Commit Phase 2**

```bash
git add scripts/etl/run_health_etl.py backend/core/healthdb.py
git commit -m "feat: add operational state detection and confidence decay to FAIR ETL"
```

---

## Phase 3 — Frontend Reflection

### Task 7: Add Types + Create `StateBadge` Component

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/components/shared/StateBadge.tsx`

- [ ] **Step 1: Add `OperationalState` type to `frontend/src/types/index.ts`**

After the existing type definitions at the top, add:
```typescript
export type OperationalState = 'On' | 'Off' | 'Off_Stale' | 'Inactive';
```

- [ ] **Step 2: Extend `DeviceRank` interface**

```typescript
export interface DeviceRank {
  ahu_id: string;
  index: number;
  tier?: string;
  level?: string;
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}
```

- [ ] **Step 3: Extend `AlertAHU` interface**

Find `AlertAHU` and add:
```typescript
export interface AlertAHU {
  // ...existing fields...
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}
```

- [ ] **Step 4: Create `frontend/src/components/shared/StateBadge.tsx`**

```tsx
import React from 'react';
import type { OperationalState } from '../../types';

interface StateBadgeProps {
  state: OperationalState;
  lastMeasured?: string | null;
  className?: string;
}

const STATE_CONFIG: Record<OperationalState, { label: string; dot: string; color: string; bg: string }> = {
  On: {
    label: 'On',
    dot: '●',
    color: '#00E5A0',
    bg: 'rgba(0, 229, 160, 0.12)',
  },
  Off: {
    label: 'Off',
    dot: '○',
    color: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.12)',
  },
  Off_Stale: {
    label: 'Off · Stale',
    dot: '○',
    color: '#f97316',
    bg: 'rgba(249, 115, 22, 0.12)',
  },
  Inactive: {
    label: 'Inactive',
    dot: '—',
    color: '#556677',
    bg: 'rgba(85, 102, 119, 0.12)',
  },
};

function formatHoursAgo(isoTimestamp: string): string {
  const diff = Date.now() - new Date(isoTimestamp).getTime();
  const hours = Math.floor(diff / 3_600_000);
  return hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}

const StateBadge: React.FC<StateBadgeProps> = ({ state, lastMeasured, className }) => {
  const cfg = STATE_CONFIG[state];
  const tooltip =
    state === 'Off_Stale' && lastMeasured
      ? `Last measured ${formatHoursAgo(lastMeasured)}`
      : undefined;

  return (
    <span
      title={tooltip}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 9999,
        fontSize: 11,
        fontWeight: 500,
        color: cfg.color,
        background: cfg.bg,
        border: `1px solid ${cfg.color}44`,
        whiteSpace: 'nowrap',
        cursor: tooltip ? 'help' : 'default',
      }}
    >
      <span style={{ fontSize: 8 }}>{cfg.dot}</span>
      {cfg.label}
    </span>
  );
};

export default StateBadge;
```

- [ ] **Step 5: Write a Jest test for StateBadge**

Create `frontend/src/__tests__/StateBadge.test.tsx`:
```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import StateBadge from '../components/shared/StateBadge';

describe('StateBadge', () => {
  it('renders On state', () => {
    render(<StateBadge state="On" />);
    expect(screen.getByText(/On/)).toBeInTheDocument();
  });

  it('renders Inactive state', () => {
    render(<StateBadge state="Inactive" />);
    expect(screen.getByText(/Inactive/)).toBeInTheDocument();
  });

  it('adds tooltip for Off_Stale when lastMeasured provided', () => {
    const ts = new Date(Date.now() - 50 * 3_600_000).toISOString(); // 50h ago
    render(<StateBadge state="Off_Stale" lastMeasured={ts} />);
    const badge = screen.getByText(/Off · Stale/);
    expect(badge.closest('[title]')).toHaveAttribute('title', expect.stringContaining('ago'));
  });
});
```

- [ ] **Step 6: Run frontend tests**

```bash
cd frontend && npm test -- --testPathPattern=StateBadge --watchAll=false
```

Expected: all pass.

---

### Task 8: Wire `StateBadge` into Dashboard Components

**Files:**
- Modify: `frontend/src/components/dashboard/AHURankingsTable.tsx`
- Modify: `frontend/src/components/dashboard/DeviceDetailCard.tsx`
- Modify: `frontend/src/components/dashboard/LatestOverview.tsx`
- Modify: `frontend/src/components/dashboard/AlertsModal.tsx`

- [ ] **Step 1: Update `AHURankingsTable.tsx`**

Add `operational_state` to `AHURankRow` interface:
```typescript
import type { OperationalState } from '../../types';
import StateBadge from '../shared/StateBadge';

export interface AHURankRow {
  id: string;
  label: string;
  level: number;
  healthScore: number;
  trend: number;
  status: AHUStatus;
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}
```

In the table row JSX, add a `<StateBadge />` cell after the health score cell. Find the health score `<td>`:
```tsx
              <td ...>
                ...
                {Math.round(row.healthScore)}
              </td>
```
Add immediately after it:
```tsx
              <td style={{ padding: '10px 12px' }}>
                {row.operational_state && (
                  <StateBadge
                    state={row.operational_state}
                    lastMeasured={row.last_on_timestamp}
                  />
                )}
              </td>
```

Also add a `State` column header in the `<thead>` alongside the existing headers.

- [ ] **Step 2: Update `DeviceDetailCard.tsx`**

The props interface (line 4) is:
```typescript
interface DeviceDetailCardProps {
  healthScore: number;
  // ... other fields
}
```

Add to the interface and imports:
```tsx
import StateBadge from '../shared/StateBadge';
import type { OperationalState } from '../../types';

interface DeviceDetailCardProps {
  healthScore: number;
  // ... existing fields ...
  operational_state?: OperationalState;
  last_on_timestamp?: string | null;
}
```

In the JSX next to `{Math.round(healthScore)}` (line 88), add:
```tsx
{operational_state && (
  <StateBadge state={operational_state} lastMeasured={last_on_timestamp} />
)}
```

Also destructure the new props in the component signature:
```tsx
const DeviceDetailCard: React.FC<DeviceDetailCardProps> = ({
  healthScore,
  // ... existing destructured props ...
  operational_state,
  last_on_timestamp,
}) => {
```

- [ ] **Step 3: Update `LatestOverview.tsx`**

Add to imports:
```tsx
import StateBadge from '../shared/StateBadge';
import type { OperationalState } from '../../types';
```

Find where `criticalAHU.healthScore` and `starAHU.healthScore` are rendered (around lines 654, 670). The AHU objects come from `siteSummaryData` — extend whatever local type or interface is used for those items to add:
```typescript
operational_state?: OperationalState;
last_on_timestamp?: string | null;
```

Next to each `score={criticalAHU.healthScore}` / `score={starAHU.healthScore}` render:
```tsx
{criticalAHU.operational_state && (
  <StateBadge
    state={criticalAHU.operational_state}
    lastMeasured={criticalAHU.last_on_timestamp}
  />
)}
```

- [ ] **Step 4: Update `AlertsModal.tsx`**

`AlertsModal` accepts `ahus: AlertAHU[]` (already imported from `types/index.ts`). The `AlertAHU` type was extended in Task 7 Step 3 with `operational_state` and `last_on_timestamp`.

Add to imports:
```tsx
import StateBadge from '../shared/StateBadge';
```

In the `AHURow` component (starts around line 35), after the tier badge rendering (around line 138), add:
```tsx
{ahu.operational_state && (
  <StateBadge
    state={ahu.operational_state}
    lastMeasured={ahu.last_on_timestamp}
  />
)}
```

---

### Task 9: Wire `StateBadge` into Chat Card + Update LLM Prompt

**Files:**
- Modify: `frontend/src/components/chat/cards/WorkOrderCard.tsx`
- Modify: `backend/llm/prompts.py`

- [ ] **Step 1: Update `WorkOrderCard.tsx`**

Add to imports:
```tsx
import StateBadge from '../../shared/StateBadge';
import type { OperationalState } from '../../../types';
```

Add `operational_state?: OperationalState; last_on_timestamp?: string | null;` to the card's props/data interface.

In the card's health display section add:
```tsx
{props.operational_state && (
  <StateBadge
    state={props.operational_state}
    lastMeasured={props.last_on_timestamp}
  />
)}
```

- [ ] **Step 2: Update LLM prompt in `backend/llm/prompts.py`**

Find the system prompt or instruction block (look for where health_index is described to the LLM). Add the following instruction block:

```python
STATE_MENTION_INSTRUCTION = """
When reporting AHU health, always mention the operational state using these patterns:
- On: "e{id} is currently On. Health index: {n} ({tier})."
- Off (≤48h): "e{id} is currently Off (last operational {X}h ago). Operational health index: {n} ({tier})."
- Off_Stale (48-168h): "e{id} is currently Off — last measured {X} hours ago. Health data is stale; index was {n} ({tier}) when last operational."
- Inactive (>168h): "e{id} is Inactive — no operational data in over a week. Health index unavailable."
Never report a healthy index for an Inactive unit. If health_index is null, say 'unavailable'.
"""
```

Incorporate this into the existing system prompt string (append to the relevant section).

- [ ] **Step 3: Run all frontend tests**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: all existing tests pass plus the new StateBadge test.

- [ ] **Step 4: Commit Phase 3**

```bash
git add frontend/src/types/index.ts \
        frontend/src/components/shared/StateBadge.tsx \
        frontend/src/__tests__/StateBadge.test.tsx \
        frontend/src/components/dashboard/AHURankingsTable.tsx \
        frontend/src/components/dashboard/DeviceDetailCard.tsx \
        frontend/src/components/dashboard/LatestOverview.tsx \
        frontend/src/components/dashboard/AlertsModal.tsx \
        frontend/src/components/chat/cards/WorkOrderCard.tsx \
        backend/llm/prompts.py
git commit -m "feat: add StateBadge component and wire operational state into all health displays"
```

---

## Verification Checklist

After all phases are done, verify these success criteria from the spec:

- [ ] `python -m pytest backend/tests/unit/test_fair_health_scoring.py -v` — all pass
- [ ] `cd frontend && npm test -- --watchAll=false` — all pass
- [ ] Run ETL dry-run: `python scripts/etl/run_health_etl.py --dry-run --level 1` — confirm `operational_state` column appears in output
- [ ] Query DuckDB directly: `SELECT ahu_id, health_index, operational_state, last_on_timestamp FROM health_hourly WHERE operational_state = 'Off' LIMIT 5` — confirm Off AHUs have non-100 health_index
- [ ] Open frontend at `localhost:3000` — confirm `<StateBadge />` renders on Rankings table, Device Detail, Alerts modal
- [ ] Chat query: ask about a known Off AHU — confirm response mentions state and last operational time
