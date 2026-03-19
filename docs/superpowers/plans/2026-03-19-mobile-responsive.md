# Mobile Responsive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the WACH Insight frontend fully usable on 375–430px mobile screens for the Vercel deployment.

**Architecture:** Tailwind responsive prefixes (`sm:`, `md:`, `lg:`) applied to existing components — no new abstractions. Each component is patched independently. Vercel routing is already configured in `vercel.json`.

**Tech Stack:** React + TypeScript + Tailwind v3 (breakpoints: `sm` = 640px, `lg` = 1024px) + Framer Motion

---

## Tailwind Breakpoint Reference

| Prefix | Min-width | Targets |
|--------|-----------|---------|
| _(none)_ | 0px | Mobile phones (375–639px) |
| `sm:` | 640px | Tablets / large phones |
| `lg:` | 1024px | Desktops |

Test at 375px (iPhone SE) for worst-case.

---

## File Structure

| File | Change |
|------|--------|
| `frontend/src/components/welcome/WelcomeHero.tsx` | Responsive H1 + sub-heading font sizes |
| `frontend/src/components/dashboard/DashboardGate.tsx` | Responsive H2 font size |
| `frontend/src/App.tsx` | Responsive main container padding + time-range row |
| `frontend/src/components/dashboard/LevelSelectorBar.tsx` | Responsive container padding + pill sizes |
| `frontend/src/components/dashboard/ScoreCard.tsx` | Responsive card padding + number size |
| `frontend/src/components/dashboard/ScoreCardsGrid.tsx` | Responsive grid (biggest change — dual-layout approach) |
| `frontend/src/components/chat/ChatWindow.tsx` | Full-width mobile bottom sheet |
| `frontend/src/components/dashboard/HealthIndexChart.tsx` | Smaller heading on mobile |
| `frontend/src/components/financial/FinancialImpactView.tsx` | Responsive typography + header flex-wrap |

**Not changed** (already mobile-safe):
- `DeviceSelector.tsx` — already `flex flex-wrap`
- `TopCostAHUsTable.tsx` — already `overflow-x-auto`
- `ExpandableHealthRankings.tsx` — already `grid grid-cols-2` for summary
- `FinancialImpactView.tsx` loading skeleton — already `grid-cols-1 md:grid-cols-3`
- `vercel.json` — SPA rewrites + API proxy already configured

---

## How to verify each task

Open Chrome DevTools → toggle device toolbar → set **375 × 812** (iPhone SE). After each task, reload the dev server page and confirm no horizontal scroll and no overlapping text.

Run dev server: `cd frontend && npm run dev`

---

## Task 1: WelcomeHero — Responsive Typography

**File:** `frontend/src/components/welcome/WelcomeHero.tsx`

The H1 is fixed at `text-[56px]` (56px). On 375px wide screen this forces the text to overflow or wrap badly. Target: `text-[32px]` on mobile, scale up to `text-[56px]` at `sm:`.

- [ ] **Step 1: Open the file and identify the two size-sensitive lines**

  In `WelcomeHero.tsx`, find:
  - Line 65: `font-display text-[56px] font-bold leading-tight`
  - Line 78: `mt-4 text-[18px]`

- [ ] **Step 2: Apply responsive font sizes to H1 and sub-heading**

  Change line 65:
  ```tsx
  // Before
  className="
    font-display text-[56px] font-bold leading-tight
    tracking-[-0.02em]
  "

  // After
  className="
    font-display text-[32px] sm:text-[56px] font-bold leading-tight
    tracking-[-0.02em]
  "
  ```

  Change line 78:
  ```tsx
  // Before
  className="
    mt-4 text-[18px]
    text-[#8A95A5]
    max-w-[600px] mx-auto
  "

  // After
  className="
    mt-4 text-[15px] sm:text-[18px]
    text-[#8A95A5]
    max-w-[600px] mx-auto
  "
  ```

- [ ] **Step 3: Verify in browser at 375px**

  `cd frontend && npm run dev`, open `localhost:3000`, Chrome DevTools → 375×812.
  Expected: heading fits within viewport, no horizontal scroll on the hero.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/welcome/WelcomeHero.tsx
  git commit -m "fix(mobile): responsive hero typography for 375px screens"
  ```

---

## Task 2: DashboardGate — Responsive H2

**File:** `frontend/src/components/dashboard/DashboardGate.tsx`

The H2 `text-[36px]` "AHU Health Overview" is too large on mobile. Fix: `text-[24px] sm:text-[36px]`.

- [ ] **Step 1: Identify the className on line 49**

  ```tsx
  className="font-display text-[36px] font-bold leading-tight tracking-[-0.02em]"
  ```

- [ ] **Step 2: Apply responsive size**

  ```tsx
  // After
  className="font-display text-[24px] sm:text-[36px] font-bold leading-tight tracking-[-0.02em]"
  ```

- [ ] **Step 3: Verify at 375px**

  Scroll past hero; "AHU Health Overview" should be readable and not overflow.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/dashboard/DashboardGate.tsx
  git commit -m "fix(mobile): responsive DashboardGate heading"
  ```

---

## Task 3: App.tsx — Responsive Main Container Padding

**File:** `frontend/src/App.tsx`

The main content uses `px-6` (24px each side = 48px total consumed) on a 375px screen. This leaves only ~327px for content. Reduce to `px-4` on mobile.

Also the time-range picker row (`flex gap-2 justify-end`) is fine, but the "no level selected" state has `px-6` too.

- [ ] **Step 1: Find the two `px-6` instances in App.tsx**

  Line 198: `className="max-w-[1280px] mx-auto px-6 pt-8 pb-24"`
  Line 305: `className="max-w-[1280px] mx-auto px-6 py-16 text-center"`

- [ ] **Step 2: Make both responsive**

  ```tsx
  // Line 198 — before
  className="max-w-[1280px] mx-auto px-6 pt-8 pb-24"
  // after
  className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-6 sm:pt-8 pb-16 sm:pb-24"

  // Line 305 — before
  className="max-w-[1280px] mx-auto px-6 py-16 text-center"
  // after
  className="max-w-[1280px] mx-auto px-4 sm:px-6 py-16 text-center"
  ```

- [ ] **Step 3: Verify at 375px**

  Dashboard content should have 16px horizontal gutters. No horizontal scroll.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/App.tsx
  git commit -m "fix(mobile): responsive main layout padding"
  ```

---

## Task 4: LevelSelectorBar — Responsive Padding + Pill Sizes

**File:** `frontend/src/components/dashboard/LevelSelectorBar.tsx`

11 level pills at `px-5 py-2.5` each will overflow or wrap awkwardly at 375px. Reduce to `px-3 py-2` on mobile with smaller text.

- [ ] **Step 1: Find the container and pill classNames**

  Line 21: `<div className="max-w-[1280px] mx-auto px-6 py-4">`
  Line 38–46: the `className` on each `motion.button`

- [ ] **Step 2: Apply responsive padding to container**

  ```tsx
  // Before
  <div className="max-w-[1280px] mx-auto px-6 py-4">
  // After
  <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-3 sm:py-4">
  ```

- [ ] **Step 3: Apply responsive size to pills**

  The `px-5 py-2.5` in the button className:
  ```tsx
  // Before
  relative px-5 py-2.5 rounded-full text-sm font-medium
  // After
  relative px-3 sm:px-5 py-1.5 sm:py-2.5 rounded-full text-xs sm:text-sm font-medium
  ```

- [ ] **Step 4: Verify at 375px**

  All 11 level pills should wrap neatly into 2–3 rows without causing horizontal scroll.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/dashboard/LevelSelectorBar.tsx
  git commit -m "fix(mobile): responsive level selector pill sizing"
  ```

---

## Task 5: ScoreCard — Responsive Padding + Number Size

**File:** `frontend/src/components/dashboard/ScoreCard.tsx`

The large `text-[36px]` number and `p-6` padding are fine on desktop but need to shrink on mobile.

- [ ] **Step 1: Find the two classNames**

  Line 38: `className="card p-6 transition-all..."`
  Line 47: `className={\`font-mono text-[36px] font-bold ${numberColor}\`}`

- [ ] **Step 2: Apply responsive values**

  ```tsx
  // Line 38 — before
  className="card p-6 transition-all duration-0.25s ease hover:border-[#1E2A3A]"
  // after
  className="card p-4 sm:p-6 transition-all duration-0.25s ease hover:border-[#1E2A3A]"

  // Line 47 — before
  className={`font-mono text-[36px] font-bold ${numberColor}`}
  // after
  className={`font-mono text-[28px] sm:text-[36px] font-bold ${numberColor}`}
  ```

- [ ] **Step 3: Verify at 375px**

  Score cards should be readable and well-padded within their grid cells.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/dashboard/ScoreCard.tsx
  git commit -m "fix(mobile): responsive ScoreCard padding and number size"
  ```

---

## Task 6: ScoreCardsGrid — Responsive Layout (Most Complex)

**File:** `frontend/src/components/dashboard/ScoreCardsGrid.tsx`

**Current problem:** `grid grid-cols-6 gap-6` with `col-span-2` cards means each card is ~1/3 of the viewport wide. On 375px: `(375 - 5×24) / 6 × 2 ≈ 80px` per card — completely unusable.

**Approach:** Dual-layout. Hide the desktop 6-col grid on mobile; show a simple 1-col (mobile) / 2-col (sm) grid instead. The desktop layout is preserved exactly with `hidden lg:grid`.

- [ ] **Step 1: Read the current return JSX in `ScoreCardsGrid.tsx` (lines 167–205)**

  Identify the `<div className="grid grid-cols-6 gap-6 mb-6">` block and the safety flag grid block.

- [ ] **Step 2: Replace the score cards grid with dual-layout**

  Replace the existing `<div className="mb-8">` block (lines 168–205) with:

  ```tsx
  return (
    <div className="mb-8">
      {/* === MOBILE / TABLET: simple 1-col → 2-col grid === */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 lg:hidden">
        {SCORE_NAMES.map((score, index) => (
          <div key={score.key}>
            {renderCard(score, index)}
          </div>
        ))}
        {topScore && scoreData[topScore.score.key] && (
          <div className="sm:col-span-2">
            <SafetyFlagCard
              title={topScore.score.label}
              value={scoreData[topScore.score.key]!.current}
              trend={scoreData[topScore.score.key]!.trend}
              info={topScore.score.info}
              chartColor={SCORE_COLORS[topScore.index]}
              data={scoreData[topScore.score.key]!.data}
            />
          </div>
        )}
      </div>

      {/* === DESKTOP: original 6-col centered layout (unchanged) === */}
      <div className="hidden lg:block">
        {/* Row 1: 3 cards */}
        <div className="grid grid-cols-6 gap-6 mb-6">
          {SCORE_NAMES.slice(0, 3).map((score, index) => (
            <div key={score.key} className="col-span-2">
              {renderCard(score, index)}
            </div>
          ))}

          {/* Row 2: 2 cards centered */}
          <div className="col-span-1" />
          {SCORE_NAMES.slice(3, 5).map((score, index) => (
            <div key={score.key} className="col-span-2">
              {renderCard(score, index + 3)}
            </div>
          ))}
          <div className="col-span-1" />
        </div>

        {/* Row 3: Safety flag card centered */}
        {topScore && scoreData[topScore.score.key] && (
          <div className="grid grid-cols-6 gap-6">
            <div className="col-span-1" />
            <div className="col-span-4">
              <SafetyFlagCard
                title={topScore.score.label}
                value={scoreData[topScore.score.key]!.current}
                trend={scoreData[topScore.score.key]!.trend}
                info={topScore.score.info}
                chartColor={SCORE_COLORS[topScore.index]}
                data={scoreData[topScore.score.key]!.data}
              />
            </div>
            <div className="col-span-1" />
          </div>
        )}
      </div>
    </div>
  );
  ```

- [ ] **Step 3: Verify mobile at 375px**

  5 score cards stack in single column. Safety flag spans full width. No overflow.

- [ ] **Step 4: Verify desktop (1280px)**

  Switch DevTools to desktop. Original 3+2 centered layout and centered safety flag card preserved exactly.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/dashboard/ScoreCardsGrid.tsx
  git commit -m "fix(mobile): responsive ScoreCardsGrid with dual-layout approach"
  ```

---

## Task 7: ChatWindow — Full-Width Mobile Bottom Sheet

**File:** `frontend/src/components/chat/ChatWindow.tsx`

**Problem:** `fixed bottom-6 right-6 w-[400px]` — on 375px screen, 400px overflows by 25px plus 24px margin. The window clips off the left edge.

**Fix:** On mobile (`< sm`), display as a full-width bottom sheet anchored to the bottom edge with rounded top corners only.

- [ ] **Step 1: Find the `motion.div` root in `ChatWindow.tsx` (lines 92–107)**

  Current classNames:
  ```
  fixed bottom-6 right-6 z-50
  w-[400px]
  rounded-[20px]
  ```

- [ ] **Step 2: Replace position/size/rounding classNames**

  ```tsx
  // Before
  className="
    fixed bottom-6 right-6 z-50
    w-[400px]
    bg-[#0B0F14]
    rounded-[20px]
    overflow-hidden
    shadow-2xl border border-[#1E2A3A]
    flex flex-col
  "

  // After
  className="
    fixed z-50
    bottom-0 right-0 left-0 sm:bottom-6 sm:right-6 sm:left-auto
    w-full sm:w-[400px]
    bg-[#0B0F14]
    rounded-t-[20px] sm:rounded-[20px]
    overflow-hidden
    shadow-2xl border border-[#1E2A3A]
    flex flex-col
  "
  ```

- [ ] **Step 3: Make animated height responsive**

  The `animate` prop currently has `height: isMinimized ? 'auto' : 560`. On mobile, 560px out of ~812px is fine, but very short phones (667px) would clip. Add a viewport-aware height:

  ```tsx
  // Before
  animate={{ height: isMinimized ? 'auto' : 560, opacity: 1, scale: 1 }}

  // After
  animate={{
    height: isMinimized
      ? 'auto'
      : typeof window !== 'undefined' && window.innerWidth < 640
        ? Math.min(560, Math.floor(window.innerHeight * 0.82))
        : 560,
    opacity: 1,
    scale: 1,
  }}
  ```

- [ ] **Step 4: Verify at 375px**

  Open chat. Widget should span full width from left edge to right edge, anchored to bottom of screen. Close/minimize still works. No horizontal overflow.

- [ ] **Step 5: Verify at 1280px (desktop)**

  Widget appears in bottom-right at 400px wide with fully rounded corners. Unchanged from original.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/components/chat/ChatWindow.tsx
  git commit -m "fix(mobile): ChatWindow full-width bottom sheet on mobile"
  ```

---

## Task 8: HealthIndexChart — Responsive Heading

**File:** `frontend/src/components/dashboard/HealthIndexChart.tsx`

Minor: the `text-[24px]` chart heading is fine, but the `p-6` card padding burns mobile screen space. Also reduce chart height on mobile.

- [ ] **Step 1: Find classNames in HealthIndexChart.tsx**

  Line 112: `className="card p-6"`
  Line 119: `className="font-display text-[24px] font-bold tracking-[-0.01em] flex items-center"`
  Line 151: `<ResponsiveContainer width="100%" height={320}>`

- [ ] **Step 2: Apply responsive changes**

  ```tsx
  // Line 112
  // Before: "card p-6"
  // After:
  className="card p-4 sm:p-6"

  // Line 119
  // Before: "font-display text-[24px] font-bold..."
  // After:
  className="font-display text-[20px] sm:text-[24px] font-bold tracking-[-0.01em] flex items-center"
  ```

  For the chart height, wrap in a responsive div instead of using the hardcoded `height={320}`:
  ```tsx
  // Before
  <ResponsiveContainer width="100%" height={320}>

  // After — keep 320 (ResponsiveContainer respects parent height; 320 is fine on mobile too)
  // No change needed here — ResponsiveContainer already handles width. 320px height is acceptable.
  ```

- [ ] **Step 3: Verify at 375px**

  Health Index card should have tighter padding. Heading readable. Chart fills width correctly.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/dashboard/HealthIndexChart.tsx
  git commit -m "fix(mobile): responsive HealthIndexChart padding and heading"
  ```

---

## Task 9: FinancialImpactView — Responsive Typography + Header

**File:** `frontend/src/components/financial/FinancialImpactView.tsx`

Two issues:
1. `text-[42px]` savings amount overflows on mobile (42px × ~8 chars = very wide)
2. Header `flex items-start justify-between` with a Configure button: on mobile with a long device name, this is cramped

- [ ] **Step 1: Find the relevant classNames**

  Line 72: `h3 className="font-display text-[28px] font-bold..."`
  Line 90: `div className="text-[42px] font-bold font-mono text-[#00E5A0]"`
  Line 69: `div className="flex items-start justify-between"`

- [ ] **Step 2: Apply responsive changes**

  ```tsx
  // Line 69 — header row: allow wrapping on mobile
  // Before
  <div className="flex items-start justify-between">
  // After
  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">

  // Line 72
  // Before
  className="font-display text-[28px] font-bold tracking-[-0.01em]"
  // After
  className="font-display text-[22px] sm:text-[28px] font-bold tracking-[-0.01em]"

  // Line 90
  // Before
  className="text-[42px] font-bold font-mono text-[#00E5A0]"
  // After
  className="text-[30px] sm:text-[42px] font-bold font-mono text-[#00E5A0]"
  ```

- [ ] **Step 3: Verify at 375px**

  Financial section: heading readable, savings amount fits in one line, Configure button stacks below title on mobile.

- [ ] **Step 4: Verify at 640px+ (tablet)**

  Header returns to side-by-side layout.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/financial/FinancialImpactView.tsx
  git commit -m "fix(mobile): responsive FinancialImpactView typography and header layout"
  ```

---

## Task 10: End-to-End Mobile Verification

No code changes — pure verification pass.

- [ ] **Step 1: Start dev server**

  ```bash
  cd frontend && npm run dev
  ```

- [ ] **Step 2: Chrome DevTools 375×812 — walk through each section**

  Checklist:
  - [ ] WelcomeHero: heading fits, no horizontal scroll
  - [ ] DashboardGate: "AHU Health Overview" fits
  - [ ] LevelSelectorBar: 11 pills wrap neatly in 2–3 rows
  - [ ] DeviceSelector: chips wrap neatly
  - [ ] HealthIndexChart: chart fills width, heading readable
  - [ ] ScoreCardsGrid: 5 cards stack 1-col, safety flag full-width
  - [ ] ExpandableHealthRankings: 2-col summary cards side by side; expanded list readable
  - [ ] CombinedScoresChart: chart fills width (ResponsiveContainer handles this)
  - [ ] FinancialImpactView: header wraps, savings number fits, 3 breakdown cards stack 1-col
  - [ ] TopCostAHUsTable: horizontal scroll works without breaking layout
  - [ ] ChatWidget bubble: visible in bottom-right, not clipped
  - [ ] ChatWindow open: full-width bottom sheet, no overflow

- [ ] **Step 3: Chrome DevTools 768×1024 (iPad)**

  Everything should look correct at intermediate size.

- [ ] **Step 4: Desktop 1280px**

  Original desktop layout completely unchanged.

- [ ] **Step 5: Build check**

  ```bash
  cd frontend && npm run build
  ```
  Expected: no TypeScript errors, build succeeds.

- [ ] **Step 6: Commit final verification note (optional)**

  ```bash
  git commit --allow-empty -m "chore: mobile responsive pass complete — verified 375px/768px/1280px"
  ```

---

## Summary of Changes

| Component | What changes |
|-----------|-------------|
| `WelcomeHero` | H1: `text-[56px]` → `text-[32px] sm:text-[56px]`; sub: `text-[18px]` → `text-[15px] sm:text-[18px]` |
| `DashboardGate` | H2: `text-[36px]` → `text-[24px] sm:text-[36px]` |
| `App.tsx` | `px-6` → `px-4 sm:px-6` on main container |
| `LevelSelectorBar` | `px-6` → `px-4 sm:px-6`; pill `px-5 py-2.5 text-sm` → `px-3 sm:px-5 py-1.5 sm:py-2.5 text-xs sm:text-sm` |
| `ScoreCard` | `p-6` → `p-4 sm:p-6`; number `text-[36px]` → `text-[28px] sm:text-[36px]` |
| `ScoreCardsGrid` | Dual-layout: mobile 1-col/2-col grid hidden on lg; desktop 6-col layout hidden below lg |
| `ChatWindow` | Full-width bottom sheet on mobile; `w-[400px]` fixed → `w-full sm:w-[400px]` |
| `HealthIndexChart` | `p-6` → `p-4 sm:p-6`; heading `text-[24px]` → `text-[20px] sm:text-[24px]` |
| `FinancialImpactView` | Header stacks on mobile; `text-[28px]`/`text-[42px]` scaled down |
