# AHU On/Off Period Shading — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show translucent grey `ReferenceArea` shading bands with an "OFF" label on every single-device chart whenever an AHU was powered off during the displayed time range.

**Architecture:** A new `GET /api/on-off-periods/{ahu_id}` backend endpoint derives off-period intervals from the existing `is_on` flag in `db_reader.py`. Each parent component that hosts single-device charts fetches these intervals once and passes them as an `offPeriods` prop. A shared `renderOffPeriodAreas` helper renders `ReferenceArea` bands identically across all six eligible charts.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/Recharts (frontend), pytest (backend tests), Jest + React Testing Library (frontend tests)

---

## File Map

**New files:**
- `backend/routes/on_off_periods.py` — FastAPI route for off-period intervals
- `backend/tests/test_on_off_periods.py` — backend endpoint tests
- `frontend/src/utils/offPeriodAreas.tsx` — shared `renderOffPeriodAreas` helper
- `frontend/src/__tests__/offPeriodAreas.test.tsx` — helper tests

**Modified files:**
- `backend/core/db_reader.py` — add `get_off_periods(ahu_id, time_range)` function
- `backend/tests/test_db_reader.py` — add tests for `get_off_periods`
- `backend/main.py` — register new router
- `frontend/src/types/index.ts` — add `OffPeriod` type
- `frontend/src/api/client.ts` — add `fetchOffPeriods`
- `frontend/src/components/dashboard/HealthIndexChart.tsx` — remove `showColorSegments`, add `offPeriods`
- `frontend/src/components/dashboard/CombinedScoresChart.tsx` — add `offPeriods`
- `frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx` — add `offPeriods`
- `frontend/src/components/deepdive/SingleDeviceChart.tsx` — remove opacity dimming, add `offPeriods`
- `frontend/src/components/prediction/MeasurementHistoryChart.tsx` — add `offPeriods`
- `frontend/src/components/shared/MetricMiniChart.tsx` — add `offPeriods`
- `frontend/src/App.tsx` — fetch offPeriods, pass to HealthIndexChart + CombinedScoresChart, remove `showColorSegments`
- `frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx` — fetch offPeriods, pass through
- `frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx` — accept + forward `offPeriods`
- `frontend/src/components/deepdive/DeepDiveView.tsx` — fetch offPeriods, pass to SingleDeviceChart

---

## Task 1: Backend — `get_off_periods` in `db_reader.py`

**Files:**
- Modify: `backend/core/db_reader.py`
- Modify: `backend/tests/test_db_reader.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_db_reader.py`:

```python
def test_get_off_periods_returns_empty_when_no_data(seeded_db):
    # Device with no data → empty list
    result = db_reader.get_off_periods("e9999", "7d")
    assert result == []


def test_get_off_periods_returns_empty_when_always_on(seeded_db):
    # SAMPLE_ROW has current L1=5.5A (>2A) → is_on=True → no off periods
    result = db_reader.get_off_periods("e0101", "7d")
    assert result == []


def test_get_off_periods_returns_interval_for_off_rows(tmp_path, monkeypatch):
    """Two off-rows sandwiched between on-rows produce one interval."""
    db_path = str(tmp_path / "offtest.duckdb")
    db = HealthDB(db_path)

    base = {
        "ahu_id": "e0101", "level": 1, "health_index": 60.0, "tier": "Monitor",
        "energy_anomaly": 0.1, "pf_degradation": 0.1, "phase_imbalance": 0.1,
        "thd_drift": 0.05, "overload": 0.2,
        "raw_power_total": 0.5, "raw_energy_import": 5000.0,
        "raw_hourly_delta": 1.0, "raw_predicted_delta": 1.0,
        "raw_energy_anomaly_raw": 0.3, "raw_power_factor_avg": 0.85,
        "raw_current_unbalance": 1.0, "raw_composite_thd": 2.0,
        "raw_apparent_power_total": 2.0,
        "raw_current_l1": 5.0, "raw_current_l2": 5.0, "raw_current_l3": 5.0,
        "raw_volts_l1_n": 230.0, "raw_volts_l2_n": 230.0, "raw_volts_l3_n": 230.0,
        "raw_current_l1_thd": 2.0, "raw_current_l3_thd": 1.5,
        "raw_volts_l1_thd": 2.0, "raw_volts_l2_thd": 2.0, "raw_volts_l3_thd": 2.0,
        "raw_nema_voltage_imbalance": 0.5, "raw_p95_current": 5.5, "safety_flags": "",
    }

    rows = [
        {**base, "timestamp": pd.Timestamp("2026-04-01 08:00:00+00:00"),
         "raw_current_l1": 5.0, "raw_current_l2": 5.0, "raw_current_l3": 5.0},  # on
        {**base, "timestamp": pd.Timestamp("2026-04-01 22:00:00+00:00"),
         "raw_current_l1": 0.0, "raw_current_l2": 0.0, "raw_current_l3": 0.0},  # off
        {**base, "timestamp": pd.Timestamp("2026-04-01 23:00:00+00:00"),
         "raw_current_l1": 0.0, "raw_current_l2": 0.0, "raw_current_l3": 0.0},  # off
        {**base, "timestamp": pd.Timestamp("2026-04-02 07:00:00+00:00"),
         "raw_current_l1": 5.0, "raw_current_l2": 5.0, "raw_current_l3": 5.0},  # on
    ]
    db.upsert(pd.DataFrame(rows))
    monkeypatch.setattr(db_reader, "_DB_PATH", db_path)
    # Clear the singleton cache so the monkeypatched path is picked up
    db_reader._DB_INSTANCES.clear()

    result = db_reader.get_off_periods("e0101", "7d")

    assert len(result) == 1
    assert "start" in result[0] and "end" in result[0]
    # Off period starts at first off row, ends at first on row after it
    assert "2026-04-01T22:00:00" in result[0]["start"]
    assert "2026-04-02T07:00:00" in result[0]["end"]
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_db_reader.py::test_get_off_periods_returns_empty_when_no_data tests/test_db_reader.py::test_get_off_periods_returns_empty_when_always_on tests/test_db_reader.py::test_get_off_periods_returns_interval_for_off_rows -v
```

Expected: `AttributeError: module 'core.db_reader' has no attribute 'get_off_periods'`

- [ ] **Step 3: Implement `get_off_periods` in `db_reader.py`**

Add after the `get_health_index_series` function (around line 255):

```python
def get_off_periods(ahu_id: str, time_range: str) -> list[dict]:
    """
    Returns contiguous off-period intervals for a single AHU.
    Each dict has {"start": <iso str>, "end": <iso str>}.
    """
    from models.schemas import ALLOWED_DEVICES
    if ahu_id not in ALLOWED_DEVICES:
        return []

    df = _get_df(ahu_ids=[ahu_id], time_range=time_range)
    if df.empty or "is_on" not in df.columns:
        return []

    rows = df[df["ahu_id"] == ahu_id].sort_values("timestamp").reset_index(drop=True)
    if rows.empty:
        return []

    periods: list[dict] = []
    in_off = False
    start_ts = None

    for _, row in rows.iterrows():
        if not row["is_on"] and not in_off:
            in_off = True
            start_ts = row["timestamp"]
        elif row["is_on"] and in_off:
            in_off = False
            periods.append({
                "start": start_ts.isoformat(),
                "end": row["timestamp"].isoformat(),
            })

    # Close an open off-period at the last data point
    if in_off and start_ts is not None:
        periods.append({
            "start": start_ts.isoformat(),
            "end": rows["timestamp"].iloc[-1].isoformat(),
        })

    return periods
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && python -m pytest tests/test_db_reader.py::test_get_off_periods_returns_empty_when_no_data tests/test_db_reader.py::test_get_off_periods_returns_empty_when_always_on tests/test_db_reader.py::test_get_off_periods_returns_interval_for_off_rows -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/core/db_reader.py backend/tests/test_db_reader.py
git commit -m "feat: add get_off_periods to db_reader"
```

---

## Task 2: Backend — Route + registration

**Files:**
- Create: `backend/routes/on_off_periods.py`
- Create: `backend/tests/test_on_off_periods.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_on_off_periods.py`:

```python
import os
import sys
import pytest
import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.healthdb import HealthDB
from core import db_reader

# Patch DB before app import so the route uses the test DB
@pytest.fixture()
def client_with_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.duckdb")
    db = HealthDB(db_path)
    row = {
        "timestamp": pd.Timestamp("2026-04-01 10:00:00+00:00"),
        "ahu_id": "e0101", "level": 1, "health_index": 75.0, "tier": "Monitor",
        "energy_anomaly": 0.3, "pf_degradation": 0.2, "phase_imbalance": 0.1,
        "thd_drift": 0.05, "overload": 0.4,
        "raw_power_total": 0.9, "raw_energy_import": 10000.0,
        "raw_hourly_delta": 2.0, "raw_predicted_delta": 1.5,
        "raw_energy_anomaly_raw": 0.5, "raw_power_factor_avg": 0.88,
        "raw_current_unbalance": 2.0, "raw_composite_thd": 3.0,
        "raw_apparent_power_total": 3.7,
        "raw_current_l1": 5.5, "raw_current_l2": 5.2, "raw_current_l3": 5.4,
        "raw_volts_l1_n": 233.0, "raw_volts_l2_n": 234.0, "raw_volts_l3_n": 232.0,
        "raw_current_l1_thd": 2.6, "raw_current_l3_thd": 1.5,
        "raw_volts_l1_thd": 2.8, "raw_volts_l2_thd": 2.4, "raw_volts_l3_thd": 2.2,
        "raw_nema_voltage_imbalance": 0.66, "raw_p95_current": 5.6, "safety_flags": "",
    }
    db.upsert(pd.DataFrame([row]))
    monkeypatch.setattr(db_reader, "_DB_PATH", db_path)
    db_reader._DB_INSTANCES.clear()
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DEV_API_KEY", "test-key")

    from main import app
    return TestClient(app, headers={"Authorization": "Bearer test-key"})


def test_get_off_periods_known_device_always_on(client_with_db):
    resp = client_with_db.get("/api/on-off-periods/e0101?range=7d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ahu_id"] == "e0101"
    assert body["range"] == "7d"
    assert body["off_periods"] == []


def test_get_off_periods_unknown_device(client_with_db):
    resp = client_with_db.get("/api/on-off-periods/e9999?range=7d")
    assert resp.status_code == 404


def test_get_off_periods_invalid_range(client_with_db):
    resp = client_with_db.get("/api/on-off-periods/e0101?range=bad")
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_on_off_periods.py -v
```

Expected: import errors or 404s because the route doesn't exist yet.

- [ ] **Step 3: Create `backend/routes/on_off_periods.py`**

```python
"""
on_off_periods.py
─────────────────
GET /api/on-off-periods/{ahu_id}?range=24h|7d|30d

Returns contiguous time intervals when the AHU was powered off,
derived from the is_on flag in the health database.
"""

from fastapi import APIRouter, HTTPException, Query
from models.schemas import ALLOWED_DEVICES
from core import db_reader

router = APIRouter()

_VALID_RANGES = {"24h", "7d", "30d"}


@router.get("/on-off-periods/{ahu_id}")
async def get_on_off_periods(
    ahu_id: str,
    range: str = Query(default="7d", description="24h | 7d | 30d"),
):
    if ahu_id not in ALLOWED_DEVICES:
        raise HTTPException(status_code=404, detail=f"Unknown device: {ahu_id}")
    if range not in _VALID_RANGES:
        raise HTTPException(status_code=400, detail=f"range must be one of: {sorted(_VALID_RANGES)}")

    off_periods = db_reader.get_off_periods(ahu_id, range)
    return {"ahu_id": ahu_id, "range": range, "off_periods": off_periods}
```

- [ ] **Step 4: Register the router in `backend/main.py`**

After the existing router imports (around line 37), add:

```python
from routes.on_off_periods import router as on_off_periods_router
```

After the existing `app.include_router(...)` calls, add:

```python
app.include_router(on_off_periods_router, prefix="/api")
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd backend && python -m pytest tests/test_on_off_periods.py -v
```

Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/routes/on_off_periods.py backend/tests/test_on_off_periods.py backend/main.py
git commit -m "feat: add GET /api/on-off-periods/{ahu_id} endpoint"
```

---

## Task 3: Frontend shared foundation — type + API client + render utility

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/utils/offPeriodAreas.tsx`
- Create: `frontend/src/__tests__/offPeriodAreas.test.tsx`

- [ ] **Step 1: Add `OffPeriod` type to `frontend/src/types/index.ts`**

Add at the top of the file (after the first imports or at a logical grouping point):

```ts
export type OffPeriod = { start: string; end: string };
```

- [ ] **Step 2: Add `fetchOffPeriods` to `frontend/src/api/client.ts`**

Add after the existing functions (before the end of the file):

```ts
/**
 * GET /api/on-off-periods/{deviceId}?range=...
 * Returns contiguous intervals when the AHU was powered off.
 * Returns [] on any error so charts degrade gracefully.
 */
export async function fetchOffPeriods(deviceId: string, range: string): Promise<import('./types').OffPeriod[]> {
  try {
    const data = await apiFetch<{ off_periods: import('./types').OffPeriod[] }>(
      `/on-off-periods/${deviceId}?range=${range}`
    );
    return data.off_periods ?? [];
  } catch {
    return [];
  }
}
```

Note: the import path for `OffPeriod` in `client.ts` should match the actual relative path. Since `client.ts` is at `frontend/src/api/client.ts` and types are at `frontend/src/types/index.ts`, use:

```ts
export async function fetchOffPeriods(deviceId: string, range: string): Promise<OffPeriod[]> {
  try {
    const data = await apiFetch<{ off_periods: OffPeriod[] }>(
      `/on-off-periods/${deviceId}?range=${range}`
    );
    return data.off_periods ?? [];
  } catch {
    return [];
  }
}
```

And add `OffPeriod` to the existing import at the top of `client.ts`:

```ts
import { LevelsResponse, HealthIndexResponse, ScoresResponse, MeasurementsResponse, SiteSummaryData, OffPeriod } from '../types';
```

- [ ] **Step 3: Write the failing test for `renderOffPeriodAreas`**

Create `frontend/src/__tests__/offPeriodAreas.test.tsx`:

```tsx
import React from 'react';
import { render } from '@testing-library/react';

// Mock ReferenceArea so we can inspect it in jsdom
jest.mock('recharts', () => ({
  ReferenceArea: ({ x1, x2, fill, label }: any) => (
    <div
      data-testid="reference-area"
      data-x1={x1}
      data-x2={x2}
      data-fill={fill}
      data-label={label?.value}
    />
  ),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { renderOffPeriodAreas } = require('../utils/offPeriodAreas');

describe('renderOffPeriodAreas', () => {
  it('returns null when offPeriods is undefined', () => {
    const { container } = render(<div>{renderOffPeriodAreas(undefined)}</div>);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('returns null when offPeriods is empty', () => {
    const { container } = render(<div>{renderOffPeriodAreas([])}</div>);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('renders one ReferenceArea per off period', () => {
    const periods = [
      { start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' },
      { start: '2026-04-03T23:00:00Z', end: '2026-04-04T07:00:00Z' },
    ];
    const { container } = render(<div>{renderOffPeriodAreas(periods)}</div>);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(2);
  });

  it('passes correct x1/x2 from period start/end', () => {
    const periods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(<div>{renderOffPeriodAreas(periods)}</div>);
    const area = container.querySelector('[data-testid="reference-area"]');
    expect(area?.getAttribute('data-x1')).toBe('2026-04-01T22:00:00Z');
    expect(area?.getAttribute('data-x2')).toBe('2026-04-02T06:00:00Z');
  });

  it('renders the OFF label', () => {
    const periods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(<div>{renderOffPeriodAreas(periods)}</div>);
    const area = container.querySelector('[data-testid="reference-area"]');
    expect(area?.getAttribute('data-label')).toBe('OFF');
  });
});
```

- [ ] **Step 4: Run test to confirm it fails**

```bash
cd frontend && npm test -- --testPathPattern=offPeriodAreas --watchAll=false
```

Expected: `Cannot find module '../utils/offPeriodAreas'`

- [ ] **Step 5: Create `frontend/src/utils/offPeriodAreas.tsx`**

```tsx
import React from 'react';
import { ReferenceArea } from 'recharts';
import type { OffPeriod } from '../types';

export function renderOffPeriodAreas(offPeriods: OffPeriod[] | undefined): React.ReactNode {
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

- [ ] **Step 6: Run tests to confirm they pass**

```bash
cd frontend && npm test -- --testPathPattern=offPeriodAreas --watchAll=false
```

Expected: 5 PASSED

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/utils/offPeriodAreas.tsx frontend/src/__tests__/offPeriodAreas.test.tsx
git commit -m "feat: add OffPeriod type, fetchOffPeriods client fn, and renderOffPeriodAreas utility"
```

---

## Task 4: Update `HealthIndexChart`

**Files:**
- Modify: `frontend/src/components/dashboard/HealthIndexChart.tsx`

This task removes the `showColorSegments` two-line logic and adds the `offPeriods` prop.

- [ ] **Step 1: Write the failing test**

Add to a new test file `frontend/src/__tests__/HealthIndexChart.test.tsx` (check if one already exists at `frontend/src/__tests__/` — if not, create it):

```tsx
import React from 'react';
import { render } from '@testing-library/react';

jest.mock('recharts', () => ({
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ReferenceArea: ({ x1, x2 }: any) => (
    <div data-testid="reference-area" data-x1={x1} data-x2={x2} />
  ),
}));

jest.mock('framer-motion', () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
}));

jest.mock('../utils/formatTick', () => ({
  formatDateMYT: () => 'Apr 10, 2026',
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { default: HealthIndexChart } = require('../components/dashboard/HealthIndexChart');

const device = { id: 'e0101', name: 'e0101', label: 'AHU-01', department: 'Ward A' };
const data = [
  { timestamp: '2026-04-01T08:00:00Z', e0101: 75 },
  { timestamp: '2026-04-01T22:00:00Z', e0101: 70 },
];

describe('HealthIndexChart', () => {
  it('renders without offPeriods and shows no ReferenceArea', () => {
    const { container } = render(
      <HealthIndexChart data={data} devices={[device]} />
    );
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('renders a ReferenceArea for each off period when offPeriods provided', () => {
    const offPeriods = [
      { start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' },
    ];
    const { container } = render(
      <HealthIndexChart data={data} devices={[device]} offPeriods={offPeriods} />
    );
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
  });

  it('does not accept showColorSegments prop (it is removed)', () => {
    // Just verify it renders without crash when the old prop is absent
    expect(() =>
      render(<HealthIndexChart data={data} devices={[device]} />)
    ).not.toThrow();
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npm test -- --testPathPattern=HealthIndexChart --watchAll=false
```

Expected: Tests importing `ReferenceArea` will fail because it is not in the chart; the `showColorSegments` removal test may not fail but should pass once implemented.

- [ ] **Step 3: Update `HealthIndexChart.tsx`**

Replace the props interface:

```ts
// OLD
interface HealthIndexChartProps {
  data: Array<{ timestamp: string; [key: string]: number; originalTs?: string; is_on?: boolean }>;
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
  showColorSegments?: boolean;
}
```

```ts
// NEW
import type { OffPeriod } from '../../types';

interface HealthIndexChartProps {
  data: Array<{ timestamp: string; [key: string]: number | string | boolean | undefined }>;
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
  offPeriods?: OffPeriod[];
}
```

Update the function signature:

```ts
// OLD
const HealthIndexChart: React.FC<HealthIndexChartProps> = ({ data, devices, showColorSegments = false }) => {
```

```ts
// NEW
const HealthIndexChart: React.FC<HealthIndexChartProps> = ({ data, devices, offPeriods }) => {
```

Add `ReferenceArea` to the recharts import at the top:

```ts
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts';
```

Add `renderOffPeriodAreas` import after the other local imports:

```ts
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';
```

Inside the `<AreaChart>` JSX, **replace** the entire `{!showColorSegments && ...}` and `{showColorSegments && ...}` blocks with:

```tsx
{/* Single line per device — no on/off color splitting */}
{devices.map((device, index) => (
  <Area
    key={device.id}
    type="monotone"
    dataKey={device.name}
    stroke={getColor(index)}
    strokeWidth={2}
    fill="none"
    connectNulls
    dot={false}
  />
))}

{/* Off-period shading bands */}
{renderOffPeriodAreas(offPeriods)}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd frontend && npm test -- --testPathPattern=HealthIndexChart --watchAll=false
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/HealthIndexChart.tsx frontend/src/__tests__/HealthIndexChart.test.tsx
git commit -m "feat: replace two-line on/off segments with ReferenceArea shading in HealthIndexChart"
```

---

## Task 5: Update `CombinedScoresChart`

**Files:**
- Modify: `frontend/src/components/dashboard/CombinedScoresChart.tsx`
- Modify: `frontend/src/__tests__/CombinedScoresChart.test.tsx`

- [ ] **Step 1: Add a failing test to the existing test file**

Open `frontend/src/__tests__/CombinedScoresChart.test.tsx` and add `ReferenceArea` to the Recharts mock and a new test:

```tsx
// Add to the recharts mock object:
ReferenceArea: ({ x1, x2 }: any) => (
  <div data-testid="reference-area" data-x1={x1} data-x2={x2} />
),
```

Add this test at the end of the `describe` block:

```tsx
it('renders a ReferenceArea for each off period', () => {
  const scoreData = {
    energy_anomaly:  makeScoreEntry([0.1, 0.2]),
    pf_degradation:  makeScoreEntry([0.2, 0.3]),
    phase_imbalance: makeScoreEntry([0.1, 0.1]),
    thd_drift:       makeScoreEntry([0.3, 0.3]),
    overload:        makeScoreEntry([0.0, 0.1]),
  };
  const offPeriods = [
    { start: '2026-01-01T22:00:00Z', end: '2026-01-02T06:00:00Z' },
  ];
  const { container } = render(
    <CombinedScoresChart scoreData={scoreData} timeRange="7d" offPeriods={offPeriods} />
  );
  expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
});

it('renders no ReferenceArea when offPeriods is undefined', () => {
  const scoreData = {
    energy_anomaly:  makeScoreEntry([0.1]),
    pf_degradation:  makeScoreEntry([0.2]),
    phase_imbalance: makeScoreEntry([0.1]),
    thd_drift:       makeScoreEntry([0.3]),
    overload:        makeScoreEntry([0.0]),
  };
  const { container } = render(
    <CombinedScoresChart scoreData={scoreData} timeRange="7d" />
  );
  expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
});
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd frontend && npm test -- --testPathPattern=CombinedScoresChart --watchAll=false
```

Expected: new tests fail — `offPeriods` prop not accepted and `ReferenceArea` not rendered.

- [ ] **Step 3: Update `CombinedScoresChart.tsx`**

Add imports at the top:

```ts
import { ReferenceArea } from 'recharts';  // add to existing recharts import
import type { OffPeriod } from '../../types';
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';
```

Update props interface:

```ts
interface CombinedScoresChartProps {
  scoreData: Record<string, ScoreEntry>;
  timeRange: TimeRange;
  offPeriods?: OffPeriod[];
}
```

Update function signature:

```ts
const CombinedScoresChart: React.FC<CombinedScoresChartProps> = ({ scoreData, timeRange, offPeriods }) => {
```

Inside `<LineChart>`, add after the last `<Line>` element:

```tsx
{renderOffPeriodAreas(offPeriods)}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd frontend && npm test -- --testPathPattern=CombinedScoresChart --watchAll=false
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/CombinedScoresChart.tsx frontend/src/__tests__/CombinedScoresChart.test.tsx
git commit -m "feat: add offPeriods shading to CombinedScoresChart"
```

---

## Task 6: Update `RawScoreRelationChart`

**Files:**
- Modify: `frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/RawScoreRelationChart.test.tsx`:

```tsx
import React from 'react';
import { render } from '@testing-library/react';

jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ReferenceArea: ({ x1, x2 }: any) => (
    <div data-testid="reference-area" data-x1={x1} data-x2={x2} />
  ),
}));

jest.mock('../utils/formatTick', () => ({
  formatTickByRange: () => '',
  tickIntervalByRange: () => 5,
  formatDateMYT: () => '',
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { default: RawScoreRelationChart } = require('../components/dashboard/derivation/RawScoreRelationChart');

const makeProps = () => ({
  scoreName: 'Energy Anomaly',
  series: [{ label: 'δ kWh', unit: 'kWh', style: 'solid', data: [{ timestamp: '2026-04-01T00:00:00Z', value: 1.0 }] }],
  scoreData: [{ timestamp: '2026-04-01T00:00:00Z', value: 70 }],
  referenceLines: [],
  chartColor: '#3B82F6',
  timeRange: '7d' as const,
});

describe('RawScoreRelationChart', () => {
  it('renders no ReferenceArea when offPeriods is absent', () => {
    const { container } = render(<RawScoreRelationChart {...makeProps()} />);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(0);
  });

  it('renders a ReferenceArea per off period', () => {
    const offPeriods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(<RawScoreRelationChart {...makeProps()} offPeriods={offPeriods} />);
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd frontend && npm test -- --testPathPattern=RawScoreRelationChart --watchAll=false
```

Expected: new `offPeriods` test fails.

- [ ] **Step 3: Update `RawScoreRelationChart.tsx`**

Add to imports:

```ts
import { ReferenceArea } from 'recharts';  // add to existing recharts import
import type { OffPeriod } from '../../../types';
import { renderOffPeriodAreas } from '../../../utils/offPeriodAreas';
```

Update props interface to add:

```ts
offPeriods?: OffPeriod[];
```

Update function signature to destructure `offPeriods`:

```ts
const RawScoreRelationChart: React.FC<RawScoreRelationChartProps> = ({
  scoreName, series, scoreData, referenceLines = [], chartColor, headerAction, timeRange, offPeriods,
}) => {
```

Inside `<LineChart>`, add after the score `<Line>` element:

```tsx
{renderOffPeriodAreas(offPeriods)}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd frontend && npm test -- --testPathPattern=RawScoreRelationChart --watchAll=false
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx frontend/src/__tests__/RawScoreRelationChart.test.tsx
git commit -m "feat: add offPeriods shading to RawScoreRelationChart"
```

---

## Task 7: Update `SingleDeviceChart`

**Files:**
- Modify: `frontend/src/components/deepdive/SingleDeviceChart.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/SingleDeviceChart.test.tsx`:

```tsx
import React from 'react';
import { render } from '@testing-library/react';

jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ReferenceArea: ({ x1, x2 }: any) => (
    <div data-testid="reference-area" data-x1={x1} data-x2={x2} />
  ),
}));

jest.mock('../../api/client', () => ({
  fetchMeasurements: jest.fn().mockResolvedValue({ measurements: {} }),
}));

jest.mock('../../constants/metricGroups', () => ({
  SCORE_METRIC_GROUPS: [],
  METRIC_META: {},
}));

jest.mock('../../constants/chartConfig', () => ({
  CHART_CONFIG: { HEIGHTS: { LOADING_STATE: 180, SINGLE_DEVICE: 300 }, MARGINS: { SINGLE: {} }, CHART_COLORS: ['#4fbd95'] },
}));

jest.mock('../../hooks/useMetricSelection', () => ({
  useMetricSelection: () => ({ selectedMetrics: [], setSelectedMetrics: jest.fn(), toggleMetric: jest.fn() }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { default: SingleDeviceChart } = require('../components/deepdive/SingleDeviceChart');

describe('SingleDeviceChart', () => {
  it('renders without opacity dimming style regardless of isOn', () => {
    const { container } = render(
      <SingleDeviceChart deviceId="e0101" deviceLabel="AHU-01" timeRange="7d" isOn={false} />
    );
    // The wrapper div should not have opacity or grayscale inline styles
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper?.style?.opacity).not.toBe('0.45');
    expect(wrapper?.style?.filter).not.toContain('grayscale');
  });

  it('renders ReferenceArea for each off period', () => {
    const offPeriods = [{ start: '2026-04-01T22:00:00Z', end: '2026-04-02T06:00:00Z' }];
    const { container } = render(
      <SingleDeviceChart deviceId="e0101" deviceLabel="AHU-01" timeRange="7d" offPeriods={offPeriods} />
    );
    expect(container.querySelectorAll('[data-testid="reference-area"]')).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd frontend && npm test -- --testPathPattern=SingleDeviceChart --watchAll=false
```

Expected: opacity test fails (opacity is still 0.45 in old code), ReferenceArea test fails.

- [ ] **Step 3: Update `SingleDeviceChart.tsx`**

Add to imports:

```ts
import { ReferenceArea } from 'recharts';  // add to existing recharts import
import type { OffPeriod } from '../../types';
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';
```

Update the props interface:

```ts
interface SingleDeviceChartProps {
  deviceId: string;
  deviceLabel: string;
  timeRange: string;
  isOn?: boolean;
  offPeriods?: OffPeriod[];
}
```

Update the function signature:

```ts
const SingleDeviceChart: React.FC<SingleDeviceChartProps> = ({ deviceId, deviceLabel, timeRange, isOn = true, offPeriods }) => {
```

Replace the outer wrapper `<div>` that has the inline opacity/grayscale style:

```tsx
// OLD
<div style={{ opacity: isOn ? 1 : 0.45, filter: isOn ? 'none' : 'grayscale(80%)', transition: 'opacity 0.2s, filter 0.2s' }}>
```

```tsx
// NEW
<div>
```

Inside `<LineChart>`, add after the last `<Line>` mapping:

```tsx
{renderOffPeriodAreas(offPeriods)}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd frontend && npm test -- --testPathPattern=SingleDeviceChart --watchAll=false
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/SingleDeviceChart.tsx frontend/src/__tests__/SingleDeviceChart.test.tsx
git commit -m "feat: add offPeriods shading to SingleDeviceChart, remove opacity dimming"
```

---

## Task 8: Update `MeasurementHistoryChart` and `MetricMiniChart`

**Files:**
- Modify: `frontend/src/components/prediction/MeasurementHistoryChart.tsx`
- Modify: `frontend/src/components/shared/MetricMiniChart.tsx`

These two charts use raw ISO timestamps as XAxis dataKeys — no timestamp transformation needed.

- [ ] **Step 1: Update `MeasurementHistoryChart.tsx`**

Add to imports:

```ts
import { ReferenceArea } from 'recharts';  // add to existing recharts import
import type { OffPeriod } from '../../types';
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';
```

Update props interface to add:

```ts
offPeriods?: OffPeriod[];
```

Update function signature:

```ts
export default function MeasurementHistoryChart({
  label, unit, data, color, loading, isCoreMetric, tNow, offPeriods,
}: MeasurementHistoryChartProps) {
```

Inside `<LineChart>`, add after the `<Line>` element:

```tsx
{renderOffPeriodAreas(offPeriods)}
```

- [ ] **Step 2: Update `MetricMiniChart.tsx`**

Add to imports:

```ts
import { ReferenceArea } from 'recharts';  // add to existing recharts import
import type { OffPeriod } from '../../types';
import { renderOffPeriodAreas } from '../../utils/offPeriodAreas';
```

Update props interface to add:

```ts
offPeriods?: OffPeriod[];
```

Update function signature:

```ts
export default function MetricMiniChart({
  label, unit, data, color, loading, offPeriods,
}: MetricMiniChartProps) {
```

Inside `<LineChart>`, add after the `<Line>` element:

```tsx
{renderOffPeriodAreas(offPeriods)}
```

- [ ] **Step 3: Run the full frontend test suite to confirm nothing broke**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: all existing tests pass, no new failures.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/prediction/MeasurementHistoryChart.tsx frontend/src/components/shared/MetricMiniChart.tsx
git commit -m "feat: add offPeriods shading to MeasurementHistoryChart and MetricMiniChart"
```

---

## Task 9: Wire `App.tsx` — fetch offPeriods, pass to HealthIndexChart + CombinedScoresChart

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the `fetchOffPeriods` import and state in `App.tsx`**

Add `fetchOffPeriods` to the existing import from `'./api/client'`:

```ts
import { ..., fetchOffPeriods } from './api/client';
```

Add `OffPeriod` to the types import:

```ts
import { ..., OffPeriod } from './types';
```

Add a state variable near the other `useState` declarations:

```ts
const [offPeriods, setOffPeriods] = React.useState<OffPeriod[]>([]);
```

- [ ] **Step 2: Add the `useEffect` to fetch off-periods when a single device is selected**

Find the `useEffect` blocks that fetch health data and add a new one after them. Place it in the same section where other device-specific data is fetched:

```ts
// Fetch off-periods when a single device is selected
React.useEffect(() => {
  if (!selectedDevice || selectedDevice === 'all') {
    setOffPeriods([]);
    return;
  }
  fetchOffPeriods(selectedDevice, chartRange).then(setOffPeriods);
}, [selectedDevice, chartRange]);
```

- [ ] **Step 3: Pass `offPeriods` to `HealthIndexChart` and `CombinedScoresChart`, remove `showColorSegments`**

Find the `<HealthIndexChart>` usage (around line 280):

```tsx
// OLD
<HealthIndexChart data={healthChartData as any} devices={chartDevices} showColorSegments={isSingleDevice} />
```

```tsx
// NEW — offPeriods formatted to match the timestamp format used in healthChartData
// App.tsx formats timestamps via formatTickByRange before passing to HealthIndexChart,
// so we must apply the same formatting to off-period boundaries.
<HealthIndexChart
  data={healthChartData as any}
  devices={chartDevices}
  offPeriods={
    isSingleDevice
      ? offPeriods.map((p) => ({
          start: formatTickByRange(p.start, chartRange),
          end: formatTickByRange(p.end, chartRange),
        }))
      : undefined
  }
/>
```

Find the `<CombinedScoresChart>` usage:

```tsx
// OLD
<CombinedScoresChart scoreData={scoreCardData} timeRange={chartRange} />
```

```tsx
// NEW — CombinedScoresChart uses raw ISO timestamps as its XAxis dataKey,
// so pass offPeriods directly without any formatting.
<CombinedScoresChart
  scoreData={scoreCardData}
  timeRange={chartRange}
  offPeriods={isSingleDevice ? offPeriods : undefined}
/>
```

- [ ] **Step 4: Run the full frontend test suite**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: fetch and wire offPeriods into HealthIndexChart and CombinedScoresChart from App.tsx"
```

---

## Task 10: Wire `ScoreDerivationSection` → `ScoreCardWithSelector` → `RawScoreRelationChart` + `MetricMiniChart`

**Files:**
- Modify: `frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx`
- Modify: `frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx`

`ScoreDerivationSection` already has `deviceId` and knows the `timeRange`. It fetches `offPeriods` once and passes them down. `ScoreCardWithSelector` forwards them to `RawScoreRelationChart` and `MetricMiniChart`.

- [ ] **Step 1: Update `ScoreDerivationSection.tsx`**

Read the full file first. The component receives `deviceId` and `timeRange` props. Add:

```ts
import { fetchOffPeriods } from '../../../api/client';
import type { OffPeriod } from '../../../types';
```

Add state:

```ts
const [offPeriods, setOffPeriods] = React.useState<OffPeriod[]>([]);
```

Add useEffect (after existing effects, before render):

```ts
React.useEffect(() => {
  if (!deviceId) return;
  fetchOffPeriods(deviceId, timeRange).then(setOffPeriods);
}, [deviceId, timeRange]);
```

Pass `offPeriods` to each `<ScoreCardWithSelector>`:

```tsx
<ScoreCardWithSelector
  ...existingProps
  offPeriods={offPeriods}
/>
```

- [ ] **Step 2: Update `ScoreCardWithSelector.tsx`**

Add `offPeriods` to the props interface:

```ts
import type { OffPeriod } from '../../../types';

interface ScoreCardWithSelectorProps {
  ...existing fields...
  offPeriods?: OffPeriod[];
}
```

Destructure in function signature:

```ts
export default function ScoreCardWithSelector({
  deviceId, scoreName, scoreKey,
  series, scoreData, referenceLines,
  chartColor, timeRange, availableMetrics, offPeriods,
}: ScoreCardWithSelectorProps) {
```

Pass to `<RawScoreRelationChart>`:

```tsx
<RawScoreRelationChart
  ...existingProps
  offPeriods={offPeriods}
/>
```

Pass to each `<MetricMiniChart>` rendered inside `ScoreCardWithSelector`:

```tsx
<MetricMiniChart
  ...existingProps
  offPeriods={offPeriods}
/>
```

- [ ] **Step 3: Run the full test suite**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx
git commit -m "feat: wire offPeriods through ScoreDerivationSection to RawScoreRelationChart and MetricMiniChart"
```

---

## Task 11: Wire `DeepDiveView` → `SingleDeviceChart`

**Files:**
- Modify: `frontend/src/components/deepdive/DeepDiveView.tsx`

`DeepDiveView` has `timeRange` and reads `selectedDevice` from the Zustand store. It fetches `offPeriods` once and passes them to `SingleDeviceChart`.

- [ ] **Step 1: Update `DeepDiveView.tsx`**

Add imports:

```ts
import { fetchOffPeriods } from '../../api/client';
import type { OffPeriod } from '../../types';
```

Add state:

```ts
const [offPeriods, setOffPeriods] = React.useState<OffPeriod[]>([]);
```

Add useEffect after the existing destructuring from the store:

```ts
React.useEffect(() => {
  if (!selectedDevice || selectedDevice === 'all') {
    setOffPeriods([]);
    return;
  }
  fetchOffPeriods(selectedDevice, timeRange).then(setOffPeriods);
}, [selectedDevice, timeRange]);
```

Pass to `<SingleDeviceChart>`:

```tsx
<SingleDeviceChart
  deviceId={selectedDevice!}
  deviceLabel={labelMap[selectedDevice!] ?? selectedDevice!}
  timeRange={timeRange}
  isOn={isSelectedDeviceOn}
  offPeriods={offPeriods}
/>
```

- [ ] **Step 2: Run the full test suite**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: all tests pass.

- [ ] **Step 3: Run the full backend test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/deepdive/DeepDiveView.tsx
git commit -m "feat: wire offPeriods through DeepDiveView to SingleDeviceChart"
```

---

## Self-Review

**Spec coverage:**
- ✅ `GET /api/on-off-periods/{ahu_id}` endpoint — Task 2
- ✅ `OffPeriod` type — Task 3
- ✅ `fetchOffPeriods` client fn — Task 3
- ✅ `renderOffPeriodAreas` utility — Task 3
- ✅ `HealthIndexChart` — `showColorSegments` removed, `offPeriods` added — Task 4
- ✅ `CombinedScoresChart` — Task 5
- ✅ `RawScoreRelationChart` — Task 6
- ✅ `SingleDeviceChart` — opacity dimming removed, `offPeriods` added — Task 7
- ✅ `MeasurementHistoryChart` — Task 8
- ✅ `MetricMiniChart` — Task 8
- ✅ Timestamp alignment for `HealthIndexChart` — Task 9 Step 3 (formatted) vs all other charts (raw ISO)
- ✅ Parent wiring: `App.tsx` — Task 9, `ScoreDerivationSection` — Task 10, `DeepDiveView` — Task 11
- ✅ Multi-device exclusion: `offPeriods` only passed when `isSingleDevice` — Task 9

**Type consistency check:**
- `OffPeriod` defined in Task 3, used in Tasks 4–11 ✅
- `renderOffPeriodAreas(offPeriods: OffPeriod[] | undefined)` defined in Task 3, called consistently in Tasks 4–8 ✅
- `fetchOffPeriods(deviceId: string, range: string): Promise<OffPeriod[]>` defined in Task 3, called in Tasks 9–11 ✅

**Placeholder scan:** No TBDs, no "handle edge cases" without code, all steps have code.
