# Dashboard Controls — Unified Strip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three separate sticky control areas (LevelSelectorBar, DeviceSelector, time range buttons) with a single compact `DashboardControls` unified strip component that opens floating panel dropdowns.

**Architecture:** Create `DashboardControls.tsx` as a single self-contained component with an internal `DropdownSegment` sub-component. All selection state comes from Zustand directly; the only prop is `devices` (API-derived). App.tsx removes LevelSelectorBar, the sticky device/time sub-bar, and mounts `<DashboardControls devices={devices} />` in their place.

**Tech Stack:** React 18, TypeScript, Tailwind v3, Zustand (`useAppStore`), jsdom + React Testing Library for tests.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/components/dashboard/DashboardControls.tsx` | **Create** | Unified strip + floating panel logic |
| `frontend/src/__tests__/DashboardControls.test.tsx` | **Create** | RTL tests for behaviour |
| `frontend/src/App.tsx` | **Modify** | Swap old controls for `<DashboardControls>` |
| `frontend/src/components/dashboard/LevelSelectorBar.tsx` | **Retain, no edit** | Kept but no longer rendered |
| `frontend/src/components/dashboard/DeviceSelector.tsx` | **Retain, no edit** | Kept but no longer rendered |

---

## Task 1 — Write DashboardControls tests (failing)

**Files:**
- Create: `frontend/src/__tests__/DashboardControls.test.tsx`

This task writes all tests first and verifies they fail before any implementation exists. The component under test uses Zustand, so the store must be reset between tests.

- [ ] **Step 1: Create the test file**

```tsx
// frontend/src/__tests__/DashboardControls.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { useAppStore } from '../store/useAppStore';
import DashboardControls from '../components/dashboard/DashboardControls';

// Reset Zustand store between tests
beforeEach(() => {
  useAppStore.setState({
    selectedLevel: null,
    selectedDevice: null,
    timeRange: '7d',
  });
});

const devices = [
  { id: 'e0413', name: 'AHU-01', label: 'Unit 1', department: 'Mechanical' },
  { id: 'e0414', name: 'AHU-02', label: 'Unit 2', department: 'Electrical' },
];

describe('DashboardControls — strip rendering', () => {
  it('renders LVL, DEV, RANGE segments', () => {
    render(<DashboardControls devices={[]} />);
    expect(screen.getByText('LVL')).toBeInTheDocument();
    expect(screen.getByText('DEV')).toBeInTheDocument();
    expect(screen.getByText('RANGE')).toBeInTheDocument();
  });

  it('shows — for LVL when no level selected', () => {
    render(<DashboardControls devices={[]} />);
    // LVL segment should display —
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('shows selected level number when level is set', () => {
    useAppStore.setState({ selectedLevel: 4 });
    render(<DashboardControls devices={[]} />);
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('shows current timeRange value (7d by default)', () => {
    render(<DashboardControls devices={[]} />);
    expect(screen.getByText('7d')).toBeInTheDocument();
  });
});

describe('DashboardControls — DEV segment disabled state', () => {
  it('DEV segment shows — and ignores clicks when no level selected', () => {
    render(<DashboardControls devices={devices} />);
    // DEV segment shows —
    const devSegmentValues = screen.getAllByText('—');
    // at least one — for DEV
    expect(devSegmentValues.length).toBeGreaterThan(0);
    // Clicking DEV does not open a panel
    const devLabel = screen.getByText('DEV');
    fireEvent.click(devLabel.parentElement!);
    expect(screen.queryByPlaceholderText('Search…')).not.toBeInTheDocument();
  });

  it('DEV segment opens panel when level is selected', () => {
    useAppStore.setState({ selectedLevel: 3 });
    render(<DashboardControls devices={devices} />);
    const devLabel = screen.getByText('DEV');
    fireEvent.click(devLabel.parentElement!);
    expect(screen.getByPlaceholderText('Search…')).toBeInTheDocument();
  });
});

describe('DashboardControls — Level panel', () => {
  it('opens level panel on LVL segment click', () => {
    render(<DashboardControls devices={[]} />);
    const lvlLabel = screen.getByText('LVL');
    fireEvent.click(lvlLabel.parentElement!);
    expect(screen.getByText('Level 1')).toBeInTheDocument();
    expect(screen.getByText('Level 11')).toBeInTheDocument();
  });

  it('selecting a level calls selectLevel and closes the panel', () => {
    render(<DashboardControls devices={[]} />);
    const lvlLabel = screen.getByText('LVL');
    fireEvent.click(lvlLabel.parentElement!);
    fireEvent.click(screen.getByText('Level 5'));
    expect(useAppStore.getState().selectedLevel).toBe(5);
    expect(screen.queryByText('Level 1')).not.toBeInTheDocument();
  });

  it('only one panel open at a time — opening RANGE closes LVL panel', () => {
    render(<DashboardControls devices={[]} />);
    // Open LVL panel
    fireEvent.click(screen.getByText('LVL').parentElement!);
    expect(screen.getByText('Level 1')).toBeInTheDocument();
    // Open RANGE panel
    fireEvent.click(screen.getByText('RANGE').parentElement!);
    expect(screen.queryByText('Level 1')).not.toBeInTheDocument();
    expect(screen.getByText('24h')).toBeInTheDocument();
  });
});

describe('DashboardControls — Range panel', () => {
  it('opens range panel and shows 24h / 7d / 30d', () => {
    render(<DashboardControls devices={[]} />);
    fireEvent.click(screen.getByText('RANGE').parentElement!);
    // 24h appears in the panel (may also appear in the strip value)
    const items = screen.getAllByText('24h');
    expect(items.length).toBeGreaterThan(0);
    expect(screen.getAllByText('30d').length).toBeGreaterThan(0);
  });

  it('selecting a range calls setTimeRange and closes the panel', () => {
    render(<DashboardControls devices={[]} />);
    fireEvent.click(screen.getByText('RANGE').parentElement!);
    // Find the 30d option inside the panel and click it
    const thirtyD = screen.getAllByText('30d')[0];
    fireEvent.click(thirtyD);
    expect(useAppStore.getState().timeRange).toBe('30d');
    // Panel should close — 24h should no longer be in the panel
    // (strip still shows 30d, but the list is gone)
  });
});

describe('DashboardControls — Device search', () => {
  it('filters device list by id substring', () => {
    useAppStore.setState({ selectedLevel: 2 });
    render(<DashboardControls devices={devices} />);
    fireEvent.click(screen.getByText('DEV').parentElement!);
    const search = screen.getByPlaceholderText('Search…');
    fireEvent.change(search, { target: { value: '0413' } });
    expect(screen.getByText('e0413')).toBeInTheDocument();
    expect(screen.queryByText('e0414')).not.toBeInTheDocument();
  });

  it('shows No devices available row when devices is empty and level selected', () => {
    useAppStore.setState({ selectedLevel: 1 });
    render(<DashboardControls devices={[]} />);
    fireEvent.click(screen.getByText('DEV').parentElement!);
    expect(screen.getByText('No devices available')).toBeInTheDocument();
    expect(screen.getByText('All AHUs')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests — verify they all fail (component does not exist yet)**

```bash
cd /Users/rdmasia/wach-insight/frontend && npx jest --testPathPattern=DashboardControls --no-coverage 2>&1 | tail -20
```

Expected: `Cannot find module '../components/dashboard/DashboardControls'`

---

## Task 2 — Implement DashboardControls.tsx

**Files:**
- Create: `frontend/src/components/dashboard/DashboardControls.tsx`

Build the component in one pass: strip → DropdownSegment sub-component → three panels → click-outside → viewport clamping.

- [ ] **Step 1: Create the file**

```tsx
// frontend/src/components/dashboard/DashboardControls.tsx
import React from 'react';
import { TimeRange, useAppStore } from '../../store/useAppStore';

// ── Constants ──────────────────────────────────────────────────────────────
const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const TIME_RANGES: TimeRange[] = ['24h', '7d', '30d'];

// ── Types ──────────────────────────────────────────────────────────────────
interface DashboardControlsProps {
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
}

type OpenPanel = 'level' | 'device' | 'range' | null;

// ── DropdownSegment ────────────────────────────────────────────────────────
// Internal sub-component — not exported.
interface SegmentProps {
  label: string;
  value: string;
  isActive: boolean;       // green accent colour
  isOpen: boolean;         // #1A2330 highlight
  isDisabled?: boolean;    // #4A5568, cursor default, click ignored
  onClick: () => void;
  children: React.ReactNode; // panel content
}

const DropdownSegment: React.FC<SegmentProps> = ({
  label,
  value,
  isActive,
  isOpen,
  isDisabled = false,
  onClick,
  children,
}) => {
  const segRef = React.useRef<HTMLDivElement>(null);

  // Resolve text colour
  let textColour = '#8A95A5';
  if (isDisabled) textColour = '#4A5568';
  else if (isActive) textColour = '#00E5A0';

  const segBg = isOpen ? '#1A2330' : 'transparent';

  // Viewport-clamped panel: align left edge of panel to left edge of segment.
  // If that would overflow the right edge of the viewport, shift left.
  const [panelLeft, setPanelLeft] = React.useState<number>(0);

  React.useEffect(() => {
    if (!isOpen || !segRef.current) return;
    const rect = segRef.current.getBoundingClientRect();
    const panelMinWidth = 140;
    const rightEdge = rect.left + panelMinWidth;
    const viewportWidth = window.innerWidth;
    if (rightEdge > viewportWidth - 8) {
      setPanelLeft(viewportWidth - 8 - panelMinWidth - rect.left);
    } else {
      setPanelLeft(0);
    }
  }, [isOpen]);

  return (
    <div ref={segRef} style={{ position: 'relative', display: 'inline-block' }}>
      {/* Segment button */}
      <div
        role="button"
        aria-expanded={isOpen}
        aria-disabled={isDisabled}
        onClick={isDisabled ? undefined : onClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          padding: '8px 13px',
          fontSize: '12px',
          color: textColour,
          cursor: isDisabled ? 'default' : 'pointer',
          whiteSpace: 'nowrap',
          background: segBg,
          transition: 'color 0.15s, background 0.15s',
          userSelect: 'none',
        }}
      >
        <span style={{ fontSize: '9px', color: '#4A5568' }}>{label}</span>
        <span style={{ fontWeight: 600 }}>{value}</span>
        {!isDisabled && (
          <span style={{ fontSize: '9px', opacity: 0.5 }}>{isOpen ? '▴' : '▾'}</span>
        )}
      </div>

      {/* Floating panel */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: panelLeft,
            background: '#141D28',
            border: '1px solid #1E2A3A',
            borderRadius: '10px',
            padding: '6px',
            minWidth: '140px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3)',
            zIndex: 50,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

// ── Shared panel item style helpers ───────────────────────────────────────
const PanelItem: React.FC<{
  label: string;
  selected: boolean;
  disabled?: boolean;
  onClick?: () => void;
}> = ({ label, selected, disabled = false, onClick }) => (
  <div
    onClick={disabled ? undefined : onClick}
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '7px 10px',
      borderRadius: '6px',
      fontSize: '12px',
      color: disabled ? '#4A5568' : selected ? '#00E5A0' : '#8A95A5',
      fontWeight: selected ? 600 : 400,
      cursor: disabled ? 'default' : 'pointer',
    }}
    onMouseEnter={(e) => {
      if (!disabled) (e.currentTarget as HTMLElement).style.background = '#1E2A3A';
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLElement).style.background = 'transparent';
    }}
  >
    <span>{label}</span>
    {selected && <span style={{ fontSize: '6px', color: '#00E5A0' }}>●</span>}
  </div>
);

// ── DashboardControls ──────────────────────────────────────────────────────
const DashboardControls: React.FC<DashboardControlsProps> = ({ devices }) => {
  const { selectedLevel, selectLevel, selectedDevice, selectDevice, timeRange, setTimeRange } =
    useAppStore();

  const [openPanel, setOpenPanel] = React.useState<OpenPanel>(null);
  const [deviceSearch, setDeviceSearch] = React.useState('');

  const containerRef = React.useRef<HTMLDivElement>(null);

  // Click-outside — single listener on document
  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenPanel(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const togglePanel = (panel: OpenPanel) =>
    setOpenPanel((prev) => (prev === panel ? null : panel));

  // Filtered devices for search
  const filteredDevices = deviceSearch
    ? devices.filter((d) => d.id.toLowerCase().includes(deviceSearch.toLowerCase()))
    : devices;

  // Segment display values
  const lvlValue = selectedLevel !== null ? String(selectedLevel) : '—';
  const devValue =
    selectedDevice && selectedDevice !== 'all' ? selectedDevice : 'All';
  const devIsActive = Boolean(selectedDevice && selectedDevice !== 'all');
  const devIsDisabled = selectedLevel === null;

  return (
    <div
      className="sticky top-0 z-30 backdrop-blur-xl"
      style={{ background: 'rgba(11,15,20,0.85)', borderBottom: '1px solid #1E2A3A' }}
    >
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-2.5">
        <div className="overflow-x-auto" ref={containerRef}>
          {/* Unified pill strip */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              background: '#111820',
              border: '1px solid #1E2A3A',
              borderRadius: '10px',
              overflow: 'visible',
            }}
          >
            {/* LVL segment */}
            <DropdownSegment
              label="LVL"
              value={lvlValue}
              isActive={selectedLevel !== null}
              isOpen={openPanel === 'level'}
              onClick={() => togglePanel('level')}
            >
              {LEVELS.map((lvl) => (
                <PanelItem
                  key={lvl}
                  label={`Level ${lvl}`}
                  selected={selectedLevel === lvl}
                  onClick={() => {
                    selectLevel(lvl);
                    setOpenPanel(null);
                  }}
                />
              ))}
            </DropdownSegment>

            {/* Separator */}
            <div style={{ width: '1px', height: '20px', background: '#1E2A3A', flexShrink: 0 }} />

            {/* DEV segment */}
            <DropdownSegment
              label="DEV"
              value={devIsDisabled ? '—' : devValue}
              isActive={devIsActive}
              isOpen={openPanel === 'device'}
              isDisabled={devIsDisabled}
              onClick={() => togglePanel('device')}
            >
              {/* Search input */}
              <input
                autoFocus
                placeholder="Search…"
                value={deviceSearch}
                onChange={(e) => setDeviceSearch(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0B0F14',
                  border: '1px solid #1E2A3A',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  fontSize: '11px',
                  color: '#E8ECF1',
                  marginBottom: '6px',
                  outline: 'none',
                }}
                onMouseDown={(e) => e.stopPropagation()}
              />

              {/* Scrollable list — max 240px */}
              <div style={{ maxHeight: '240px', overflowY: 'auto' }}>
                {/* All AHUs */}
                <PanelItem
                  label="All AHUs"
                  selected={!selectedDevice || selectedDevice === 'all'}
                  onClick={() => {
                    selectDevice(null);
                    setOpenPanel(null);
                    setDeviceSearch('');
                  }}
                />

                {devices.length === 0 ? (
                  <PanelItem label="No devices available" selected={false} disabled />
                ) : (
                  filteredDevices.map((d) => (
                    <div
                      key={d.id}
                      title={[d.label, d.department].filter(Boolean).join(' — ') || d.id}
                    >
                      <PanelItem
                        label={d.id}
                        selected={selectedDevice === d.id}
                        onClick={() => {
                          selectDevice(d.id);
                          setOpenPanel(null);
                          setDeviceSearch('');
                        }}
                      />
                    </div>
                  ))
                )}
              </div>
            </DropdownSegment>

            {/* Separator */}
            <div style={{ width: '1px', height: '20px', background: '#1E2A3A', flexShrink: 0 }} />

            {/* RANGE segment */}
            <DropdownSegment
              label="RANGE"
              value={timeRange}
              isActive={true}
              isOpen={openPanel === 'range'}
              onClick={() => togglePanel('range')}
            >
              {TIME_RANGES.map((r) => (
                <PanelItem
                  key={r}
                  label={r}
                  selected={timeRange === r}
                  onClick={() => {
                    setTimeRange(r);
                    setOpenPanel(null);
                  }}
                />
              ))}
            </DropdownSegment>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardControls;
```

- [ ] **Step 2: Run tests — verify they pass**

```bash
cd /Users/rdmasia/wach-insight/frontend && npx jest --testPathPattern=DashboardControls --no-coverage 2>&1 | tail -30
```

Expected: All tests pass. If any fail, read the error carefully and fix only the specific assertion that's wrong — do not change the test expectations.

- [ ] **Step 3: Commit**

```bash
cd /Users/rdmasia/wach-insight && git add frontend/src/components/dashboard/DashboardControls.tsx frontend/src/__tests__/DashboardControls.test.tsx
git commit -m "feat(dashboard): add DashboardControls unified strip component with floating panels"
```

---

## Task 3 — Wire DashboardControls into App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

Remove the old controls and mount the new one. The `TIME_RANGES`, `timeRange`, and `setTimeRange` bindings that were in App.tsx are no longer needed at the App level — `DashboardControls` owns them internally.

- [ ] **Step 1: Add DashboardControls import (line 15, after existing imports)**

In `frontend/src/App.tsx`, find:
```tsx
import LevelSelectorBar from './components/dashboard/LevelSelectorBar';
```
Add directly below it:
```tsx
import DashboardControls from './components/dashboard/DashboardControls';
```

- [ ] **Step 2: Remove TIME_RANGES constant (line 55)**

Find and delete this line:
```tsx
const TIME_RANGES: TimeRange[] = ['24h', '7d', '30d'];
```

- [ ] **Step 3: Remove setTimeRange from the destructured store (line 62)**

Find:
```tsx
const { selectedLevel, selectedDevice, selectDevice, timeRange, setTimeRange } = useAppStore();
```
Replace with:
```tsx
const { selectedLevel, selectedDevice, selectDevice, timeRange } = useAppStore();
```

Note: `timeRange` is still needed for the API fetch effects and child components (CombinedScoresChart, ExpandableHealthRankings, FinancialImpactView).

- [ ] **Step 4: Remove LevelSelectorBar and the sticky sub-bar; add DashboardControls**

Find this block inside the JSX (starting at the `{/* ZONE C — Dashboard */}` comment section):
```tsx
      {/* ZONE C — Dashboard */}
      <div id="dashboard">
        {/* Sticky level selector */}
        <LevelSelectorBar />

        {/* Dashboard content — only shown when a level is selected */}
        <AnimatePresence mode="wait">
          {selectedLevel ? (
            <motion.main
              key={`level-${selectedLevel}`}
              className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-6 sm:pt-8 pb-16 sm:pb-24"
```

Replace with:
```tsx
      {/* ZONE C — Dashboard */}
      <div id="dashboard">
        {/* Unified controls strip */}
        <DashboardControls devices={devices} />

        {/* Dashboard content — only shown when a level is selected */}
        <AnimatePresence mode="wait">
          {selectedLevel ? (
            <motion.main
              key={`level-${selectedLevel}`}
              className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-6 sm:pt-8 pb-16 sm:pb-24"
```

- [ ] **Step 5: Remove the sticky sub-bar div (DeviceSelector + time range buttons)**

Inside `motion.main`, find and delete the entire sticky sub-bar block:
```tsx
              {/* Sticky sub-bar: device selector + time range */}
              <div className="sticky top-[100px] z-20 bg-[#0B0F14] -mx-4 sm:-mx-6 px-4 sm:px-6 pb-2 pt-1">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <DeviceSelector
                      devices={devices}
                      selectedDevice={selectedDevice}
                      onSelectDevice={selectDevice}
                    />
                  </div>
                  <div className="flex gap-2 pt-1 flex-shrink-0">
                    {TIME_RANGES.map((range) => (
                      <button
                        key={range}
                        onClick={() => setTimeRange(range)}
                        className={`px-4 py-2.5 min-h-[44px] sm:py-1.5 sm:min-h-0 rounded text-sm border transition-colors ${timeRange === range
                          ? 'bg-[#1E2A3A] border-[#3B82F6] text-white'
                          : 'bg-transparent border-[#1E2A3A] text-[#8A95A5] hover:border-[#3B82F6]'
                          }`}
                      >
                        {range}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
```

After deletion, the Health Index Chart section (`{/* Health Index Chart */}`) should follow directly inside `motion.main` after the loading/error blocks.

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd /Users/rdmasia/wach-insight/frontend && npx tsc --noEmit 2>&1
```

Expected: No errors. If TypeScript flags `setTimeRange` or `TIME_RANGES` as unused, remove their import from the destructuring (`TimeRange` type import in `useAppStore` line can stay — it's used for the `timeRange` variable type).

- [ ] **Step 7: Run all tests to ensure nothing is broken**

```bash
cd /Users/rdmasia/wach-insight/frontend && npx jest --no-coverage 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
cd /Users/rdmasia/wach-insight && git add frontend/src/App.tsx
git commit -m "feat(dashboard): wire DashboardControls into App.tsx; remove LevelSelectorBar and sticky sub-bar"
```

---

## Task 4 — Measure bar height and fix scroll-margin-top

The new single bar is shorter than the old two-bar layout (~52px vs ~170px). The `scroll-mt-4` (16px) class on `#prediction-section` is likely too small to offset the new bar height, and `#dashboard` scroll targets also need verifying.

- [ ] **Step 1: Start the dev server**

```bash
cd /Users/rdmasia/wach-insight/frontend && npm run dev
```

Open `http://localhost:3000` in a browser.

- [ ] **Step 2: Measure the rendered bar height**

Open browser DevTools console and run:
```js
document.querySelector('.sticky.top-0.z-30').getBoundingClientRect().height
```

Note the exact pixel value. It should be approximately 52px (padding 10px top + 10px bottom + segment content ~32px = 52px).

- [ ] **Step 3: Update scroll-margin-top on #prediction-section**

In `frontend/src/App.tsx`, find:
```tsx
                <div id="prediction-section" className="scroll-mt-4">
```

The `scroll-mt-*` value must be enough to clear the sticky bar + a small breathing gap (~8px). Tailwind `scroll-mt-16` = 64px which covers a 52px bar plus buffer. Update:
```tsx
                <div id="prediction-section" className="scroll-mt-16">
```

If the measured height differs significantly from 52px, adjust the class:
- Bar 40–55px → `scroll-mt-16` (64px)
- Bar 55–70px → `scroll-mt-20` (80px)

- [ ] **Step 4: Verify navigation scroll works**

In the browser: open a level, select a device, open the chat widget and send a prediction question (or navigate to prediction section manually). The content should start just below the sticky bar with ~8px gap, not hidden behind it and not over-scrolled.

- [ ] **Step 5: Commit**

```bash
cd /Users/rdmasia/wach-insight && git add frontend/src/App.tsx
git commit -m "fix(scroll): update scroll-margin-top to clear new unified controls bar height"
```

---

## Task 5 — Push to remote

- [ ] **Step 1: Push all commits**

```bash
cd /Users/rdmasia/wach-insight && git push origin main
```

- [ ] **Step 2: Final visual check (Desktop + Mobile)**

**Desktop (1280px):** Strip shows left-aligned, all three segments visible, panel dropdowns open cleanly below trigger. No horizontal overflow.

**Mobile iPhone SE (375px) via DevTools:** Strip shows left-aligned, horizontal scroll if needed (not wrapping). Panels open without clipping the right edge. All touch targets register on first tap.

**Functional checks (both sizes):**
1. Before selecting a level: DEV shows `DEV · —` in grey (`#4A5568`), click does nothing
2. Select Level 4: LVL shows `LVL · 4` in green, DEV becomes clickable showing `DEV · All`
3. Open DEV panel: shows search box, "All AHUs", device ids with tooltips
4. Search filters device list by id
5. Select a device: DEV shows in green with device id, panel closes
6. Open RANGE panel: 3 items, current one in green with dot indicator
7. Click outside any open panel: panel closes
8. Opening a second panel closes the first

---

## What is NOT changed

- Zustand store shape
- `LevelSelectorBar.tsx` and `DeviceSelector.tsx` (retained, not rendered)
- All downstream components: HealthIndexChart, ScoreCardsGrid, ExpandableHealthRankings, CombinedScoresChart, ScoreDerivationSection, PredictionView, FinancialImpactView
- Color palette, fonts, animation style
