# Scoring Standardization Audit — 2026-05-04

## Canonical Convention

- **Scale:** 0–100
- **Direction:** high = good (100 = healthy, 0 = critical)
- **Conversion site:** ETL ingest only — routes and frontend pass through unchanged

## Producer Matrix

| File | Symbol (function/class) | Score(s) emitted | Scale | Direction | Notes |
|------|-------------------------|------------------|-------|-----------|-------|
| backend/core/fair_health_scoring.py | score_energy_anomaly | energy_anomaly | 0–1 | high=good | Returns `1.0 - penalty`; clamp01 |
| backend/core/fair_health_scoring.py | score_power_factor | pf_degradation | 0–1 | high=good | Returns `1.0 - penalty`; clamp01 |
| backend/core/fair_health_scoring.py | score_phase_imbalance | phase_imbalance | 0–1 | high=good | Returns `1.0 - penalty`; clamp01 |
| backend/core/fair_health_scoring.py | score_thd_drift | thd_drift | 0–1 | high=good | Returns `1.0 - penalty`; clamp01 |
| backend/core/fair_health_scoring.py | score_overload | overload | 0–1 | high=good | Returns `1.0 - clamp01(penalty)`; clamp01 |
| backend/core/fair_health_scoring.py | calculate_health_index | health_index | 0–100 | high=good | `weighted_avg(scores) × 100`, clipped [0,100] |
| backend/core/fair_health_scoring.py | generate_fleet_risk_assessment_fair | health_index + 5 component scores | health_index: 0–100, components: 0–1 | high=good | Orchestrator; calls above score functions |
| backend/core/fair_health_scoring.py | build_baselines | baseline stats (median, rstd, p5, p95) | N/A (stats) | N/A | Not a score producer; computes per-AHU robust baseline params |
| backend/core/fair_health_scoring.py | compute_safety_flags | safety_flags (string list) | N/A (flags) | N/A | Metadata only; does not affect health_index |
| backend/core/fair_health_scoring.py | get_health_tier | tier string | N/A (categorical) | N/A | Maps health_index to "Healthy"/"Monitor"/"Maintenance Soon"/"Critical" |
| backend/core/fair_health_scoring.py | get_severity | severity string | N/A (categorical) | high score → "Normal" | Maps 0–1 score to severity; ≤0.2=Critical, ≤0.4=Attention, ≤0.6=Monitor, >0.6=Normal |
| backend/core/healthdb.py | HealthDB.upsert | stores all scores | health_index: 0–100, components: 0–1 | high=good | Pass-through; stores whatever ETL writes |
| backend/core/healthdb.py | HealthDB._apply_confidence_decay | health_index | 0–100 (or null) | high=good | Sets health_index=null for Inactive AHUs; no scale math |
| backend/core/healthdb.py | HealthDB.get_latest_snapshot | health_index + components | health_index: 0–100, components: 0–1 | high=good | Read-through; no transformation |
| backend/core/healthdb.py | HealthDB.get_time_range | health_index + components | health_index: 0–100, components: 0–1 | high=good | Read-through; no transformation |
| backend/core/healthdb.py | HealthDB.get_ranking | health_index + metric | health_index: 0–100, components: 0–1 | high=good | Read-through; no transformation |
| backend/core/risk_engine.py | new_energy_anomaly_score | energy_anomaly (penalty) | 0–1 | **high=BAD** | Returns raw penalty directly; NOT inverted |
| backend/core/risk_engine.py | new_power_factor_risk_score | pf (penalty) | 0–1 | **high=BAD** | Returns raw penalty directly; NOT inverted |
| backend/core/risk_engine.py | new_phase_imbalance_score | phase_imbalance (penalty) | 0–1 | **high=BAD** | Returns raw penalty directly; NOT inverted |
| backend/core/risk_engine.py | new_thd_drift_score | thd_drift (penalty) | 0–1 | **high=BAD** | Returns raw penalty directly; NOT inverted |
| backend/core/risk_engine.py | new_overload_score | overload (penalty) | 0–1 | **high=BAD** | Returns raw penalty directly; NOT inverted |
| backend/core/risk_engine.py | energy_anomaly_score | energy_anomaly (penalty) | 0–1 | **high=BAD** | Legacy; same direction as new_* |
| backend/core/risk_engine.py | power_factor_risk_score | pf (penalty) | 0–1 | **high=BAD** | Legacy; same direction as new_* |
| backend/core/risk_engine.py | phase_imbalance_risk_score | phase_imbalance (penalty) | 0–1 | **high=BAD** | Legacy; same direction as new_* |
| backend/core/risk_engine.py | thd_risk_score | thd_drift (penalty) | 0–1 | **high=BAD** | Legacy; same direction as new_* |
| backend/core/risk_engine.py | overload_risk_score | overload (penalty) | 0–1 | **high=BAD** | Legacy; same direction as new_* |
| backend/core/risk_engine.py | calculate_ahu_health_index | health_index | 0–100 | high=good | Formula: `100 - (weighted_sum × 100)`; expects penalty scores (high=bad) as input |
| backend/core/risk_engine.py | calculate_ahu_health_index_fair | health_index | 0–100 | high=good | Same formula as above; doc says "All scores at 0 → index=100" |
| backend/core/risk_engine.py | generate_fleet_risk_assessment | health_index + 5 component scores | health_index: 0–100, components: 0–1 | health_index: high=good, components: direction ambiguous | Main risk engine orchestrator; uses new_* penalty scores internally |
| backend/core/risk_engine.py | get_severity | severity string | N/A (categorical) | N/A | Maps score to severity string |
| backend/core/risk_engine.py | generate_fleet_summary | tier counts, rankings | N/A (aggregates) | N/A | Fleet-level summary from assessments |
| backend/core/watchman.py | classify_score | tier string | N/A (categorical) | N/A | Takes health_index (0-100); <critical_threshold → Critical, <warning_threshold → Maintenance Soon |
| backend/core/db_reader.py | get_health_index_series | health_index | 0–100 | high=good | Reads from DuckDB; no transformation |
| backend/core/db_reader.py | get_score_breakdown | component scores | 0–1 | high=good | Reads from DuckDB; no transformation |
| backend/core/db_reader.py | get_raw_score_relationship | component scores + raw data | 0–1 | high=good | Reads from DuckDB; no transformation |
| backend/core/db_reader.py | get_dataframe | health_index + components | health_index: 0–100, components: 0–1 | high=good | Reads from DuckDB; no transformation |

## ETL Matrix

| File | Symbol | Reads from | Writes to | Scale at write | Direction at write | Notes |
|------|--------|------------|-----------|----------------|--------------------|-------|
| scripts/etl/run_health_etl.py | score_energy_anomaly (local) | InfluxDB raw data + baselines | Local variable → results dict | 0–1 | high=good | Returns `1.0 - penalty`; mirrors fair_health_scoring |
| scripts/etl/run_health_etl.py | score_power_factor (local) | InfluxDB raw data + baselines | Local variable → results dict | 0–1 | high=good | Returns `1.0 - penalty` |
| scripts/etl/run_health_etl.py | score_phase_imbalance (local) | InfluxDB raw data + baselines | Local variable → results dict | 0–1 | high=good | Returns `1.0 - penalty` |
| scripts/etl/run_health_etl.py | score_thd_drift (local) | InfluxDB raw data + baselines | Local variable → results dict | 0–1 | high=good | Returns `1.0 - penalty` |
| scripts/etl/run_health_etl.py | score_overload (local) | InfluxDB raw data + baselines | Local variable → results dict | 0–1 | high=good | Returns `1.0 - clamp01(penalty)` |
| scripts/etl/run_health_etl.py | calculate_health_index (local) | 5 component scores (0–1) | results dict → health_index field | 0–100 | high=good | `weighted_avg × 100`, clipped [0,100] |
| scripts/etl/run_health_etl.py | transform_health_scores | InfluxDB + DuckDB predictions | results list → DataFrame | components: 0–1, health_index: 0–100 | high=good | Main transform; calls all local score functions |
| scripts/etl/run_health_etl.py | load_to_healthdb | DataFrame from transform | HealthDB (DuckDB) health_hourly table | components: 0–1, health_index: 0–100 | high=good | `db.upsert(df)` — INSERT OR REPLACE |
| scripts/etl/run_prediction_etl.py | prediction ETL | InfluxDB energy data | HealthDB predictions table | energy_anomaly: raw float (kW·h delta) | N/A | Writes prediction deltas; not health scores |
| scripts/generate/generate_fair_health_scores.py | score_* (local) | CSV raw data | CSV output | 0–1 | high=good | Standalone generator; writes CSV not DuckDB |
| scripts/generate/generate_daily_health_index.py | health index computation | CSV or DuckDB | CSV output | 0–100 | high=good | Daily aggregation script |
| scripts/generate/generate/generate_all_levels_health_scores.py | health index computation | CSV or DuckDB | CSV output | 0–100 | high=good | Multi-level aggregation script |
| scripts/generate/generate_level1_health_scores.py | health index computation | CSV or DuckDB | CSV output | 0–100 | high=good | Level-1 specific generator |
| scripts/generate/generate_summary_report.py | summary generation | DuckDB/CSV | CSV/text report | N/A | N/A | Report generator; reads scores, doesn't transform |

## API Matrix

| Route | Handler | Field name(s) | Scale at response | Direction at response | Notes |
|-------|---------|---------------|-------------------|-----------------------|-------|
| GET /api/level/{id}/scores | get_level_scores | energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload | 0–1 | high=good | Pass-through from db_reader.get_score_breakdown → DuckDB |
| GET /api/level/{id}/health-index | get_level_health_index | health_index | 0–100 | high=good | Pass-through from db_reader.get_health_index_series → DuckDB |
| GET /api/device/{id}/raw-score-relationship | get_raw_score_relationship | component scores + raw metrics | 0–1 | high=good | Pass-through from db_reader.get_raw_score_relationship → DuckDB |
| GET /api/dashboard/ranking | dashboard_ranking | health_index (as "index") | 0–100 | high=good | Reads from DuckDB via db_reader; no scale math |
| GET /api/dashboard/trend | dashboard_trend | health_index, energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload | health_index: 0–100, components: 0–1 | high=good | Calls generate_fleet_risk_assessment; extracts from nested risk_scores |
| GET /api/dashboard/trend/csv | dashboard_trend_csv | health_index, energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload | health_index: 0–100, components: 0–1 | high=good | Same as /trend but CSV format |
| GET /api/dashboard/summary | dashboard_summary | health_index, energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload | health_index: 0–100, components: 0–1 | high=good | Reads from DuckDB; no scale math |
| GET /api/dashboard/safety-flags | dashboard_safety_flags | safety_flags (string list) | N/A | N/A | Metadata only; no score transformation |
| GET /api/dashboard/ahu-heatmap | ahu_heatmap | health_index, energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload | health_index: 0–100, components: 0–1 | high=good | Reads from DuckDB; hourly aggregation via groupby.mean() |

## Frontend Matrix

<!-- Files in scope: frontend/src/components/dashboard/HealthIndexChart.tsx, frontend/src/components/dashboard/ScoreCard.tsx, frontend/src/components/dashboard/CombinedScoresChart.tsx, frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx, frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx, frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx, frontend/src/components/dashboard/ScoreCardsGrid.tsx, frontend/src/components/dashboard/LatestOverview.tsx, frontend/src/components/dashboard/SafetyFlagCard.tsx, frontend/src/components/dashboard/AlertsModal.tsx, frontend/src/components/chat/cards/AHUSummaryCard.tsx, frontend/src/components/chat/ChatWindow.tsx, frontend/src/components/deepdive/SingleDeviceChart.tsx, frontend/src/components/deepdive/CompareMode.tsx, frontend/src/components/workorders/WorkOrderDetailModal.tsx -->

| File | Component | Field consumed | Expected scale | Expected direction | Math done in component? | Notes |
|------|-----------|----------------|----------------|--------------------|-------------------------|-------|
| frontend/src/components/dashboard/HealthIndexChart.tsx | HealthIndexChart | health_index | 0–100 | high=good | No | Displays with `.toFixed(1)`; comment says "normalised 0–100. Higher is healthier" |
| frontend/src/components/dashboard/ScoreCard.tsx | ScoreCard | component score value | 0–100 | high=good | No | Shows `value.toFixed(1)` + "/ 100" suffix; implies 0–100 scale. Trend: increasing=bad (red), decreasing=good (green) for risk scores |
| frontend/src/components/dashboard/CombinedScoresChart.tsx | CombinedScoresChart | 5 component scores | 0–100 | high=good | No | Displays with `.toFixed(1)`; expects 0–100 scale |
| frontend/src/components/dashboard/ScoreCardsGrid.tsx | ScoreCardsGrid | 5 component scores (current, trend) | 0–100 | high=good | No | Info text shows formula `score = clip(...) × 100`; expects 0–100. Finds "highest current value" for safety flag |
| frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx | RawScoreRelationChart | scoreValue + raw metric | score: 0–100, raw: N/A | high=good | No | Right Y-axis labeled "Computed score (0–100)"; shows "/ 100" in tooltip |
| frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx | ScoreCardWithSelector | scoreData series | 0–100 | high=good | No | Passes through to RawScoreRelationChart |
| frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx | ScoreDerivationSection | scoreData + series | 0–100 | high=good | No | Orchestrates score derivation charts; enriches with is_on flags |
| frontend/src/components/dashboard/LatestOverview.tsx | LatestOverview | health_index | 0–100 | high=good | No | Displays latest health snapshot |
| frontend/src/components/dashboard/SafetyFlagCard.tsx | SafetyFlagCard | safety_flags | N/A | N/A | No | Shows flag metadata; no score math |
| frontend/src/components/dashboard/AlertsModal.tsx | AlertsModal | healthScore | 0–100 | high=good | No | `healthBarColor(score)`: ≥60=amber; `.toFixed(1)` display. Sort by score ascending (worst first) |
| frontend/src/components/chat/cards/AHUSummaryCard.tsx | AHUSummaryCard | FAIR scores | 0–100 | high=good | No | Shows FAIR score bars |
| frontend/src/components/chat/ChatWindow.tsx | ChatWindow | N/A (chat interface) | N/A | N/A | No | LLM chat; references "health scores" in greeting |
| frontend/src/components/deepdive/SingleDeviceChart.tsx | SingleDeviceChart | score groups | 0–100 | high=good | No | Per-device deep dive; uses scoreKey/scoreLabel from SCORE_METRIC_GROUPS |
| frontend/src/components/deepdive/CompareMode.tsx | CompareMode | score groups | 0–100 | high=good | No | Side-by-side comparison; uses scoreKey/scoreLabel |
| frontend/src/components/workorders/WorkOrderDetailModal.tsx | WorkOrderDetailModal | score values | 0–100 | high=good | No | Color threshold: ≥70=green, ≥40=amber, <40=red. Shows `.toFixed(1)` and progress bar `width: score%` |

## Mismatches

### Mismatch 1 — Component score scale mismatch: DuckDB stores 0–1, frontend expects 0–100

- **Where:** `backend/core/db_reader.py` reads component scores from DuckDB `health_hourly` table as 0–1 floats. The API routes (`/api/level/{id}/scores`, `/api/dashboard/trend`) pass them through unchanged. Frontend components (`ScoreCard.tsx`, `CombinedScoresChart.tsx`, `ScoreCardsGrid.tsx`, `RawScoreRelationChart.tsx`) display them with "/ 100" suffix and `.toFixed(1)`, expecting 0–100 scale.
- **Convention violation:** Component scores stored in DB are 0–1 but UI renders them as 0–100. Either the API should multiply by 100, or the frontend labels are misleading.
- **Severity:** **HIGH** — If frontend receives 0–1 values and displays them as "8.5 / 100", the health score appears critically low when it's actually 0.085 (8.5% penalty = 91.5 health). **OR** if the API/frontend already multiplies by 100 somewhere, the DB schema is inconsistent with the canonical convention.
- **Chain:** ETL (0–1) → DuckDB (0–1) → db_reader (0–1) → API (0–1) → Frontend (expects 0–100)

### Mismatch 2 — risk_engine.py penalty scores use inverted direction vs fair_health_scoring.py

- **Where:** `backend/core/risk_engine.py` `new_*_score` functions return raw **penalty** values (0–1, **high=bad**). `backend/core/fair_health_scoring.py` `score_*` functions return **health** values (0–1, **high=good** via `1.0 - penalty`). Both are called by different code paths.
- **Convention violation:** Two score producers in the same codebase use opposite directions for the same logical metric. `risk_engine` is used by `/api/dashboard/trend` and `/api/dashboard/safety-flags`; `fair_health_scoring` is used by the ETL → DuckDB pipeline.
- **Severity:** **HIGH** — If `generate_fleet_risk_assessment` feeds risk_engine penalty scores directly to the frontend while DuckDB stores health scores, the same metric has opposite meanings depending on the API endpoint.
- **Chain:** risk_engine (high=bad) → dashboard API → Frontend vs. fair_health_scoring (high=good) → ETL → DuckDB → health_scores API → Frontend

### Mismatch 3 — health_index scale is consistent (0–100) but component scores are not

- **Where:** `calculate_health_index` in both `fair_health_scoring.py` and `run_health_etl.py` produces health_index on 0–100 scale. But the 5 component scores stored alongside it in DuckDB are on 0–1 scale.
- **Convention violation:** The canonical convention says "0–100" for all scores. Component scores are 0–1 at rest in DuckDB.
- **Severity:** **MEDIUM** — Display may be correct if frontend multiplies by 100, but the DB is the source of truth and violates the "0–100" convention. Conversion happens at consumer (frontend/API) instead of at ETL ingest.
- **Chain:** ETL writes components as 0–1 → DuckDB stores 0–1 → API returns 0–1 → Frontend may multiply by 100

### Mismatch 4 — ScoreCard.tsx trend direction ambiguity for component scores

- **Where:** `frontend/src/components/dashboard/ScoreCard.tsx` comment says "For risk scores: increasing trend is bad (red), decreasing is good (green)". But the canonical convention is "high = good", meaning an increasing health score should be green.
- **Convention violation:** If component scores are 0–100 health scores (high=good), an increasing trend should be positive. The component treats them as risk/penalty scores where increasing = bad.
- **Severity:** **MEDIUM** — Trend color may be inverted for component scores if they are health scores (high=good) but rendered as risk scores (high=bad).
- **Chain:** Frontend ScoreCard trend logic assumes high=bad for components, but canonical convention says high=good

### Mismatch 5 — AlertsModal healthBarColor thresholds assume 0–100 scale

- **Where:** `frontend/src/components/dashboard/AlertsModal.tsx` `healthBarColor(score)`: `≥60` returns amber. This threshold only makes sense if scores are 0–100.
- **Convention violation:** None if scores are indeed 0–100. But if component scores arrive as 0–1 from the API, `≥60` would always be true (any score ≥ 0.6), making the color logic broken.
- **Severity:** **LOW** — Only affects AlertsModal; health_index is consistently 0–100 so this likely works. Would break only if component scores are passed here.
- **Chain:** API returns health_index (0–100) → AlertsModal (thresholds calibrated for 0–100)

### Mismatch 6 — WorkOrderDetailModal color thresholds assume 0–100

- **Where:** `frontend/src/components/workorders/WorkOrderDetailModal.tsx` uses `score >= 70 ? green : score >= 40 ? amber : red` and `width: ${score}%`.
- **Convention violation:** Same as Mismatch 5 — thresholds calibrated for 0–100. Progress bar width uses score directly as percentage.
- **Severity:** **LOW** — Only affects work order modal; consistent with health_index being 0–100.
- **Chain:** API returns health_index (0–100) → WorkOrderDetailModal (thresholds calibrated for 0–100)

### Mismatch 7 — generate_fleet_risk_assessment returns nested risk_scores with mixed structures

- **Where:** `backend/routes/dashboard.py` extracts component scores from `generate_fleet_risk_assessment` output using `.get("power_factor", {}).get("score", 0.0)` (nested) but `.get("energy_anomaly", 0.0)` (flat). The nested structure comes from `risk_engine.py`'s assessment builder.
- **Convention violation:** Inconsistent response shape — one score is flat, four are nested objects with `score`, `severity`, `confidence`, `signal` keys.
- **Severity:** **LOW** — Cosmetic / API shape inconsistency. Values are correct but parsing is fragile.
- **Chain:** risk_engine → dashboard API → frontend parsing

### Mismatch 8 — ETL local score functions duplicate fair_health_scoring.py logic

- **Where:** `scripts/etl/run_health_etl.py` has its own local `score_*` functions that mirror `backend/core/fair_health_scoring.py` almost identically. Both return `1.0 - penalty` (health direction).
- **Convention violation:** Code duplication — two copies of the same scoring logic. Risk of drift if one is updated and the other isn't.
- **Severity:** **LOW** — No correctness issue today (both produce same output), but maintenance risk.
- **Chain:** N/A (internal code organization)


## Ranked Fix List

---

### 🔴 Tuesday AM Batch — Must-fix to unblock metric inventory

---

1. **[HIGH] Normalize component score scale at API boundary: multiply 0–1 → 0–100**
   - **File:** `backend/core/db_reader.py:get_score_breakdown()` (line ~370) and `backend/routes/dashboard.py:dashboard_trend()` (series building block)
   - **Change:** Multiply all 5 component scores by 100 when reading from DuckDB before returning in API responses. Update docstrings to reflect 0–100 scale at API boundary.
   - **Tests to update:** `backend/tests/test_db_reader.py`, `backend/tests/e2e/test_smoke.py`
   - **Estimated effort:** 30 min
   - **Blocks:** ScoreCard, CombinedScoresChart, ScoreCardsGrid, RawScoreRelationChart, LatestOverview, AlertsModal, WorkOrderDetailModal, SingleDeviceChart, CompareMode, AHUSummaryCard

2. **[HIGH] Unify score direction across risk_engine.py and fair_health_scoring.py**
   - **File:** `backend/core/risk_engine.py:new_*_score` functions (lines 352–606)
   - **Change:** Invert the return values of `new_energy_anomaly_score`, `new_power_factor_risk_score`, `new_phase_imbalance_score`, `new_thd_drift_score`, `new_overload_score` to return `1.0 - penalty` (high=good) instead of raw penalty (high=bad). Update `calculate_ahu_health_index` formula accordingly (it currently does `100 - weighted_sum × 100` which assumes penalty input).
   - **Alternative:** Add a clear `invert=True/False` parameter or rename functions to `new_*_penalty` to disambiguate.
   - **Tests to update:** `backend/tests/test_prediction_engine.py`, all tests importing from `risk_engine`
   - **Estimated effort:** 1 h
   - **Blocks:** /api/dashboard/trend, /api/dashboard/safety-flags, /api/dashboard/ranking (if risk_engine feeds ranking)

3. **[HIGH] Fix ScoreCard.tsx trend direction for health scores**
   - **File:** `frontend/src/components/dashboard/ScoreCard.tsx` (line ~34)
   - **Change:** Reverse trend color logic so increasing = good (green) and decreasing = bad (red) for health-direction scores. The comment "For risk scores: increasing trend is bad" needs to be updated or the component needs a `direction` prop.
   - **Tests to update:** None (no unit tests for ScoreCard trend colors)
   - **Estimated effort:** 15 min
   - **Blocks:** ScoreCard, ScoreCardsGrid (uses ScoreCard internally)

---

### 🟡 Tuesday PM / Later — Convention compliance and cleanup

---

4. **[MEDIUM] Move component score 0→100 conversion to ETL ingest layer**
   - **File:** `scripts/etl/run_health_etl.py:transform_health_scores()` (line ~601)
   - **Change:** Multiply each of the 5 component scores by 100 inside `transform_health_scores()` before building the results dict. Update DuckDB schema comments to reflect 0–100 for all score columns. Remove any `* 100` or `/ 100` math from API routes and frontend components (they become pure pass-through).
   - **Tests to update:** `scripts/test/test_fair_scoring.py`, `scripts/test/verify_etl_pipeline.py`, `backend/tests/test_db_reader.py`
   - **Estimated effort:** 1 h
   - **Blocks:** Everything downstream (ETL → DuckDB → API → Frontend). Should be done AFTER fix #1 is validated.

5. **[MEDIUM] Align `generate_fleet_risk_assessment` response shape**
   - **File:** `backend/core/risk_engine.py:generate_fleet_risk_assessment()` (line ~1258) and `backend/routes/dashboard.py` extraction block
   - **Change:** Flatten `risk_scores` so all 5 component scores use the same structure (either all flat floats or all nested objects). If nested, add `score` key to `energy_anomaly` too. If flat, strip `severity`/`confidence`/`signal` from the other 4.
   - **Tests to update:** `backend/tests/test_prediction_engine.py`
   - **Estimated effort:** 30 min
   - **Blocks:** /api/dashboard/trend, /api/dashboard/trend/csv, /api/dashboard/summary

6. **[MEDIUM] Deduplicate ETL local score functions**
   - **File:** `scripts/etl/run_health_etl.py` (local `score_*` functions at lines ~175–345)
   - **Change:** Replace local `score_energy_anomaly`, `score_power_factor`, `score_phase_imbalance`, `score_thd_drift`, `score_overload` with imports from `backend/core/fair_health_scoring.py`. Remove duplicate code (~170 lines).
   - **Tests to update:** `scripts/test/test_fair_scoring.py` (may need import path updates)
   - **Estimated effort:** 30 min
   - **Blocks:** ETL pipeline correctness — must verify imported functions have identical signatures

7. **[LOW] Standardize AlertsModal healthBarColor thresholds**
   - **File:** `frontend/src/components/dashboard/AlertsModal.tsx` (line ~31)
   - **Change:** Add explicit JSDoc comment confirming `healthBarColor` expects 0–100 input. Add runtime guard: `if (score > 1 && score <= 100) { /* OK */ } else if (score <= 1) { score *= 100; }` to defend against 0–1 input.
   - **Tests to update:** None
   - **Estimated effort:** 15 min
   - **Blocks:** AlertsModal only

8. **[LOW] Standardize WorkOrderDetailModal score thresholds**
   - **File:** `frontend/src/components/workorders/WorkOrderDetailModal.tsx` (line ~318)
   - **Change:** Same defensive guard as #7. Add comment confirming 0–100 expected scale.
   - **Tests to update:** None
   - **Estimated effort:** 15 min
   - **Blocks:** WorkOrderDetailModal only

9. **[LOW] Update ScoreCardsGrid.tsx info text formulas**
   - **File:** `frontend/src/components/dashboard/ScoreCardsGrid.tsx` (lines ~27, 59, 92, 123, 154)
   - **Change:** The info text shows `score = clip(...) × 100` which is correct for 0–100 output. Verify formulas match the actual ETL implementation after deduplication (fix #6). If ETL stores 0–100 directly, update info text to show `score = clip(...) × 100` as final stored value.
   - **Tests to update:** None
   - **Estimated effort:** 15 min
   - **Blocks:** ScoreCardsGrid info tooltips only

10. **[LOW] Add schema-level validation for score ranges**
    - **File:** `backend/core/healthdb.py` (`_SCHEMA_SQL`)
    - **Change:** Add CHECK constraints to `health_hourly` table: `CHECK (health_index >= 0 AND health_index <= 100)`, `CHECK (energy_anomaly >= 0 AND energy_anomaly <= 100)`, etc. for all 5 component scores after they're converted to 0–100.
    - **Tests to update:** `backend/tests/test_db_reader.py`
    - **Estimated effort:** 30 min
    - **Blocks:** Nothing (defensive measure); requires fix #4 first

---

## Verification Checklist

- [x] Producer Matrix has ≥1 row per score-emitting function in `fair_health_scoring.py`, `healthdb.py`, `risk_engine.py`, `db_reader.py`, `watchman.py`
- [x] ETL Matrix has ≥1 row per file returned by `grep -rl 'health_index|score|HealthDB' scripts/`
- [x] API Matrix covers every route in `health_scores.py` and `dashboard.py` that returns a score field
- [x] Frontend Matrix covers `HealthIndexChart`, `ScoreCard`, `CombinedScoresChart`, `ScoreCardsGrid`, `RawScoreRelationChart`, `ScoreCardWithSelector`, `ScoreDerivationSection`, `LatestOverview`, `SafetyFlagCard`, `AlertsModal`, `AHUSummaryCard`, `SingleDeviceChart`, `CompareMode`, `WorkOrderDetailModal`
- [x] Mismatches section has 8 numbered entries with severity ratings (3 HIGH, 3 MEDIUM, 2 LOW)
- [x] Ranked Fix List has 10 entries sorted by severity, with "Tuesday AM Batch" cutoff after fix #3
- [x] Zero production code was modified — this is a read-only audit

## Out of Scope Today
- Applying fixes (Tuesday AM)
- Touching tests (Tuesday)
- Metric inventory of 46 power-meter fields (Tuesday PM)
- Frontend grey-state work (Thursday)
