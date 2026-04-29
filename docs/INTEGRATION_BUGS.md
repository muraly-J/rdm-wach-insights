# WACH Insight — Integration Bugs & Known Gaps

Last audited: 2026-03-24
All issues resolved: 2026-03-24

---

## BUG-001 ✓ RESOLVED — removed misleading TODO; endpoint was already implemented

**File:** `frontend/src/api/client.ts:77`
**Symptom:** `fetchRawScoreRelationship(deviceId, range)` contained a misleading TODO comment
  despite the backend endpoint being fully implemented.
**Resolution:** Removed the `// TODO: Implement backend endpoint` comment and added explicit
  return type `Promise<Record<string, unknown>>` to `fetchRawScoreRelationship`.
**Commit:** `72d4cb3`

---

## GAP-001 ✓ RESOLVED — kVA demand charge implemented using raw_apparent_power_total

**File:** `backend/routes/financial_impact.py`
**Symptom:** `max_demand_rate` (RM/kVA/month) was stored in `financial_config.json` but not
  used in cost calculations.
**Resolution:** Implemented kVA demand charge as `peak_kva × max_demand_rate` using the
  `raw_apparent_power_total` column already present in `health_all_levels.csv`. Added
  `demand_charge_myr` field to per-AHU rows, summary totals, return dict, and `_empty_response`.
  Four TDD tests added in `backend/tests/test_financial_impact.py` — all pass.
**Commit:** `adf7e79`

---

## GAP-002 ✓ RESOLVED — Jest tests added: useAppStore, API client, CombinedScoresChart

**Symptom:** `frontend/src/` contained zero test files.
**Resolution:** Added three test files covering critical paths:
  - `frontend/src/__tests__/useAppStore.test.ts` — 11 state transition tests
  - `frontend/src/__tests__/api.test.ts` — 6 API client mock tests
  - `frontend/src/__tests__/CombinedScoresChart.test.tsx` — 4 data merge tests
  Fixed Jest TypeScript support (`@babel/preset-typescript`) and `import.meta.env` handling
  via inline babel visitor in `jest.config.cjs`. All 21 tests pass.
**Commit:** `b574ead`

---

## GAP-003 ✓ RESOLVED — ahu_id renamed to device_id in CSVs and all Python/TS code

**Symptom:** `data/predictions.csv` and `data/health_all_levels.csv` used `ahu_id` as the
  device identifier column; all API responses and Python code used `device_id`.
**Resolution:** Renamed `ahu_id → device_id` header in both CSV files (via `sed` on header line
  to avoid malformed-row pandas errors). Updated all `'ahu_id'` string literals in
  `backend/core/csv_reader.py`, `backend/routes/financial_impact.py`, and 27 other Python
  source files. No `ahu_id` column references remain in source code.
**Commit:** `6701219` (29 files changed)

---

## GAP-004 ✓ RESOLVED — .env.example updated to use correct LLM_BACKEND name

**Symptom:** The correct env var is `LLM_BACKEND`; the name `LLM_PROVIDER` appeared in verbal
  references and was absent from `.env.example`.
**Resolution:** Added explicit `LLM_BACKEND=qwen` entry to `.env.example`. LM Studio section
  added. Gemini has since been removed — Qwen is the only LLM provider.
  CONSTITUTION.md already documented the correct name.
**Commit:** `72d4cb3`
