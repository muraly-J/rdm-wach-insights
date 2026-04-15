# Frontend Agentic Upgrade — Design Spec

**Date:** 2026-04-15
**Status:** Draft
**Depends on:** [Agentic System Plan](../plans/2026-04-14-agentic-system.md) (Tasks 1-13 backend)

## Context

The agentic system plan adds work orders, agent routing, Watchman alerts, and Telegram notifications to the backend. But the frontend only gets 2 tasks (14-15): extend chat types and add approve/dismiss buttons. This spec designs a maximal frontend upgrade — transforming the UI into a full agentic command center.

## Architecture: Incremental Layers

Three independently deployable layers. Each builds on the previous.

| Layer | Focus | Shippable alone? |
|-------|-------|-------------------|
| 1 | Chat Evolution | Yes |
| 2 | Work Order System | Yes (needs Layer 1 cards) |
| 3 | Polish Pass | Yes |

---

## Layer 1: Chat Evolution

Transform RDM-Atlas from a simple chatbot into a full assistant UX.

### 1.1 SSE Streaming Responses

**New backend endpoint:** `GET /api/chat/stream` (SSE)
- Accepts same payload as `POST /api/chat` via query params or initial POST
- Emits structured events:
  - `text_delta` — incremental text tokens
  - `tool_call_start` — agent is calling a tool (name, args)
  - `tool_call_result` — tool returned (name, result summary)
  - `actions` — ActionItem[] for HITL buttons
  - `navigate` — NavigateTarget for dashboard navigation
  - `done` — stream complete, includes full message for history

**Frontend:**
- New `useSSEChat` hook in `frontend/src/hooks/useSSEChat.ts`
- Uses `fetch` with `ReadableStream` (not `EventSource`) since SSE endpoint accepts POST body
- Progressive markdown rendering as tokens arrive
- Fallback: if SSE fails, fall back to existing `POST /api/chat`

**Files to create:**
- `frontend/src/hooks/useSSEChat.ts`

**Files to modify:**
- `frontend/src/components/chat/ChatWindow.tsx` — use `useSSEChat` instead of direct `sendChatMessage`
- `frontend/src/api/client.ts` — add SSE stream function

### 1.2 Structured Response Cards

Bot messages can contain embedded structured cards, rendered as React components instead of raw markdown.

**Card types:**

| Card | Data source | Renders |
|------|-------------|---------|
| `WorkOrderCard` | `ActionItem[]` from response | Draft work order with approve/dismiss/edit buttons |
| `AHUSummaryCard` | `ahu_summary` field in response | Compact FAIR scores, sparkline, severity badge |
| `ChartCard` | `chart_data` field in response | Inline Recharts chart (reuses existing chart components) |

**Implementation:**
- `BotMessage.tsx` checks for structured fields in the message object
- Each card type is a separate component in `frontend/src/components/chat/cards/`
- Cards parsed from JSON in bot response, not extracted from markdown

**Files to create:**
- `frontend/src/components/chat/cards/WorkOrderCard.tsx`
- `frontend/src/components/chat/cards/AHUSummaryCard.tsx`
- `frontend/src/components/chat/cards/ChartCard.tsx`

**Files to modify:**
- `frontend/src/components/chat/BotMessage.tsx` — render cards based on structured data
- `frontend/src/api/client.ts` — extend response types

### 1.3 Agent Reasoning Display

Collapsible section in bot messages showing tool calls the agent made.

- Collapsed by default, toggle via "Show reasoning" link
- Each tool call rendered as: `tool_name(args) → result_summary`
- Framer Motion expand/collapse animation
- Data comes from `tool_calls` array in SSE stream or response

**Files to modify:**
- `frontend/src/components/chat/BotMessage.tsx` — add collapsible reasoning section

### 1.4 Suggested Prompts

Contextual prompt suggestions that adapt to dashboard state and conversation.

**Initial state (no messages):**
- 4-6 prompts based on `selectedLevel` and `selectedDevice` from Zustand store
- Examples: "How is Level {N} performing?", "Any alerts for {device}?", "Show me the worst AHUs"

**After bot reply:**
- 2-3 follow-up suggestions derived from response context
- Backend returns `suggestions: string[]` in response

**Rendering:**
- Horizontal scrollable chip row below input field
- Click fills input and auto-submits
- Chips fade in with stagger animation

**Files to create:**
- `frontend/src/components/chat/SuggestedPrompts.tsx`

**Files to modify:**
- `frontend/src/components/chat/ChatWindow.tsx` — render SuggestedPrompts
- `frontend/src/api/client.ts` — add `suggestions` to response type

### 1.5 Conversation History Sidebar

Left sidebar visible in fullscreen chat mode. Stores past conversations locally.

**Storage:** `localStorage` key `rdm-atlas-history`
- Each conversation: `{ id, title, messages[], createdAt, updatedAt }`
- Title auto-generated from first user message (truncated to 50 chars)
- Max 50 conversations stored, oldest pruned on overflow

**UI:**
- Sidebar shows list of past conversations, grouped by date (Today, Yesterday, This Week, Older)
- Click to restore conversation into chat
- Delete button per conversation
- "New Chat" button at top
- Collapsible on click, hidden in panel mode (only visible in fullscreen)

**Files to create:**
- `frontend/src/components/chat/ConversationHistory.tsx`
- `frontend/src/hooks/useConversationHistory.ts`

**Files to modify:**
- `frontend/src/components/chat/ChatWindow.tsx` — integrate sidebar in fullscreen mode

### 1.6 Fullscreen Split View

Expand chat to fullscreen with dashboard visible alongside.

**Layout:**
- Chat: 40% width (left), Dashboard: 60% width (right)
- Dashboard responds to `navigate` commands from chat (e.g., switch level, highlight device)
- Toggle button in chat header switches between panel → fullscreen → split
- `chatMode` in Zustand store extended: `'panel' | 'fullscreen' | 'split'`

**Files to modify:**
- `frontend/src/App.tsx` — conditional layout when `chatMode === 'split'`
- `frontend/src/store/useAppStore.ts` — add `'split'` to chatMode type
- `frontend/src/components/chat/ChatHeader.tsx` — add split view toggle
- `frontend/src/components/chat/ChatWidget.tsx` — handle split mode rendering

---

## Layer 2: Work Order System

Three-tier UI for work order management.

### 2.1 Inline Chat Actions (Enhanced)

Extends the basic approve/dismiss from the agentic plan with richer interactions.

**WorkOrderCard features:**
- Severity badge: critical (red `#FF4D4D`), warning (amber `#FFB020`), info (blue `#4DA6FF`)
- State transitions animate: draft → loading spinner → "Ticket Submitted" with checkmark
- Edit mode: inline form for title/description, saves via `PATCH /api/work-orders/{id}`
- FAIR score snapshot displayed as mini horizontal bar chart
- AHU ID links to device detail in dashboard

**Files:**
- Uses `WorkOrderCard` from Layer 1 (1.2)
- `frontend/src/api/client.ts` — already has `approveWorkOrder`, `dismissWorkOrder`, `editWorkOrder` from agentic plan Task 14

### 2.2 Notification Badge + Slide-Out Panel

Persistent indicator of pending work orders, accessible from any view.

**Badge:**
- Icon button in top-right area (near chat bubble button position)
- Shows count of `status=draft` work orders
- Polls `GET /api/work-orders?status=draft` every 60s
- Badge pulses on count increase

**Slide-out panel:**
- Opens from right edge, overlays content (does not push layout)
- Grouped by severity (critical first, then warning, then info)
- Each item shows: AHU ID, level, title, severity badge, relative time ("2m ago")
- Quick actions: approve (green), dismiss (gray), expand to detail
- "View all" link navigates to full Work Orders dashboard

**Files to create:**
- `frontend/src/components/workorders/WorkOrderBadge.tsx`
- `frontend/src/components/workorders/WorkOrderPanel.tsx`
- `frontend/src/components/workorders/WorkOrderPanelItem.tsx`
- `frontend/src/hooks/useWorkOrderPolling.ts`

**Files to modify:**
- `frontend/src/App.tsx` — render badge and panel
- `frontend/src/store/useAppStore.ts` — add work order slice (drafts, panelOpen, selectedWorkOrder)

### 2.3 Dedicated Work Orders Dashboard View

Full-page view for work order management.

**Access:** New mode in dashboard mode toggle: `'simple' | 'deepdive' | 'workorders'`

**Components:**

**Stats Bar (top):**
- 4 metric cards: Total Open, Critical Count, Avg Time-to-Resolve, This Week vs Last Week delta
- Same card style as existing KPIStrip

**Table View:**
- Sortable columns: ID, AHU, Level, Severity, Status, Created, Trigger Source
- Filterable: status (multi-select), severity (multi-select), level (dropdown), date range
- Pagination: 20 per page
- Row click → detail modal

**Detail Modal:**
- Full work order info
- FAIR breakdown chart (reuses existing Recharts pattern)
- Status timeline: vertical stepper showing draft → approved → in_progress → resolved with timestamps
- Notes section (read-only for now, shows audit trail from backend)
- Action buttons: approve/dismiss (if draft), mark resolved (if in_progress)

**Files to create:**
- `frontend/src/components/workorders/WorkOrdersView.tsx` — main view container
- `frontend/src/components/workorders/WorkOrderStatsBar.tsx`
- `frontend/src/components/workorders/WorkOrderTable.tsx`
- `frontend/src/components/workorders/WorkOrderFilters.tsx`
- `frontend/src/components/workorders/WorkOrderDetailModal.tsx`
- `frontend/src/components/workorders/StatusTimeline.tsx`

**Files to modify:**
- `frontend/src/App.tsx` — add workorders mode rendering
- `frontend/src/store/useAppStore.ts` — extend dashboardMode, add work order filters/pagination state
- `frontend/src/components/dashboard/ModeToggle.tsx` — add "Work Orders" option

---

## Layer 3: Polish Pass

### 3.1 Transitions & Animations

- Framer Motion `layoutId` for shared-element transitions (work order card in chat → same card in panel/dashboard)
- `AnimatePresence` for: slide-out panel enter/exit, modal mount/unmount, fullscreen toggle
- Staggered entrance for card lists (`staggerChildren: 0.05`) and table rows
- Skeleton → content crossfade on data load

### 3.2 Loading States

- Skeleton variants for: work order table rows, chat streaming, dashboard cards during poll
- Reuses existing `Skeleton` component pattern from `frontend/src/components/shared/Skeleton.tsx`
- Pulse animation consistent with existing style

### 3.3 Action Feedback

- CSS-only toast notifications (bottom-right corner)
  - "Work order approved" (green), "Work order dismissed" (gray), "Error: ..." (red)
  - Auto-dismiss after 3 seconds, manual dismiss via X
  - No external library — simple component + CSS animation
- Button micro-interactions: `scale(0.97)` on press, color transition on state change

**Files to create:**
- `frontend/src/components/shared/Toast.tsx`
- `frontend/src/hooks/useToast.ts`

### 3.4 Responsive Design

- Chat split view → stacked layout below 1024px
- Work order panel → full-screen sheet below 768px
- Work order table → card layout below 768px
- All interactive elements: `min-h-[44px]` touch targets
- Existing dashboard already responsive — just audit new components

### 3.5 Polling Infrastructure

- `usePolling` hook: `(fetcher, intervalMs, options: { enabled, onError, pauseWhenHidden })`
- Pauses polling when `document.hidden === true` (Page Visibility API)
- Error retry: exponential backoff (1s, 2s, 4s, max 30s), resets on success
- Used by: work order badge (60s), optionally dashboard refresh

**Files to create:**
- `frontend/src/hooks/usePolling.ts`

---

## Zustand Store Extensions

New slices added to `useAppStore.ts`:

```
// Chat extensions
chatMode: 'panel' | 'fullscreen' | 'split'  // extend existing

// Work orders
workOrders: WorkOrder[]
workOrderDraftsCount: number
workOrderPanelOpen: boolean
workOrderFilters: { status: string[], severity: string[], level: number | null, dateRange: [string, string] | null }
workOrderPage: number
selectedWorkOrderId: number | null

// Dashboard mode extension
dashboardMode: 'simple' | 'deepdive' | 'workorders'  // extend existing
```

---

## New Files Summary

| File | Layer | Purpose |
|------|-------|---------|
| `hooks/useSSEChat.ts` | 1 | SSE streaming chat hook |
| `hooks/useConversationHistory.ts` | 1 | localStorage conversation persistence |
| `hooks/useWorkOrderPolling.ts` | 2 | Poll work order drafts count |
| `hooks/usePolling.ts` | 3 | Generic polling hook |
| `hooks/useToast.ts` | 3 | Toast notification state |
| `components/chat/cards/WorkOrderCard.tsx` | 1 | Inline work order card |
| `components/chat/cards/AHUSummaryCard.tsx` | 1 | AHU health summary card |
| `components/chat/cards/ChartCard.tsx` | 1 | Inline chart card |
| `components/chat/SuggestedPrompts.tsx` | 1 | Contextual prompt chips |
| `components/chat/ConversationHistory.tsx` | 1 | Conversation history sidebar |
| `components/workorders/WorkOrderBadge.tsx` | 2 | Nav badge with count |
| `components/workorders/WorkOrderPanel.tsx` | 2 | Slide-out panel |
| `components/workorders/WorkOrderPanelItem.tsx` | 2 | Panel list item |
| `components/workorders/WorkOrdersView.tsx` | 2 | Full dashboard view |
| `components/workorders/WorkOrderStatsBar.tsx` | 2 | Stats cards row |
| `components/workorders/WorkOrderTable.tsx` | 2 | Sortable/filterable table |
| `components/workorders/WorkOrderFilters.tsx` | 2 | Filter controls |
| `components/workorders/WorkOrderDetailModal.tsx` | 2 | Detail modal |
| `components/workorders/StatusTimeline.tsx` | 2 | Vertical status stepper |
| `components/shared/Toast.tsx` | 3 | Toast notification component |

## Modified Files Summary

| File | Layers | Changes |
|------|--------|---------|
| `api/client.ts` | 1, 2 | SSE stream function, extended response types, work order API functions |
| `store/useAppStore.ts` | 1, 2 | chatMode split, dashboardMode workorders, work order state slice |
| `App.tsx` | 1, 2, 3 | Split view layout, work order badge, workorders view mode |
| `components/chat/ChatWindow.tsx` | 1 | SSE hook, suggested prompts, conversation history |
| `components/chat/ChatWidget.tsx` | 1 | Split mode rendering |
| `components/chat/ChatHeader.tsx` | 1 | Split view toggle |
| `components/chat/BotMessage.tsx` | 1 | Structured cards, reasoning display |
| `components/chat/MessageList.tsx` | 1 | Pass card/action data to BotMessage |
| `components/dashboard/ModeToggle.tsx` | 2 | Add "Work Orders" option |

---

## Design Tokens

Consistent with existing dark luxury theme:

| Token | Value | Usage |
|-------|-------|-------|
| Severity Critical | `#FF4D4D` | Work order badges, alerts |
| Severity Warning | `#FFB020` | Work order badges |
| Severity Info | `#4DA6FF` | Work order badges |
| Success | `#00E5A0` | Approved state, existing accent |
| Surface Elevated | `#141920` | Cards, panels, modals |
| Border Subtle | `#1E2530` | Card borders, dividers |
| Text Muted | `#6d6e71` | Secondary text, timestamps |

---

## Backend Coordination

This spec assumes the agentic system backend (Tasks 1-13) is implemented. Additionally, Layer 1 requires:

- **New endpoint:** `GET /api/chat/stream` — SSE version of `/api/chat`
- **Response extension:** `suggestions: string[]` field in chat response
- **Response extension:** `tool_calls: Array<{name, args, result}>` in chat response
- **Response extension:** `ahu_summary` and `chart_data` optional fields for structured cards

These backend additions are small extensions of the existing chat route and should be specced in a companion backend task.

---

## Verification Plan

**Layer 1:**
1. Open chat → see suggested prompts based on current level
2. Send message → response streams in token-by-token
3. Bot shows reasoning (collapsible) with tool calls
4. Ask about AHU → AHUSummaryCard renders inline
5. Switch to fullscreen → conversation history sidebar appears
6. Switch to split view → dashboard visible alongside chat

**Layer 2:**
1. Ask bot to create work order → WorkOrderCard appears with approve/dismiss
2. Approve → card animates to "Ticket Submitted"
3. Badge in nav shows pending count
4. Click badge → slide-out panel with pending work orders
5. Navigate to Work Orders view → table with filters
6. Click row → detail modal with status timeline

**Layer 3:**
1. Cards animate in with stagger
2. Approve action → toast appears bottom-right, auto-dismisses
3. Resize window → responsive layouts activate
4. Switch tabs → polling pauses, resumes on return
