# Thur Grey Effect Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract scattered "device-not-trustworthy" visual treatment into a single `useGreyState` hook and propagate it across Deep Dive (single + compare) and all Score Derivation charts so any chart whose source AHU is Off, stale, or low-confidence is desaturated + dimmed with a `StateBadge` overlay.

**Architecture:** Pure derivation hook in `frontend/src/hooks/useGreyState.ts` takes `{ operationalState, lastMeasured, confidence, isOn }` and returns `{ isGrey, reason, opacity, filter, state, lastMeasured }`. A thin presentational wrapper `GreyStateWrapper` applies the CSS treatment + overlays `StateBadge`. Consumers (`DeviceDetailCard`, `SingleDeviceChart`, `DeviceColumn`, `RawScoreRelationChart`, `ScoreCardWithSelector`) replace ad-hoc `opacity/grayscale` snippets with the hook + wrapper. Predicted Hourly Consumption (`DeltaForecastChart`) is explicitly skipped.

**Tech Stack:** React 18, TypeScript, Vite, Jest + React Testing Library, existing `StateBadge` (`frontend/src/components/shared/StateBadge.tsx`), `OperationalState` type (`frontend/src/types/index.ts:5`).

---

## File Structure

**Create:**
- `frontend/src/hooks/useGreyState.ts` — derivation hook
- `frontend/src/components/shared/GreyStateWrapper.tsx` — visual wrapper
- `frontend/src/__tests__/useGreyState.test.ts` — hook unit tests
- `frontend/src/__tests__/GreyStateWrapper.test.tsx` — wrapper render tests

**Modify:**
- `frontend/src/components/dashboard/DeviceDetailCard.tsx` — replace inline `opacity/grayscale`
- `frontend/src/components/deepdive/SingleDeviceChart.tsx` — wrap chart container
- `frontend/src/components/deepdive/DeviceColumn.tsx` — wrap per-device column
- `frontend/src/components/deepdive/CompareMode.tsx` — pass operational state per device into `DeviceColumn`
- `frontend/src/components/deepdive/DeepDiveView.tsx` — supply per-device state map to children
- `frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx` — wrap chart, accept state props
- `frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx` — propagate state down
- `frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx` — supply state to derivation panel

**Skip (explicitly):** `frontend/src/components/prediction/DeltaForecastChart.tsx` (Predicted Hourly Consumption) — leaves visual treatment unchanged.

---

## Conventions used by every task

- Visual treatment constants (locked):
  - `opacity: 0.4`
  - `filter: 'grayscale(85%) saturate(0.4)'`
  - Stale threshold: `STALE_HOURS = 6`
  - Low-confidence threshold: `CONFIDENCE_MIN = 0.5`
- Trigger logic: grey if any of
  - `isOn === false` OR `operationalState === 'Off' | 'Off_Stale' | 'Inactive'`
  - `lastMeasured` older than `STALE_HOURS`
  - `confidence` defined AND `< CONFIDENCE_MIN`
- Tests run from `frontend/`: `npm test -- <pattern>`
- Type-check: `npm run build` (or `tsc --noEmit` if available)

---

### Task 1: Add `useGreyState` hook with failing tests

**Files:**
- Create: `frontend/src/hooks/useGreyState.ts`
- Test: `frontend/src/__tests__/useGreyState.test.ts`

- [ ] **Step 1: Write failing tests**

```ts
// frontend/src/__tests__/useGreyState.test.ts
import { renderHook } from '@testing-library/react';
import { useGreyState, STALE_HOURS, CONFIDENCE_MIN } from '../hooks/useGreyState';

describe('useGreyState', () => {
  test('On + fresh + high confidence → not grey', () => {
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'On', lastMeasured: new Date().toISOString(), confidence: 0.9 }),
    );
    expect(result.current.isGrey).toBe(false);
    expect(result.current.reason).toBeNull();
  });

  test('isOn=false → grey, reason=off', () => {
    const { result } = renderHook(() => useGreyState({ isOn: false }));
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('off');
  });

  test('operationalState Off_Stale → grey, reason=stale', () => {
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'Off_Stale', lastMeasured: '2020-01-01T00:00:00Z' }),
    );
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('stale');
  });

  test('lastMeasured older than STALE_HOURS → grey, reason=stale', () => {
    const old = new Date(Date.now() - (STALE_HOURS + 1) * 3600_000).toISOString();
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'On', lastMeasured: old }),
    );
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('stale');
  });

  test('confidence below CONFIDENCE_MIN → grey, reason=low_confidence', () => {
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'On', confidence: CONFIDENCE_MIN - 0.01 }),
    );
    expect(result.current.isGrey).toBe(true);
    expect(result.current.reason).toBe('low_confidence');
  });

  test('off precedence over stale + low_confidence', () => {
    const { result } = renderHook(() =>
      useGreyState({ operationalState: 'Off', confidence: 0.1, lastMeasured: '2020-01-01T00:00:00Z' }),
    );
    expect(result.current.reason).toBe('off');
  });

  test('returns visual constants when grey', () => {
    const { result } = renderHook(() => useGreyState({ isOn: false }));
    expect(result.current.opacity).toBe(0.4);
    expect(result.current.filter).toBe('grayscale(85%) saturate(0.4)');
  });

  test('returns identity treatment when not grey', () => {
    const { result } = renderHook(() => useGreyState({ operationalState: 'On' }));
    expect(result.current.opacity).toBe(1);
    expect(result.current.filter).toBe('none');
  });
});
```

- [ ] **Step 2: Run, expect fail**

Run: `cd frontend && npm test -- useGreyState`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement hook**

```ts
// frontend/src/hooks/useGreyState.ts
import { useMemo } from 'react';
import type { OperationalState } from '../types';

export const STALE_HOURS = 6;
export const CONFIDENCE_MIN = 0.5;

export type GreyReason = 'off' | 'stale' | 'low_confidence';

export interface UseGreyStateInput {
  operationalState?: OperationalState;
  lastMeasured?: string | null;
  confidence?: number;
  isOn?: boolean;
}

export interface GreyStateResult {
  isGrey: boolean;
  reason: GreyReason | null;
  opacity: number;
  filter: string;
  state: OperationalState | undefined;
  lastMeasured: string | null | undefined;
}

function isOff(input: UseGreyStateInput): boolean {
  if (input.isOn === false) return true;
  const s = input.operationalState;
  return s === 'Off' || s === 'Off_Stale' || s === 'Inactive';
}

function isStale(lastMeasured: string | null | undefined, operationalState?: OperationalState): boolean {
  if (operationalState === 'Off_Stale') return true;
  if (!lastMeasured) return false;
  const ageMs = Date.now() - new Date(lastMeasured).getTime();
  return ageMs > STALE_HOURS * 3600_000;
}

export function useGreyState(input: UseGreyStateInput): GreyStateResult {
  return useMemo(() => {
    let reason: GreyReason | null = null;
    if (isOff(input)) reason = 'off';
    else if (isStale(input.lastMeasured, input.operationalState)) reason = 'stale';
    else if (typeof input.confidence === 'number' && input.confidence < CONFIDENCE_MIN)
      reason = 'low_confidence';

    const isGrey = reason !== null;
    return {
      isGrey,
      reason,
      opacity: isGrey ? 0.4 : 1,
      filter: isGrey ? 'grayscale(85%) saturate(0.4)' : 'none',
      state: input.operationalState,
      lastMeasured: input.lastMeasured,
    };
  }, [input.operationalState, input.lastMeasured, input.confidence, input.isOn]);
}
```

- [ ] **Step 4: Run, expect pass**

Run: `cd frontend && npm test -- useGreyState`
Expected: PASS — 8 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useGreyState.ts frontend/src/__tests__/useGreyState.test.ts
git commit -m "feat: add useGreyState hook for unified off/stale/low-confidence detection"
```

---

### Task 2: Add `GreyStateWrapper` presentational component

**Files:**
- Create: `frontend/src/components/shared/GreyStateWrapper.tsx`
- Test: `frontend/src/__tests__/GreyStateWrapper.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/src/__tests__/GreyStateWrapper.test.tsx
import { render, screen } from '@testing-library/react';
import GreyStateWrapper from '../components/shared/GreyStateWrapper';

describe('GreyStateWrapper', () => {
  test('renders children at full opacity when not grey', () => {
    render(
      <GreyStateWrapper operationalState="On">
        <div data-testid="child">child</div>
      </GreyStateWrapper>,
    );
    const wrapper = screen.getByTestId('grey-state-wrapper');
    expect(wrapper.style.opacity).toBe('1');
    expect(wrapper.style.filter).toBe('none');
    expect(screen.queryByTestId('grey-state-badge')).toBeNull();
  });

  test('applies grey treatment and overlays StateBadge when off', () => {
    render(
      <GreyStateWrapper operationalState="Off" lastMeasured={null}>
        <div>child</div>
      </GreyStateWrapper>,
    );
    const wrapper = screen.getByTestId('grey-state-wrapper');
    expect(wrapper.style.opacity).toBe('0.4');
    expect(wrapper.style.filter).toContain('grayscale');
    expect(screen.getByTestId('grey-state-badge')).toBeInTheDocument();
  });

  test('badgePlacement="none" suppresses overlay even when grey', () => {
    render(
      <GreyStateWrapper operationalState="Off" badgePlacement="none">
        <div>child</div>
      </GreyStateWrapper>,
    );
    expect(screen.queryByTestId('grey-state-badge')).toBeNull();
  });
});
```

- [ ] **Step 2: Run, expect fail**

Run: `cd frontend && npm test -- GreyStateWrapper`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement wrapper**

```tsx
// frontend/src/components/shared/GreyStateWrapper.tsx
import React from 'react';
import StateBadge from './StateBadge';
import { useGreyState, UseGreyStateInput } from '../../hooks/useGreyState';

interface GreyStateWrapperProps extends UseGreyStateInput {
  children: React.ReactNode;
  badgePlacement?: 'top-right' | 'top-left' | 'none';
  className?: string;
  style?: React.CSSProperties;
}

const GreyStateWrapper: React.FC<GreyStateWrapperProps> = ({
  children,
  badgePlacement = 'top-right',
  className,
  style,
  ...stateInput
}) => {
  const grey = useGreyState(stateInput);
  const showBadge = grey.isGrey && badgePlacement !== 'none' && grey.state;

  const overlayPos: React.CSSProperties =
    badgePlacement === 'top-left' ? { top: 8, left: 8 } : { top: 8, right: 8 };

  return (
    <div
      data-testid="grey-state-wrapper"
      className={className}
      style={{
        position: 'relative',
        opacity: grey.opacity,
        filter: grey.filter,
        transition: 'opacity 200ms ease, filter 200ms ease',
        ...style,
      }}
    >
      {children}
      {showBadge && (
        <div
          data-testid="grey-state-badge"
          style={{ position: 'absolute', zIndex: 5, ...overlayPos, filter: 'none', opacity: 1 }}
        >
          <StateBadge state={grey.state!} lastMeasured={grey.lastMeasured ?? undefined} />
        </div>
      )}
    </div>
  );
};

export default GreyStateWrapper;
```

- [ ] **Step 4: Run, expect pass**

Run: `cd frontend && npm test -- GreyStateWrapper`
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/shared/GreyStateWrapper.tsx frontend/src/__tests__/GreyStateWrapper.test.tsx
git commit -m "feat: add GreyStateWrapper component combining useGreyState + StateBadge overlay"
```

---

### Task 3: Refactor `DeviceDetailCard` to use `useGreyState`

**Files:**
- Modify: `frontend/src/components/dashboard/DeviceDetailCard.tsx:32-46`

- [ ] **Step 1: Replace ad-hoc opacity/filter with hook output**

Replace the existing `opacity: isOn ? 1 : 0.45` and `filter: isOn ? 'none' : 'grayscale(80%)'` lines with values from `useGreyState`. The existing inline `StateBadge` rendered later in the card stays — do not double-overlay (this card already shows the badge in flow).

```tsx
// at top of component body, after destructuring props
const grey = useGreyState({
  operationalState: operational_state,
  lastMeasured: last_on_timestamp,
  isOn,
});
```

Replace these two style lines:

```tsx
// before
opacity: isOn ? 1 : 0.45,
filter: isOn ? 'none' : 'grayscale(80%)',
```

```tsx
// after
opacity: grey.opacity,
filter: grey.filter,
transition: 'opacity 200ms ease, filter 200ms ease',
```

Add import at top:

```tsx
import { useGreyState } from '../../hooks/useGreyState';
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Run existing tests**

Run: `cd frontend && npm test`
Expected: PASS, no regressions.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/DeviceDetailCard.tsx
git commit -m "refactor: use useGreyState in DeviceDetailCard"
```

---

### Task 4: Wrap `SingleDeviceChart` body with `GreyStateWrapper`

**Files:**
- Modify: `frontend/src/components/deepdive/SingleDeviceChart.tsx`

Component already accepts `isOn` and per-timestamp `isOnByTimestamp`. We add device-level grey only — per-point off-bands stay as-is.

- [ ] **Step 1: Add props and wrap chart container**

Add to props interface:

```tsx
operationalState?: import('../../types').OperationalState;
lastMeasured?: string | null;
confidence?: number;
```

Destructure them in the component signature (default undefined).

Add import:

```tsx
import GreyStateWrapper from '../shared/GreyStateWrapper';
```

Wrap the outermost JSX `return` element so the entire chart card greys when device is off/stale/low-confidence:

```tsx
return (
  <GreyStateWrapper
    operationalState={operationalState}
    lastMeasured={lastMeasured}
    confidence={confidence}
    isOn={isOn}
  >
    {/* existing JSX unchanged */}
  </GreyStateWrapper>
);
```

Remove the old `{!isOn && (...)}` inline label at line ~94 — `StateBadge` overlay replaces it.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/deepdive/SingleDeviceChart.tsx
git commit -m "feat: wrap SingleDeviceChart in GreyStateWrapper"
```

---

### Task 5: Pipe per-device state into Compare mode

**Files:**
- Modify: `frontend/src/components/deepdive/CompareMode.tsx`
- Modify: `frontend/src/components/deepdive/DeviceColumn.tsx`

Compare mode renders one `DeviceColumn` per device. Need a `Record<deviceId, { operational_state, last_on_timestamp }>` from caller.

- [ ] **Step 1: Extend `CompareModeProps`**

```tsx
import type { OperationalState } from '../../types';

interface CompareModeProps {
  deviceIds: string[];
  labelMap: Record<string, string>;
  timeRange: string;
  stateMap?: Record<string, { operational_state?: OperationalState; last_on_timestamp?: string | null; confidence?: number }>;
}
```

Destructure `stateMap = {}` and forward:

```tsx
<DeviceColumn
  key={id}
  deviceId={id}
  deviceLabel={labelMap[id] ?? id}
  selectedMetrics={selectedMetrics}
  timeRange={timeRange}
  colorMap={colorMap}
  operationalState={stateMap[id]?.operational_state}
  lastMeasured={stateMap[id]?.last_on_timestamp}
  confidence={stateMap[id]?.confidence}
/>
```

- [ ] **Step 2: Update `DeviceColumn`**

Add to props interface:

```tsx
operationalState?: import('../../types').OperationalState;
lastMeasured?: string | null;
confidence?: number;
```

Import + wrap return:

```tsx
import GreyStateWrapper from '../shared/GreyStateWrapper';

// in render:
return (
  <GreyStateWrapper
    operationalState={operationalState}
    lastMeasured={lastMeasured}
    confidence={confidence}
  >
    {/* existing column JSX */}
  </GreyStateWrapper>
);
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/deepdive/CompareMode.tsx frontend/src/components/deepdive/DeviceColumn.tsx
git commit -m "feat: per-device grey state in Compare mode columns"
```

---

### Task 6: Build & supply state map in `DeepDiveView`

**Files:**
- Modify: `frontend/src/components/deepdive/DeepDiveView.tsx`

The view already gets `levelDevices: DeviceInfo[]`. Extend `DeviceInfo` consumers to include operational state if available, or pull from the existing rankings data the parent already fetches.

- [ ] **Step 1: Add prop `deviceStateMap`**

```tsx
interface DeepDiveViewProps {
  levelDevices: DeviceInfo[];
  labelMap: Record<string, string>;
  timeRange: string;
  isSelectedDeviceOn?: boolean;
  healthChartData?: Array<{ timestamp?: string; is_on?: boolean; [key: string]: any }>;
  isOnByTimestamp?: Record<string, boolean>;
  deviceStateMap?: Record<
    string,
    {
      operational_state?: import('../../types').OperationalState;
      last_on_timestamp?: string | null;
      confidence?: number;
    }
  >;
}
```

Default `deviceStateMap = {}` in destructure.

- [ ] **Step 2: Forward to children**

For `SingleDeviceChart`:

```tsx
<SingleDeviceChart
  deviceId={selectedDevice as string}
  deviceLabel={labelMap[selectedDevice as string] ?? (selectedDevice as string)}
  timeRange={timeRange}
  isOn={isSelectedDeviceOn}
  healthChartData={healthChartData}
  isOnByTimestamp={isOnByTimestamp}
  operationalState={deviceStateMap[selectedDevice as string]?.operational_state}
  lastMeasured={deviceStateMap[selectedDevice as string]?.last_on_timestamp}
  confidence={deviceStateMap[selectedDevice as string]?.confidence}
/>
```

For `CompareMode`:

```tsx
<CompareMode
  deviceIds={compareDevices}
  labelMap={labelMap}
  timeRange={timeRange}
  stateMap={deviceStateMap}
/>
```

- [ ] **Step 3: Update `App.tsx` callers (lines 478, 621)**

In `frontend/src/App.tsx`, locate both `<DeepDiveView ... />` JSX uses and pass:

```tsx
deviceStateMap={Object.fromEntries(
  (rankings ?? []).map((r) => [
    r.id,
    { operational_state: r.operational_state, last_on_timestamp: r.last_on_timestamp },
  ]),
)}
```

If a different ranking variable name is used in scope, substitute it. Source = whatever array supplies the AHURankingsTable in that branch.

- [ ] **Step 4: Type-check + tests**

Run: `cd frontend && npx tsc --noEmit && npm test`
Expected: no errors, no regressions.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/DeepDiveView.tsx frontend/src/App.tsx
git commit -m "feat: thread deviceStateMap through DeepDiveView to single+compare views"
```

---

### Task 7: Wrap `RawScoreRelationChart` in grey state

**Files:**
- Modify: `frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx`

- [ ] **Step 1: Extend props + wrap return**

Add to props:

```tsx
operationalState?: import('../../../types').OperationalState;
lastMeasured?: string | null;
confidence?: number;
```

Import:

```tsx
import GreyStateWrapper from '../../shared/GreyStateWrapper';
```

Wrap outermost element of return JSX:

```tsx
<GreyStateWrapper
  operationalState={operationalState}
  lastMeasured={lastMeasured}
  confidence={confidence}
>
  {/* existing JSX */}
</GreyStateWrapper>
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/derivation/RawScoreRelationChart.tsx
git commit -m "feat: wrap RawScoreRelationChart in GreyStateWrapper"
```

---

### Task 8: Propagate state through `ScoreCardWithSelector` and `ScoreDerivationSection`

**Files:**
- Modify: `frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx`
- Modify: `frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx`

- [ ] **Step 1: Extend `ScoreCardWithSelector` props**

Add:

```tsx
operationalState?: import('../../../types').OperationalState;
lastMeasured?: string | null;
confidence?: number;
```

Forward to the rendered `RawScoreRelationChart`. If the file also renders the score card itself (numeric tile), wrap that section in `GreyStateWrapper` with `badgePlacement="none"` (avoid duplicate badge — the chart inside owns the overlay).

```tsx
import GreyStateWrapper from '../../shared/GreyStateWrapper';

<GreyStateWrapper
  operationalState={operationalState}
  lastMeasured={lastMeasured}
  confidence={confidence}
  badgePlacement="none"
>
  {/* score-card numeric tile JSX */}
</GreyStateWrapper>

<RawScoreRelationChart
  /* existing props */
  operationalState={operationalState}
  lastMeasured={lastMeasured}
  confidence={confidence}
/>
```

- [ ] **Step 2: Update `ScoreDerivationSection`**

Add the same three props to its interface, destructure with defaults, and forward to every `<ScoreCardWithSelector />` it renders. Then update the parent (likely `App.tsx` or `Dashboard` root) — search:

```bash
grep -n "ScoreDerivationSection" frontend/src --include="*.tsx" -r
```

Pass the selected device's state from the same rankings source used in Task 6:

```tsx
<ScoreDerivationSection
  /* existing props */
  operationalState={selectedRanking?.operational_state}
  lastMeasured={selectedRanking?.last_on_timestamp}
/>
```

- [ ] **Step 3: Type-check + tests**

Run: `cd frontend && npx tsc --noEmit && npm test`
Expected: no errors, no regressions.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx frontend/src/components/dashboard/derivation/ScoreDerivationSection.tsx frontend/src/App.tsx
git commit -m "feat: propagate grey state through ScoreDerivation panels"
```

---

### Task 9: Manual verification page

**Files:**
- Create: `frontend/src/pages/__greyStateDebug.tsx` (dev-only, not routed in prod)

- [ ] **Step 1: Create harness**

```tsx
// frontend/src/pages/__greyStateDebug.tsx
import React from 'react';
import GreyStateWrapper from '../components/shared/GreyStateWrapper';

const cases: Array<{ label: string; props: any }> = [
  { label: 'On / fresh', props: { operationalState: 'On', lastMeasured: new Date().toISOString() } },
  { label: 'Off', props: { operationalState: 'Off', lastMeasured: null } },
  { label: 'Off · Stale', props: { operationalState: 'Off_Stale', lastMeasured: '2020-01-01T00:00:00Z' } },
  { label: 'Inactive', props: { operationalState: 'Inactive' } },
  { label: 'Stale by age', props: { operationalState: 'On', lastMeasured: new Date(Date.now() - 12 * 3600_000).toISOString() } },
  { label: 'Low confidence', props: { operationalState: 'On', confidence: 0.2 } },
];

export default function GreyStateDebug() {
  return (
    <div style={{ padding: 24, background: '#0B0F14', color: '#E8ECF1', minHeight: '100vh' }}>
      <h1>useGreyState visual matrix</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {cases.map((c) => (
          <GreyStateWrapper key={c.label} {...c.props}>
            <div style={{ background: '#1a2234', border: '1px solid #2a3649', borderRadius: 12, padding: 24, height: 160 }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{c.label}</div>
              <div style={{ marginTop: 8, fontSize: 11, color: '#8899aa' }}>
                {JSON.stringify(c.props)}
              </div>
            </div>
          </GreyStateWrapper>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Mount temporarily for visual check**

Edit `frontend/src/App.tsx` to render `<GreyStateDebug />` at top of root return when `import.meta.env.DEV && window.location.hash === '#greydbg'`. Visit `http://localhost:3000/#greydbg`. Confirm:
- "On / fresh" cell at full color, no badge
- "Off" cell desaturated 0.4 opacity with `Off` badge top-right
- "Off · Stale" badge reads `Off · Stale` with hours-ago tooltip
- "Inactive" badge reads `Inactive`
- "Stale by age" greyed with `On` badge (state=On but stale)
- "Low confidence" greyed with `On` badge

- [ ] **Step 3: Remove harness mount, keep file under `pages/`**

Revert the temporary `App.tsx` mount. File stays for future regression checks.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/__greyStateDebug.tsx frontend/src/App.tsx
git commit -m "test: add manual verification harness for useGreyState"
```

---

### Task 10: Final sweep

- [ ] **Step 1: Confirm no leftover ad-hoc grey logic**

Run:

```bash
grep -rn "grayscale(80%)\|grayscale(70%)\|opacity: 0\.4[0-9]" frontend/src --include="*.tsx"
```

Expected: only matches inside `useGreyState.ts` / `GreyStateWrapper.tsx` (the constant), and `DeltaForecastChart.tsx` is allowed to retain its own treatment (skipped scope). Anything else → port to the hook in a follow-up step.

- [ ] **Step 2: Confirm `DeltaForecastChart` untouched**

Run:

```bash
git diff origin/main -- frontend/src/components/prediction/DeltaForecastChart.tsx
```

Expected: empty diff.

- [ ] **Step 3: Full test + build**

Run: `cd frontend && npm test && npm run build`
Expected: PASS, build succeeds.

- [ ] **Step 4: Commit (if any cleanup needed)**

```bash
git commit -am "chore: cleanup post grey-state propagation" || true
```

---

## Self-Review Notes

- Spec coverage: extract hook ✓ (Task 1), apply across Deep Dive single ✓ (Task 4,6), Compare ✓ (Task 5,6), Score Derivation panel charts ✓ (Tasks 7,8), skip Predicted Hourly ✓ (Task 10 guard), visual treatment 0.4 + desaturate + StateBadge overlay ✓ (Task 2 constants), manual verification ✓ (Task 9).
- Trigger surface uses existing `OperationalState` and `last_on_timestamp` fields already on rankings response — no backend change. `confidence` is wired as optional input; backend can populate later without further frontend churn.
- `HealthIndexChart` is intentionally not wrapped: it shows multi-AHU level data, not a single device, and already renders per-period off-bands. Greying the whole chart would hide healthy data. If single-device variant exists later, wrap then.
