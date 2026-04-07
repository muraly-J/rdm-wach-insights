# RDM-WACH Frontend Redesign — Design Spec

**Date:** 2026-04-07  
**Status:** Approved  
**Approach:** Phased component replacement (preserve existing Zustand store, chart components, API layer)

---

## 1. Branding

- Site name: **RDM-WACH** (replaces "WACH Insight" everywhere — page title, nav bar, footer)
- Chatbot name: **RDM-Atlas** (replaces "WACH AI" everywhere — chat header, greeting message, bot message attribution)
- Welcome/hero page: **removed entirely** — app loads directly into the dashboard
- AHU coverage disclaimer: moves from the welcome page to the **dashboard footer** (always visible)

---

## 2. Device Label Mapping

All device references in the UI show the human-readable label instead of the internal ID.

- **Display format:** `AHU-L1-ES-01 — Engineering Services`  
  (derived from the `label` and `department` fields returned by `/api/level/{id}/devices`)
- **Internal ID** (`e0101` style) is used **only** in API call parameters — never rendered in the UI
- A device label lookup map is built per level when the level is selected, keyed by device ID
- This applies to: filter dropdowns, chart tooltips, chart legends, rankings table, heatmap labels, compare mode column headers, and any other device reference

---

## 3. Filter Bar (Sticky Top)

The filter bar is sticky at the top of the page, always visible.

**Left side — breadcrumb filter:**
```
[All Levels ▾] → [Level ▾] → [Device ▾]
```
- Selecting "All Levels" clears level and device, shows site-wide data
- Selecting a level clears the device selection and loads level-scoped data
- Selecting a device loads device-scoped data
- In **Compare Mode** (Deep Dive sub-mode), the Device filter becomes a multi-select for up to 3 devices simultaneously

**Right side — time range pills:**
```
[24h]  [7d]  [30d]  [All-time]
```
- Active range highlighted with accent colour
- `All-time` requires a new backend parameter (see Section 9)
- Selected time range persists across filter state changes

---

## 4. KPI Strip

Always visible regardless of filter state or dashboard mode.

| Metric | All Levels | Level selected | Device selected |
|---|---|---|---|
| Site Health | Avg across all AHUs | Avg across level AHUs | AHU health score |
| Total AHUs | Building total | Level count | 1 |
| In Alert | Building-wide | Level-scoped | — (show status badge) |
| Best AHU | Building-wide (label) | Level-scoped (label) | — |
| Worst AHU | Building-wide (label) | Level-scoped (label) | — |

"Best" and "Worst" AHU cells show the human label (`AHU-L1-ES-01 — Engineering Services`), not the internal ID.

---

## 5. Mode Toggle

A toggle rendered **above the Health Index Chart** (in Simple Mode) or above the Deep Dive content area:

```
[ Simple Mode ]  [ Deep Dive Mode ]
```

- Switching modes preserves the current filter state (level, device, time range)
- Default: Simple Mode
- Mode stored in Zustand store (not persisted across page reloads)

---

## 6. Simple Mode

Default view. Sections render top to bottom:

### 6.1 Health Index Chart
- Time series chart of health index scores
- All Levels: single aggregated average line across all AHUs (plotting 47 individual lines is unreadable)
- Level selected: one line per AHU in that level
- Device selected: single AHU line
- Uses existing `HealthIndexChart` component

### 6.2 Score Cards
- Five FAIR score cards: Energy Anomaly, PF Degradation, Phase Imbalance, THD Drift, Overload
- Shows current score + trend delta vs previous period
- Uses existing `ScoreCardsGrid` component

### 6.3 AHU Rankings Table
Replaces the existing `ExpandableHealthRankings` and `AHUHeatmap` components.

A sortable table with the following columns:

| Column | Description | Sortable |
|---|---|---|
| AHU Name | Human label (`AHU-L1-ES-01 — Engineering Services`) | Yes |
| Level | Building level number | Yes |
| Health Score | 0–100 index | Yes (default: descending) |
| Trend | Arrow + delta vs previous period (↑↓) | Yes |
| Status | Badge: Good / Warning / Critical | Yes |

- At "All Levels": shows all AHUs across the building
- Level selected: shows only AHUs in that level
- Device selected: table is hidden; replace with a single-device detail card showing name, level, health score, trend, and status badge
- Pagination or virtual scroll if row count exceeds 20

### 6.4 Raw Data Explorer
Visible **only when a device is selected**.

- Metric multi-select, grouped by score category (Energy, PF, Phase Imbalance, THD, Overload)
- Plots selected metrics as a multi-series chart on a shared time axis
- Uses existing `SCORE_METRIC_GROUPS` and `METRIC_META` from `constants/metricGroups.ts`
- Fetches from `/api/device/{id}/measurements`

---

## 7. Deep Dive Mode

Replaces everything below the mode toggle (Health Index Chart, Score Cards, Rankings Table, Raw Data Explorer). KPI strip remains visible.

Requires a device to be selected before data is shown. If no device is selected, show a prompt: _"Select a device to begin deep dive analysis."_

### 7.1 Sub-mode Toggle
```
[ Single Device ]  [ Compare Mode ]
```

### 7.2 Single Device Sub-mode
- Full-width layout
- Metric multi-select (grouped by category, same as Raw Data Explorer)
- Single large multi-series chart
- Works with any time range including all-time

### 7.3 Compare Mode Sub-mode
- Device filter in top bar becomes a multi-select supporting **up to 3 devices**
- **Shared metric selector**: one metric multi-select above the columns; all columns plot the same metrics
- Side-by-side columns: 2 devices = 2 columns, 3 devices = 3 columns
- Each column header shows the device human label
- Each column has its own chart (same metrics, different device data)
- Columns share the same time axis and time range
- Works with any time range including all-time

---

## 8. RDM-Atlas Chatbot

### 8.1 Floating Action Button
- Always visible, fixed bottom-right corner
- Teal-green accent, chat bubble icon
- Opens chatbot in Corner Mode on click

### 8.2 Corner Mode (right sidebar)
- Slides in from the right edge, ~380px wide
- Overlays the dashboard (does not push content)
- Header contains: "RDM-Atlas" label, expand-to-fullscreen icon, close icon
- Full conversation history visible, input at bottom

### 8.3 Fullscreen Mode
- Takes over the full viewport
- Header contains: "RDM-Atlas" label, collapse-to-sidebar icon, close icon
- Same conversation continues — no state reset on mode switch

### 8.4 Financial Context
- Financial impact data is **not displayed** anywhere in the frontend UI
- Backend financial endpoints remain intact
- `App.tsx` fetches financial data silently in the background (same as the current `FinancialImpactView` fetch, moved to a `useEffect` in App) and stores it in `financialImpact` via `setFinancialImpact`
- When sending chat messages, the current `financialImpact` from the Zustand store is passed as context in the API payload — RDM-Atlas uses it to answer cost-related questions
- The `FinancialImpact` type and `setFinancialImpact` store action are kept but no longer rendered visually

---

## 9. Backend Changes Required

### 9.1 All-time Time Range
A new time range parameter `all` (or `all-time`) must be supported by the following endpoints:

- `GET /api/level/{id}/health-index?time_range=all`
- `GET /api/level/{id}/scores?time_range=all`
- `GET /api/device/{id}/measurements?range=all`
- `GET /api/device/{id}/raw-score-relationship?range=all`
- `GET /api/dashboard/ranking?range=all`
- `GET /api/site/summary?range=all`

Backend should return the full available history when `all` is specified, with no date truncation.

The frontend `TimeRange` type in `store/useAppStore.ts` must be extended:
```ts
export type TimeRange = '24h' | '7d' | '30d' | 'all';
```

### 9.2 No Other New Endpoints Required
All other data needs (KPI strip, rankings table, Deep Dive charts, Compare Mode) are served by existing endpoints, scoped by the existing level/device/range parameters.

---

## 10. Removed Components

The following components are **deleted** as part of this redesign:

| Component | Reason |
|---|---|
| `WelcomeHero` | Welcome page removed |
| `FloatingParticles` | Part of welcome page |
| `AHUWireframeSVG` | Part of welcome page |
| `ScrollCTA` | Part of welcome page |
| `AHUCoverageDisclaimer` | Moves to footer as plain text |
| `CapabilityPills` | Part of welcome page |
| `ExpandableHealthRankings` | Replaced by sortable table |
| `AHUHeatmap` | Replaced by sortable table |
| `FinancialImpactView` | Financial UI removed |
| `FinancialSettingsDrawer` | Financial UI removed |
| `TopCostAHUsTable` | Financial UI removed |
| `CostBreakdownCard` | Financial UI removed |
| `SiteSummaryView` | Replaced by KPI strip |
| `SpotlightCards` | Part of SiteSummaryView |
| `TrendDeltas` | Part of SiteSummaryView |
| `LevelHeatMap` | Part of SiteSummaryView |
| `KPIStrip` (existing) | Rebuilt as part of new KPI strip |
| `HamburgerMenu` | Nav restructured into filter bar |
| `SiteNavBar` | Rebuilt as new sticky filter bar |

---

## 11. Preserved Components

These components are reused with minimal or no changes:

| Component | Notes |
|---|---|
| `HealthIndexChart` | Used in Simple Mode |
| `ScoreCardsGrid` / `ScoreCard` | Used in Simple Mode |
| `CombinedScoresChart` | Kept in Simple Mode, renders below Score Cards |
| `ScoreDerivationSection` | Kept in Simple Mode, device-only, lazy-loaded (unchanged) |
| `PredictionView` | Keep in Simple Mode, device-only |
| `ChatWidget` / `ChatWindow` / `ChatInput` etc. | Renamed to RDM-Atlas, sidebar/fullscreen modes added |
| `VariableSelector` | Reused in Raw Data Explorer and Deep Dive |
| `useAppStore` | Extended with `dashboardMode`, `deepDiveSubMode`, `compareDevices`, updated `TimeRange` |
| All API client functions | Unchanged except `TimeRange` type update |

---

## 12. State Changes (Zustand Store)

New fields added to the store:

```ts
// Dashboard mode
dashboardMode: 'simple' | 'deepdive';
setDashboardMode: (mode: 'simple' | 'deepdive') => void;

// Deep Dive sub-mode
deepDiveSubMode: 'single' | 'compare';
setDeepDiveSubMode: (mode: 'single' | 'compare') => void;

// Compare mode devices (up to 3)
compareDevices: string[];  // device IDs
setCompareDevices: (devices: string[]) => void;

// TimeRange extended
timeRange: '24h' | '7d' | '30d' | 'all';
```

Existing fields removed:
- `heroVisible` / `setHeroVisible` (welcome page gone)
- `hamburgerOpen` / `toggleHamburger` (hamburger menu gone)
