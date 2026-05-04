# Scoring Standardization Audit — 2026-05-04

## Canonical Convention

- **Scale:** 0–100
- **Direction:** high = good (100 = healthy, 0 = critical)
- **Conversion site:** ETL ingest only — routes and frontend pass through unchanged

## Producer Matrix

| File | Symbol (function/class) | Score(s) emitted | Scale | Direction | Notes |
|------|-------------------------|------------------|-------|-----------|-------|

## ETL Matrix

| File | Symbol | Reads from | Writes to | Scale at write | Direction at write | Notes |
|------|--------|------------|-----------|----------------|--------------------|-------|

## API Matrix

| Route | Handler | Field name(s) | Scale at response | Direction at response | Notes |
|-------|---------|---------------|-------------------|-----------------------|-------|

## Frontend Matrix

<!-- Files in scope: frontend/src/components/dashboard/HealthIndexChart.tsx, frontend/src/components/dashboard/ScoreCard.tsx, frontend/src/components/dashboard/CombinedScoresChart.tsx, frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx, frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx, frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx, frontend/src/components/dashboard/ScoreCardsGrid.tsx, frontend/src/components/dashboard/LatestOverview.tsx, frontend/src/components/dashboard/SafetyFlagCard.tsx, frontend/src/components/dashboard/AlertsModal.tsx, frontend/src/components/chat/cards/AHUSummaryCard.tsx, frontend/src/components/chat/ChatWindow.tsx, frontend/src/components/deepdive/SingleDeviceChart.tsx, frontend/src/components/deepdive/CompareMode.tsx, frontend/src/components/workorders/WorkOrderDetailModal.tsx -->

| File | Component | Field consumed | Expected scale | Expected direction | Math done in component? | Notes |
|------|-----------|----------------|----------------|--------------------|-------------------------|-------|

## Mismatches

(Filled during Task 6.)

## Ranked Fix List

(Filled during Task 7.)
