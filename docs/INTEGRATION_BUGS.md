# WACH Insight — Integration Bugs & Known Gaps

Last audited: 2026-03-24

---

## BUG-001: fetchRawScoreRelationship not wired to backend

**File:** `frontend/src/api/client.ts:77`
**Symptom:** `fetchRawScoreRelationship(deviceId, range)` contains only a TODO comment and makes a
  bare `apiFetch` call with no error handling or fallback:
  ```ts
  // TODO: Implement backend endpoint
  return apiFetch(`/device/${deviceId}/raw-score-relationship?range=${range}`);
  ```
**Impact:** The `RawScoreRelationChart` inside `ScoreDerivationSection` (lazy-loaded) receives no
  data and renders blank. Users drilling into score derivation see an empty chart.
**Root cause:** The backend route `GET /api/device/{id}/raw-score-relationship` exists in the
  router declaration but the underlying InfluxDB pivot query in `influx_client.py` may not be
  fully implemented. Needs verification.
**Fix needed:**
  1. Confirm `backend/routes/health_scores.py → get_raw_score_relationship()` returns real pivot data.
  2. Remove the TODO comment from `frontend/src/api/client.ts`.
  3. Add a loading/error state to `RawScoreRelationChart`.
**Priority:** Medium — visible only when user drills into the score derivation panel.

---

## GAP-001: kVA-based demand charge not included in financial impact

**File:** `backend/routes/financial_impact.py:95`
**Symptom:** `max_demand_rate` (RM/kVA/month) is stored in `financial_config.json` and displayed
  in the UI but is not used in cost calculations:
  ```python
  # max_demand_rate is stored but not yet used in calculations
  # TODO: implement kVA-based demand charge when meter data is available
  ```
**Impact:** Reported monthly cost underestimates true TNB C1/C2 utility bill for facilities with
  peak kVA demand charges. The missing component can be 20–40% of total bill.
**Root cause:** kVA demand data is available in InfluxDB but not yet queried by `influx_client.py`.
**Fix needed:** Add a `demand_charge_myr` field to the financial impact response, computed as
  `max_demand_rate × peak_kva_this_month` when `kva_demand` measurements exist.
**Priority:** Low — placeholder in place, existing cost breakdown is still useful. Not blocking.

---

## GAP-002: No frontend unit or integration tests

**Symptom:** `frontend/src/` contains zero `.test.tsx`, `.spec.tsx`, or `.test.ts` files.
  (Confirmed: `glob frontend/src/**/*.test.*` returns empty.)
**Impact:** Component regressions go undetected until manual review. Past bugs that would have
  been caught by tests:
  - `CombinedScoresChart` data merge broken (fixed manually)
  - `ScoreCard` template literal `{color}` not interpolated (fixed manually)
  - `LevelSelectorBar` received props but store wasn't connected (fixed manually)
**Fix needed:** Add Vitest + React Testing Library. Minimum coverage:
  - `useAppStore` — state transitions (level selection, device selection, chat open/close)
  - `fetchHealthIndex` + `fetchScoreBreakdown` — mock with `msw`, assert shape
  - `CombinedScoresChart` — unit test the data merge function in isolation
**Priority:** Medium — required before onboarding external contributors (e.g., Bishal's PRs).

---

## GAP-003: predictions.csv uses ahu_id column, not device_id

**Symptom:** `data/predictions.csv` has columns `[timestamp, ahu_id, level, energy_current,
  hourly_delta, ...]` — the device identifier column is `ahu_id`, not `device_id`.
**Impact:** Any code or test that reads predictions.csv and looks for a `device_id` column will
  silently fail or return NaN. The scenario test must use `ahu_id`.
**Current state:** 121 rows, 121 unique `ahu_id` values — one per AHU, no duplicates.
**Fix needed:** Decide on a canonical column name (`device_id` preferred for consistency with
  all other data frames) and rename `ahu_id → device_id` in:
  - `data/predictions.csv`
  - `scripts/etl/run_prediction_etl.py` (writer)
  - `backend/core/csv_reader.py` (reader)
**Priority:** Low — current code works because it uses the correct column name internally.
  Becomes a bug if new code assumes `device_id` without checking.

---

## GAP-004: LLM_BACKEND env var misnamed in some contexts

**Symptom:** The correct env var is `LLM_BACKEND` (see `backend/llm/client_factory.py:18`).
  The name `LLM_PROVIDER` does not exist anywhere in source code but may appear in verbal
  references or external notes.
**Impact:** Contributor sets `LLM_PROVIDER=gemini` in `.env`, sees no effect, backend silently
  defaults to `qwen`.
**Fix needed:** CONSTITUTION.md already documents the correct name. Ensure `.env.example` uses
  `LLM_BACKEND` and no doc files introduce `LLM_PROVIDER`.
**Priority:** Low — clarified in CONSTITUTION.md.
