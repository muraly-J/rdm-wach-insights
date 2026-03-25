# Dashboard Controls — Unified Strip Design Spec

## Context

The current dashboard has three separate sticky/inline control areas:
- `LevelSelectorBar` — full-width sticky bar with 11 level pill buttons
- `DeviceSelector` — horizontal chip row (inside sticky wrapper in App.tsx)
- Time range buttons — inline buttons (24h / 7d / 30d)

These will be replaced by a single compact **Unified Strip** with floating panel dropdowns.

---

## Design

### The Strip

A single sticky bar (`sticky top-0 z-30`, backdrop-blur) containing one pill-shaped container with three tappable segments divided by separators:

```
[ LVL · 4 | DEV · e0413 | RANGE · 7d ]
```

- Strip is left-aligned inside the `max-w-[1280px] mx-auto px-4 sm:px-6` container
- Open segment gets a light `#1A2330` highlight background
- RANGE segment always renders in `#00E5A0` (a range is always active)
- LVL segment renders in `#00E5A0` when a level is selected, `#8A95A5` otherwise
- DEV segment renders in `#00E5A0` when a specific device is selected (not All), `#8A95A5` for All or disabled

### Segments

| Segment | Label | Display when selected | Display when default/none |
|---------|-------|-----------------------|--------------------------|
| Level | `LVL` | `Level 4` | `—` |
| Device | `DEV` | device id e.g. `e0413` | `All` |
| Range | `RANGE` | `7d` | n/a — always has a value |

**Disabled DEV state:** colour `#4A5568`, cursor default, click ignored, shows `DEV · —`. Active only after a level is selected.

**No level deselect:** There is no "clear level" affordance. Once a level is selected, the only way to show no-level state is a page refresh. This is intentional — the no-level state is an onboarding prompt, not a persistent mode.

### Floating Panels

Each segment opens a floating panel directly below it on click. Closes on outside click or option selection. Only one panel open at a time.

**Panel style:** `background: #141D28`, `border: 1px solid #1E2A3A`, `border-radius: 10px`, `box-shadow: 0 8px 32px rgba(0,0,0,0.5)`, `min-width: 140px`, `z-index: 50`.

**Panel positioning:** Left-edge of panel aligns to left-edge of its trigger segment. If this would cause the panel to overflow the right edge of the viewport, shift it left so it stays within `8px` of the viewport edge.

**Level panel:** Plain list, items `Level 1` → `Level 11`. Selected item shown in `#00E5A0` with a `●` dot indicator.

**Device panel:** Search input at top (`placeholder: "Search…"`), then scrollable list: `All AHUs` first, then individual devices shown as `device.id` with `title="${device.label} — ${device.department}"` for tooltip. Max height `240px`, overflow-y scroll.
- If `devices.length === 0` (level selected but data still loading or empty), show `All AHUs` only with a single disabled row reading `No devices available`.

**Range panel:** Three items — `24h`, `7d`, `30d`. Selected item in `#00E5A0`. Defined as an internal constant inside the component — not a prop.

---

## Architecture

### New file
`frontend/src/components/dashboard/DashboardControls.tsx`

- Single exported component `DashboardControls`
- Internal `DropdownSegment` sub-component (not exported) handles open/close/panel logic
- Reads ALL state from Zustand directly — no props for selection state:
  - `selectedLevel`, `selectLevel`
  - `selectedDevice`, `selectDevice`
  - `timeRange`, `setTimeRange`
  - (All are already in `useAppStore`)
- Single prop: `devices` (needed because it comes from API data in App.tsx, not the store)

```tsx
interface DashboardControlsProps {
  devices: Array<{ id: string; name: string; label?: string; department?: string }>;
}
```

### App.tsx changes
- Remove `<LevelSelectorBar />` import and usage
- Remove the sticky `<div>` wrapping `DeviceSelector` + time buttons
- Add `<DashboardControls devices={devices} />`
- Remove `timeRange` / `setTimeRange` / `TIME_RANGES` props passed to other components — they now read from the store or `DashboardControls` handles them internally

### scroll-margin-top update
The current layout has two stacked sticky bars (LevelSelectorBar ~100px + device/time bar). The new single bar will be shorter (~52px). The `scroll-mt-4` class on `#prediction-section` and the `top-[100px]` on the old sticky device bar must be updated during implementation once the actual rendered height is measured. The implementation task should verify and correct these values.

### Files kept but no longer rendered
- `LevelSelectorBar.tsx` — retained, not rendered
- `DeviceSelector.tsx` — retained, not rendered

---

## Behaviour Details

- Only one panel open at a time — opening a second panel closes the first
- Selecting a level calls `selectLevel(n)` which resets `selectedDevice` to null via existing store logic
- Click-outside uses a single `mousedown` listener on `document`, removed on unmount
- On narrow viewports the strip wraps with `overflow-x-auto` on its outer wrapper so it never causes horizontal overflow on the page
- Device search filters `device.id` case-insensitively against the input value

---

## What Does NOT Change

- Color palette, fonts, animation style
- Zustand store shape
- All downstream components (HealthIndexChart, ScoreCardsGrid, etc.) are unaffected
