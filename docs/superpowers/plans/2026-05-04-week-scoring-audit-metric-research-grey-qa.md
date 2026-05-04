# RDM Insight — Week Plan (2026-05-04 Mon → 2026-05-08 Fri)

## Context

Focused 5-day push covering 4 goals. Order: scoring foundation first, then formula validation + metric expansion research, then UI grey-state propagation, then QA sweep. Foundation-first because metric research and UI both depend on a standardized score scale/direction.

Goals in scope:
- **#3** Standardize all scoring + health index to **0–100, high = good**.
- **#4** Validate the 4 FAIR formulas; inventory the 46 power-meter metrics; prototype an expanded multi-score health index (research only — ship next week).
- **#5** Propagate the grey-state effect to Deep Dive (single device), Compare mode, and Score Derivation plots. Skip Predicted Hourly Consumption.
- **#2** Friday quality sweep (lint/types/tests/deps/docs/dead-code), light pass, log + fix blockers only.

Out of scope this week: ticket generation/status (#1).

---

## Daily Plan

### Mon — Scoring Standardization Audit (#3)

Output: `docs/audits/2026-05-04-scoring-audit.md`

- Producers to map: `backend/core/fair_health_scoring.py`, `backend/core/healthdb.py`, `backend/core/risk_engine.py`, ETL under `scripts/etl/` and `scripts/generate/`.
- Consumers to map: `backend/routes/health_scores.py`, `backend/routes/dashboard.py`, frontend `HealthIndexChart`, `ScoreCard`, `CombinedScoresChart`, `components/dashboard/derivation/*`.
- Per site capture: scale (0–1 vs 0–100), direction (high=good vs high=bad), source field, display format.
- Define canonical convention: **0–100, high = good** at API boundary; conversion only at ETL ingest.
- Deliverable: matrix table + ranked fix list (consumed Tue).

### Tue — Std Fixes + 46-Metric Inventory (#3 close, #4 start)

AM — apply Mon fix list:
- Normalize all scores to 0–100, high=good at API boundary.
- Single converter utility in `backend/core/fair_health_scoring.py`; frontend stops doing scale/direction math.
- Update `backend/tests/` for new direction; align with prior FAIR inversion commits (`0dbb31c`, `4aa8c90`, `1f7d7db`).

PM — metric inventory:
- Query InfluxDB schema via `backend/core/influx_client.py` to enumerate the 46 power-meter fields.
- Output: `docs/audits/2026-05-04-metric-inventory.md`.
- Columns: name, unit, sample range, current usage (which FAIR score consumes it, or unused), technician-relevance rank 1–5, tag (keep / drop / promote-to-new-score).

### Wed — Formula Validation + Prototype New Scores (#4)

AM — validate the 4 FAIR formulas:
- Document each formula (F, A, I, R) from `backend/core/fair_health_scoring.py`.
- Pull a 1-week historical sample from InfluxDB for 3 AHUs (healthy, degraded, off).
- Recompute by hand and diff vs stored values. Flag edge cases: div-by-zero, missing metric, off-state, low-confidence.

PM — prototype expansion:
- From Tue inventory, pick 3–5 promote candidates (likely set: power-factor stability, current imbalance, harmonic distortion, runtime hours, cycling frequency — final picks driven by inventory).
- Draft formulas in `scripts/research/score_prototypes.py`. Run against historical sample, plot distributions, sanity check.
- Recommend new health-index composition (target 7–9 blended scores) with weights.
- Deliverable: validation report + prototype script + recommendation. **Not shipped this week.**

### Thu — Grey Effect Propagation (#5)

Trigger = (off) OR (stale data) OR (low confidence) — reuse existing operational-state logic from `StateBadge` (commit `ce22979`) and `DataFreshnessIndicator`.

- Extract grey logic from `HealthIndexChart`, `RawScoreRelationChart`, `DeviceDetailCard` into a shared hook `useGreyState(ahuId)` under `frontend/src/hooks/`.
- Apply hook across:
  - Deep Dive single-device view components.
  - Compare mode chart components.
  - All Score Derivation panel charts under `frontend/src/components/dashboard/derivation/`.
- Skip Predicted Hourly Consumption.
- Visual treatment: desaturate + opacity 0.4 + `StateBadge` overlay (match existing pattern).
- Verify each state via mock-data toggle or a manual test page.

### Fri — QA Sweep (#2)

Light pass, time-box ~2h per area. Output: `docs/audits/2026-05-04-qa-sweep.md`.

- Lint/format/types: `ruff check backend/`, `mypy backend/` (if configured), `npm run lint`, `tsc --noEmit`. Fix easy, log rest.
- Tests: `pytest backend/tests/ --cov`, `npm test -- --coverage`. Note coverage gaps on scoring, ticket router, RAG.
- Deps: `pip list --outdated`, `npm outdated`, `npm audit`. Log security-critical only.
- Docs drift: spot-check `CLAUDE.md`, `API.md`, `docs/CONSTITUTION.md` (endpoints, AHU counts, ports, score convention now 0–100).
- Dead code: grep unused exports, stale `scripts/debug/`, orphan routes.
- Output is a backlog for following Monday — fix only blockers in-week.

---

## Critical Files

Backend:
- `backend/core/fair_health_scoring.py` — score definitions + canonical converter (Tue).
- `backend/core/healthdb.py`, `backend/core/risk_engine.py` — score producers.
- `backend/core/influx_client.py` — metric enumeration source (Tue PM).
- `backend/routes/health_scores.py`, `backend/routes/dashboard.py` — API boundary normalization.
- `scripts/etl/`, `scripts/generate/` — ETL ingest conversions.
- `scripts/research/score_prototypes.py` — **new**, Wed prototype.
- `backend/tests/` — direction/scale assertions.

Frontend:
- `frontend/src/hooks/useGreyState.ts` — **new**, Thu shared hook.
- `frontend/src/components/dashboard/HealthIndexChart.tsx`, `derivation/RawScoreRelationChart.tsx`, `DeviceDetailCard.tsx` — source patterns to extract.
- `frontend/src/components/shared/StateBadge.tsx`, `DataFreshnessIndicator.tsx` — trigger inputs.
- Deep Dive, Compare mode, Score Derivation panels — apply hook.

Audits (new files):
- `docs/audits/2026-05-04-scoring-audit.md` (Mon)
- `docs/audits/2026-05-04-metric-inventory.md` (Tue)
- `docs/audits/2026-05-04-formula-validation.md` (Wed)
- `docs/audits/2026-05-04-qa-sweep.md` (Fri)

---

## Reuse (no new code where existing fits)

- Operational-state + confidence decay already in `HealthDB` (commit `7b444fd`) — feed `useGreyState`.
- `StateBadge` overlay component already wired across health displays — reuse, don't reinvent.
- Existing FAIR-inversion test patterns (commit `ed22de5`) — extend rather than rewrite.

---

## Verification

- **Mon**: audit doc lists ≥1 row per producer + consumer site; mismatches enumerated.
- **Tue**: `pytest backend/tests/` green after std fixes; manual API hit on `/api/health-scores` returns 0–100 with high=good; inventory doc has all 46 metrics rowed.
- **Wed**: prototype script runs end-to-end on 3 sample AHUs; recomputed FAIR values match stored within tolerance (or drift documented).
- **Thu**: visit Deep Dive / Compare / Derivation views with a forced off/stale/low-confidence AHU (e.g. via mock toggle) — grey applies on every chart in scope; healthy AHU renders normal.
- **Fri**: audit doc filed; CI green (`backend` and `frontend` workflows under `.github/workflows/`); blocker fixes committed; non-blockers logged as backlog.

---

## Risks

- Mon audit may surface more divergence than expected → Tue AM may overrun; Tue PM inventory could slip to Wed AM, compressing Wed prototype work.
- 46-metric InfluxDB enumeration may need a one-off Flux query — budget 30min before falling back to schema doc.
- Grey hook extraction may reveal divergent logic across the 3 source components — pick one as canonical (recommend `HealthIndexChart`) and align others.
