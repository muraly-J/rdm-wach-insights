# AHU On/Off Period Shading — Design Spec

**Date:** 2026-04-10  
**Status:** Approved

---

## Problem

When viewing a single AHU's charts, there is no visual indication of when the unit was powered off. Off-period data is either missing, misleading, or silently blended with active readings. The existing two-line colored-segment approach in `HealthIndexChart` is inconsistent with all other charts and will be replaced.

---

## Scope

### Included charts (single-device views only)
| Component | File |
|---|---|
| `HealthIndexChart` | `frontend/src/components/dashboard/HealthIndexChart.tsx` |
| `CombinedScoresChart` | `frontend/src/components/dashboard/CombinedScoresChart.tsx` |
| `RawScoreRelationChart` | `frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx` |
| `SingleDeviceChart` | `frontend/src/components/deepdive/SingleDeviceChart.tsx` |
| `MeasurementHistoryChart` | `frontend/src/components/prediction/MeasurementHistoryChart.tsx` |
| `MetricMiniChart` | `frontend/src/components/shared/MetricMiniChart.tsx` |

### Excluded charts
- `HealthIndexChart` in multi-device mode (more than 1 AHU on same plot)
- `DeltaForecastChart` — forward-looking prediction, on/off state not applicable
- `PredictionChart` — historical profiles + prediction, on/off state not applicable

---

## Visual Treatment

Off periods are shown as **`ReferenceArea` background shading bands**:
- Fill: `rgba(80, 80, 80, 0.25)`
- Label: `"OFF"` at `insideTopLeft`, font size 9, color `#6d6e71`
- `ifOverflow="hidden"` to clip bands at chart boundaries
- The line/area series retains its normal color throughout — no line color changes

---

## Architecture

### 1. Backend endpoint

```
GET /api/on-off-periods/{ahu_id}?range=24h|7d|30d
```

**Response:**
```json
{
  "ahu_id": "e0507",
  "range": "7d",
  "off_periods": [
    { "start": "2026-04-03T22:00:00+08:00", "end": "2026-04-04T06:00:00+08:00" }
  ]
}
```

Implementation uses the existing `is_on` derivation in `backend/core/db_reader.py`. Groups consecutive `is_on=False` rows into contiguous `{start, end}` intervals. No new InfluxDB queries.

New route file: `backend/routes/on_off_periods.py`  
Registered in `backend/main.py` under `/api` prefix.

### 2. Shared type

Add to `frontend/src/types/index.ts`:
```ts
export type OffPeriod = { start: string; end: string };
```

### 3. API client function

Add to `frontend/src/api/client.ts`:
```ts
export async function fetchOffPeriods(deviceId: string, range: string): Promise<OffPeriod[]>
```

Returns `[]` on error (charts degrade gracefully with no shading).

### 4. Shared rendering utility

New file: `frontend/src/utils/offPeriodAreas.tsx`

```ts
import { ReferenceArea } from 'recharts';
import type { OffPeriod } from '../types';

export function renderOffPeriodAreas(offPeriods: OffPeriod[] | undefined) {
  if (!offPeriods?.length) return null;
  return offPeriods.map((p, i) => (
    <ReferenceArea
      key={i}
      x1={p.start}
      x2={p.end}
      fill="rgba(80,80,80,0.25)"
      label={{ value: 'OFF', position: 'insideTopLeft', fontSize: 9, fill: '#6d6e71' }}
      ifOverflow="hidden"
    />
  ));
}
```

### 5. Parent-level data fetching

Each parent that hosts single-device charts fetches off-periods once per `(deviceId, timeRange)` change and passes `offPeriods` down as a prop:

| Parent component | Charts it feeds |
|---|---|
| `DeviceDetailCard` | `HealthIndexChart`, `CombinedScoresChart` |
| `ScoreCardWithSelector` / `ScoreDerivationSection` | `RawScoreRelationChart` |
| `DeviceColumn` (inside `DeepDiveView`) | `SingleDeviceChart`, `MeasurementHistoryChart`, `MetricMiniChart` |

### 6. Chart updates (per chart)

Each of the six eligible charts:
1. Adds `offPeriods?: OffPeriod[]` to its props interface
2. Calls `{renderOffPeriodAreas(offPeriods)}` inside its Recharts composition
3. `HealthIndexChart` additionally: removes `showColorSegments` prop, removes all two-line on/off segment logic, removes the `onData`/`offData` split
4. `SingleDeviceChart` additionally: removes the inline `opacity`/`grayscale` dimming style on the wrapper div

All callers of `HealthIndexChart` that pass `showColorSegments` have that prop removed.

---

## Timestamp alignment

`ReferenceArea` `x1`/`x2` values must match the format of the chart's XAxis `dataKey` exactly — Recharts does string comparison to position the band. Some charts (e.g. `HealthIndexChart`) format timestamps before passing data in, while others use raw ISO strings.

Rule: `fetchOffPeriods` returns raw ISO timestamps. Each parent that formats chart data (e.g. via `formatTickByRange`) must apply the **same formatting** to `offPeriods[].start` and `offPeriods[].end` before passing them to charts. Charts that use raw ISO timestamps need no transformation.

---

## Error handling & edge cases

- If `fetchOffPeriods` fails or returns an empty array, charts render normally with no shading — no broken state
- If an off-period spans the entire visible time range, the whole chart background is shaded
- `offPeriods` is optional on all chart props — passing `undefined` is safe and produces no shading (correct behavior for multi-device views)
- The `is_on` field on `HealthIndexChart`'s data type remains in the interface (it comes from the health index API) but is no longer used for rendering

---

## Files changed

**New:**
- `backend/routes/on_off_periods.py`
- `frontend/src/utils/offPeriodAreas.tsx`

**Modified:**
- `backend/main.py` — register new router
- `frontend/src/types/index.ts` — add `OffPeriod` type
- `frontend/src/api/client.ts` — add `fetchOffPeriods`
- `frontend/src/components/dashboard/HealthIndexChart.tsx`
- `frontend/src/components/dashboard/CombinedScoresChart.tsx`
- `frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx`
- `frontend/src/components/deepdive/SingleDeviceChart.tsx`
- `frontend/src/components/prediction/MeasurementHistoryChart.tsx`
- `frontend/src/components/shared/MetricMiniChart.tsx`
- Parent components that host these charts (fetch + pass `offPeriods`)
