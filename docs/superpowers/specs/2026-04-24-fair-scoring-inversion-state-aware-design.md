# FAIR Scoring Inversion & State-Aware Filtering — Design Spec

**Date:** 2026-04-24
**Status:** Approved
**Scope:** Backend scoring engine + ETL pipeline + frontend visualization

---

## Overview

Two coordinated changes to make WACH Insight health reporting honest and intuitive:

1. **Score Inversion (Phase 1):** Convert the FAIR engine from penalty-based (0=healthy, 1=bad) to health-based (0=critical, 1=healthy) representation natively throughout the stack.
2. **State-Aware Filtering (Phase 2):** Detect On/Off operational state from raw phase currents; filter Off periods from baselines; apply confidence decay to health shown for Off units.
3. **Frontend Reflection (Phase 3):** Surface `operational_state` on every health display with a shared `<StateBadge />` component.

Approach: **Invert-first, then State** — math fix is self-contained and reviewable alone; state detection is the complex stream touching 5+ files.

---

## Phase 1: Score Inversion

### Files changed
- `backend/core/fair_health_scoring.py`
- `backend/tests/unit/test_fair_health_scoring.py`

### Logic change

Each `score_*` function currently returns a **penalty** ∈ [0,1] where 1=bad. After this change, each returns a **health score** ∈ [0,1] where 1=healthy.

Mechanical diff per scoring function:
```python
# Before (penalty):
score = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
return score, z

# After (health):
penalty = clamp01(LEVEL_WEIGHT * lv + TREND_WEIGHT * tr)
return 1.0 - penalty, z
```

Affected functions: `score_energy_anomaly`, `score_power_factor`, `score_phase_imbalance`, `score_thd_drift`, `score_overload`.

### `calculate_health_index` change

```python
# Before:
penalty = sum(HEALTH_INDEX_WEIGHTS.get(k, 0) * score for k, score in scores.items())
return float(np.clip(100.0 - penalty * 100.0, 0.0, 100.0))

# After:
health = sum(HEALTH_INDEX_WEIGHTS.get(k, 0) * score for k, score in scores.items())
return float(np.clip(health * 100.0, 0.0, 100.0))
```

### Invariants preserved

- Z-scores (`z_energy`, `z_pf`, etc.) are diagnostic only — unchanged.
- Neutral fallback `0.5` remains correct (midpoint of [0,1] under both semantics).
- Health tiers (Critical 0–39, Monitor 60–79, Healthy 80–100) map identically to output range.
- Safety flags are baseline-derived, not score-derived — unchanged.

### `get_severity()` — also needs inversion

`get_severity(score, risk_type)` currently interprets high score = bad. After inversion, high score = healthy. Thresholds flip:

```python
# Before (penalty semantics):
if score >= 0.8: return "Critical"
elif score >= 0.6: return "Attention Required"
elif score >= 0.4: return "Monitor"
else: return "Normal"

# After (health semantics):
if score <= 0.2: return "Critical"
elif score <= 0.4: return "Attention Required"
elif score <= 0.6: return "Monitor"
else: return "Normal"
```

### Test updates

All assertions in `test_fair_health_scoring.py` that test `score >= X` as an indication of badness flip direction. Health index assertions invert. The tier thresholds remain the same numbers.

---

## Phase 2: State-Aware Filtering

### Files changed
- `scripts/generate/generate_fair_health_scores.py`
- `backend/core/fair_health_scoring.py` (new helper + baseline filter)
- `backend/core/healthdb.py` (schema + decay query logic)
- `backend/tools/health_tools.py` (if it does raw DB reads bypassing healthdb)

### 2a. InfluxDB Fetch

Add `raw_current_l1`, `raw_current_l2`, `raw_current_l3` to the `fetch_raw_metrics()` call in `generate_fair_health_scores.py`. Same Flux query pattern as existing current metrics. These columns are already defined in `healthdb`'s `health_hourly` table schema.

### 2b. State Detection

New pure function in `fair_health_scoring.py`:
```python
OPERATIONAL_THRESHOLD_A = 2.0  # Amps — all three phases below this = Off

def is_operational(l1: float, l2: float, l3: float) -> bool:
    """Returns True if AHU is drawing power on at least one phase."""
    if any(v is None or np.isnan(v) for v in [l1, l2, l3]):
        return True  # unknown = assume On (conservative)
    return not (l1 < OPERATIONAL_THRESHOLD_A and l2 < OPERATIONAL_THRESHOLD_A and l3 < OPERATIONAL_THRESHOLD_A)
```

Unknown/NaN phase currents are treated as On (conservative — avoids falsely filtering real On-period data from baselines).

### 2c. Baseline Filtering

Inside `build_baselines()`, filter each AHU's history to On-only rows before computing robust stats:

```python
for ahu_id, grp in df.groupby("device_id"):
    grp = grp.sort_values("timestamp")
    # Filter to operational periods only
    if all(c in grp.columns for c in ["current_l1", "current_l2", "current_l3"]):
        on_mask = grp.apply(
            lambda r: is_operational(r["current_l1"], r["current_l2"], r["current_l3"]),
            axis=1
        )
        grp_on = grp[on_mask]
    else:
        grp_on = grp  # fallback: no phase data available, use all rows
    # ... compute baselines on grp_on
```

If filtered group has < 3 rows, baseline fields = NaN (insufficient On-history — neutral score returned).

### 2d. ETL Output — New Fields

Each assessment row written to DuckDB gains two new columns:

| Column | Type | Description |
|--------|------|-------------|
| `operational_state` | TEXT | `"On"` or `"Off"` at time of ETL run |
| `last_on_timestamp` | TIMESTAMP | Most recent timestamp where unit was operational |

The ETL computes `last_on_timestamp` by scanning the current window for the most recent row where `is_operational()` returns True.

### 2e. Confidence Decay — HealthDB Query Layer

Applied in `HealthDB.get_latest_snapshot()` (and any other read path returning health data) — **not** in ETL. ETL writes raw state; API interprets it.

| `Now - last_on_timestamp` | `state` returned | `health_index` |
|--------------------------|-----------------|----------------|
| ≤ 48h | `"Off"` | last known score as-is |
| 48h – 168h | `"Off_Stale"` | last known score as-is |
| > 168h | `"Inactive"` | `null` |

If `last_on_timestamp` is null (AHU never seen On in data window), treat as `"Inactive"`.

The `last_measured` field (timestamp of last On record) is passed alongside `health_index` so frontend and LLM can show "Last measured Xh ago."

---

## Phase 3: Frontend Reflection

### Files changed
- `frontend/src/components/shared/StateBadge.tsx` (new)
- `frontend/src/store/useAppStore.ts` (type extension)
- `frontend/src/components/dashboard/AHURankingsTable.tsx`
- `frontend/src/components/dashboard/DeviceDetailCard.tsx`
- `frontend/src/components/dashboard/LatestOverview.tsx`
- `frontend/src/components/dashboard/AlertsModal.tsx`
- `frontend/src/components/chat/cards/WorkOrderCard.tsx`
- `backend/llm/prompts.py`

### 3a. StateBadge Component

New shared component `frontend/src/components/shared/StateBadge.tsx`:

```tsx
type OperationalState = "On" | "Off" | "Off_Stale" | "Inactive";

interface StateBadgeProps {
  state: OperationalState;
  lastMeasured?: string | null; // ISO timestamp, shown in tooltip for Stale
}
```

| State | Badge text | Color |
|-------|-----------|-------|
| `On` | `● On` | `#00E5A0` (project teal accent) |
| `Off` | `○ Off` | amber |
| `Off_Stale` | `○ Off · Stale` | orange, tooltip: "Last measured Xh ago" |
| `Inactive` | `— Inactive` | muted gray |

### 3b. Color Scale

No change required. Existing components map low health_index → red, high → green. Phase 1 inversion makes health_index semantics match this existing direction. Verify no component applies an internal `100 - health_index` transformation.

### 3c. Component Updates

Each of the 5 components receives `operational_state` and `last_on_timestamp` from the API response (via Zustand store) and renders `<StateBadge />` adjacent to the health score display. No new API calls — data comes from the existing health snapshot endpoint.

### 3d. Zustand Store Type Extension

```typescript
// useAppStore.ts — extend AHUHealthData
interface AHUHealthData {
  // ... existing fields
  operational_state: "On" | "Off" | "Off_Stale" | "Inactive";
  last_on_timestamp: string | null;
}
```

### 3e. LLM Prompt Update

`backend/llm/prompts.py` — add instruction for the model to mention state and staleness:

- On: "e0101 is currently **On**. Its health index is 74 (Monitor)."
- Off (fresh): "e0101 is currently **Off** (last operational 6h ago). Its operational health index is 42 (Critical)."
- Off (stale): "e0101 is currently **Off** — last measured **52 hours ago**. Health data is stale; index was 61 (Monitor) when last operational."
- Inactive: "e0101 is **Inactive** — no operational data in over a week. Health index is unavailable."

---

## Data Flow Summary

```
InfluxDB (raw L1/L2/L3 + existing metrics)
    ↓  [generate_fair_health_scores.py]
State detection → is_operational()
Baseline build → On-only rows → robust_params()
Score inversion → health scores [0,1] where 1=healthy
    ↓  DuckDB (health_hourly + operational_state + last_on_timestamp)
    ↓  [HealthDB.get_latest_snapshot()]
Confidence decay applied → state / health_index / last_measured
    ↓  API response
    ↓  Zustand store → all dashboard + chat components
<StateBadge /> + color scale + LLM prompt
```

---

## Out of Scope

- Changing TREND_WINDOW_H, SENSITIVITY, or HEALTH_INDEX_WEIGHTS (separate tuning concern)
- New InfluxDB measurements beyond L1/L2/L3 current
- Historical backfill of `operational_state` for existing DuckDB records
- Work order integration with Off state

---

## Success Criteria

1. AHU scoring Off for > 1 week shows `health_index: null` and `state: "Inactive"` — never a false 100.
2. All `score_*` functions return ∈ [0,1] where 1=healthy; unit tests confirm.
3. Baselines computed exclusively from On-period rows (verified by checking a known-Off AHU's baseline row count).
4. All 5 frontend components render `<StateBadge />` for every health display.
5. Chat responses explicitly mention state and staleness per the prompt templates above.
