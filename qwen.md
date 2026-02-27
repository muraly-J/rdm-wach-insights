# WACH Insight Project Memory

## Project Context

This is the **WACH Insight** project - an AHU (Air Handling Unit) analytics dashboard for the Women & Child Ward at Hospital KL. The system:

- Analyzes **112+ AHUs** using **InfluxDB** (`wach_bucket_3`) for time-series data
- Collects metrics: power_total, energy_import, power_factor_avg, current_unbalance, THD metrics
- Uses **FAIR algorithm** (60% relative + 40% absolute scoring) for health indices
- **Health Index Range**: 0-100, with tiers:
  - Healthy: 80-100 (green)
  - Monitor: 60-79 (yellow/amber)
  - Maintenance Soon: 40-59 (orange)
  - Critical: 0-39 (red)

## Infrastructure Notes

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python), Uvicorn worker, Gunicorn |
| Frontend | React + Vite |
| Deployment | Cloudflare Tunnel + Vercel |
| Database | InfluxDB (bucket: wach_bucket_3) |

### Directory Structure
```
wach-insight/
├── api/                       # External API integration
│   └── index.py
├── backend/                   # FastAPI server
│   ├── core/                 # Business logic
│   │   ├── charts.py         # Chart builder utilities
│   │   ├── influx_client.py  # InfluxDB query client
│   │   ├── risk_engine.py    # Health scoring engine (FAIR algorithm)
│   │   └── summarizer.py     # LLM response summarization
│   ├── llm/                  # LLM query translation
│   │   ├── prompts.py        # System prompt fortranslator.py
│   │   └── translator.py     # Converts natural language to structured queries
│   ├── middleware/           # Request handling
│   │   ├── query_logger.py   # Logs all queries to database
│   │   └── validator.py      # Input validation middleware
│   ├── models/               # Data schemas
│   │   └── schemas.py        # Pydantic models and allowed values
│   ├── routes/               # API endpoints
│   │   ├── dashboard.py      # Fleet Dashboard endpoints (NEW)
│   │   ├── electrical_risk.py
│   │   └── query.py          # Main query endpoint
│   ├── main.py               # FastAPI application entry point
│   └── config.py             # Environment configuration
├── docs/                     # Documentation & archives
│   ├── qwen_updated.md       # This file (current project state)
│   ├── CLEANUP_SUMMARY.md    # Recent codebase cleanup
│   └── archive/              # Backed-up files
├── frontend/                 # React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── AhuHealthTrendDashboard.jsx  # Fleet Dashboard charts
│   │   │   ├── ChatPanel.jsx      # LLM query input panel
│   │   │   ├── ChatView.jsx       # Main chat interface
│   │   │   ├── ElectricalRiskView.jsx  # Risk analysis view
│   │   │   ├── FleetDashboard.jsx     # Alternative dashboard
│   │   │   └── OutputPanel.jsx    # LLM response output
│   │   ├── api.js              # Frontend API client
│   │   ├── App.jsx             # Main app component
│   │   └── main.jsx            # React entry point
│   └── vite.config.js          # Vite bundler configuration
├── scripts/                    # Automation & utilities
│   ├── fetch_raw_data.py           # Fetch raw InfluxDB data
│   ├── generate_level1_health_scores.py  # Generate health scores
│   └── test_*.py                   # Test scripts for presets
├── data/                       # Generated output files
│   └── level1_hourly_health.csv  # Health scores for Level 1 (21 devices)
├── paraquet_data/              # Parquet data storage
└── venv/                       # Python virtual environment
```

## FAIR Health Scoring Algorithm (Stage 2B)

### Core Principle
Each AHU's health score uses **60% relative** (per-AHU baseline) + **40% absolute** (fleet percentile):

```
Health Index = 100 - weighted_penalty × 100

Where: weighted_penalty = 
    energy_anomaly     × 0.15
    + power_factor     × 0.25
    + phase_imbalance  × 0.25
    + thd_drift        × 0.15
    + overload         × 0.20
```

### Scoring Components

#### 1. Energy Anomaly (weight: 0.15)
- **Relative**: Z-score comparing to each AHU's historical delta_kwh mean
- **Absolute**: Percentile rank within fleet distribution
- Uses hourly `delta_kwh` (not cumulative energy)

#### 2. Power Factor Degradation (weight: 0.25)
- **Relative**: Z-score comparing to each AHU's historical PF mean
- **Absolute**: Percentile rank within fleet distribution
- **Load Discount**: If running <60% of own mean power, penalize less (load-dependent degradation)

#### 3. Phase Imbalance (weight: 0.25)
- **Relative**: Z-score comparing to each AHU's historical imbalance mean
- **Absolute**: Percentile rank within fleet distribution

#### 4. THD Drift (weight: 0.15)
- **Relative**: Z-score comparing to each AHU's historical THD mean
- **Absolute**: Percentile rank within fleet distribution

#### 5. Overload (weight: 0.20)
- Uses p95 ceiling per AHU for normalization
- Compare current power to historical max acceptable load

### Output Schema (per AHU)
```json
{
  "ahu_id": "wach_e0101",
  "timestamp": "2026-02-23T14:00:00+08:00",
  "health_index": 84,
  "health_tier": "Healthy",
  "risk_scores": {
    "power_factor": {"score": 0.15, "severity": "Normal", ...},
    "phase_imbalance": {"score": 0.25, "severity": "Elevated", ...},
    "thd_drift": {"score": 0.12, "severity": "Normal", ...},
    "overload": {"score": 0.18, "severity": "Monitor", ...}
  },
  "data_quality": {...}
}
```

## Codebase Cleanup (Feb 25, 2026)

### Files Removed
| Category | Count |
|----------|-------|
| Risk engine patch files | 8 versions |
| Empty directories | 4 |
| Backup files | Multiple |
| Unused configs | 5+ |

### Scripts Organized
All Python utilities moved to `scripts/`:
- `fetch_raw_data.py` - Raw data fetching
- `generate_level1_health_scores.py` - Health scoring (FAIR algorithm)
- `test_backend_presets.py` - Backend preset testing
- Additional test scripts

### Documentation Consolidated
All docs moved to `docs/`:
- `qwen_updated.md` - This file (project memory)
- `CLEANUP_SUMMARY.md` - Cleanup details
- `reference_data.md` - AHU reference data
- `ahu_relationships.tsv` - Level mappings

### Backend Import and Function Fix (Feb 26, 2026)

**Issue**: Backend server fails to start with import errors and API endpoints return keyword argument errors.

**Root Cause**:
1. Initial `backend/main.py` used absolute imports: `from backend.routes.dashboard import ...`
2. Risk scoring functions had incorrect parameter names/missing required arguments

**Fix Applied**:
1. Changed all backend imports to relative format in `backend/main.py`:
   ```python
   # BEFORE (BROKEN):
   from backend.routes.dashboard import dashboard_router
   
   # AFTER (FIXED):
   from routes.dashboard import dashboard_router
   ```

2. Fixed risk scoring function signatures in `backend/core/risk_engine.py`:
   | Function | Issue | Fix |
   |----------|-------|-----|
   | `power_factor_risk_score()` | Missing params: `ahu_std_pf`, `fleet_median_pf`, `fleet_p5_pf`, `current_power`, `ahu_mean_power` | Added all required parameters |
   | `overload_risk_score()` | Wrong parameter names | Renamed to match function signature |
   | `phase_imbalance_risk_score()` | Missing params: `ahu_std`, `fleet_median`, `fleet_p5` | Added all required parameters |
   | `thd_risk_score()` | Used wrong param name: `thd_slope_7d_l1_normalized` | Changed to `slope_7d_normalized` |

3. Added THD mean/std calculation in `fetch_ahu_metrics()` function

4. Added `float()` casts for numpy types to prevent serialization errors in routes/dashboard.py

**Files Modified**:
| File | Change |
|------|--------|
| `backend/main.py` | Changed absolute imports to relative |
| `backend/core/risk_engine.py` | Fixed function signatures, added THD stats calculation |
| `backend/routes/dashboard.py` | Added float() casts for numpy types |

**Build Status**:
- ✅ Frontend: SUCCESS (664 KB)
- ✅ Backend API endpoints working
- ✅ Dashboard ranking/trend/summary endpoints functional

## Autonomous Codebase Mapping

### Key Patterns

1. **API Router Pattern**: Routes are registered in `backend/main.py` using:
   - `app.include_router(router, prefix="/api")` or no prefix for dashboard
   - Router paths should NOT include `/api` in `APIRouter(prefix=...)`

2. **Component Naming**:
   - Components use PascalCase: `FleetDashboard.jsx`, `ChatView.jsx`
   - Dashboard routes don't use React Router - uses conditional rendering in App.jsx

3. **CSS Variables** (in `frontend/src/index.css`):
   ```css
   --bg-base: #080c18;           /* Dark background */
   --bg-panel: #0d1424;          /* Card panels */
   --teal: #00c9b1;              /* Primary color */
   --amber: #f5a623;             /* Warning color */
   --red: #ff4d6d;               /* Error/critical color */
   ```

4. **AHU ID Convention**: `e0101`, `e0203` etc. where:
   - First digit after 'e' = level (01 → Level 1)
   - Last two digits = unit number
   - To get level from ID: extract chars 1-3, convert to int

5. **Time Range Mapping**:
| UI Parameter | Influx Parameter |
|--------------|------------------|
| 24h | last_24h |
| 7d | last_7d |
| 30d | last_30d |

## Lessons Learned

### Date: 2026-02-24
**Error**: Dashboard routes returning 404 Not Found even though they appeared in code inspection.

**Root Cause**:
- Initial `dashboard.py` had `APIRouter(prefix="/api/dashboard")`
- Routes registered as `/api/dashboard/ranking` but main.py didn't include it
- After fixing prefix to `/dashboard`, the routes should work

**Fix Applied**:
1. Changed router from `APIRouter(prefix="/api/dashboard")` to `APIRouter(prefix="/dashboard")`
2. Added `app.include_router(dashboard_router)` in main.py
3. Used `asyncio.to_thread()` to wrap synchronous functions

**Rule**: When adding new routes:
- Router prefix should NOT include `/api`
- Add router to `backend/main.py` in the `create_app()` function
- Ensure backend is restarted with `kill -9 <pid>` and fresh restart

### Date: 2026-02-24
**Error**: Using `await` on non-async function in dashboard.py

**Root Cause**:
- `generate_fleet_risk_assessment()` is a sync function
- Was calling it with `await` syntax

**Fix Applied**:
- Wrapped with `asyncio.to_thread()` to call sync functions in async context

**Rule**: For FastAPI endpoints:
- Use `async def` for route handlers
- Wrap sync functions with `await asyncio.to_thread(func, args...)`

### Date: 2026-02-25
**Error**: Dashboard shows "No data available" even after CSV loads successfully.

**Root Cause**: The `allAhuIds` extraction logic was incorrect for long-format CSV data.

**CSV Structure (Long Format)**:
```
timestamp,ahu_id,level,health_index,energy_anomaly,pf_degradation,phase_imbalance,thd_drift,overload
2026-02-18 16:00:00,e0101,Level 1,29.8,0.0027,0.15,0.02,3.2,0
```

**Original Code (BROKEN)**:
```javascript
const allAhuIds = Object.keys(allData[0]).filter(key => key !== 'timestamp' && key !== 'level')
// Result: ['ahu_id', 'health_index', ...] - column NAMES, not AHU VALUES
```

**Fix Applied**:
```javascript
// Extract unique VALUES from ahu_id column
const allAhuIds = [...new Set(allData.map(row => row.ahu_id))]
  .filter(id => id != null && typeof id === 'string')
  .sort()
// Result: ['e0101', 'e0102', ..., 'e0212']
```

## DashboardScrollability Fix

**Issue**: Charts not scrolling, blank space at bottom.

**Fix Applied**:
- Added `overflowY: 'auto'` to charts grid container
- Removed `maxHeight` constraint

**Current State**: Dashboard fully scrollable with charts

---

## Fleet Dashboard Crash Fix (Feb 26, 2026)

**Issue**: Clicking "Fleet Dashboard" opens and crashes immediately.

**Root Cause**: Infinite re-render loop caused by dependency cycle between two useEffect hooks:

1. **useEffect #1** (line 647-653): Triggers when `timeRange` or `selectedLevel` changes
   - Calls `loadData()` → loads CSV data
   - After loading, calls `fetchSummaries()`

2. **useEffect #2** (line 610-619): Triggers when `allData.length` changes
   - Depends on: `[selectedLevel, timeRange, highlightedAhu, allData.length]`
   - When `loadData()` completes and sets `allData`, this triggers
   - Which then calls `fetchSummaries()` again → updates state
   - This causes the component to re-render, creating a loop

**The Cycle**:
```
timeRange/selectedLevel change
  ↓
loadData() → fetchSummaries()
  ↓
summaries state updated
  ↓
useEffect #2 triggers (allData.length changed)
  ↓
fetchSummaries() called again
  ↓
summaries updated → re-render
  ↓
LOOP CONTINUES UNTIL CRASH
```

**Original Code (BROKEN)**:
```javascript
// Effect #1: Load data when range/level changes
useEffect(() => {
  const timer = setTimeout(() => {
    console.log('[Dashboard] timeRange or level changed...')
    loadData()
  }, 100)
  return () => clearTimeout(timer)
}, [timeRange, selectedLevel])

// Effect #2: Fetch summaries when allData changes
useEffect(() => {
  if (allData.length > 0) {
    fetchSummaries(selectedLevel, timeRange, highlightedAhu)
  }
}, [selectedLevel, timeRange, highlightedAhu, allData.length]) // ❌ allData.length causes loop
```

**Final Fix Applied (Feb 26, 2026 - Latest)**:
The root cause was that two useEffects were calling `fetchSummaries()` simultaneously, causing race conditions. The simplest solution is to **remove the separate fetchSummaries useEffect entirely** and let `loadData()` handle fetching summaries directly.

```javascript
// REMOVED: Problematic fetchSummaries useEffect that caused duplicate calls
// The useEffect triggered both when allData changed AND when summariesLoaded changed

// Updated: loadData() now solely responsible for calling fetchSummaries
const loadData = useCallback(async () => {
  setIsLoading(true)
  setError(null)
  try {
    // ... CSV loading code ...
    setAllData(rows)
    
    // Fetch summaries after data is loaded (no useEffect needed!)
    await fetchSummaries(selectedLevel, timeRange, highlightedAhu)
  } catch (err) {
    console.error('[Dashboard] Error loading health data:', err)
    setError('Failed to load dashboard data.')
  } finally {
    setIsLoading(false)
  }
}, [selectedLevel, timeRange])

// Added: useEffect for highlightedAhu changes (device selection)
useEffect(() => {
  if (allData.length > 0) {
    const timer = setTimeout(() => {
      loadData() // Reload to fetch device-specific summaries
    }, 100)
    return () => clearTimeout(timer)
  }
}, [highlightedAhu])

// REMOVED: summariesLoaded state variable
// The state was causing complexity and race conditions
```

**Files Modified (Final Fix)**:
| File | Change |
|------|--------|
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | Removed `summariesLoaded` state variable; Removed duplicate fetchSummaries useEffect; Added standalone useEffect for highlightedAhu changes |

**Verification Steps**:
1. Click "Fleet Dashboard" button
2. Dashboard should load without crashing
3. Charts should render with health data
4. Switching levels/time ranges should work without loop

### Fix Applied (Feb 26, 2026)
| Issue | Fix |
|-------|-----|
| Dashboard crash on click | Removed infinite re-render loop by removing summariesLoaded state and duplicate useEffect; added error boundaries around chart rendering |

### Latest Fix (Feb 26, 2026 - Final)

## How Fleet Dashboard Loads

The dashboard follows this loading flow:

### Step 1: Component Mounts
```javascript
State initialized:
- selectedLevel = '1'
- timeRange = '24h'
- allData = []
- summaries = {}
- isLoading = false
```

### Step 2: Initial useEffect Triggers (100ms delay)
```javascript
useEffect(() => {
  const timer = setTimeout(() => { loadData() }, 100)
}, [timeRange, selectedLevel])
```

### Step 3: loadData() Executes
1. Sets `isLoading = true`
2. Fetches CSV file: `level1_hourly_health_24h.csv`
3. Parses CSV → 576 rows for Level 1
4. Filters by level prefix: `Level 1`
5. Stores data: `setAllData(rows)`
6. Calls `fetchSummaries(selectedLevel, timeRange, highlightedAhu)`
7. API call to `/dashboard/summary` with params
8. Receives LLM summaries for each metric
9. Stores summaries: `setSummaries(res.data.summaries)`
10. Sets `isLoading = false` in finally block

### Step 4: Component Re-renders with Data
With `isLoading = false` and data loaded:
- Header displays (Level selector, Time range toggle)
- Device pills show all Level 1 AHUs
- Charts grid renders with 6 charts

### Step 5: Chart Rendering with Error Protection
Each HealthChart is wrapped in try-catch:
- Health Index chart
- Energy Anomaly chart
- PF Degradation chart
- Phase Imbalance chart
- THD Drift chart
- Overload chart

If any chart throws an error, it's caught and displayed as:
```
Error rendering chart: [error message]
```

### Key Changes Made:

1. **Removed Infinite Loop**: No more `summariesLoaded` state flag causing re-render cycles

2. **Error Boundaries**: Each chart wrapped in try-catch to prevent React crash

3. **Clean Code**: Removed verbose debug console.log statements

4. **Simplified Flow**: Single source of truth - `loadData()` handles all data loading

## Current Status
- ✅ Dashboard loads without crash
- ✅ Level 1 data displayed correctly (21 devices)
- ✅ All health index charts render with AHU lines
- ✅ Legend shows all Level 1 devices
- ✅ FAIR health scoring algorithm implemented

### Working Features
- ✅ Dashboard loads without crash
- ✅ Level 1 data displayed correctly (21 devices)
- ✅ All health index charts render with AHU lines
- ✅ Legend shows all Level 1 devices
- ✅ FAIR health scoring algorithm implemented
- ✅ Health scores regenerated with correct per-AHU baselines
- ✅ Time range toggle (24h/7d/30d) working with separate CSV files
- ✅ Two-phase data generation (fetch raw → compute scores)
- ✅ 2-second delay between InfluxDB requests to avoid timeout
- ✅ `/api/dashboard/summary` endpoint with real CSV data
- ✅ Summary content text increased to 14px

### Recent Implementation: Debouncing for Smooth UX
**Issue**: Dashboard was laggy when switching devices/time ranges due to instant API calls

**Solution Implemented**:
- Added ellipsis cycling (., .., ...) for loading indicators
- Implemented debouncing mechanism to wait before fetching summaries
- User proposes: 1-second delay before CSV load, 1-second delay before API call
- During waiting periods, show "Loading summary." with cycling ellipsis

**Planned Behavior**:
1. User clicks on device or changes time range
2. System waits 1 second (shows "Loading summary.")
3. Loads CSV data
4. Waits 1 more second
5. Fetches LLM summaries from `/api/dashboard/summary`

- **Two-phase process**:
  - Phase 1: Fetch raw metrics from InfluxDB for each time range (24h, 7d, 30d) with 2-second delays
  - Phase 2: Apply FAIR scoring formulas to pre-fetched raw data files

- **CSV Files Generated**:
  - `level1_hourly_health_24h.csv` (576 rows, last 24 hours)
  - `level1_hourly_health_7d.csv` (338 rows, last 7 days)
  - `level1_hourly_health_30d.csv` (362 rows, last 30 days)

- **Frontend**: Updated to load `level1_hourly_health_{timeRange}.csv` dynamically

### Bug Fixes (Feb 26, 2026)
| Issue | Status |
|-------|--------|
| Dashboard crash on "Fleet Dashboard" click | ✅ Fixed - Added `summariesLoaded` state flag to break infinite re-render loop |

---

## Parameter Naming Bug Pattern (Feb 26, 2026)

**Pattern**: Helper functions with parameter naming mismatches causing runtime crashes

### History of This Issue
This has happened multiple times - when creating/modifying functions, the parameter name and internal variable reference don't match:

| Date | Issue | Location |
|------|-------|----------|
| Feb 26, 2026 | `buildSummary` - parameter `ahus` vs reference `ahuIds` | Line 278 |
| Feb 26, 2026 | `buildWorstDevicesList` - parameter `ahus` vs reference `ahuIds` | Line 298 |

### Prevention Checklist
When creating/modifying functions, verify:
- [ ] All parameter names match their usage inside the function body
- [ ] Run `npm run build` after any function modification
- [ ] Check browser console for "ReferenceError: X is not defined" on first load
- [ ] Use consistent naming conventions (e.g., `ahuIds` for arrays of AHU IDs)
- [ ] Run linter before committing

### Diagnostic Pattern
If you see `ReferenceError: X is not defined`:
1. Check if variable `X` is a parameter name vs usage
2. Search for all occurrences of `X` in the function body
3. Verify parameter list matches usage

---

### Parameter Naming Bug Fix (Feb 26, 2026)

**Issue**: Dashboard crashes on load with "ReferenceError: ahuIds is not defined"

**Root Cause**: Two helper functions had parameter naming mismatch:
- `buildSummary()` - parameter named `ahus` but code used `ahuIds`
- `buildWorstDevicesList()` - parameter named `ahus` but code used `ahuIds`

**Fix Applied**:
| File | Line | Change |
|------|------|--------|
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~278 | `${ahuIds.length}` → `${ahus.length}` |
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~298 | `!ahuIds` → `!ahus` |

**Verification**: Dashboard loads without crash, all 6 charts render correctly

### Remaining Tasks
- ⚠️ Level selector only shows data for Level 1 (other levels need CSV generation)
- ⚠️ Frontend code-splitting for large chunks (>500 KB warning)

### Key Files
| File | Purpose |
|------|---------|
| `backend/core/risk_engine.py` | FAIR health scoring engine |
| `scripts/generate_level1_health_scores.py` | Health score generation script (updated with two-phase approach) |
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | Fleet Dashboard component (updated with dynamic CSV loading) |
| `frontend/public/level1_hourly_health_*.csv` | Pre-generated CSV files for time ranges |

### Script Usage
```bash
# Generate all time ranges (24h, 7d, 30d)
python scripts/generate_level1_health_scores.py --all-ranges

# Generate specific time range
python scripts/generate_level1_health_scores.py --range 7d

# Fetch only (Phase 1)
python scripts/generate_level1_health_scores.py --fetch-only

# Compute scores only (Phase 2)
python scripts/generate_level1_health_scores.py --compute-only
```

### Build Status
```
✓ Frontend build: SUCCESS (664 KB)
✓ Backend startup: SUCCESS (port 8000)
✓ API endpoints working: /api/dashboard/ranking, /api/dashboard/trend, /api/dashboard/summary
✓ Health scores generation: SUCCESS
✓ No broken imports detected
```

### Backend Fixes (Feb 26, 2026)
| Issue | Fix |
|-------|-----|
| Import errors on startup | Changed absolute `backend.*` to relative imports |
| `power_factor_risk_score()` missing params | Added: `ahu_std_pf`, `fleet_median_pf`, `fleet_p5_pf`, `current_power`, `ahu_mean_power` |
| `overload_risk_score()` wrong params | Renamed parameters to match function signature |
| `phase_imbalance_risk_score()` missing params | Added: `ahu_std`, `fleet_median`, `fleet_p5` |
| `thd_risk_score()` wrong param name | Changed `thd_slope_7d_l1_normalized` → `slope_7d_normalized` |
| Numpy type serialization | Added `float()` casts for numpy types in routes/dashboard.py |

### Parameter Naming Bug Fix (Feb 26, 2026)

**Issue**: Dashboard crashes on load with "ReferenceError: ahuIds is not defined"

**Root Cause**: Two helper functions had parameter naming mismatch:
- `buildSummary()` - parameter named `ahus` but code used `ahuIds`
- `buildWorstDevicesList()` - parameter named `ahus` but code used `ahuIds`

**Fix Applied**:
| File | Line | Change |
|------|------|--------|
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~278 | `${ahuIds.length}` → `${ahus.length}` |
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~298 | `!ahuIds` → `!ahus` |

**Verification**: Dashboard loads without crash, all 6 charts render correctly

---

## Dashboard Row Height Fix (Feb 26, 2026)

**Issue**: Charts were too short to read plots clearly

### Root Cause
- Chart height was only 360px ( ResponsiveContainer )
- Row container had `overflow: 'hidden'` preventing any scrolling
- Dashboard grid didn't have proper scrolling configuration

### Fix Applied
| File | Line | Change |
|------|------|--------|
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~485 | height `{360}` → `{1200}` (3x taller) |
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~1075 | overflow `'hidden'` → `'auto'` (enable scrolling) |

### Changes Made
1. **Increased Chart Height**: ResponsiveContainer height changed from 360px to 1200px (3x taller)
2. **Enabled Scrolling**: Row containers changed from `overflow: 'hidden'` to `overflowY: 'auto'`
3. **Dashboard Container**: Already had `overflowY: 'auto'` on the grid container for page-level scrolling

### Build Status
```
✓ Frontend build: SUCCESS (671 KB)
✓ Charts render with proper height
✓ Dashboard scrolling working for all 6 charts
```

**Verification**: Dashboard displays properly with taller charts and smooth scrolling

---

## Dashboard Scrolling Fix (Feb 26, 2026)

**Issue**: Row-level scrollbars were appearing instead of natural page scroll

### Root Cause
The dashboard had nested scroll containers:
1. Dashboard grid container had `overflowY: 'auto'` (per-container scrollbar)
2. Each row had `overflowY: 'auto'` (per-row scrollbars)
3. `.app` class had `overflow: hidden` (blocked page scroll)

### Fix Applied
| File | Line | Change |
|------|------|--------|
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~1059 | Removed `overflowY: 'auto'` from grid container |
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | ~1073 | Removed `overflowY: 'auto'` from row containers |
| `frontend/src/index.css` | ~48 | Changed `.app overflow: hidden` → `overflow-y: auto` |

### Changes Made
1. **Removed dashboard grid overflow** - allows content to flow naturally
2. **Removed row overflow** - no per-row scrollbars
3. **Enabled page-level scroll** - `.app` now scrolls naturally

### Expected Behavior
- Charts are 1200px tall (no scrolling within row)
- Single browser page scrollbar appears
- Smooth scroll through all 6 charts as one natural flow

### Build Status
```
✓ Frontend build: SUCCESS (671 KB)
✓ Single page scroll, no per-row scrollbars
```

---

## Dashboard CSV Loading Fix (Feb 27, 2026)

**Issue**: When toggling between 24h, 7d, and 30d time ranges:
- X-axis updated correctly
- Charts showed same data (browser caching issue)

### Root Cause
Browser caches static CSV files in `frontend/public/`. The fetch request returns cached data instead of fresh content.

### Fix Applied
**File**: `frontend/src/components/AhuHealthTrendDashboard.jsx` (line 477)

```javascript
// BEFORE:
const response = await fetch(csvFile)

// AFTER:
const response = await fetch(csvFile, { cache: 'no-cache' })
```

### What This Does
- Forces browser to fetch fresh data for each time range toggle
- Prevents stale CSV content from being displayed
- Ensures 24h/7d/30d charts show correct date ranges

### Second Attempt Fix (Feb 27, 2026)

**Issue**: Time range toggle STILL showing same data after first fix.

**Root Cause**: 
- Browser caching too aggressive even with `cache: 'no-cache'`
- Vite dev server not configured to prevent caching of static assets

**Final Fix Applied**:
```javascript
// Added timestamp query parameter for unique URLs
const cacheBuster = Date.now()
const csvFileBase = csvFileMap[timeRange] || '/level1_health_data.csv'
const csvFile = `${csvFileBase}?t=${cacheBuster}`

// Changed to no-store for strict caching control
const response = await fetch(csvFile, { cache: 'no-store' })
```

**Vite Config Update**:
```javascript
server: {
  headers: {
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
  }
}
```

### Build Status
```
✓ Frontend build: SUCCESS (673 KB)
✓ Cache-busting added to CSV fetch
```

**Verification**: Time range toggles now load fresh CSV data for each selection.

