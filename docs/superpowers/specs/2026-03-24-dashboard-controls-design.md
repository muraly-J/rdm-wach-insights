# Dashboard Controls — Unified Strip Design Spec

## Context

The current dashboard has three separate sticky/inline control areas:
- `LevelSelectorBar` — full-width sticky bar with 11 level pill buttons
- `DeviceSelector` — horizontal chip row (inside sticky wrapper in App.tsx)
- Time range buttons — inline buttons (24h / 7d / 30d)

These will be replaced by a single compact **Unified Strip** with floating panel dropdowns, giving the dashboard a cleaner, more professional feel without sacrificing any functionality.

---

## Design

### The Strip

A single sticky bar (`sticky top-0 z-30`, backdrop-blur) containing one pill-shaped container with three tappable segments divided by separators:

```
[ LVL · 4 | DEV · e0413 | RANGE · 30d ]
```

- The entire strip is left-aligned inside the max-width container
- Active (non-default) segment glows `#00E5A0`
- Open segment gets a light `#1A2330` highlight

### Segments

| Segment | Label | Default value | Disabled when |
|---------|-------|---------------|---------------|
| Level | `LVL` | `—` (none) | never |
| Device | `DEV` | `All` (after level selected) | no level selected |
| Range | `RANGE` | `24h` | never |

**Disabled DEV state:** colour `#4A5568`, cursor default, click ignored, shows `DEV · —`.

### Floating Panels

Each segment opens a floating panel directly below it on click. Closes on outside click or option selection.

**Panel style:** `background: #141D28`, `border: 1px solid #1E2A3A`, `border-radius: 10px`, `box-shadow: 0 8px 32px rgba(0,0,0,0.5)`, `min-width: 140px`, `z-index: 50`.

**Level panel:** Plain list, items `Level 1` → `Level 11`. Selected item shown in `#00E5A0`.

**Device panel:** Search input at top (`placeholder: "Search…"`), then scrollable list: `All AHUs` first, then individual device IDs. Max height `240px`, overflow-y scroll. Only available after a level is selected.

**Range panel:** Three items — `24h`, `7d`, `30d`. Selected item in `#00E5A0`.

---

## Architecture

### New file
`frontend/src/components/dashboard/DashboardControls.tsx`

- Single exported component `DashboardControls`
- Internal `DropdownSegment` sub-component (not exported) handles the open/close/panel logic for each segment
- Reads `selectedLevel`, `selectLevel`, `selectedDevice`, `selectDevice` from Zustand (`useAppStore`)
- Props: `devices`, `timeRange`, `onTimeRangeChange`, `timeRanges`

```tsx
interface DashboardControlsProps {
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
  timeRanges: readonly TimeRange[];
}
```

### App.tsx changes
- Remove `<LevelSelectorBar />` import and usage
- Remove the sticky `<div>` wrapping `DeviceSelector` + time buttons
- Add `<DashboardControls devices={devices} timeRange={timeRange} onTimeRangeChange={setTimeRange} timeRanges={TIME_RANGES} />`

### Files kept but no longer rendered
- `LevelSelectorBar.tsx` — retained, just not used
- `DeviceSelector.tsx` — retained, just not used

---

## Behaviour Details

- Only one panel open at a time — opening a second closes the first
- Selecting a level resets selectedDevice to `null` (existing Zustand behaviour via `selectLevel`)
- Click-outside uses a single `mousedown` listener on `document`, removed on unmount
- On mobile the strip scrolls horizontally if viewport is narrow (the strip uses `overflow-x-auto` on its wrapper)

---

## What Does NOT Change

- Color palette, fonts, animation style
- Zustand store shape
- All downstream components (HealthIndexChart, ScoreCardsGrid, etc.) receive the same props/state as before
- `scroll-margin-top` values on `#prediction-section` and `#dashboard` remain valid since the new bar is the same height (~44px) as before
