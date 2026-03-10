# WACH-INSIGHT UI Revamp — Implementation Plan

> **Target coder:** Qwen3 80B 4-bit  
> **Stack:** React (Vite) + Tailwind CSS + Recharts/Plotly + Framer Motion  
> **Design DNA:** Dark luxurious industrial — inspired by [resourcedm.com](https://www.resourcedm.com/)

---

## 1  Design System & Tokens

### 1.1  Colour Palette

Derive every colour from CSS custom properties on `:root`.

| Token | Hex | Usage |
|---|---|---|
| `--bg-primary` | `#0B0F14` | Page background (near-black with a cool blue undertone) |
| `--bg-secondary` | `#111820` | Card / panel surfaces |
| `--bg-tertiary` | `#1A2230` | Elevated surfaces, modals, chat window |
| `--border-subtle` | `#1E2A3A` | Card borders, dividers |
| `--border-accent` | `#00E5A0` | Accent ring on hover / focus (the RDM teal-green) |
| `--text-primary` | `#E8ECF1` | Headings, primary body |
| `--text-secondary` | `#8A95A5` | Descriptions, secondary copy |
| `--accent` | `#00E5A0` | CTA buttons, active states, chart highlight colour |
| `--accent-glow` | `rgba(0,229,160,0.15)` | Glow / box-shadow behind accent elements |
| `--accent-secondary` | `#00B8D4` | Secondary chart colour, link hover |
| `--danger` | `#FF4D6A` | Unhealthy score, alerts |
| `--warning` | `#FFB020` | Moderate score band |
| `--success` | `#00E5A0` | Healthy score band (same as accent) |
| `--chart-1` through `--chart-5` | `#00E5A0, #00B8D4, #7C5CFC, #FF6B8A, #FFB020` | Five score series |

### 1.2  Typography

Use **two** Google Fonts:

| Role | Font | Weight | Size guideline |
|---|---|---|---|
| Display / H1 | **Plus Jakarta Sans** | 700–800 | 48–64 px |
| Headings H2–H4 | Plus Jakarta Sans | 600 | 24–36 px |
| Body | **DM Sans** | 400 / 500 | 15–16 px |
| Mono (data labels) | **JetBrains Mono** | 400 | 13 px |

Letter-spacing on display headings: `−0.02em`. Line-height body: `1.65`.

### 1.3  Spacing Scale

Use an 8 px base grid: `4, 8, 12, 16, 24, 32, 48, 64, 96, 128`.

### 1.4  Radius & Elevation

- Cards: `border-radius: 16px` with a `1px solid var(--border-subtle)` border.
- Elevated cards on hover: add `box-shadow: 0 0 40px var(--accent-glow)` and border transitions to `var(--border-accent)`.
- Buttons: `border-radius: 999px` (pill).
- Modals / chat: `border-radius: 20px`.

### 1.5  Micro-interactions (Framer Motion)

- **Entrance:** `y: 30 → 0, opacity: 0 → 1, duration: 0.6, ease: [0.22, 1, 0.36, 1]` (custom cubic).
- **Stagger children:** `staggerChildren: 0.08`.
- **Hover on cards:** `scale: 1.015, transition: { duration: 0.25 }`.
- **Chart fade-in:** `opacity 0 → 1` over 0.8 s after data loads.
- **Scroll-triggered reveals:** Use `whileInView` on every section with `viewport: { once: true, amount: 0.3 }`.

---

## 2  Page Architecture

The app is a **single-page scrollable experience** with four logical zones:

```
┌────────────────────────────────────────────────┐
│  ZONE A — Welcome Hero  (100 vh)               │
├────────────────────────────────────────────────┤
│  ZONE B — Dashboard unlock transition           │
├────────────────────────────────────────────────┤
│  ZONE C — Dashboard (scrollable)                │
│   ├─ Level selector bar (sticky)                │
│   ├─ Health Index overview chart                 │
│   ├─ Five-Score breakdown charts                 │
│   ├─ Device selector (conditional)               │
│   └─ Raw-data ↔ Score relationship charts        │
├────────────────────────────────────────────────┤
│  ZONE D — Floating chat widget (fixed pos)      │
└────────────────────────────────────────────────┘
```

---

## 3  ZONE A — Welcome Hero

### 3.1  Layout

Full-viewport (`h-screen`) section with vertically + horizontally centred content.

Background: CSS radial-gradient mesh —  
```css
background:
  radial-gradient(ellipse 60% 50% at 20% 30%, rgba(0,229,160,0.06), transparent),
  radial-gradient(ellipse 50% 60% at 80% 70%, rgba(0,184,212,0.05), transparent),
  var(--bg-primary);
```

Add a subtle animated noise overlay (`mix-blend-mode: overlay; opacity: 0.03`) using a small tiling SVG noise pattern for texture.

### 3.2  Content Hierarchy

1. **Logo / wordmark** — `WACH-INSIGHT` in Plus Jakarta Sans 800. The "WACH" part uses `color: var(--accent)`, the rest white. Displayed at ~20 px, uppercase, letter-spacing `0.15em`, positioned above the main heading.
2. **Main heading** (H1, 56 px):  
   > "Intelligent AHU Health Monitoring"  
   Fade in with `y:40→0` over 0.8 s.
3. **Sub-heading** (body, 18 px, `--text-secondary`, max-width 600 px, centred):  
   > "Real-time health scoring, trend analysis, and anomaly detection for your air handling units — across every level of your building."  
   Fade in staggered 0.15 s after heading.
4. **Capabilities pill badges** — a horizontal row of small rounded pills:  
   `Health Index` · `5-Score Breakdown` · `Device Drill-down` · `AI Chat Assistant`  
   Each pill: `bg: var(--bg-secondary), border: 1px solid var(--border-subtle), color: var(--text-secondary), font-size: 13px, padding: 6px 16px, border-radius: 999px`.  
   Stagger-animate in after sub-heading.
5. **Limitations disclaimer** — a smaller italic line (14 px, `--text-secondary`):  
   > "Note: Scores are model-derived estimates and should complement — not replace — physical inspections."
6. **Scroll CTA** — a downward-pointing animated chevron (`animate: { y: [0,8,0] }` loop) with the text "Scroll to explore" in 13 px mono.

### 3.3  Decorative Elements

- A faint wireframe outline of an AHU unit (SVG, `stroke: var(--border-subtle), stroke-width: 0.5`) positioned absolute behind the text, slightly rotated, at 20 % opacity. This adds the industrial IoT flavour from the RDM site without overwhelming.
- Floating dots/particles — 15–20 tiny circles (`2–4 px`) scattered, each with a slow CSS `@keyframes float` (translate-y ±10 px over 6–10 s, randomised delays). Colour: `var(--accent)` at 20 % opacity.

---

## 4  ZONE B — Dashboard Unlock Transition

### 4.1  Scroll-triggered Gate

As the user scrolls past the hero, a thin horizontal line (the "gate") expands from centre outward:

```
Implementation:
- A <div> with h-[2px] and bg: var(--accent).
- On scroll into view, animate scaleX from 0 → 1 (duration 0.6s, ease out).
- Simultaneously, text below fades in: "Dashboard" in H2 (36 px).
```

This is a purely cosmetic transition. No authentication or actual "unlocking" — just a visual beat that signals the shift from marketing copy to data.

### 4.2  Section Header

After the line:

```
DASHBOARD
─────────────────────  (the animated line)
"Select a building level to begin exploring AHU health data."
```

The word "DASHBOARD" is in Plus Jakarta Sans 700, letter-spacing `0.2em`, 14 px, `--text-secondary`, uppercase — like a label. Below it the H2 "AHU Health Overview" in 36 px white.

---

## 5  ZONE C — The Dashboard

### 5.1  Level Selector Bar

**Position:** `sticky top-0 z-30` with a `backdrop-blur-xl` and `bg: rgba(11,15,20,0.85)` so content scrolls behind it with a frosted-glass effect. Horizontal padding matches content max-width (1280 px centred).

**Content:**

```
[Level 1]  [Level 2]  [Level 3]  [Level 4]  [Level 5]  ...
```

- Each level is a **pill button**: idle state = transparent bg, `--text-secondary` text, `1px solid var(--border-subtle)`.
- Active state = `bg: var(--accent), color: var(--bg-primary)` (dark text on green), `box-shadow: 0 0 20px var(--accent-glow)`.
- Hover state = border colour transitions to `var(--accent)` over 0.2 s.
- The bar scrolls horizontally on mobile if there are many levels (`overflow-x: auto, scrollbar-hidden`).

**Behaviour:** Selecting a level triggers a React state change that cascades down to all chart components. All charts should show a skeleton/shimmer loading state for 300–500 ms before rendering new data (even if data is instant, add artificial delay for polish — the shimmer itself is a luxury cue).

### 5.2  Health Index Overview Chart

**Container:** Full-width card (`max-w-[1280px] mx-auto`), `bg: var(--bg-secondary)`, `border: 1px solid var(--border-subtle)`, `border-radius: 16px`, internal padding `32px`.

**Chart spec:**

| Property | Value |
|---|---|
| Library | Recharts `<AreaChart>` (or Plotly for richer interactivity) |
| X-axis | Time (datetime) — formatted as `MMM DD` or `HH:mm` depending on range |
| Y-axis | Health Index (0–100) |
| Series | One line per AHU in the selected level, each labelled |
| Fill | Gradient area fill from `var(--accent)` at 30 % opacity → transparent |
| Stroke | 2 px, coloured per-device from `chart-1…chart-5` palette, cycling |
| Grid lines | Horizontal only, `stroke: var(--border-subtle)`, dashed |
| Tooltip | Custom: dark bg (`--bg-tertiary`), `border-radius: 12px`, shows device name + index value + timestamp |
| Legend | Below chart, horizontal, dot + label style |

**Header inside card:**
```
Health Index — Level {n}
{count} AHUs monitored  ·  Last updated {timestamp}
```
H3 in 24 px white. Meta line in 14 px `--text-secondary`.

**Interaction:** Hovering a legend item highlights that AHU's line and dims others to 20 % opacity (use Recharts' `onMouseEnter` on Legend items to set active state).

### 5.3  Five-Score Breakdown

Below the health index chart, render **five cards in a responsive grid** (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6`).

Each card represents one of the five component scores. Each card contains:

1. **Score label** (e.g., "Temperature Score") — 16 px, 600 weight.
2. **Current average** — large number (`36 px, JetBrains Mono 700`), coloured by health band:
   - `>=80 → var(--success)`
   - `50–79 → var(--warning)`
   - `<50 → var(--danger)`
3. **Sparkline** — a small `<LineChart>` (Recharts, 100 % width, 80 px height, no axes, no grid) showing the trend over the selected time range.
   - Stroke: corresponding `--chart-n` colour.
   - Area fill: same colour at 10 % opacity.
4. **Trend indicator** — a small arrow (↑ or ↓) with percentage change vs previous period.

**Card styling:**
```css
background: var(--bg-secondary);
border: 1px solid var(--border-subtle);
border-radius: 16px;
padding: 24px;
transition: all 0.25s ease;
```
On hover: `border-color: var(--chart-n)` (matching that score's colour), subtle `box-shadow`.

Below the five summary cards, render a **full-width stacked or overlaid line chart** showing all five scores over time on a single plot. This gives a comparative view. Use distinct colours from the `chart-1…5` palette, with a toggle to show/hide individual scores.

### 5.4  Device Selector (Drill-down)

**Trigger:** Within the level view, provide a **device dropdown or horizontal scrollable chip row** directly below the level selector (or as a sub-bar).

```
All AHUs (default)  |  AHU-L1-01  |  AHU-L1-02  |  AHU-L1-03  |  ...
```

- Default = "All AHUs" (aggregate / multi-line view as described above).
- Selecting a specific device = **single-device mode**.

**Styling:** Same pill-button pattern as the level selector but slightly smaller (font 13 px). Active device gets an underline accent bar (`::after` pseudo-element, 2 px tall, `bg: var(--accent)`, animated width from 0 → 100 %).

### 5.5  Single-Device Mode — Extended Charts

When a specific device is selected, the dashboard morphs:

1. **Health Index chart** → now shows only that device's health index (single line, thicker stroke `3px`, prominent area fill).
2. **Five-Score cards** → values update to that device. Sparklines update.
3. **Five-Score combined chart** → single device's five scores.
4. **NEW SECTION — Raw Data ↔ Score Relationship Charts** (appears below, animated in with `whileInView`):

#### 5.5.1  Relationship Charts Container

A new card section with a header:

```
Score Derivation — {Device Name}
"Visualising how raw sensor data maps to computed scores over time."
```

Render **five chart panels** (one per score), each in its own card, arranged in a `grid-cols-1 lg:grid-cols-2 gap-6` grid (the fifth card spans full width or is centred).

Each panel contains a **dual-axis chart**:

| Axis | Content |
|---|---|
| Left Y-axis | Raw data value (e.g., temperature in °C, pressure in Pa, etc.) — coloured `--text-secondary` |
| Right Y-axis | Computed score (0–100) — coloured with the corresponding `--chart-n` |
| X-axis | Time |
| Series 1 | Raw data — rendered as a thin (`1.5px`) line, `--text-secondary` colour at 60 % opacity |
| Series 2 | Score — rendered as a thicker (`2.5px`) line in `--chart-n` colour with gradient area fill |

**Tooltip:** Shows both values at the hovered timestamp. Custom-styled matching the global tooltip design.

**Header per panel:**
```
{Score Name}
Raw: {metric name} ({unit})  →  Score: 0–100
```

This makes the causal relationship between raw signals and derived scores visually explicit.

#### 5.5.2  Transition Animation

When switching from all-device to single-device mode:

- Existing charts smoothly resize/reflow (Framer Motion `layout` prop on chart containers).
- New relationship charts slide up from below with `y:40→0, opacity:0→1`, staggered `0.1s` each.

When switching back to "All AHUs":

- Relationship charts slide down and fade out.
- Overview charts re-expand.

---

## 6  ZONE D — Chat Widget

### 6.1  Idle State (Collapsed)

**Position:** `fixed bottom-6 right-6 z-50`.

**Appearance:**  
- A circular button, `56px × 56px`.
- `bg: var(--accent)`, `border-radius: 50%`.
- Contains a chat-bubble SVG icon in `var(--bg-primary)` (dark).
- Constant subtle animation: `box-shadow` pulses between `0 0 0 0 var(--accent-glow)` and `0 0 0 12px var(--accent-glow)` on a 3 s loop — a gentle "breathing" glow.

**Hover state:**  
- Scale up to `1.1`.
- A small tooltip label appears above: "Chat with WACH AI" — fades in from below (y:8→0).
- The pulsing glow intensifies (`0 0 0 20px`).

### 6.2  Opening Animation

On click:

1. The circle **morphs** into a rounded rectangle chat window (`400px wide × 560px tall` on desktop, full-width on mobile). Use Framer Motion `layoutId` to animate the shape transition smoothly.
2. The icon inside cross-fades to a header bar.
3. Total animation duration: `0.45s`, custom spring `{ stiffness: 300, damping: 28 }`.

### 6.3  Open State — Chat Window

**Structure:**

```
┌─────────────────────────────────┐
│  HEADER BAR                     │  48px tall
│  "WACH AI" + status dot + ✕     │
├─────────────────────────────────┤
│                                 │
│  MESSAGE AREA (scrollable)      │  flex-1, overflow-y-auto
│                                 │
│  [Bot message bubble]           │
│            [User message bubble]│
│  [Bot typing indicator]         │
│                                 │
├─────────────────────────────────┤
│  INPUT BAR                      │  56px tall
│  [text input]        [send btn] │
└─────────────────────────────────┘
```

**Header bar:**
- `bg: var(--bg-tertiary)`, `border-bottom: 1px solid var(--border-subtle)`.
- Left: accent-coloured dot (8 px circle, `bg: var(--accent)`) + "WACH AI" in 14 px 600 weight.
- Right: close button (✕) — on click, reverses the morph animation.

**Message bubbles:**
- Bot: `bg: var(--bg-secondary), border-radius: 16px 16px 16px 4px`, left-aligned, max-width 85 %.
- User: `bg: var(--accent), color: var(--bg-primary), border-radius: 16px 16px 4px 16px`, right-aligned, max-width 85 %.
- Each bubble appears with a small pop animation (`scale: 0.9→1, opacity: 0→1, duration: 0.2s`).

**Typing indicator:**  
Three small dots (`6px`) in a row, each animating `opacity: 0.3→1→0.3` with staggered delays — the classic bouncing/pulsing dots.

**Input bar:**
- `bg: var(--bg-secondary)`, `border-top: 1px solid var(--border-subtle)`.
- Text input: no visible border, transparent bg, placeholder "Ask about your AHUs…" in `--text-secondary`.
- Send button: circular, `32px`, `bg: var(--accent)`, arrow-up icon in `--bg-primary`. Disabled state at 30 % opacity when input is empty.
- Submit on Enter key or button click.

**Initial bot message (on first open):**
> "Hey! I'm WACH AI. I can help you understand health scores, investigate anomalies, or explain what's driving a specific score. What would you like to know?"

### 6.4  Chat Backend Integration

The chat functionality is **pre-configured** — the plan assumes an existing API endpoint. Wire up:

```
POST /api/chat
Body: { message: string, context: { level: number, device: string | null } }
Response: { reply: string }
```

Pass the current dashboard context (selected level, selected device) with each message so the chatbot can give contextual answers.

### 6.5  Closing Animation

Reverse of opening: the rectangle morphs back to the circle, content cross-fades back to the chat icon. `0.35s` duration.

---

## 7  Responsive Breakpoints

| Breakpoint | Name | Key adaptations |
|---|---|---|
| `<640px` | Mobile | Single-column grid. Chat opens full-screen. Level selector horizontal scroll. Charts reduce height to 200 px. Hide sparklines on score cards. |
| `640–1024px` | Tablet | 2-column grid for score cards. Chat stays as floating panel (340 px wide). |
| `1024–1280px` | Desktop | 3-column grid. Full chart heights (320 px). |
| `>1280px` | Wide | 5-column grid for score cards. Content max-width 1280 px centred. |

---

## 8  Component Tree (React)

```
<App>
  ├── <WelcomeHero />
  │     ├── <FloatingParticles />
  │     ├── <AHUWireframeSVG />
  │     ├── <CapabilityPills />
  │     └── <ScrollCTA />
  │
  ├── <DashboardGate />          ← the animated line transition
  │
  ├── <Dashboard>
  │     ├── <LevelSelectorBar />          ← sticky
  │     ├── <DeviceSelector />            ← sub-bar, conditional chips
  │     ├── <HealthIndexChart />          ← AreaChart, multi or single line
  │     ├── <ScoreCardsGrid>
  │     │     └── <ScoreCard /> × 5       ← sparkline + big number
  │     ├── <CombinedScoresChart />       ← overlaid 5-score line chart
  │     └── <ScoreDerivationSection>      ← only in single-device mode
  │           └── <RawScoreRelationChart /> × 5
  │
  └── <ChatWidget>
        ├── <ChatBubbleButton />          ← collapsed state
        └── <ChatWindow>                  ← expanded state
              ├── <ChatHeader />
              ├── <MessageList />
              │     ├── <BotMessage />
              │     ├── <UserMessage />
              │     └── <TypingIndicator />
              └── <ChatInput />
```

### 8.1  Key State

```typescript
interface AppState {
  selectedLevel: number | null;         // null = no level selected yet
  selectedDevice: string | null;        // null = "All AHUs"
  chatOpen: boolean;
  chatMessages: ChatMessage[];
  dashboardData: {
    healthIndex: TimeSeriesData[];
    scores: Record<ScoreName, TimeSeriesData[]>;
    devices: Device[];
    rawData: Record<ScoreName, TimeSeriesData[]>;  // per-device only
  } | null;
  isLoading: boolean;
}
```

Use React Context or Zustand for state management. Zustand is preferred for simplicity.

---

## 9  Data Contracts (API Shape)

Define TypeScript interfaces the frontend expects. The backend must match these.

```typescript
// GET /api/levels
type LevelsResponse = { levels: number[] };

// GET /api/level/:id/health-index
type HealthIndexResponse = {
  devices: { id: string; name: string; data: { timestamp: string; value: number }[] }[];
};

// GET /api/level/:id/scores
type ScoresResponse = {
  devices: {
    id: string;
    name: string;
    scores: Record<
      'temperature' | 'vibration' | 'pressure' | 'airflow' | 'energy',
      { current: number; trend: number; data: { timestamp: string; value: number }[] }
    >;
  }[];
};

// GET /api/device/:id/raw-score-relationship
type RawScoreResponse = {
  scores: Record<
    string,
    {
      rawMetric: string;
      rawUnit: string;
      rawData: { timestamp: string; value: number }[];
      scoreData: { timestamp: string; value: number }[];
    }
  >;
};
```

---

## 10  Skeleton / Loading States

Every data-dependent component must have a skeleton state:

- **Charts:** A card with the correct dimensions, containing 3–4 horizontal bars of `bg: var(--border-subtle)` with a shimmer animation (`background-position` sliding left→right, `linear-gradient(90deg, var(--border-subtle), var(--bg-tertiary), var(--border-subtle))`, `animation: shimmer 1.5s infinite`).
- **Score cards:** Same shimmer over a placeholder rectangle for the number and sparkline area.
- **Level selector:** Shimmer-filled pill shapes.

---

## 11  Accessibility

- All interactive elements must be keyboard-navigable (`tabIndex`, `onKeyDown` for Enter/Space).
- Chart data should have an `aria-label` summary (e.g., "Health index chart for Level 1 showing 5 AHUs over the past 7 days").
- Colour is never the sole indicator — scores also show the numeric value.
- Chat widget: `aria-live="polite"` on the message area for screen readers.
- Contrast ratios: `--text-primary` on `--bg-primary` ≥ 7:1 (AAA). `--text-secondary` on `--bg-primary` ≥ 4.5:1 (AA).

---

## 12  Performance Notes

- **Lazy-load** the `<ScoreDerivationSection>` (code-split with `React.lazy` + `Suspense`) since it only renders in single-device mode.
- **Virtualise** the chat message list if it grows long (use `react-virtuoso`).
- **Debounce** level/device selection to avoid rapid re-fetches (200 ms).
- **Memoize** chart components with `React.memo` and stable keys — Recharts re-renders are expensive.
- Charts should receive data as props, not fetch internally, so parent can manage caching.

---

## 13  File Structure

```
src/
├── main.tsx
├── App.tsx
├── index.css                        ← Tailwind directives + CSS variables
├── store/
│   └── useAppStore.ts               ← Zustand store
├── api/
│   └── client.ts                    ← Fetch wrappers for all endpoints
├── components/
│   ├── welcome/
│   │   ├── WelcomeHero.tsx
│   │   ├── FloatingParticles.tsx
│   │   ├── AHUWireframeSVG.tsx
│   │   ├── CapabilityPills.tsx
│   │   └── ScrollCTA.tsx
│   ├── dashboard/
│   │   ├── DashboardGate.tsx
│   │   ├── Dashboard.tsx
│   │   ├── LevelSelectorBar.tsx
│   │   ├── DeviceSelector.tsx
│   │   ├── HealthIndexChart.tsx
│   │   ├── ScoreCardsGrid.tsx
│   │   ├── ScoreCard.tsx
│   │   ├── CombinedScoresChart.tsx
│   │   └── derivation/
│   │       ├── ScoreDerivationSection.tsx
│   │       └── RawScoreRelationChart.tsx
│   ├── chat/
│   │   ├── ChatWidget.tsx
│   │   ├── ChatBubbleButton.tsx
│   │   ├── ChatWindow.tsx
│   │   ├── ChatHeader.tsx
│   │   ├── MessageList.tsx
│   │   ├── BotMessage.tsx
│   │   ├── UserMessage.tsx
│   │   ├── TypingIndicator.tsx
│   │   └── ChatInput.tsx
│   └── shared/
│       ├── Skeleton.tsx
│       ├── Tooltip.tsx
│       └── PillButton.tsx
├── hooks/
│   ├── useHealthData.ts
│   ├── useScores.ts
│   └── useChat.ts
├── types/
│   └── index.ts                     ← All TypeScript interfaces
└── utils/
    ├── colors.ts                    ← Score-to-colour mapping helper
    └── format.ts                    ← Date/number formatters
```

---

## 14  Implementation Order (Suggested for Coder)

| Phase | What to build | Dependencies |
|---|---|---|
| **1** | Design tokens in `index.css`, Tailwind config, shared `PillButton` and `Skeleton` components | None |
| **2** | `WelcomeHero` with all sub-components and animations | Phase 1 |
| **3** | `DashboardGate` scroll animation | Phase 1 |
| **4** | `LevelSelectorBar` + `DeviceSelector` + Zustand store wiring | Phase 1 |
| **5** | `HealthIndexChart` with mock data | Phase 4 |
| **6** | `ScoreCardsGrid` + `ScoreCard` with sparklines | Phase 4 |
| **7** | `CombinedScoresChart` | Phase 4 |
| **8** | `ScoreDerivationSection` + `RawScoreRelationChart` (lazy loaded) | Phase 5–7 |
| **9** | `ChatWidget` full implementation (collapsed → expanded → messaging) | Phase 1 |
| **10** | API integration, loading states, error handling | Phase 5–9 |
| **11** | Responsive polish, accessibility audit, performance tuning | All |

---

## 15  Mock Data Generator

Include a `src/mocks/` folder with a generator function so the coder can develop the UI before the real API is ready:

```typescript
// src/mocks/generateMockData.ts
export function generateHealthIndex(deviceCount: number, points: number) {
  return Array.from({ length: deviceCount }, (_, i) => ({
    id: `ahu-${i + 1}`,
    name: `AHU-${String(i + 1).padStart(2, '0')}`,
    data: Array.from({ length: points }, (_, j) => ({
      timestamp: new Date(Date.now() - (points - j) * 3600000).toISOString(),
      value: 60 + Math.random() * 35 + Math.sin(j / 10) * 10,
    })),
  }));
}
// Similar generators for scores, raw data, etc.
```

---

## 16  Summary of Key Design Principles

1. **Dark, immersive, luxurious** — the RDM-inspired near-black backgrounds with teal/green accents create a command-centre feel.
2. **Progressive disclosure** — hero → gate → level → device → raw data. Each scroll reveals more depth.
3. **Motion with purpose** — every animation serves orientation (scroll reveals), feedback (hover states), or delight (chat morph). Nothing gratuitous.
4. **Data density without clutter** — generous spacing, card-based layout, and consistent colour coding keep dense data readable.
5. **Contextual AI** — the chatbot knows what level and device you're looking at, making it immediately useful.
