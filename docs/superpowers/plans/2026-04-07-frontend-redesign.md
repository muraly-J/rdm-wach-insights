# RDM-WACH Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the WACH Insight frontend into a dashboard-first app called RDM-WACH with a new filter hierarchy, Simple/Deep Dive modes, sortable AHU rankings table, RDM-Atlas chatbot with sidebar/fullscreen, and all-time backend range support.

**Architecture:** Phased component replacement — the existing Zustand store, chart components (HealthIndexChart, ScoreCardsGrid, CombinedScoresChart, etc.), and API client are preserved. Layout, routing, nav, and features are replaced or added. The welcome page is removed entirely; the app loads directly into the dashboard.

**Tech Stack:** React 18, TypeScript, Zustand 5, Recharts, Framer Motion, Tailwind v3, Jest + @testing-library/react, FastAPI (backend), Python

---

## File Map

### New files
- `frontend/src/utils/deviceLabel.ts` — resolves internal ID → human label
- `frontend/src/components/nav/FilterBar.tsx` — sticky filter bar (replaces SiteNavBar + DashboardControls)
- `frontend/src/components/dashboard/KPIStrip.tsx` — always-visible KPI cards
- `frontend/src/components/dashboard/ModeToggle.tsx` — Simple / Deep Dive toggle
- `frontend/src/components/dashboard/AHURankingsTable.tsx` — sortable AHU rankings table
- `frontend/src/components/dashboard/DeviceDetailCard.tsx` — single device card (replaces table when device selected)
- `frontend/src/components/deepdive/DeepDiveView.tsx` — Deep Dive mode container
- `frontend/src/components/deepdive/SingleDeviceChart.tsx` — full-width multi-metric chart
- `frontend/src/components/deepdive/CompareMode.tsx` — compare mode container (2–3 devices)
- `frontend/src/components/deepdive/DeviceColumn.tsx` — single column in compare mode
- `frontend/src/__tests__/deviceLabel.test.ts`
- `frontend/src/__tests__/AHURankingsTable.test.tsx`
- `frontend/src/__tests__/FilterBar.test.tsx`
- `frontend/src/__tests__/KPIStrip.test.tsx`

### Modified files
- `frontend/src/types/index.ts` — extend `TimeRange` to include `'all'`
- `frontend/src/store/useAppStore.ts` — add `dashboardMode`, `deepDiveSubMode`, `compareDevices`; remove `heroVisible`, `hamburgerOpen`
- `frontend/src/App.tsx` — full restructure: remove hero, wire Simple Mode, add background financial fetch
- `frontend/src/components/chat/ChatWidget.tsx` — add sidebar/fullscreen modes, rename to RDM-Atlas
- `frontend/src/components/chat/ChatWindow.tsx` — accept `mode` prop, update layout
- `frontend/src/components/chat/ChatHeader.tsx` — add expand/collapse icons
- `frontend/src/components/chat/ChatBubbleButton.tsx` — update tooltip to RDM-Atlas
- `frontend/index.html` — update `<title>` to RDM-WACH
- `frontend/src/__tests__/useAppStore.test.ts` — update for new store fields
- `backend/routes/health_scores.py` — add `'all'` to valid_ranges
- `backend/routes/measurements.py` — add `'all'` to `_RANGE_MAP`
- `backend/routes/dashboard.py` — add `'all'` to ranking + safety-flags ranges
- `backend/routes/site_summary.py` — add `'all'` range support

### Deleted files (Task 2)
- `frontend/src/components/welcome/` — entire directory (6 files)
- `frontend/src/components/financial/` — entire directory (4 files)
- `frontend/src/components/summary/` — entire directory (5 files)
- `frontend/src/components/dashboard/ExpandableHealthRankings.tsx`
- `frontend/src/components/dashboard/AHUHeatmap.tsx`
- `frontend/src/components/dashboard/HealthRankSection.tsx`
- `frontend/src/components/dashboard/SafetyFlagCard.tsx`
- `frontend/src/components/dashboard/SafetyFlagsCombinedCard.tsx`
- `frontend/src/components/nav/HamburgerMenu.tsx`
- `frontend/src/components/nav/SiteNavBar.tsx`
- `frontend/src/components/dashboard/DashboardControls.tsx`

---

## Task 1: Extend TypeScript types and Zustand store

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/store/useAppStore.ts`
- Modify: `frontend/src/__tests__/useAppStore.test.ts`

- [ ] **Step 1: Write failing store tests for new fields**

Open `frontend/src/__tests__/useAppStore.test.ts` and add at the end:

```ts
describe('useAppStore — dashboard mode', () => {
  it('dashboardMode defaults to simple', () => {
    expect(useAppStore.getState().dashboardMode).toBe('simple');
  });

  it('setDashboardMode updates dashboardMode', () => {
    useAppStore.getState().setDashboardMode('deepdive');
    expect(useAppStore.getState().dashboardMode).toBe('deepdive');
  });

  it('deepDiveSubMode defaults to single', () => {
    expect(useAppStore.getState().deepDiveSubMode).toBe('single');
  });

  it('setDeepDiveSubMode updates deepDiveSubMode', () => {
    useAppStore.getState().setDeepDiveSubMode('compare');
    expect(useAppStore.getState().deepDiveSubMode).toBe('compare');
  });

  it('compareDevices defaults to empty array', () => {
    expect(useAppStore.getState().compareDevices).toEqual([]);
  });

  it('setCompareDevices replaces the array', () => {
    useAppStore.getState().setCompareDevices(['e0101', 'e0202']);
    expect(useAppStore.getState().compareDevices).toEqual(['e0101', 'e0202']);
  });

  it('setCompareDevices enforces max 3 devices', () => {
    useAppStore.getState().setCompareDevices(['e0101', 'e0202', 'e0303', 'e0404']);
    expect(useAppStore.getState().compareDevices).toHaveLength(3);
  });
});

describe('useAppStore — timeRange all', () => {
  it('setTimeRange accepts all', () => {
    useAppStore.getState().setTimeRange('all');
    expect(useAppStore.getState().timeRange).toBe('all');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest --testPathPattern="useAppStore" --no-coverage 2>&1 | tail -20
```

Expected: FAIL — `setDashboardMode is not a function` or property undefined.

- [ ] **Step 3: Update `types/index.ts` — extend TimeRange**

In `frontend/src/types/index.ts`, the `TimeRange` type is defined in `useAppStore.ts`, not `types/index.ts`. Update the store file in the next step. No changes needed here yet.

- [ ] **Step 4: Update `useAppStore.ts`**

Replace the full file content at `frontend/src/store/useAppStore.ts`:

```ts
import { create } from 'zustand';
import { AppState, ChatMessage, DashboardData, FinancialImpact, SiteSummaryData } from '../types';

const INITIAL_BOT_MESSAGE: ChatMessage = {
  id: 'init-1',
  role: 'bot',
  content: "Hey! I'm RDM-Atlas. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?",
  timestamp: new Date(),
};

export const initialState: AppState = {
  selectedLevel: null,
  selectedDevice: null,
  chatOpen: false,
  chatMessages: [INITIAL_BOT_MESSAGE],
  dashboardData: null,
  isLoading: false,
  heroVisible: false,
};

export type TimeRange = '24h' | '7d' | '30d' | 'all';

export type DashboardMode = 'simple' | 'deepdive';
export type DeepDiveSubMode = 'single' | 'compare';

interface AppStore extends AppState {
  selectLevel: (level: number | null) => void;
  clearLevel: () => void;
  selectDevice: (deviceId: string | null) => void;

  timeRange: TimeRange;
  setTimeRange: (range: TimeRange) => void;

  toggleChat: () => void;
  openChat: () => void;
  closeChat: () => void;

  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;

  setDashboardData: (data: DashboardData | null) => void;
  setLoading: (loading: boolean) => void;

  financialImpact: FinancialImpact | null;
  setFinancialImpact: (data: FinancialImpact | null) => void;

  siteSummaryData: SiteSummaryData | null;
  setSiteSummaryData: (d: SiteSummaryData) => void;

  // Dashboard mode
  dashboardMode: DashboardMode;
  setDashboardMode: (mode: DashboardMode) => void;

  // Deep Dive sub-mode
  deepDiveSubMode: DeepDiveSubMode;
  setDeepDiveSubMode: (mode: DeepDiveSubMode) => void;

  // Compare mode devices (max 3)
  compareDevices: string[];
  setCompareDevices: (devices: string[]) => void;

  // Chat display mode
  chatMode: 'sidebar' | 'fullscreen';
  setChatMode: (mode: 'sidebar' | 'fullscreen') => void;
}

export const useAppStore = create<AppStore>((set) => ({
  ...initialState,

  timeRange: '7d',
  setTimeRange: (range) => set({ timeRange: range }),

  selectLevel: (level) => set({ selectedLevel: level, selectedDevice: null }),
  clearLevel: () => set({ selectedLevel: null, selectedDevice: null }),
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  toggleChat: () => set((state) => ({ chatOpen: !state.chatOpen })),
  openChat: () => set({ chatOpen: true }),
  closeChat: () => set({ chatOpen: false }),

  addMessage: (message) => set((state) => ({
    chatMessages: [...state.chatMessages, message],
  })),
  setMessages: (messages) => set({ chatMessages: messages }),

  setDashboardData: (data) => set({ dashboardData: data }),
  setLoading: (loading) => set({ isLoading: loading }),

  financialImpact: null,
  setFinancialImpact: (data) => set({ financialImpact: data }),

  siteSummaryData: null,
  setSiteSummaryData: (d) => set({ siteSummaryData: d }),

  dashboardMode: 'simple',
  setDashboardMode: (mode) => set({ dashboardMode: mode }),

  deepDiveSubMode: 'single',
  setDeepDiveSubMode: (mode) => set({ deepDiveSubMode: mode }),

  compareDevices: [],
  setCompareDevices: (devices) => set({ compareDevices: devices.slice(0, 3) }),

  chatMode: 'sidebar',
  setChatMode: (mode) => set({ chatMode: mode }),
}));
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd frontend && npx jest --testPathPattern="useAppStore" --no-coverage 2>&1 | tail -20
```

Expected: PASS — all tests green.

- [ ] **Step 6: Commit**

```bash
cd frontend && git add src/store/useAppStore.ts src/__tests__/useAppStore.test.ts
git commit -m "feat(store): add dashboardMode, deepDiveSubMode, compareDevices, chatMode; extend TimeRange to all"
```

---

## Task 2: Branding, cleanup, and deletion

**Files:**
- Modify: `frontend/index.html`
- Delete: welcome, financial, summary, old nav components (listed in File Map)

- [ ] **Step 1: Update page title**

In `frontend/index.html`, replace:
```html
<title>WACH Insight</title>
```
with:
```html
<title>RDM-WACH</title>
```

- [ ] **Step 2: Delete removed component directories**

```bash
rm -rf frontend/src/components/welcome
rm -rf frontend/src/components/financial
rm -rf frontend/src/components/summary
```

- [ ] **Step 3: Delete replaced dashboard/nav components**

```bash
rm frontend/src/components/dashboard/ExpandableHealthRankings.tsx
rm frontend/src/components/dashboard/AHUHeatmap.tsx
rm frontend/src/components/dashboard/HealthRankSection.tsx
rm frontend/src/components/dashboard/SafetyFlagCard.tsx
rm frontend/src/components/dashboard/SafetyFlagsCombinedCard.tsx
rm frontend/src/components/nav/HamburgerMenu.tsx
rm frontend/src/components/nav/SiteNavBar.tsx
rm frontend/src/components/dashboard/DashboardControls.tsx
```

- [ ] **Step 4: Temporarily stub App.tsx to prevent build errors**

The existing `App.tsx` imports many deleted components. Replace it with a minimal stub so the build doesn't fail during subsequent tasks:

```tsx
// frontend/src/App.tsx — temporary stub, replaced in Task 7
import { useAppStore } from './store/useAppStore';
import ChatWidget from './components/chat/ChatWidget';

function App() {
  return (
    <div className="min-h-screen bg-[#0B0F14] text-[#E8ECF1]">
      <p style={{ padding: 24, color: '#00E5A0' }}>RDM-WACH — rebuilding…</p>
      <ChatWidget />
    </div>
  );
}

export default App;
```

- [ ] **Step 5: Verify build compiles**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds with no import errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/src/App.tsx
git commit -m "feat(branding): rename to RDM-WACH, remove welcome/financial/summary/old-nav components"
```

---

## Task 3: Device label utility

**Files:**
- Create: `frontend/src/utils/deviceLabel.ts`
- Create: `frontend/src/__tests__/deviceLabel.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/__tests__/deviceLabel.test.ts`:

```ts
import { resolveDeviceLabel, buildLabelMap } from '../utils/deviceLabel';

const devices = [
  { id: 'e0101', label: 'AHU-L1-ES-01', department: 'Engineering Services', area: 'Zone A' },
  { id: 'e0202', label: 'AHU-L2-MS-01', department: 'Medical Services', area: 'Zone B' },
  { id: 'e0303', label: 'AHU-L3-01', department: '', area: '' },
];

describe('resolveDeviceLabel', () => {
  it('returns label — department when both present', () => {
    expect(resolveDeviceLabel('e0101', devices)).toBe('AHU-L1-ES-01 — Engineering Services');
  });

  it('returns label only when department is empty', () => {
    expect(resolveDeviceLabel('e0303', devices)).toBe('AHU-L3-01');
  });

  it('returns the raw id when device is not found', () => {
    expect(resolveDeviceLabel('e9999', devices)).toBe('e9999');
  });
});

describe('buildLabelMap', () => {
  it('builds a map from id to human label', () => {
    const map = buildLabelMap(devices);
    expect(map['e0101']).toBe('AHU-L1-ES-01 — Engineering Services');
    expect(map['e0202']).toBe('AHU-L2-MS-01 — Medical Services');
    expect(map['e0303']).toBe('AHU-L3-01');
  });

  it('returns empty object for empty input', () => {
    expect(buildLabelMap([])).toEqual({});
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest --testPathPattern="deviceLabel" --no-coverage 2>&1 | tail -10
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement the utility**

Create `frontend/src/utils/deviceLabel.ts`:

```ts
export interface DeviceInfo {
  id: string;
  label: string;
  department: string;
  area: string;
}

export function resolveDeviceLabel(id: string, devices: DeviceInfo[]): string {
  const device = devices.find((d) => d.id === id);
  if (!device) return id;
  return device.label && device.department
    ? `${device.label} — ${device.department}`
    : device.label || id;
}

export function buildLabelMap(devices: DeviceInfo[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const d of devices) {
    map[d.id] = resolveDeviceLabel(d.id, devices);
  }
  return map;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx jest --testPathPattern="deviceLabel" --no-coverage 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/deviceLabel.ts frontend/src/__tests__/deviceLabel.test.ts
git commit -m "feat(utils): add resolveDeviceLabel and buildLabelMap utilities"
```

---

## Task 4: FilterBar component

**Files:**
- Create: `frontend/src/components/nav/FilterBar.tsx`
- Create: `frontend/src/__tests__/FilterBar.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/__tests__/FilterBar.test.tsx`:

```tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterBar from '../components/nav/FilterBar';
import { useAppStore } from '../store/useAppStore';

beforeEach(() => {
  useAppStore.setState({
    selectedLevel: null,
    selectedDevice: null,
    timeRange: '7d',
    dashboardMode: 'simple',
    deepDiveSubMode: 'single',
    compareDevices: [],
  });
});

const devices = [
  { id: 'e0101', label: 'AHU-L1-ES-01', department: 'Engineering Services', area: '' },
  { id: 'e0202', label: 'AHU-L1-MS-01', department: 'Medical Services', area: '' },
];

describe('FilterBar', () => {
  it('renders RDM-WACH brand name', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText('RDM-WACH')).toBeInTheDocument();
  });

  it('shows All Levels when no level selected', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText(/All Levels/i)).toBeInTheDocument();
  });

  it('shows active time range highlighted', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText('7d')).toBeInTheDocument();
  });

  it('clicking a time range updates the store', () => {
    render(<FilterBar levelDevices={devices} />);
    fireEvent.click(screen.getByText('24h'));
    expect(useAppStore.getState().timeRange).toBe('24h');
  });

  it('shows All as time range option', () => {
    render(<FilterBar levelDevices={devices} />);
    expect(screen.getByText('All')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest --testPathPattern="FilterBar" --no-coverage 2>&1 | tail -10
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement FilterBar**

Create `frontend/src/components/nav/FilterBar.tsx`:

```tsx
import React from 'react';
import { useAppStore, TimeRange } from '../../store/useAppStore';
import { resolveDeviceLabel, DeviceInfo } from '../../utils/deviceLabel';

const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: 'all', label: 'All' },
];

interface FilterBarProps {
  levelDevices: DeviceInfo[];
}

type OpenPanel = 'level' | 'device' | null;

const FilterBar: React.FC<FilterBarProps> = ({ levelDevices }) => {
  const {
    selectedLevel, selectLevel, clearLevel,
    selectedDevice, selectDevice,
    timeRange, setTimeRange,
    dashboardMode, deepDiveSubMode,
    compareDevices, setCompareDevices,
  } = useAppStore();

  const [openPanel, setOpenPanel] = React.useState<OpenPanel>(null);
  const [deviceSearch, setDeviceSearch] = React.useState('');
  const containerRef = React.useRef<HTMLDivElement>(null);

  const isCompareMode = dashboardMode === 'deepdive' && deepDiveSubMode === 'compare';

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenPanel(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filteredDevices = deviceSearch
    ? levelDevices.filter((d) => {
        const label = resolveDeviceLabel(d.id, levelDevices).toLowerCase();
        return label.includes(deviceSearch.toLowerCase()) || d.id.includes(deviceSearch.toLowerCase());
      })
    : levelDevices;

  const levelLabel = selectedLevel !== null ? `Level ${selectedLevel}` : 'All Levels';

  const deviceLabel = isCompareMode
    ? compareDevices.length > 0
      ? `${compareDevices.length} device${compareDevices.length > 1 ? 's' : ''}`
      : 'Select devices'
    : selectedDevice && selectedDevice !== 'all'
      ? resolveDeviceLabel(selectedDevice, levelDevices)
      : 'All AHUs';

  const toggleCompareDevice = (id: string) => {
    if (compareDevices.includes(id)) {
      setCompareDevices(compareDevices.filter((d) => d !== id));
    } else if (compareDevices.length < 3) {
      setCompareDevices([...compareDevices, id]);
    }
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 30,
        background: 'rgba(11,15,20,0.92)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.30)',
      }}
    >
      <div
        style={{ maxWidth: 1280, margin: '0 auto' }}
        className="px-4 sm:px-6 py-2.5 flex items-center gap-4"
      >
        {/* Brand */}
        <span style={{ color: '#00E5A0', fontWeight: 700, fontSize: 13, letterSpacing: '0.08em', flexShrink: 0 }}>
          RDM-WACH
        </span>

        {/* Filter pills */}
        <div className="flex items-center gap-1 flex-1 overflow-x-auto">
          {/* Level selector */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setOpenPanel(openPanel === 'level' ? null : 'level')}
              style={{
                background: selectedLevel !== null ? 'rgba(0,229,160,0.12)' : '#1a2234',
                border: `1px solid ${selectedLevel !== null ? '#00E5A0' : '#2e3f55'}`,
                color: selectedLevel !== null ? '#00E5A0' : '#8899aa',
                borderRadius: 20,
                padding: '4px 12px',
                fontSize: 12,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              {levelLabel}
              <span style={{ fontSize: 9, opacity: 0.6 }}>{openPanel === 'level' ? '▴' : '▾'}</span>
            </button>
            {openPanel === 'level' && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 6px)', left: 0,
                background: '#141D28', border: '1px solid #2e3f55', borderRadius: 10,
                padding: 6, minWidth: 140, boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 50,
                maxHeight: 280, overflowY: 'auto',
              }}>
                <FilterItem label="All Levels" selected={selectedLevel === null} onClick={() => { clearLevel(); setOpenPanel(null); }} />
                {LEVELS.map((lvl) => (
                  <FilterItem key={lvl} label={`Level ${lvl}`} selected={selectedLevel === lvl}
                    onClick={() => { selectLevel(lvl); setOpenPanel(null); }} />
                ))}
              </div>
            )}
          </div>

          {selectedLevel !== null && (
            <>
              <span style={{ color: '#2e3f55', fontSize: 11 }}>›</span>
              {/* Device selector */}
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setOpenPanel(openPanel === 'device' ? null : 'device')}
                  style={{
                    background: (isCompareMode ? compareDevices.length > 0 : selectedDevice && selectedDevice !== 'all')
                      ? 'rgba(0,229,160,0.12)' : '#1a2234',
                    border: `1px solid ${(isCompareMode ? compareDevices.length > 0 : selectedDevice && selectedDevice !== 'all') ? '#00E5A0' : '#2e3f55'}`,
                    color: (isCompareMode ? compareDevices.length > 0 : selectedDevice && selectedDevice !== 'all') ? '#00E5A0' : '#8899aa',
                    borderRadius: 20,
                    padding: '4px 12px',
                    fontSize: 12,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    maxWidth: 220,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{deviceLabel}</span>
                  <span style={{ fontSize: 9, opacity: 0.6, flexShrink: 0 }}>{openPanel === 'device' ? '▴' : '▾'}</span>
                </button>
                {openPanel === 'device' && (
                  <div style={{
                    position: 'absolute', top: 'calc(100% + 6px)', left: 0,
                    background: '#141D28', border: '1px solid #2e3f55', borderRadius: 10,
                    padding: 6, minWidth: 200, boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 50,
                  }}>
                    <input
                      autoFocus
                      placeholder="Search…"
                      value={deviceSearch}
                      onChange={(e) => setDeviceSearch(e.target.value)}
                      onMouseDown={(e) => e.stopPropagation()}
                      style={{
                        width: '100%', background: '#1c2431', border: '1px solid #2e3f55',
                        borderRadius: 6, padding: '6px 10px', fontSize: 11, color: '#E8ECF1',
                        marginBottom: 6, outline: 'none',
                      }}
                    />
                    <div style={{ maxHeight: 240, overflowY: 'auto' }}>
                      {!isCompareMode && (
                        <FilterItem label="All AHUs" selected={!selectedDevice || selectedDevice === 'all'}
                          onClick={() => { selectDevice(null); setOpenPanel(null); setDeviceSearch(''); }} />
                      )}
                      {isCompareMode && (
                        <p style={{ fontSize: 10, color: '#556', padding: '4px 10px' }}>
                          Select up to 3 devices
                        </p>
                      )}
                      {filteredDevices.map((d) => {
                        const label = resolveDeviceLabel(d.id, levelDevices);
                        const isSelected = isCompareMode
                          ? compareDevices.includes(d.id)
                          : selectedDevice === d.id;
                        const isDisabled = isCompareMode && !isSelected && compareDevices.length >= 3;
                        return (
                          <FilterItem key={d.id} label={label} selected={isSelected} disabled={isDisabled}
                            onClick={() => {
                              if (isCompareMode) {
                                toggleCompareDevice(d.id);
                              } else {
                                selectDevice(d.id);
                                setOpenPanel(null);
                                setDeviceSearch('');
                              }
                            }} />
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Time range pills */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {TIME_RANGES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setTimeRange(value)}
              style={{
                background: timeRange === value ? '#00E5A0' : '#1a2234',
                border: `1px solid ${timeRange === value ? '#00E5A0' : '#2e3f55'}`,
                color: timeRange === value ? '#000' : '#8899aa',
                borderRadius: 20,
                padding: '4px 10px',
                fontSize: 11,
                fontWeight: timeRange === value ? 700 : 400,
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const FilterItem: React.FC<{
  label: string; selected: boolean; disabled?: boolean; onClick?: () => void;
}> = ({ label, selected, disabled = false, onClick }) => (
  <div
    onClick={disabled ? undefined : onClick}
    style={{
      padding: '7px 10px', borderRadius: 6, fontSize: 12,
      color: disabled ? '#3a4a5a' : selected ? '#00E5A0' : '#8899aa',
      fontWeight: selected ? 600 : 400,
      cursor: disabled ? 'default' : 'pointer',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    }}
    onMouseEnter={(e) => { if (!disabled) (e.currentTarget as HTMLElement).style.background = '#2e3f55'; }}
    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
  >
    <span>{label}</span>
    {selected && <span style={{ fontSize: 6, color: '#00E5A0' }}>●</span>}
  </div>
);

export default FilterBar;
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx jest --testPathPattern="FilterBar" --no-coverage 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/nav/FilterBar.tsx frontend/src/__tests__/FilterBar.test.tsx
git commit -m "feat(nav): add FilterBar with breadcrumb filter, time range pills, compare multi-select"
```

---

## Task 5: KPIStrip component

**Files:**
- Create: `frontend/src/components/dashboard/KPIStrip.tsx`
- Create: `frontend/src/__tests__/KPIStrip.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/__tests__/KPIStrip.test.tsx`:

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import KPIStrip from '../components/dashboard/KPIStrip';
import type { SiteSummaryData } from '../types';

const mockSummary: SiteSummaryData = {
  totalAHUs: 47,
  avgSiteHealth: 82.4,
  ahusInAlert: 6,
  estMonthlyCostMYR: 0,
  starAHU: { id: 'e0303', name: 'AHU-L3-ES-02', level: 3, healthScore: 97, monthlyCostMYR: 0, safetyFlags: 0 },
  criticalAHU: { id: 'e0707', name: 'AHU-L7-MS-01', level: 7, healthScore: 43, monthlyCostMYR: 0, safetyFlags: 2 },
  levelTiles: [],
  trendDeltas: [],
};

describe('KPIStrip', () => {
  it('renders site health score', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('82.4')).toBeInTheDocument();
  });

  it('renders total AHU count', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('47')).toBeInTheDocument();
  });

  it('renders in-alert count', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('renders best AHU label', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('AHU-L3-ES-02')).toBeInTheDocument();
  });

  it('renders worst AHU label', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={null} selectedDevice={null} deviceLabel={null} deviceHealth={null} />);
    expect(screen.getByText('AHU-L7-MS-01')).toBeInTheDocument();
  });

  it('shows device health when device is selected', () => {
    render(<KPIStrip summary={mockSummary} selectedLevel={1} selectedDevice="e0101" deviceLabel="AHU-L1-ES-01 — Engineering Services" deviceHealth={88} />);
    expect(screen.getByText('88')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest --testPathPattern="KPIStrip" --no-coverage 2>&1 | tail -10
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement KPIStrip**

Create `frontend/src/components/dashboard/KPIStrip.tsx`:

```tsx
import React from 'react';
import type { SiteSummaryData } from '../../types';

interface KPIStripProps {
  summary: SiteSummaryData | null;
  selectedLevel: number | null;
  selectedDevice: string | null;
  deviceLabel: string | null;   // human label when device selected
  deviceHealth: number | null;  // 0-100 health score when device selected
}

interface KPICardProps {
  label: string;
  value: string | number;
  valueColor?: string;
  small?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({ label, value, valueColor = '#E8ECF1', small = false }) => (
  <div style={{
    background: '#1a2234',
    border: '1px solid #2a3649',
    borderRadius: 10,
    padding: '10px 14px',
    flex: 1,
    minWidth: 0,
  }}>
    <div style={{ color: '#556677', fontSize: 9, fontWeight: 600, letterSpacing: '0.06em', marginBottom: 4, textTransform: 'uppercase' }}>
      {label}
    </div>
    <div style={{ color: valueColor, fontSize: small ? 11 : 20, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
      {value}
    </div>
  </div>
);

const KPIStrip: React.FC<KPIStripProps> = ({ summary, selectedLevel, selectedDevice, deviceLabel, deviceHealth }) => {
  if (!summary) {
    return (
      <div className="flex gap-3 mb-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} style={{ flex: 1, height: 60, background: '#1a2234', borderRadius: 10, animation: 'pulse 1.5s infinite' }} />
        ))}
      </div>
    );
  }

  const healthValue = selectedDevice
    ? (deviceHealth !== null ? deviceHealth.toFixed(1) : '—')
    : summary.avgSiteHealth.toFixed(1);

  const healthColor = (() => {
    const v = selectedDevice ? deviceHealth : summary.avgSiteHealth;
    if (v === null) return '#8899aa';
    if (v >= 80) return '#00E5A0';
    if (v >= 60) return '#f59e0b';
    return '#ff6b6b';
  })();

  const alertColor = summary.ahusInAlert > 0 ? '#ff6b6b' : '#00E5A0';

  return (
    <div className="flex gap-3 mb-6 flex-wrap">
      <KPICard
        label={selectedDevice ? 'AHU Health' : selectedLevel ? 'Level Health' : 'Site Health'}
        value={healthValue}
        valueColor={healthColor}
      />
      <KPICard
        label="Total AHUs"
        value={summary.totalAHUs}
      />
      <KPICard
        label="In Alert"
        value={summary.ahusInAlert}
        valueColor={alertColor}
      />
      {selectedDevice ? (
        <KPICard
          label="Device"
          value={deviceLabel ?? selectedDevice}
          small
          valueColor="#8899aa"
        />
      ) : (
        <KPICard
          label="Best AHU"
          value={summary.starAHU.name}
          small
          valueColor="#00E5A0"
        />
      )}
      {!selectedDevice && (
        <KPICard
          label="Worst AHU"
          value={summary.criticalAHU.name}
          small
          valueColor="#ff6b6b"
        />
      )}
    </div>
  );
};

export default KPIStrip;
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx jest --testPathPattern="KPIStrip" --no-coverage 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/KPIStrip.tsx frontend/src/__tests__/KPIStrip.test.tsx
git commit -m "feat(dashboard): add KPIStrip component"
```

---

## Task 6: ModeToggle component

**Files:**
- Create: `frontend/src/components/dashboard/ModeToggle.tsx`

- [ ] **Step 1: Implement ModeToggle**

Create `frontend/src/components/dashboard/ModeToggle.tsx`:

```tsx
import React from 'react';
import { useAppStore, DashboardMode } from '../../store/useAppStore';

const ModeToggle: React.FC = () => {
  const { dashboardMode, setDashboardMode } = useAppStore();

  return (
    <div style={{
      display: 'inline-flex',
      background: '#1a2234',
      border: '1px solid #2a3649',
      borderRadius: 10,
      padding: 3,
      marginBottom: 20,
    }}>
      {(['simple', 'deepdive'] as DashboardMode[]).map((mode) => {
        const isActive = dashboardMode === mode;
        const label = mode === 'simple' ? 'Simple Mode' : 'Deep Dive Mode';
        return (
          <button
            key={mode}
            onClick={() => setDashboardMode(mode)}
            style={{
              background: isActive ? '#00E5A0' : 'transparent',
              color: isActive ? '#000' : '#8899aa',
              border: 'none',
              borderRadius: 8,
              padding: '6px 16px',
              fontSize: 12,
              fontWeight: isActive ? 700 : 400,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};

export default ModeToggle;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/dashboard/ModeToggle.tsx
git commit -m "feat(dashboard): add ModeToggle component"
```

---

## Task 7: AHURankingsTable and DeviceDetailCard

**Files:**
- Create: `frontend/src/components/dashboard/AHURankingsTable.tsx`
- Create: `frontend/src/components/dashboard/DeviceDetailCard.tsx`
- Create: `frontend/src/__tests__/AHURankingsTable.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/__tests__/AHURankingsTable.test.tsx`:

```tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import AHURankingsTable from '../components/dashboard/AHURankingsTable';

const rows = [
  { id: 'e0101', label: 'AHU-L1-ES-01 — Engineering Services', level: 1, healthScore: 92, trend: 3.2, status: 'Good' as const },
  { id: 'e0707', label: 'AHU-L7-MS-01 — Medical Services', level: 7, healthScore: 43, trend: -8.1, status: 'Critical' as const },
  { id: 'e0303', label: 'AHU-L3-01', level: 3, healthScore: 71, trend: 1.0, status: 'Warning' as const },
];

describe('AHURankingsTable', () => {
  it('renders AHU human labels', () => {
    render(<AHURankingsTable rows={rows} />);
    expect(screen.getByText('AHU-L1-ES-01 — Engineering Services')).toBeInTheDocument();
  });

  it('renders health scores', () => {
    render(<AHURankingsTable rows={rows} />);
    expect(screen.getByText('92')).toBeInTheDocument();
    expect(screen.getByText('43')).toBeInTheDocument();
  });

  it('renders status badges', () => {
    render(<AHURankingsTable rows={rows} />);
    expect(screen.getByText('Good')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('sorts by health score ascending when header clicked', () => {
    render(<AHURankingsTable rows={rows} />);
    const healthHeader = screen.getByText(/Health/i);
    fireEvent.click(healthHeader);
    const cells = screen.getAllByRole('cell');
    // First data row should now be the Critical one (lowest score)
    expect(cells.some((c) => c.textContent === '43')).toBe(true);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest --testPathPattern="AHURankingsTable" --no-coverage 2>&1 | tail -10
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement AHURankingsTable**

Create `frontend/src/components/dashboard/AHURankingsTable.tsx`:

```tsx
import React from 'react';

export type AHUStatus = 'Good' | 'Warning' | 'Critical';

export interface AHURankRow {
  id: string;
  label: string;   // human label: "AHU-L1-ES-01 — Engineering Services"
  level: number;
  healthScore: number;
  trend: number;   // signed delta vs previous period
  status: AHUStatus;
}

type SortKey = 'label' | 'level' | 'healthScore' | 'trend' | 'status';
type SortDir = 'asc' | 'desc';

interface AHURankingsTableProps {
  rows: AHURankRow[];
}

const STATUS_COLOR: Record<AHUStatus, string> = {
  Good: '#00E5A0',
  Warning: '#f59e0b',
  Critical: '#ff6b6b',
};

const AHURankingsTable: React.FC<AHURankingsTableProps> = ({ rows }) => {
  const [sortKey, setSortKey] = React.useState<SortKey>('healthScore');
  const [sortDir, setSortDir] = React.useState<SortDir>('desc');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = React.useMemo(() => {
    return [...rows].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const cmp = typeof aVal === 'string'
        ? aVal.localeCompare(bVal as string)
        : (aVal as number) - (bVal as number);
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const SortHeader: React.FC<{ label: string; sortK: SortKey }> = ({ label, sortK }) => (
    <th
      onClick={() => handleSort(sortK)}
      style={{ cursor: 'pointer', userSelect: 'none', padding: '8px 12px', textAlign: 'left',
        fontSize: 10, fontWeight: 600, color: sortKey === sortK ? '#00E5A0' : '#556677',
        letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}
    >
      {label} {sortKey === sortK ? (sortDir === 'asc' ? '↑' : '↓') : ''}
    </th>
  );

  if (rows.length === 0) {
    return (
      <div style={{ padding: 24, color: '#556677', textAlign: 'center', fontSize: 13 }}>
        No AHU data available for this selection.
      </div>
    );
  }

  return (
    <div style={{ background: '#1a2234', border: '1px solid #2a3649', borderRadius: 12, overflow: 'hidden', marginBottom: 24 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #2a3649' }}>
            <SortHeader label="AHU Name" sortK="label" />
            <SortHeader label="Level" sortK="level" />
            <SortHeader label="Health" sortK="healthScore" />
            <SortHeader label="Trend" sortK="trend" />
            <SortHeader label="Status" sortK="status" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={row.id}
              style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <td style={{ padding: '10px 12px', fontSize: 12, color: '#C8D4E0' }}>{row.label}</td>
              <td style={{ padding: '10px 12px', fontSize: 12, color: '#8899aa' }}>L{row.level}</td>
              <td style={{ padding: '10px 12px' }}>
                <span style={{
                  fontSize: 14, fontWeight: 700,
                  color: row.healthScore >= 80 ? '#00E5A0' : row.healthScore >= 60 ? '#f59e0b' : '#ff6b6b',
                }}>
                  {Math.round(row.healthScore)}
                </span>
              </td>
              <td style={{ padding: '10px 12px', fontSize: 12, color: row.trend >= 0 ? '#00E5A0' : '#ff6b6b' }}>
                {row.trend >= 0 ? '↑' : '↓'} {Math.abs(row.trend).toFixed(1)}%
              </td>
              <td style={{ padding: '10px 12px' }}>
                <span style={{
                  background: `${STATUS_COLOR[row.status]}22`,
                  color: STATUS_COLOR[row.status],
                  border: `1px solid ${STATUS_COLOR[row.status]}55`,
                  borderRadius: 20,
                  padding: '2px 8px',
                  fontSize: 10,
                  fontWeight: 600,
                }}>
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AHURankingsTable;
```

- [ ] **Step 4: Implement DeviceDetailCard**

Create `frontend/src/components/dashboard/DeviceDetailCard.tsx`:

```tsx
import React from 'react';
import type { AHUStatus } from './AHURankingsTable';

interface DeviceDetailCardProps {
  label: string;       // "AHU-L1-ES-01 — Engineering Services"
  level: number;
  healthScore: number;
  trend: number;
  status: AHUStatus;
}

const STATUS_COLOR: Record<AHUStatus, string> = {
  Good: '#00E5A0',
  Warning: '#f59e0b',
  Critical: '#ff6b6b',
};

const DeviceDetailCard: React.FC<DeviceDetailCardProps> = ({ label, level, healthScore, trend, status }) => (
  <div style={{
    background: '#1a2234', border: `1px solid ${STATUS_COLOR[status]}44`,
    borderRadius: 12, padding: '16px 20px', marginBottom: 24,
    display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap',
  }}>
    <div style={{ flex: 1, minWidth: 200 }}>
      <div style={{ fontSize: 10, color: '#556677', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
        Selected Device — Level {level}
      </div>
      <div style={{ fontSize: 14, color: '#E8ECF1', fontWeight: 600 }}>{label}</div>
    </div>
    <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 10, color: '#556677', marginBottom: 2 }}>HEALTH</div>
        <div style={{ fontSize: 24, fontWeight: 700, color: STATUS_COLOR[status] }}>{Math.round(healthScore)}</div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 10, color: '#556677', marginBottom: 2 }}>TREND</div>
        <div style={{ fontSize: 14, fontWeight: 600, color: trend >= 0 ? '#00E5A0' : '#ff6b6b' }}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
        </div>
      </div>
      <span style={{
        background: `${STATUS_COLOR[status]}22`, color: STATUS_COLOR[status],
        border: `1px solid ${STATUS_COLOR[status]}55`,
        borderRadius: 20, padding: '4px 12px', fontSize: 11, fontWeight: 600,
      }}>
        {status}
      </span>
    </div>
  </div>
);

export default DeviceDetailCard;
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd frontend && npx jest --testPathPattern="AHURankingsTable" --no-coverage 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dashboard/AHURankingsTable.tsx \
        frontend/src/components/dashboard/DeviceDetailCard.tsx \
        frontend/src/__tests__/AHURankingsTable.test.tsx
git commit -m "feat(dashboard): add AHURankingsTable and DeviceDetailCard components"
```

---

## Task 8: Restructure App.tsx — Simple Mode

**Files:**
- Modify: `frontend/src/App.tsx`

This is the core wiring task. App.tsx becomes the layout shell: FilterBar + KPIStrip + ModeToggle + Simple or Deep Dive content.

- [ ] **Step 1: Implement restructured App.tsx**

Replace `frontend/src/App.tsx` with:

```tsx
import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { formatTickByRange } from './utils/formatTick';
import { buildLabelMap } from './utils/deviceLabel';

// Nav
import FilterBar from './components/nav/FilterBar';

// Dashboard
import KPIStrip from './components/dashboard/KPIStrip';
import ModeToggle from './components/dashboard/ModeToggle';
import AHURankingsTable, { AHURankRow, AHUStatus } from './components/dashboard/AHURankingsTable';
import DeviceDetailCard from './components/dashboard/DeviceDetailCard';
import HealthIndexChart from './components/dashboard/HealthIndexChart';
import ScoreCardsGrid from './components/dashboard/ScoreCardsGrid';
import CombinedScoresChart from './components/dashboard/CombinedScoresChart';

// Deep Dive (lazy)
const DeepDiveView = React.lazy(() => import('./components/deepdive/DeepDiveView'));

// Score Derivation (lazy, device-only)
const ScoreDerivationSection = React.lazy(
  () => import('./components/dashboard/derivation/ScoreDerivationSection')
);

// Prediction (lazy, device-only)
const PredictionView = React.lazy(() => import('./components/prediction/PredictionView'));

// Chat
import ChatWidget from './components/chat/ChatWidget';

// State
import { useAppStore } from './store/useAppStore';

// API
import {
  fetchHealthIndex, fetchLevelDevices, fetchRawScoreRelationship,
  fetchScoreBreakdown, fetchSiteSummary, fetchDashboardRanking,
} from './api/client';
import { fetchFinancialImpact } from './api/financial';
import type { HealthIndexResponse, RawScoreResponse, ScoresResponse } from './types';

interface ScoreEntry {
  current: number;
  trend: number;
  data: Array<{ timestamp: string; value: number }>;
}

function getStatus(score: number): AHUStatus {
  if (score >= 80) return 'Good';
  if (score >= 60) return 'Warning';
  return 'Critical';
}

function App() {
  const {
    selectedLevel, selectedDevice, timeRange,
    setSiteSummaryData, siteSummaryData,
    dashboardMode,
    setFinancialImpact,
  } = useAppStore();

  const [healthData, setHealthData] = React.useState<HealthIndexResponse | null>(null);
  const [scoresData, setScoresData] = React.useState<ScoresResponse | null>(null);
  const [rawData, setRawData] = React.useState<RawScoreResponse | null>(null);
  const [rankingRows, setRankingRows] = React.useState<AHURankRow[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [levelDevices, setLevelDevices] = React.useState<
    Array<{ id: string; label: string; department: string; area: string }>
  >([]);

  // Fetch level devices when level changes
  React.useEffect(() => {
    if (!selectedLevel) { setLevelDevices([]); return; }
    fetchLevelDevices(selectedLevel)
      .then((r) => setLevelDevices(r.devices))
      .catch(() => setLevelDevices([]));
  }, [selectedLevel]);

  const labelMap = React.useMemo(() => buildLabelMap(levelDevices), [levelDevices]);

  // Fetch health + scores whenever filter changes
  React.useEffect(() => {
    if (!selectedLevel) return;
    setIsLoading(true);
    setError(null);
    const range = timeRange === 'all' ? '30d' : timeRange; // backend all-time added in Task 11
    Promise.all([
      fetchHealthIndex(selectedLevel, range as '24h' | '7d' | '30d', selectedDevice),
      fetchScoreBreakdown(selectedLevel, range as '24h' | '7d' | '30d'),
    ])
      .then(([health, scores]) => {
        setHealthData(health);
        setScoresData(scores);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [selectedLevel, selectedDevice, timeRange]);

  // Fetch raw-score relationship for single device
  React.useEffect(() => {
    if (!selectedDevice || selectedDevice === 'all') { setRawData(null); return; }
    const range = timeRange === 'all' ? '30d' : timeRange;
    fetchRawScoreRelationship(selectedDevice, range as '24h' | '7d' | '30d')
      .then((data) => setRawData(data as RawScoreResponse))
      .catch(() => setRawData(null));
  }, [selectedDevice, timeRange]);

  // Fetch site summary on mount and time range change
  React.useEffect(() => {
    const range = timeRange === 'all' ? '30d' : timeRange;
    fetchSiteSummary(range as '24h' | '7d' | '30d')
      .then((data) => setSiteSummaryData(data))
      .catch(() => {});
  }, [timeRange, setSiteSummaryData]);

  // Background financial fetch (silent, for RDM-Atlas context)
  React.useEffect(() => {
    if (!selectedLevel) return;
    const range = (timeRange === 'all' || timeRange === '7d') ? '30d' : timeRange as '24h' | '30d';
    fetchFinancialImpact(selectedLevel, range, selectedDevice !== 'all' ? selectedDevice : null)
      .then((data) => setFinancialImpact(data))
      .catch(() => {});
  }, [selectedLevel, selectedDevice, timeRange, setFinancialImpact]);

  // Fetch rankings for the table
  React.useEffect(() => {
    if (!selectedLevel) { setRankingRows([]); return; }
    const rangeMap: Record<string, 'last_24h' | 'last_7d' | 'last_30d'> = {
      '24h': 'last_24h', '7d': 'last_7d', '30d': 'last_30d', 'all': 'last_30d',
    };
    const apiRange = rangeMap[timeRange] ?? 'last_7d';
    fetchDashboardRanking(selectedLevel, apiRange)
      .then((data: any) => {
        const allDevices = [...(data.best ?? []), ...(data.worst ?? [])];
        const seen = new Set<string>();
        const rows: AHURankRow[] = allDevices
          .filter((d: any) => { if (seen.has(d.ahu_id)) return false; seen.add(d.ahu_id); return true; })
          .map((d: any) => ({
            id: d.ahu_id,
            label: labelMap[d.ahu_id] ?? d.ahu_id,
            level: selectedLevel,
            healthScore: d.index,
            trend: d.trend ?? 0,
            status: getStatus(d.index),
          }));
        setRankingRows(rows);
      })
      .catch(() => setRankingRows([]));
  }, [selectedLevel, timeRange, labelMap]);

  // Health chart data
  const healthChartData = React.useMemo(() => {
    if (!healthData?.devices?.length) return [];
    const series = selectedDevice && selectedDevice !== 'all'
      ? healthData.devices.filter((d) => d.id === selectedDevice)
      : healthData.devices;
    const refData = series[0]?.data ?? [];
    return refData.map((point, idx) => {
      const timestamp = formatTickByRange(point.timestamp, timeRange === 'all' ? '30d' : timeRange);
      const entry: Record<string, any> = { timestamp };
      series.forEach(({ id, data }) => {
        entry[labelMap[id] ?? id] = data[idx]?.value ?? null;
      });
      return entry;
    });
  }, [healthData, selectedDevice, timeRange, labelMap]);

  const chartDevices = React.useMemo(() => {
    if (selectedDevice && selectedDevice !== 'all') {
      return levelDevices
        .filter((d) => d.id === selectedDevice)
        .map((d) => ({ id: d.id, name: labelMap[d.id] ?? d.id, label: d.label, department: d.department, level: selectedLevel! }));
    }
    return levelDevices.map((d) => ({
      id: d.id, name: labelMap[d.id] ?? d.id,
      label: d.label, department: d.department, level: selectedLevel!,
    }));
  }, [levelDevices, selectedDevice, labelMap, selectedLevel]);

  const scoreCardData = React.useMemo<Record<string, ScoreEntry>>(() => {
    if (!scoresData?.devices?.length) return {};
    const scoreNames = ['energy_anomaly', 'pf_degradation', 'phase_imbalance', 'thd_drift', 'overload'] as const;
    const relevantDevices = selectedDevice && selectedDevice !== 'all'
      ? scoresData.devices.filter((d) => d.id === selectedDevice)
      : scoresData.devices;
    if (relevantDevices.length === 0) return {};
    const result: Record<string, ScoreEntry> = {};
    scoreNames.forEach((name) => {
      const allScores = relevantDevices.map((d) => d.scores[name]).filter(Boolean);
      if (allScores.length === 0) return;
      const count = allScores.length;
      const avgCurrent = allScores.reduce((s, v) => s + v.current, 0) / count;
      const avgTrend = allScores.reduce((s, v) => s + v.trend, 0) / count;
      const pointCount = allScores[0]?.data.length ?? 0;
      const avgData = Array.from({ length: pointCount }, (_, i) => ({
        timestamp: allScores[0]?.data[i]?.timestamp ?? '',
        value: allScores.reduce((s, v) => s + (v.data[i]?.value ?? 0), 0) / count,
      }));
      result[name] = { current: avgCurrent, trend: avgTrend, data: avgData };
    });
    return result;
  }, [scoresData, selectedDevice]);

  // Current device health for KPI strip
  const deviceHealth = React.useMemo(() => {
    if (!selectedDevice || selectedDevice === 'all' || !healthData) return null;
    const dev = healthData.devices.find((d) => d.id === selectedDevice);
    if (!dev?.data?.length) return null;
    return dev.data[dev.data.length - 1]?.value ?? null;
  }, [healthData, selectedDevice]);

  const deviceLabel = selectedDevice ? (labelMap[selectedDevice] ?? selectedDevice) : null;

  const showDerivation = Boolean(selectedDevice && selectedDevice !== 'all');

  // Selected device ranking row (for DeviceDetailCard)
  const selectedDeviceRow = rankingRows.find((r) => r.id === selectedDevice);

  return (
    <div className="min-h-screen bg-[#0B0F14] text-[#E8ECF1]">
      <FilterBar levelDevices={levelDevices} />

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-6 pb-16">
        {/* KPI Strip — always visible */}
        <KPIStrip
          summary={siteSummaryData}
          selectedLevel={selectedLevel}
          selectedDevice={selectedDevice}
          deviceLabel={deviceLabel}
          deviceHealth={deviceHealth}
        />

        {/* Mode toggle */}
        <ModeToggle />

        {/* Loading / error */}
        {isLoading && (
          <div className="flex justify-center py-4">
            <span className="text-[#556677] text-sm animate-pulse">Loading data…</span>
          </div>
        )}
        {error && !isLoading && (
          <div className="mb-4 px-4 py-3 rounded bg-red-900/20 border border-red-700 text-red-400 text-sm">
            Failed to load data: {error}
          </div>
        )}

        {/* Content */}
        <AnimatePresence mode="wait">
          {dashboardMode === 'simple' ? (
            <motion.div
              key="simple"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              {selectedLevel ? (
                <>
                  {/* Health Index Chart */}
                  <div className="mb-8">
                    <HealthIndexChart data={healthChartData as any} devices={chartDevices} />
                  </div>

                  {/* Score Cards */}
                  <ScoreCardsGrid scoreData={scoreCardData} />

                  {/* Combined Scores Chart */}
                  <CombinedScoresChart scoreData={scoreCardData} timeRange={timeRange === 'all' ? '30d' : timeRange} />

                  {/* Rankings table or Device detail card */}
                  {selectedDevice && selectedDevice !== 'all' && selectedDeviceRow ? (
                    <DeviceDetailCard
                      label={selectedDeviceRow.label}
                      level={selectedDeviceRow.level}
                      healthScore={selectedDeviceRow.healthScore}
                      trend={selectedDeviceRow.trend}
                      status={selectedDeviceRow.status}
                    />
                  ) : (
                    <AHURankingsTable rows={rankingRows} />
                  )}

                  {/* Score Derivation (device only) */}
                  {showDerivation && rawData && (
                    <React.Suspense fallback={<div className="card p-6 h-40 flex items-center justify-center"><span className="text-[#556677]">Loading derivation…</span></div>}>
                      <ScoreDerivationSection
                        deviceName={deviceLabel ?? selectedDevice ?? ''}
                        deviceId={selectedDevice ?? ''}
                        rawData={rawData.scores}
                        timeRange={timeRange === 'all' ? '30d' : timeRange}
                      />
                    </React.Suspense>
                  )}

                  {/* Prediction (device only) */}
                  {selectedDevice && selectedDevice !== 'all' && (
                    <div className="mt-8">
                      <React.Suspense fallback={<div className="h-48 animate-pulse bg-[#2e3f55] rounded-xl" />}>
                        <PredictionView deviceId={selectedDevice} />
                      </React.Suspense>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center justify-center h-48 text-[#556677]">
                  Select a level to view dashboard data.
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="deepdive"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              <React.Suspense fallback={<div className="h-64 animate-pulse bg-[#1a2234] rounded-xl" />}>
                <DeepDiveView levelDevices={levelDevices} labelMap={labelMap} timeRange={timeRange} />
              </React.Suspense>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer disclaimer */}
        <p className="text-center text-xs mt-12 pb-4" style={{ color: '#3a4a5a' }}>
          ⚠ Data shown covers monitored AHUs only. Not all devices may be represented.
        </p>
      </div>

      <ChatWidget />
    </div>
  );
}

export default App;
```

- [ ] **Step 2: Verify build compiles**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds (DeepDiveView import will fail until Task 9 — add a temporary stub if needed).

- [ ] **Step 3: Create temporary DeepDiveView stub** (if build fails on missing module)

```bash
mkdir -p frontend/src/components/deepdive
cat > frontend/src/components/deepdive/DeepDiveView.tsx << 'EOF'
import React from 'react';
const DeepDiveView: React.FC<any> = () => (
  <div style={{ padding: 24, color: '#556677' }}>Deep Dive — coming in next task</div>
);
export default DeepDiveView;
EOF
```

- [ ] **Step 4: Verify build compiles with stub**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/deepdive/DeepDiveView.tsx
git commit -m "feat(app): restructure App.tsx for Simple Mode with FilterBar, KPIStrip, ModeToggle, AHURankingsTable"
```

---

## Task 9: Deep Dive Mode — Single Device and Compare Mode

**Files:**
- Create: `frontend/src/components/deepdive/DeepDiveView.tsx` (replaces stub)
- Create: `frontend/src/components/deepdive/SingleDeviceChart.tsx`
- Create: `frontend/src/components/deepdive/CompareMode.tsx`
- Create: `frontend/src/components/deepdive/DeviceColumn.tsx`

- [ ] **Step 1: Implement DeepDiveSubModeToggle sub-component and DeepDiveView**

Create `frontend/src/components/deepdive/DeepDiveView.tsx`:

```tsx
import React from 'react';
import { useAppStore, DeepDiveSubMode } from '../../store/useAppStore';
import { DeviceInfo } from '../../utils/deviceLabel';
import SingleDeviceChart from './SingleDeviceChart';
import CompareMode from './CompareMode';

interface DeepDiveViewProps {
  levelDevices: DeviceInfo[];
  labelMap: Record<string, string>;
  timeRange: string;
}

const DeepDiveView: React.FC<DeepDiveViewProps> = ({ levelDevices, labelMap, timeRange }) => {
  const { selectedDevice, selectedLevel, deepDiveSubMode, setDeepDiveSubMode, compareDevices } = useAppStore();

  const hasDevice = Boolean(selectedDevice && selectedDevice !== 'all');
  const hasCompareDevices = compareDevices.length >= 2;

  return (
    <div>
      {/* Sub-mode toggle */}
      <div style={{ display: 'inline-flex', background: '#1a2234', border: '1px solid #2a3649', borderRadius: 10, padding: 3, marginBottom: 20 }}>
        {(['single', 'compare'] as DeepDiveSubMode[]).map((mode) => {
          const isActive = deepDiveSubMode === mode;
          return (
            <button
              key={mode}
              onClick={() => setDeepDiveSubMode(mode)}
              style={{
                background: isActive ? 'rgba(0,229,160,0.15)' : 'transparent',
                color: isActive ? '#00E5A0' : '#8899aa',
                border: isActive ? '1px solid #00E5A044' : '1px solid transparent',
                borderRadius: 8, padding: '5px 14px', fontSize: 12,
                fontWeight: isActive ? 600 : 400, cursor: 'pointer',
              }}
            >
              {mode === 'single' ? 'Single Device' : 'Compare Mode'}
            </button>
          );
        })}
      </div>

      {deepDiveSubMode === 'single' ? (
        hasDevice ? (
          <SingleDeviceChart
            deviceId={selectedDevice!}
            deviceLabel={labelMap[selectedDevice!] ?? selectedDevice!}
            timeRange={timeRange}
          />
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: '#556677', fontSize: 13 }}>
            Select a device to begin deep dive analysis.
          </div>
        )
      ) : (
        hasCompareDevices ? (
          <CompareMode
            deviceIds={compareDevices}
            labelMap={labelMap}
            timeRange={timeRange}
          />
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: '#556677', fontSize: 13 }}>
            Select 2–3 devices using the Device filter above to compare them.
          </div>
        )
      )}
    </div>
  );
};

export default DeepDiveView;
```

- [ ] **Step 2: Implement SingleDeviceChart**

Create `frontend/src/components/deepdive/SingleDeviceChart.tsx`:

```tsx
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { fetchMeasurements } from '../../api/client';
import { SCORE_METRIC_GROUPS, METRIC_META } from '../../constants/metricGroups';

interface SingleDeviceChartProps {
  deviceId: string;
  deviceLabel: string;
  timeRange: string;
}

const CHART_COLORS = ['#00E5A0', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#EF4444'];

const SingleDeviceChart: React.FC<SingleDeviceChartProps> = ({ deviceId, deviceLabel, timeRange }) => {
  const [selectedMetrics, setSelectedMetrics] = React.useState<string[]>(['power_total', 'power_factor_avg']);
  const [chartData, setChartData] = React.useState<Record<string, any>[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [groupOpen, setGroupOpen] = React.useState<string | null>(null);

  const apiRange = (timeRange === 'all' ? '30d' : timeRange) as '24h' | '7d' | '30d';

  React.useEffect(() => {
    if (selectedMetrics.length === 0 || !deviceId) return;
    setIsLoading(true);
    fetchMeasurements(deviceId, selectedMetrics, apiRange)
      .then((res) => {
        const firstMetric = selectedMetrics[0];
        const points = res.measurements[firstMetric] ?? [];
        const data = points.map((p, i) => {
          const entry: Record<string, any> = { timestamp: p.timestamp };
          selectedMetrics.forEach((m) => {
            entry[m] = res.measurements[m]?.[i]?.value ?? null;
          });
          return entry;
        });
        setChartData(data);
      })
      .catch(() => setChartData([]))
      .finally(() => setIsLoading(false));
  }, [deviceId, selectedMetrics, apiRange]);

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: '#8899aa' }}>Metrics for</span>
        <span style={{ fontSize: 13, color: '#00E5A0', fontWeight: 600 }}>{deviceLabel}</span>
      </div>

      {/* Metric selector grouped by category */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {SCORE_METRIC_GROUPS.map((group) => (
          <div key={group.scoreKey} style={{ position: 'relative' }}>
            <button
              onClick={() => setGroupOpen(groupOpen === group.scoreKey ? null : group.scoreKey)}
              style={{
                background: '#1a2234', border: '1px solid #2a3649', borderRadius: 8,
                padding: '5px 10px', fontSize: 11, color: '#8899aa', cursor: 'pointer',
              }}
            >
              {group.scoreLabel} ▾
            </button>
            {groupOpen === group.scoreKey && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 4px)', left: 0, zIndex: 20,
                background: '#141D28', border: '1px solid #2a3649', borderRadius: 8,
                padding: 6, minWidth: 180, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
              }}>
                {group.availableMetrics.map((m) => (
                  <div
                    key={m.key}
                    onClick={() => toggleMetric(m.key)}
                    style={{
                      padding: '5px 8px', borderRadius: 5, cursor: 'pointer', fontSize: 11,
                      color: selectedMetrics.includes(m.key) ? '#00E5A0' : '#8899aa',
                      display: 'flex', alignItems: 'center', gap: 6,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#2a3649')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                      background: selectedMetrics.includes(m.key) ? '#00E5A0' : '#2a3649',
                      border: '1px solid #2a3649',
                    }} />
                    {m.label}
                    <span style={{ marginLeft: 'auto', fontSize: 9, color: '#445566' }}>{m.unit}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Chart */}
      <div style={{ background: '#1a2234', border: '1px solid #2a3649', borderRadius: 12, padding: 16 }}>
        {isLoading ? (
          <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#556677' }}>
            Loading data…
          </div>
        ) : chartData.length === 0 ? (
          <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#556677' }}>
            No data for selected metrics.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3649" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: '#556677' }} />
              <YAxis tick={{ fontSize: 10, fill: '#556677' }} />
              <Tooltip
                contentStyle={{ background: '#141D28', border: '1px solid #2a3649', borderRadius: 8, fontSize: 11 }}
                labelStyle={{ color: '#8899aa' }}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: '#8899aa' }} />
              {selectedMetrics.map((metricKey, i) => (
                <Line
                  key={metricKey}
                  type="monotone"
                  dataKey={metricKey}
                  name={METRIC_META[metricKey]?.label ?? metricKey}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  dot={false}
                  strokeWidth={1.5}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default SingleDeviceChart;
```

- [ ] **Step 3: Implement DeviceColumn**

Create `frontend/src/components/deepdive/DeviceColumn.tsx`:

```tsx
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchMeasurements } from '../../api/client';
import { METRIC_META } from '../../constants/metricGroups';

interface DeviceColumnProps {
  deviceId: string;
  deviceLabel: string;
  selectedMetrics: string[];
  timeRange: string;
  colorMap: Record<string, string>;
}

const DeviceColumn: React.FC<DeviceColumnProps> = ({ deviceId, deviceLabel, selectedMetrics, timeRange, colorMap }) => {
  const [chartData, setChartData] = React.useState<Record<string, any>[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);

  const apiRange = (timeRange === 'all' ? '30d' : timeRange) as '24h' | '7d' | '30d';

  React.useEffect(() => {
    if (selectedMetrics.length === 0 || !deviceId) return;
    setIsLoading(true);
    fetchMeasurements(deviceId, selectedMetrics, apiRange)
      .then((res) => {
        const firstMetric = selectedMetrics[0];
        const points = res.measurements[firstMetric] ?? [];
        const data = points.map((p, i) => {
          const entry: Record<string, any> = { timestamp: p.timestamp };
          selectedMetrics.forEach((m) => {
            entry[m] = res.measurements[m]?.[i]?.value ?? null;
          });
          return entry;
        });
        setChartData(data);
      })
      .catch(() => setChartData([]))
      .finally(() => setIsLoading(false));
  }, [deviceId, selectedMetrics, apiRange]);

  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{
        background: '#1a2234', border: '1px solid #2a3649', borderRadius: 10,
        padding: '10px 14px', marginBottom: 8,
      }}>
        <div style={{ fontSize: 10, color: '#556677', marginBottom: 2 }}>Device</div>
        <div style={{ fontSize: 12, color: '#00E5A0', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {deviceLabel}
        </div>
      </div>
      <div style={{ background: '#1a2234', border: '1px solid #2a3649', borderRadius: 10, padding: 12 }}>
        {isLoading ? (
          <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#556677', fontSize: 12 }}>
            Loading…
          </div>
        ) : chartData.length === 0 ? (
          <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#556677', fontSize: 12 }}>
            No data.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3649" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 9, fill: '#556677' }} />
              <YAxis tick={{ fontSize: 9, fill: '#556677' }} width={36} />
              <Tooltip
                contentStyle={{ background: '#141D28', border: '1px solid #2a3649', borderRadius: 6, fontSize: 10 }}
              />
              {selectedMetrics.map((metricKey) => (
                <Line
                  key={metricKey}
                  type="monotone"
                  dataKey={metricKey}
                  name={METRIC_META[metricKey]?.label ?? metricKey}
                  stroke={colorMap[metricKey] ?? '#00E5A0'}
                  dot={false}
                  strokeWidth={1.5}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default DeviceColumn;
```

- [ ] **Step 4: Implement CompareMode**

Create `frontend/src/components/deepdive/CompareMode.tsx`:

```tsx
import React from 'react';
import { SCORE_METRIC_GROUPS } from '../../constants/metricGroups';
import DeviceColumn from './DeviceColumn';

interface CompareModeProps {
  deviceIds: string[];      // 2 or 3 device IDs
  labelMap: Record<string, string>;
  timeRange: string;
}

const CHART_COLORS = ['#00E5A0', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];

const CompareMode: React.FC<CompareModeProps> = ({ deviceIds, labelMap, timeRange }) => {
  const [selectedMetrics, setSelectedMetrics] = React.useState<string[]>(['power_total', 'power_factor_avg']);
  const [groupOpen, setGroupOpen] = React.useState<string | null>(null);

  const colorMap = React.useMemo(() => {
    const map: Record<string, string> = {};
    selectedMetrics.forEach((m, i) => { map[m] = CHART_COLORS[i % CHART_COLORS.length]; });
    return map;
  }, [selectedMetrics]);

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  return (
    <div>
      {/* Shared metric selector */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, color: '#556677', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Shared Metrics
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {SCORE_METRIC_GROUPS.map((group) => (
            <div key={group.scoreKey} style={{ position: 'relative' }}>
              <button
                onClick={() => setGroupOpen(groupOpen === group.scoreKey ? null : group.scoreKey)}
                style={{
                  background: '#1a2234', border: '1px solid #2a3649', borderRadius: 8,
                  padding: '5px 10px', fontSize: 11, color: '#8899aa', cursor: 'pointer',
                }}
              >
                {group.scoreLabel} ▾
              </button>
              {groupOpen === group.scoreKey && (
                <div style={{
                  position: 'absolute', top: 'calc(100% + 4px)', left: 0, zIndex: 20,
                  background: '#141D28', border: '1px solid #2a3649', borderRadius: 8,
                  padding: 6, minWidth: 180, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                }}>
                  {group.availableMetrics.map((m) => (
                    <div
                      key={m.key}
                      onClick={() => toggleMetric(m.key)}
                      style={{
                        padding: '5px 8px', borderRadius: 5, cursor: 'pointer', fontSize: 11,
                        color: selectedMetrics.includes(m.key) ? '#00E5A0' : '#8899aa',
                        display: 'flex', alignItems: 'center', gap: 6,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = '#2a3649')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <span style={{
                        width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                        background: selectedMetrics.includes(m.key) ? colorMap[m.key] ?? '#00E5A0' : '#2a3649',
                        border: '1px solid #2a3649',
                      }} />
                      {m.label}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Side-by-side columns */}
      <div style={{ display: 'flex', gap: 12 }}>
        {deviceIds.map((id) => (
          <DeviceColumn
            key={id}
            deviceId={id}
            deviceLabel={labelMap[id] ?? id}
            selectedMetrics={selectedMetrics}
            timeRange={timeRange}
            colorMap={colorMap}
          />
        ))}
      </div>
    </div>
  );
};

export default CompareMode;
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/deepdive/
git commit -m "feat(deepdive): add DeepDiveView, SingleDeviceChart, CompareMode, DeviceColumn"
```

---

## Task 10: RDM-Atlas chat — sidebar and fullscreen modes

**Files:**
- Modify: `frontend/src/components/chat/ChatWidget.tsx`
- Modify: `frontend/src/components/chat/ChatWindow.tsx`
- Modify: `frontend/src/components/chat/ChatHeader.tsx`
- Modify: `frontend/src/components/chat/ChatBubbleButton.tsx`

- [ ] **Step 1: Read current ChatWindow and ChatHeader**

```bash
cat frontend/src/components/chat/ChatWindow.tsx
cat frontend/src/components/chat/ChatHeader.tsx
```

- [ ] **Step 2: Update ChatBubbleButton tooltip**

In `frontend/src/components/chat/ChatBubbleButton.tsx`, replace any text or aria-label containing "WACH AI" with "RDM-Atlas".

Open the file, find `"Chat with WACH AI"` or similar strings, replace with `"Chat with RDM-Atlas"`.

- [ ] **Step 3: Update ChatWidget with sidebar/fullscreen mode**

Replace `frontend/src/components/chat/ChatWidget.tsx`:

```tsx
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import ChatBubbleButton from './ChatBubbleButton';
import ChatWindow from './ChatWindow';

const ChatWidget: React.FC = () => {
  const { chatOpen, openChat, closeChat, chatMode, setChatMode } = useAppStore();

  const toggleFullscreen = () => setChatMode(chatMode === 'fullscreen' ? 'sidebar' : 'fullscreen');

  return (
    <>
      {/* Fullscreen overlay */}
      <AnimatePresence>
        {chatOpen && chatMode === 'fullscreen' && (
          <motion.div
            key="chat-fullscreen"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'fixed', inset: 0, zIndex: 80,
              background: '#0B0F14',
              display: 'flex', flexDirection: 'column',
            }}
          >
            <ChatWindow
              mode="fullscreen"
              onClose={closeChat}
              onToggleMode={toggleFullscreen}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <AnimatePresence>
        {chatOpen && chatMode === 'sidebar' && (
          <motion.div
            key="chat-sidebar"
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0,
              width: 380, zIndex: 70,
              background: '#0f1923',
              borderLeft: '1px solid rgba(0,229,160,0.2)',
              boxShadow: '-8px 0 40px rgba(0,0,0,0.5)',
              display: 'flex', flexDirection: 'column',
            }}
          >
            <ChatWindow
              mode="sidebar"
              onClose={closeChat}
              onToggleMode={toggleFullscreen}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB — hidden when chat is open */}
      {!chatOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
          style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 60 }}
        >
          <ChatBubbleButton onClick={openChat} />
        </motion.div>
      )}
    </>
  );
};

export default ChatWidget;
```

- [ ] **Step 4: Update ChatHeader to accept mode and toggle**

In `frontend/src/components/chat/ChatHeader.tsx`, add props `mode: 'sidebar' | 'fullscreen'`, `onToggleMode: () => void`, and `onClose: () => void`. Replace the existing header title with "RDM-Atlas". Add expand/collapse icon button.

Read the current file first, then apply this pattern:

```tsx
interface ChatHeaderProps {
  mode: 'sidebar' | 'fullscreen';
  onClose: () => void;
  onToggleMode: () => void;
}

// In the header JSX:
// Left: "RDM-Atlas" title
// Right: expand/collapse icon + close icon
//   sidebar → show expand icon (⛶ or ↗)
//   fullscreen → show collapse icon (↙)
```

Update the title from "WACH AI" to "RDM-Atlas" in the header text.

- [ ] **Step 5: Update ChatWindow to accept mode props**

In `frontend/src/components/chat/ChatWindow.tsx`, add props `mode: 'sidebar' | 'fullscreen'`, `onToggleMode: () => void`, and pass them through to `ChatHeader`. Remove any internal `isOpen` prop if it was only used for open/close (now managed by ChatWidget via store).

- [ ] **Step 6: Verify build**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chat/
git commit -m "feat(chat): rename to RDM-Atlas, add sidebar/fullscreen toggle modes"
```

---

## Task 11: Backend — all-time range support

**Files:**
- Modify: `backend/routes/health_scores.py`
- Modify: `backend/routes/measurements.py`
- Modify: `backend/routes/dashboard.py`
- Modify: `backend/routes/site_summary.py`

- [ ] **Step 1: Update health_scores.py**

In `backend/routes/health_scores.py`, find all occurrences of:

```python
valid_ranges = ["24h", "7d", "30d"]
if time_range not in valid_ranges:
    raise HTTPException(...)
```

Replace with:

```python
valid_ranges = ["24h", "7d", "30d", "all"]
if time_range not in valid_ranges:
    raise HTTPException(
        status_code=400,
        detail=f"Time range must be one of: {', '.join(valid_ranges)}"
    )
```

For the `"all"` case, determine the start date by querying the earliest available record (or use a large lookback like `"10000d"` in InfluxDB/DuckDB terms). Find the DB query function being called (e.g. `get_score_breakdown`, `get_health_index_series`) and check how `time_range` is passed to it. Add a branch:

```python
db_range = time_range if time_range != "all" else "all"
```

Then in each underlying DB reader function that builds a date filter, handle `"all"` as "no start date filter":

```python
if time_range == "all":
    # no start date constraint — return full history
    where_clause = ""  # or remove the date filter entirely
else:
    # existing logic: map "24h" -> last 1 day, "7d" -> last 7 days, "30d" -> last 30 days
    ...
```

The exact implementation depends on how the DB functions build their queries. Search for where `time_range` is used in `backend/db_reader.py` or equivalent, and add the `"all"` branch there.

- [ ] **Step 2: Update measurements.py**

In `backend/routes/measurements.py`, find `_RANGE_MAP`:

```python
_RANGE_MAP = {
    "24h": "last_24h",
    "7d":  "last_7d",
    "30d": "last_30d",
}
```

Add the all-time entry:

```python
_RANGE_MAP = {
    "24h": "last_24h",
    "7d":  "last_7d",
    "30d": "last_30d",
    "all": "all",
}
```

Then in the validation block:

```python
if range not in _RANGE_MAP:
    raise HTTPException(status_code=400, detail=f"range must be one of: {list(_RANGE_MAP)}")
```

And in the query call, handle `influx_range == "all"` by passing no start-time filter to `fetch_time_series` (or a sentinel that the function recognises as "all history").

- [ ] **Step 3: Update dashboard.py rankings and safety-flags**

In `backend/routes/dashboard.py`, find validation blocks that reject unknown ranges and add `"all"` to each. Map `"all"` to the full available dataset (no date filter), same pattern as Step 1.

- [ ] **Step 4: Update site_summary.py**

Same pattern — add `"all"` to valid ranges, handle no-date-filter case.

- [ ] **Step 5: Remove the `timeRange === 'all' ? '30d' : timeRange` workarounds in App.tsx**

Once the backend supports `"all"`, remove the fallback casts in `frontend/src/App.tsx`. Search for `timeRange === 'all' ? '30d' : timeRange` and replace each with just `timeRange`. Update the `TimeRange` cast types accordingly:

```tsx
// Before:
const range = timeRange === 'all' ? '30d' : timeRange;
fetchHealthIndex(selectedLevel, range as '24h' | '7d' | '30d', ...)

// After:
fetchHealthIndex(selectedLevel, timeRange as '24h' | '7d' | '30d' | 'all', ...)
```

Also update `fetchHealthIndex`, `fetchScoreBreakdown`, `fetchRawScoreRelationship`, `fetchMeasurements`, `fetchSiteSummary` signatures in `frontend/src/api/client.ts` to accept `'all'` in their `range` parameter types:

```ts
// In client.ts:
export async function fetchHealthIndex(
  levelId: number,
  range: '24h' | '7d' | '30d' | 'all',
  deviceId?: string | null
): Promise<HealthIndexResponse> { ... }
```

- [ ] **Step 6: Verify backend starts**

```bash
cd backend && python -m uvicorn main:app --port 8081 --reload &
sleep 3
curl -s "http://localhost:8081/api/level/1/health-index?time_range=all" | python -m json.tool | head -20
```

Expected: valid JSON response with health data (or empty array, not a 400 error).

- [ ] **Step 7: Commit**

```bash
git add backend/routes/health_scores.py backend/routes/measurements.py \
        backend/routes/dashboard.py backend/routes/site_summary.py \
        frontend/src/App.tsx frontend/src/api/client.ts
git commit -m "feat(backend+api): add all-time range support across health, scores, measurements, and summary endpoints"
```

---

## Task 12: Run all tests and final check

- [ ] **Step 1: Run the full test suite**

```bash
cd frontend && npx jest --no-coverage 2>&1 | tail -30
```

Expected: all tests pass. Fix any test that fails due to the store field removals (`heroVisible`, `hamburgerOpen`).

- [ ] **Step 2: Fix stale store tests if needed**

In `frontend/src/__tests__/useAppStore.test.ts`, remove any tests referencing `heroVisible` or `hamburgerOpen` (these fields were removed from the store in Task 1).

- [ ] **Step 3: Run build**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 4: Smoke-test the dev server**

```bash
cd frontend && npm run dev &
sleep 3
curl -s http://localhost:3000 | grep -o '<title>.*</title>'
```

Expected: `<title>RDM-WACH</title>`

- [ ] **Step 5: Final commit**

```bash
cd frontend && git add -p  # stage any unfixed files
git commit -m "fix(tests): remove stale heroVisible/hamburgerOpen test references after store cleanup"
```

---

## Summary of changes

| Area | What changed |
|---|---|
| Branding | Site → RDM-WACH, chatbot → RDM-Atlas |
| Welcome page | Removed entirely |
| Nav | SiteNavBar + DashboardControls → FilterBar with breadcrumb + time range pills |
| Dashboard default | Site-wide aggregate (no level required to see KPI strip) |
| Mode toggle | Simple Mode / Deep Dive Mode |
| Rankings | ExpandableHealthRankings + AHUHeatmap → AHURankingsTable (sortable) |
| Deep Dive | New SingleDeviceChart + CompareMode (up to 3 devices, shared metric selector) |
| Device labels | All UI references use human label (AHU-L1-ES-01 — Engineering Services) |
| Chat | Sidebar 380px + fullscreen toggle, renamed RDM-Atlas |
| Financial | Removed from UI; background fetch passes context to RDM-Atlas |
| Backend | All-time range added to 4 endpoint groups |
| Store | Added dashboardMode, deepDiveSubMode, compareDevices, chatMode; removed heroVisible, hamburgerOpen |
