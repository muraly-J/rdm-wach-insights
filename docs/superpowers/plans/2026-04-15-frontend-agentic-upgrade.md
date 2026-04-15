# Frontend Agentic Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the WACH Insight frontend from a read-only dashboard with basic chat into a full agentic command center — rich streaming chat, work order management across three UI tiers, and polished interactions.

**Architecture:** Three incremental layers, each independently deployable. Layer 1 evolves the chat (SSE streaming, structured cards, reasoning display, suggested prompts, conversation history, split view). Layer 2 adds a three-tier work order system (inline chat actions, notification badge + slide-out panel, dedicated dashboard view). Layer 3 polishes everything (animations, toasts, responsive design, polling infrastructure).

**Tech Stack:** React 18, TypeScript, Zustand 5, Recharts 2, Framer Motion 12, Tailwind CSS 3, Vite 7

**Spec:** `docs/superpowers/specs/2026-04-15-frontend-agentic-upgrade-design.md`

---

## File Map

**Create:**
- `frontend/src/types/chat.ts` — consolidated Message, ActionItem, WorkOrder types
- `frontend/src/hooks/useSSEChat.ts` — SSE streaming chat hook
- `frontend/src/hooks/useConversationHistory.ts` — localStorage conversation persistence
- `frontend/src/hooks/usePolling.ts` — generic polling hook with visibility pause
- `frontend/src/hooks/useToast.ts` — toast notification state manager
- `frontend/src/components/chat/cards/WorkOrderCard.tsx` — inline work order card
- `frontend/src/components/chat/cards/AHUSummaryCard.tsx` — AHU health summary card
- `frontend/src/components/chat/cards/ChartCard.tsx` — inline chart card
- `frontend/src/components/chat/SuggestedPrompts.tsx` — contextual prompt chips
- `frontend/src/components/chat/AgentReasoning.tsx` — collapsible tool-call display
- `frontend/src/components/chat/ConversationHistory.tsx` — conversation history sidebar
- `frontend/src/components/workorders/WorkOrderBadge.tsx` — nav badge with count
- `frontend/src/components/workorders/WorkOrderPanel.tsx` — slide-out panel
- `frontend/src/components/workorders/WorkOrderPanelItem.tsx` — panel list item
- `frontend/src/components/workorders/WorkOrdersView.tsx` — full dashboard view
- `frontend/src/components/workorders/WorkOrderStatsBar.tsx` — stats cards row
- `frontend/src/components/workorders/WorkOrderTable.tsx` — sortable/filterable table
- `frontend/src/components/workorders/WorkOrderFilters.tsx` — filter controls
- `frontend/src/components/workorders/WorkOrderDetailModal.tsx` — detail modal
- `frontend/src/components/workorders/StatusTimeline.tsx` — vertical status stepper
- `frontend/src/components/shared/Toast.tsx` — toast notification component

**Modify:**
- `frontend/src/api/client.ts` — SSE stream function, extended response types, work order API
- `frontend/src/store/useAppStore.ts` — chatMode split, dashboardMode workorders, work order state
- `frontend/src/App.tsx` — split view layout, work order badge, workorders view mode
- `frontend/src/components/chat/ChatWidget.tsx` — split mode rendering, use consolidated types
- `frontend/src/components/chat/ChatWindow.tsx` — SSE hook, suggested prompts, conversation history
- `frontend/src/components/chat/ChatHeader.tsx` — split view toggle button
- `frontend/src/components/chat/BotMessage.tsx` — structured cards, reasoning display, actions
- `frontend/src/components/chat/MessageList.tsx` — pass card/action data to BotMessage
- `frontend/src/components/dashboard/ModeToggle.tsx` — add "Work Orders" option

---

## Layer 1: Chat Evolution

---

## Task 1: Consolidate Message Types

The `Message` interface is duplicated in ChatWidget.tsx (line 8), ChatWindow.tsx (line 10), and MessageList.tsx (line 9). The store has a separate `ChatMessage` type with `timestamp`. Consolidate into one source of truth before adding new fields.

**Files:**
- Create: `frontend/src/types/chat.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/chat/ChatWidget.tsx`
- Modify: `frontend/src/components/chat/ChatWindow.tsx`
- Modify: `frontend/src/components/chat/MessageList.tsx`
- Modify: `frontend/src/components/chat/BotMessage.tsx`

- [ ] **Step 1: Create the consolidated types file**

Create `frontend/src/types/chat.ts`:

```typescript
import { NavigateTarget } from '../api/client';

export interface ActionItem {
  type: 'approve_work_order' | 'dismiss' | 'edit_draft';
  work_order_id: number;
  label: string;
  description: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

export interface AHUSummary {
  ahu_id: string;
  level: number;
  fair: { F: number; A: number; I: number; R: number; composite: number };
  severity: 'critical' | 'warning' | 'info' | 'healthy';
}

export interface ChartCardData {
  title: string;
  entries: Array<{ device: string; value: number }>;
  unit: string;
}

export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
  actions?: ActionItem[];
  tool_calls?: ToolCall[];
  ahu_summary?: AHUSummary | null;
  chart_data?: ChartCardData | null;
  suggestions?: string[];
}

export interface WorkOrder {
  id: number;
  ahu_id: string;
  level: number;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  trigger_source: string;
  fair_snapshot: Record<string, number> | null;
  notified_via: string;
  approved_by: string | null;
}
```

- [ ] **Step 2: Add work order API functions to client.ts**

Open `frontend/src/api/client.ts`. After `sendChatMessage` (line 126), add:

```typescript
// ── Work Order API ──────────────────────────────────────────────────────────

export async function fetchWorkOrders(
  status?: string
): Promise<{ work_orders: import('../types/chat').WorkOrder[]; count: number }> {
  const params = status ? `?status=${status}` : '';
  return apiFetch(`/work-orders${params}`);
}

export async function approveWorkOrder(
  id: number
): Promise<{ id: number; status: string }> {
  return apiFetch(`/work-orders/${id}/approve`, { method: 'POST' });
}

export async function dismissWorkOrder(
  id: number
): Promise<{ id: number; status: string }> {
  return apiFetch(`/work-orders/${id}/dismiss`, { method: 'POST' });
}

export async function editWorkOrder(
  id: number,
  body: { title?: string; description?: string }
): Promise<{ id: number; updated: boolean }> {
  return apiFetch(`/work-orders/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}
```

- [ ] **Step 3: Update ChatWidget.tsx to use consolidated type**

In `frontend/src/components/chat/ChatWidget.tsx`:

Replace the local `Message` interface (lines 8-13) and the `NavigateTarget` import with:

```typescript
import { Message } from '../../types/chat';
```

Remove:
```typescript
import { NavigateTarget } from '../../api/client';

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
}
```

- [ ] **Step 4: Update ChatWindow.tsx to use consolidated type**

In `frontend/src/components/chat/ChatWindow.tsx`:

Replace the local `Message` interface (lines 10-15) and `NavigateTarget` import with:

```typescript
import { Message } from '../../types/chat';
import { NavigateTarget } from '../../api/client';
```

Remove:
```typescript
interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
}
```

Keep the `NavigateTarget` import since `handleNavigate` uses it.

- [ ] **Step 5: Update MessageList.tsx to use consolidated type**

In `frontend/src/components/chat/MessageList.tsx`:

Replace the local `Message` interface (line 9) and `NavigateTarget` import with:

```typescript
import { Message } from '../../types/chat';
import { NavigateTarget } from '../../api/client';
```

Remove:
```typescript
interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
}
```

- [ ] **Step 6: Update BotMessage.tsx imports**

In `frontend/src/components/chat/BotMessage.tsx`:

Add import at top:
```typescript
import { ActionItem } from '../../types/chat';
```

No interface changes yet — `BotMessageProps` will be extended in Task 5.

- [ ] **Step 7: Build to verify no type errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/chat.ts frontend/src/api/client.ts frontend/src/components/chat/ChatWidget.tsx frontend/src/components/chat/ChatWindow.tsx frontend/src/components/chat/MessageList.tsx frontend/src/components/chat/BotMessage.tsx
git commit -m "refactor: consolidate Message types and add work order API functions"
```

---

## Task 2: SSE Streaming Chat Hook

**Files:**
- Create: `frontend/src/hooks/useSSEChat.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add SSE stream function to client.ts**

In `frontend/src/api/client.ts`, add after the work order functions:

```typescript
// ── SSE Chat Stream ─────────────────────────────────────────────────────────

export interface SSEEvent {
  type: 'text_delta' | 'tool_call_start' | 'tool_call_result' | 'actions' | 'navigate' | 'suggestions' | 'ahu_summary' | 'chart_data' | 'done';
  data: unknown;
}

export async function* streamChat(
  message: string,
  options?: {
    level?: number;
    device?: string | null;
    financial_impact?: number | null;
    history?: Array<{ role: 'user' | 'model'; content: string }>;
    persona?: string | null;
  }
): AsyncGenerator<SSEEvent> {
  const { history, persona, ...context } = options ?? {};
  const url = `${API_BASE}/chat/stream`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({
      message,
      context,
      history: history ?? [],
      persona: persona ?? null,
    }),
  });

  if (!response.ok) {
    throw new Error(`Stream error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6).trim();
        if (jsonStr === '[DONE]') return;
        try {
          yield JSON.parse(jsonStr) as SSEEvent;
        } catch {
          // skip malformed JSON
        }
      }
    }
  }
}
```

Note: `API_BASE` and `API_KEY` are already defined at the top of `client.ts` (lines 3-4).

- [ ] **Step 2: Create useSSEChat hook**

Create `frontend/src/hooks/useSSEChat.ts`:

```typescript
import { useState, useCallback, useRef } from 'react';
import { streamChat, sendChatMessage } from '../api/client';
import type { Message, ToolCall, ActionItem } from '../types/chat';

interface UseSSEChatOptions {
  onNavigate?: (target: { level: number; device?: string; view?: string }) => void;
}

export function useSSEChat(options?: UseSSEChatOptions) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendStreaming = useCallback(
    async (
      text: string,
      messages: Message[],
      setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
      context: {
        level?: number;
        device?: string | null;
        financial_impact?: number | null;
        persona?: string | null;
      }
    ) => {
      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
      };

      const botMsgId = `bot-${Date.now()}`;
      const botMsg: Message = {
        id: botMsgId,
        role: 'bot',
        content: '',
        tool_calls: [],
        actions: [],
        suggestions: [],
      };

      setMessages((prev) => [...prev, userMsg, botMsg]);
      setIsStreaming(true);

      const history = messages
        .filter((m) => m.id !== messages[0]?.id)
        .map((m) => ({
          role: (m.role === 'bot' ? 'model' : 'user') as 'user' | 'model',
          content: m.content,
        }));

      try {
        const stream = streamChat(text, {
          level: context.level,
          device: context.device,
          financial_impact: context.financial_impact,
          history,
          persona: context.persona,
        });

        for await (const event of stream) {
          setMessages((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((m) => m.id === botMsgId);
            if (idx === -1) return prev;
            const msg = { ...updated[idx] };

            switch (event.type) {
              case 'text_delta':
                msg.content += event.data as string;
                break;
              case 'tool_call_start':
                msg.tool_calls = [
                  ...(msg.tool_calls ?? []),
                  event.data as ToolCall,
                ];
                break;
              case 'tool_call_result': {
                const result = event.data as { name: string; result: string };
                msg.tool_calls = (msg.tool_calls ?? []).map((tc) =>
                  tc.name === result.name ? { ...tc, result: result.result } : tc
                );
                break;
              }
              case 'actions':
                msg.actions = event.data as ActionItem[];
                break;
              case 'navigate':
                msg.navigate = event.data as Message['navigate'];
                if (msg.navigate && options?.onNavigate) {
                  options.onNavigate(msg.navigate);
                }
                break;
              case 'suggestions':
                msg.suggestions = event.data as string[];
                break;
              case 'ahu_summary':
                msg.ahu_summary = event.data as Message['ahu_summary'];
                break;
              case 'chart_data':
                msg.chart_data = event.data as Message['chart_data'];
                break;
              case 'done':
                break;
            }

            updated[idx] = msg;
            return updated;
          });
        }
      } catch {
        // SSE failed — fall back to non-streaming
        try {
          const data = await sendChatMessage(text, {
            level: context.level,
            device: context.device,
            financial_impact: context.financial_impact,
            history,
            persona: context.persona,
          });
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? {
                    ...m,
                    content: data.reply,
                    navigate: data.navigate ?? null,
                  }
                : m
            )
          );
        } catch {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? { ...m, content: 'Sorry, something went wrong. Please try again.' }
                : m
            )
          );
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [options]
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { sendStreaming, isStreaming, abort };
}
```

- [ ] **Step 3: Build to verify no type errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds. The hook is not wired up yet.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useSSEChat.ts frontend/src/api/client.ts
git commit -m "feat: add SSE streaming chat hook with fallback to POST"
```

---

## Task 3: Wire SSE Streaming into ChatWindow

**Files:**
- Modify: `frontend/src/components/chat/ChatWindow.tsx`

- [ ] **Step 1: Import and use the SSE hook**

In `frontend/src/components/chat/ChatWindow.tsx`, add import:

```typescript
import { useSSEChat } from '../../hooks/useSSEChat';
```

- [ ] **Step 2: Replace handleSendMessage with streaming version**

Inside the `ChatWindow` component, after the store reads (around line 52), add the hook:

```typescript
const { sendStreaming, isStreaming: sseStreaming } = useSSEChat({
  onNavigate: handleNavigate,
});
```

Replace the existing `handleSendMessage` function (lines 89-124) with:

```typescript
const handleSendMessage = useCallback(
  async (text: string) => {
    await sendStreaming(text, messages, setMessages, {
      level: selectedLevel ?? undefined,
      device: selectedDevice,
      financial_impact: financialImpact?.potential_annual_savings ?? null,
      persona: selectedPersona,
    });
  },
  [sendStreaming, messages, setMessages, selectedLevel, selectedDevice, financialImpact, selectedPersona]
);
```

Remove the old `isTyping` state (`const [isTyping, setIsTyping] = useState(false)`) and replace `isTyping` references with `sseStreaming`:

In the JSX, change:
```typescript
isTyping={isTyping}
```
to:
```typescript
isTyping={sseStreaming}
```

Remove the `sendChatMessage` import if it's no longer used directly.

- [ ] **Step 3: Build to verify no type errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/ChatWindow.tsx
git commit -m "feat: wire SSE streaming into ChatWindow with POST fallback"
```

---

## Task 4: Agent Reasoning Display

**Files:**
- Create: `frontend/src/components/chat/AgentReasoning.tsx`

- [ ] **Step 1: Create the AgentReasoning component**

Create `frontend/src/components/chat/AgentReasoning.tsx`:

```tsx
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ToolCall } from '../../types/chat';

interface AgentReasoningProps {
  toolCalls: ToolCall[];
}

export default function AgentReasoning({ toolCalls }: AgentReasoningProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!toolCalls.length) return null;

  return (
    <div style={{ marginTop: 8 }}>
      <button
        onClick={() => setIsOpen((v) => !v)}
        style={{
          background: 'none',
          border: 'none',
          color: '#556677',
          cursor: 'pointer',
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: 0,
        }}
      >
        <span style={{
          display: 'inline-block',
          transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
          transition: 'transform 150ms',
          fontSize: 10,
        }}>
          ▶
        </span>
        {toolCalls.length} tool call{toolCalls.length > 1 ? 's' : ''}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              marginTop: 6,
              padding: '8px 10px',
              background: '#0D1520',
              borderRadius: 8,
              border: '1px solid #1a2638',
              fontSize: 11,
              fontFamily: 'var(--font-mono)',
              color: '#8899aa',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}>
              {toolCalls.map((tc, i) => (
                <div key={i} style={{ lineHeight: 1.5 }}>
                  <span style={{ color: '#00E5A0' }}>{tc.name}</span>
                  <span style={{ color: '#556677' }}>
                    ({Object.entries(tc.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})
                  </span>
                  {tc.result && (
                    <span style={{ color: '#6d6e71' }}> → {tc.result}</span>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chat/AgentReasoning.tsx
git commit -m "feat: add collapsible AgentReasoning component for tool call display"
```

---

## Task 5: Structured Response Cards

**Files:**
- Create: `frontend/src/components/chat/cards/WorkOrderCard.tsx`
- Create: `frontend/src/components/chat/cards/AHUSummaryCard.tsx`
- Create: `frontend/src/components/chat/cards/ChartCard.tsx`
- Modify: `frontend/src/components/chat/BotMessage.tsx`
- Modify: `frontend/src/components/chat/MessageList.tsx`

- [ ] **Step 1: Create WorkOrderCard**

Create `frontend/src/components/chat/cards/WorkOrderCard.tsx`:

```tsx
import { useState } from 'react';
import { motion } from 'framer-motion';
import type { ActionItem } from '../../../types/chat';
import { approveWorkOrder, dismissWorkOrder, editWorkOrder } from '../../../api/client';

interface WorkOrderCardProps {
  actions: ActionItem[];
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#FF4D4D',
  warning: '#FFB020',
  info: '#4DA6FF',
};

export default function WorkOrderCard({ actions }: WorkOrderCardProps) {
  const [states, setStates] = useState<Record<number, 'idle' | 'loading' | 'done' | 'dismissed'>>({});
  const [editing, setEditing] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');

  // Group actions by work_order_id
  const byId: Record<number, ActionItem[]> = {};
  for (const a of actions) {
    if (!byId[a.work_order_id]) byId[a.work_order_id] = [];
    byId[a.work_order_id].push(a);
  }

  const handleApprove = async (woId: number) => {
    setStates((prev) => ({ ...prev, [woId]: 'loading' }));
    try {
      await approveWorkOrder(woId);
      setStates((prev) => ({ ...prev, [woId]: 'done' }));
    } catch {
      setStates((prev) => ({ ...prev, [woId]: 'idle' }));
    }
  };

  const handleDismiss = async (woId: number) => {
    setStates((prev) => ({ ...prev, [woId]: 'loading' }));
    try {
      await dismissWorkOrder(woId);
      setStates((prev) => ({ ...prev, [woId]: 'dismissed' }));
    } catch {
      setStates((prev) => ({ ...prev, [woId]: 'idle' }));
    }
  };

  const handleEdit = async (woId: number) => {
    await editWorkOrder(woId, { title: editTitle, description: editDesc });
    setEditing(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
      {Object.entries(byId).map(([idStr, items]) => {
        const woId = parseInt(idStr);
        const state = states[woId] ?? 'idle';
        const approveItem = items.find((i) => i.type === 'approve_work_order');
        const dismissItem = items.find((i) => i.type === 'dismiss');
        const editItem = items.find((i) => i.type === 'edit_draft');
        const severity = approveItem?.description.match(/severity[:\s]*(\w+)/i)?.[1] ?? 'info';

        if (state === 'dismissed') return null;

        return (
          <motion.div
            key={woId}
            layout
            style={{
              background: '#141920',
              border: `1px solid ${SEVERITY_COLORS[severity] ?? '#1a2638'}33`,
              borderRadius: 10,
              padding: '10px 14px',
            }}
          >
            {state === 'done' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#00E5A0', fontSize: 13 }}>
                <span>✓</span> Ticket Submitted
              </div>
            ) : editing === woId ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="Title"
                  style={{
                    background: '#0D1520', border: '1px solid #1a2638', borderRadius: 6,
                    padding: '6px 8px', color: '#E8ECF1', fontSize: 12, outline: 'none',
                  }}
                />
                <textarea
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="Description"
                  rows={2}
                  style={{
                    background: '#0D1520', border: '1px solid #1a2638', borderRadius: 6,
                    padding: '6px 8px', color: '#E8ECF1', fontSize: 12, outline: 'none', resize: 'none',
                  }}
                />
                <div style={{ display: 'flex', gap: 6 }}>
                  <button onClick={() => handleEdit(woId)} style={{
                    background: '#00E5A0', color: '#0B0F14', border: 'none', borderRadius: 16,
                    padding: '5px 12px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                  }}>Save</button>
                  <button onClick={() => setEditing(null)} style={{
                    background: 'none', color: '#6d6e71', border: '1px solid #1a2638', borderRadius: 16,
                    padding: '5px 12px', fontSize: 11, cursor: 'pointer',
                  }}>Cancel</button>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <span style={{
                    display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
                    background: SEVERITY_COLORS[severity] ?? '#4DA6FF',
                  }} />
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#E8ECF1' }}>
                    Work Order #{woId}
                  </span>
                  <span style={{
                    fontSize: 10, color: SEVERITY_COLORS[severity] ?? '#4DA6FF',
                    textTransform: 'uppercase', fontWeight: 600,
                  }}>
                    {severity}
                  </span>
                </div>
                <p style={{ fontSize: 11, color: '#8899aa', margin: '0 0 8px' }}>
                  {approveItem?.description ?? dismissItem?.description ?? ''}
                </p>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {approveItem && (
                    <button
                      disabled={state === 'loading'}
                      onClick={() => handleApprove(woId)}
                      style={{
                        background: '#00E5A0', color: '#0B0F14', border: 'none', borderRadius: 16,
                        padding: '5px 12px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                        opacity: state === 'loading' ? 0.5 : 1, minHeight: 28,
                      }}
                    >
                      {state === 'loading' ? '...' : approveItem.label}
                    </button>
                  )}
                  {editItem && (
                    <button
                      onClick={() => { setEditing(woId); setEditTitle(''); setEditDesc(''); }}
                      style={{
                        background: 'none', color: '#8899aa', border: '1px solid #1a2638', borderRadius: 16,
                        padding: '5px 12px', fontSize: 11, cursor: 'pointer',
                      }}
                    >
                      {editItem.label}
                    </button>
                  )}
                  {dismissItem && (
                    <button
                      disabled={state === 'loading'}
                      onClick={() => handleDismiss(woId)}
                      style={{
                        background: 'none', color: '#6d6e71', border: '1px solid #1a2638', borderRadius: 16,
                        padding: '5px 12px', fontSize: 11, cursor: 'pointer',
                        opacity: state === 'loading' ? 0.5 : 1, minHeight: 28,
                      }}
                    >
                      {dismissItem.label}
                    </button>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create AHUSummaryCard**

Create `frontend/src/components/chat/cards/AHUSummaryCard.tsx`:

```tsx
import type { AHUSummary } from '../../../types/chat';

interface AHUSummaryCardProps {
  summary: AHUSummary;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#FF4D4D',
  warning: '#FFB020',
  info: '#4DA6FF',
  healthy: '#00E5A0',
};

const FAIR_LABELS = ['F', 'A', 'I', 'R'] as const;

export default function AHUSummaryCard({ summary }: AHUSummaryCardProps) {
  const color = SEVERITY_COLORS[summary.severity] ?? '#4DA6FF';

  return (
    <div style={{
      background: '#141920',
      border: `1px solid ${color}33`,
      borderRadius: 10,
      padding: '10px 14px',
      marginTop: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{
          display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
          background: color,
        }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#E8ECF1' }}>
          {summary.ahu_id}
        </span>
        <span style={{ fontSize: 10, color: '#556677' }}>Level {summary.level}</span>
        <span style={{
          marginLeft: 'auto', fontSize: 10, color, textTransform: 'uppercase', fontWeight: 600,
        }}>
          {summary.severity}
        </span>
      </div>

      {/* FAIR score bars */}
      <div style={{ display: 'flex', gap: 6 }}>
        {FAIR_LABELS.map((label) => {
          const value = summary.fair[label];
          return (
            <div key={label} style={{ flex: 1 }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', fontSize: 9,
                color: '#556677', marginBottom: 2,
              }}>
                <span>{label}</span>
                <span>{value}</span>
              </div>
              <div style={{
                height: 4, borderRadius: 2, background: '#1a2638', overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%', width: `${value}%`, borderRadius: 2,
                  background: value >= 70 ? '#00E5A0' : value >= 40 ? '#FFB020' : '#FF4D4D',
                  transition: 'width 300ms',
                }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Composite */}
      <div style={{
        marginTop: 6, fontSize: 11, color: '#8899aa',
        display: 'flex', justifyContent: 'space-between',
      }}>
        <span>Composite</span>
        <span style={{ fontWeight: 600, color }}>{summary.fair.composite}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create ChartCard**

Create `frontend/src/components/chat/cards/ChartCard.tsx`:

```tsx
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import type { ChartCardData } from '../../../types/chat';

interface ChartCardProps {
  data: ChartCardData;
}

export default function ChartCard({ data }: ChartCardProps) {
  return (
    <div style={{
      background: '#141920',
      border: '1px solid #1a2638',
      borderRadius: 10,
      padding: '10px 14px',
      marginTop: 8,
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#E8ECF1', marginBottom: 8 }}>
        {data.title}
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data.entries} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="device"
            tick={{ fontSize: 9, fill: '#556677' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide />
          <Tooltip
            contentStyle={{
              background: '#0D1520',
              border: '1px solid #1a2638',
              borderRadius: 6,
              fontSize: 11,
              color: '#E8ECF1',
            }}
            formatter={(v: number) => [`${v}${data.unit}`, '']}
          />
          <Bar dataKey="value" fill="#00E5A0" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Update BotMessage to render cards and reasoning**

In `frontend/src/components/chat/BotMessage.tsx`, update the props interface:

```typescript
import { ActionItem, ToolCall, AHUSummary, ChartCardData } from '../../types/chat';
import AgentReasoning from './AgentReasoning';
import WorkOrderCard from './cards/WorkOrderCard';
import AHUSummaryCard from './cards/AHUSummaryCard';
import ChartCard from './cards/ChartCard';

interface BotMessageProps {
  content: string;
  navigate?: NavigateTarget | null;
  onNavigate?: (target: NavigateTarget) => void;
  isLast?: boolean;
  onClearChat?: () => void;
  actions?: ActionItem[];
  tool_calls?: ToolCall[];
  ahu_summary?: AHUSummary | null;
  chart_data?: ChartCardData | null;
}
```

After the markdown rendering section (around line 92) and before the `showActions` div, add:

```tsx
{/* Agent reasoning */}
{tool_calls && tool_calls.length > 0 && (
  <AgentReasoning toolCalls={tool_calls} />
)}

{/* Structured cards */}
{ahu_summary && <AHUSummaryCard summary={ahu_summary} />}
{chart_data && <ChartCard data={chart_data} />}
{actions && actions.length > 0 && <WorkOrderCard actions={actions} />}
```

- [ ] **Step 5: Update MessageList to pass new props**

In `frontend/src/components/chat/MessageList.tsx`, update the `<BotMessage>` render (around line 54) to pass the new fields:

```tsx
<BotMessage
  content={msg.content}
  navigate={msg.navigate}
  onNavigate={onNavigate}
  isLast={isLast}
  onClearChat={isLast ? onClearChat : undefined}
  actions={msg.actions}
  tool_calls={msg.tool_calls}
  ahu_summary={msg.ahu_summary}
  chart_data={msg.chart_data}
/>
```

- [ ] **Step 6: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chat/cards/ frontend/src/components/chat/BotMessage.tsx frontend/src/components/chat/MessageList.tsx
git commit -m "feat: add structured response cards (WorkOrder, AHUSummary, Chart) and agent reasoning"
```

---

## Task 6: Suggested Prompts

**Files:**
- Create: `frontend/src/components/chat/SuggestedPrompts.tsx`
- Modify: `frontend/src/components/chat/ChatWindow.tsx`

- [ ] **Step 1: Create SuggestedPrompts component**

Create `frontend/src/components/chat/SuggestedPrompts.tsx`:

```tsx
import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

interface SuggestedPromptsProps {
  suggestions?: string[];
  onSelect: (prompt: string) => void;
  hasMessages: boolean;
}

function getInitialPrompts(level: number | null, device: string | null): string[] {
  const prompts: string[] = [];
  if (level) {
    prompts.push(`How is Level ${level} performing?`);
    prompts.push(`Any alerts on Level ${level}?`);
  } else {
    prompts.push('Which level has the most issues?');
    prompts.push('Show me site-wide health summary');
  }
  if (device && device !== 'all') {
    prompts.push(`What's wrong with ${device}?`);
    prompts.push(`Show predictions for ${device}`);
  }
  prompts.push('Show me the worst performing AHUs');
  prompts.push('Any maintenance recommendations?');
  return prompts.slice(0, 6);
}

export default function SuggestedPrompts({ suggestions, onSelect, hasMessages }: SuggestedPromptsProps) {
  const selectedLevel = useAppStore((s) => s.selectedLevel);
  const selectedDevice = useAppStore((s) => s.selectedDevice);

  const prompts = suggestions && suggestions.length > 0
    ? suggestions
    : !hasMessages
      ? getInitialPrompts(selectedLevel, selectedDevice)
      : [];

  if (!prompts.length) return null;

  return (
    <div style={{
      display: 'flex',
      gap: 6,
      flexWrap: 'wrap',
      padding: '6px 12px',
    }}>
      {prompts.map((prompt, i) => (
        <motion.button
          key={prompt}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(prompt)}
          style={{
            background: '#141920',
            border: '1px solid #1a2638',
            borderRadius: 16,
            padding: '5px 12px',
            fontSize: 11,
            color: '#8899aa',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
          whileHover={{ borderColor: '#00E5A0', color: '#E8ECF1' }}
        >
          {prompt}
        </motion.button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Wire SuggestedPrompts into ChatWindow**

In `frontend/src/components/chat/ChatWindow.tsx`, add import:

```typescript
import SuggestedPrompts from './SuggestedPrompts';
```

Track latest suggestions in state. After the `selectedPersona` state (around line 46), add:

```typescript
const [latestSuggestions, setLatestSuggestions] = useState<string[]>([]);
```

After the SSE streaming completes (or after setting bot message), update suggestions from the latest bot message. In the `sendStreaming` call or after message update, add an effect:

```typescript
// Track suggestions from latest bot message
useEffect(() => {
  const lastBot = [...messages].reverse().find((m) => m.role === 'bot');
  if (lastBot?.suggestions?.length) {
    setLatestSuggestions(lastBot.suggestions);
  }
}, [messages]);
```

Add the `handlePromptSelect` callback:

```typescript
const handlePromptSelect = useCallback(
  (prompt: string) => {
    handleSendMessage(prompt);
    setLatestSuggestions([]);
  },
  [handleSendMessage]
);
```

In the JSX, add `SuggestedPrompts` between `MessageList` and `ChatInput`:

```tsx
<SuggestedPrompts
  suggestions={latestSuggestions}
  onSelect={handlePromptSelect}
  hasMessages={messages.length > 1}
/>
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/SuggestedPrompts.tsx frontend/src/components/chat/ChatWindow.tsx
git commit -m "feat: add contextual suggested prompts in chat"
```

---

## Task 7: Conversation History

**Files:**
- Create: `frontend/src/hooks/useConversationHistory.ts`
- Create: `frontend/src/components/chat/ConversationHistory.tsx`
- Modify: `frontend/src/components/chat/ChatWindow.tsx`

- [ ] **Step 1: Create useConversationHistory hook**

Create `frontend/src/hooks/useConversationHistory.ts`:

```typescript
import { useState, useCallback, useEffect } from 'react';
import type { Message } from '../types/chat';

const STORAGE_KEY = 'rdm-atlas-history';
const MAX_CONVERSATIONS = 50;

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convos: Conversation[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convos.slice(0, MAX_CONVERSATIONS)));
}

export function useConversationHistory() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Sync to localStorage on change
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  const saveCurrentConversation = useCallback(
    (messages: Message[]) => {
      if (messages.length <= 1) return; // Don't save greeting-only

      const firstUserMsg = messages.find((m) => m.role === 'user');
      const title = firstUserMsg
        ? firstUserMsg.content.slice(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '')
        : 'New conversation';
      const now = new Date().toISOString();

      setConversations((prev) => {
        if (activeId) {
          // Update existing
          return prev.map((c) =>
            c.id === activeId ? { ...c, messages, title, updatedAt: now } : c
          );
        }
        // Create new
        const newConvo: Conversation = {
          id: `conv-${Date.now()}`,
          title,
          messages,
          createdAt: now,
          updatedAt: now,
        };
        setActiveId(newConvo.id);
        return [newConvo, ...prev];
      });
    },
    [activeId]
  );

  const loadConversation = useCallback((id: string): Message[] | null => {
    const convo = conversations.find((c) => c.id === id);
    if (!convo) return null;
    setActiveId(id);
    return convo.messages;
  }, [conversations]);

  const deleteConversation = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }, [activeId]);

  const startNewConversation = useCallback(() => {
    setActiveId(null);
  }, []);

  return {
    conversations,
    activeId,
    saveCurrentConversation,
    loadConversation,
    deleteConversation,
    startNewConversation,
  };
}
```

- [ ] **Step 2: Create ConversationHistory sidebar**

Create `frontend/src/components/chat/ConversationHistory.tsx`:

```tsx
import { motion } from 'framer-motion';
import type { Conversation } from '../../hooks/useConversationHistory';

interface ConversationHistoryProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
}

function groupByDate(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'This Week', items: [] },
    { label: 'Older', items: [] },
  ];

  for (const c of conversations) {
    const d = new Date(c.updatedAt);
    if (d >= today) groups[0].items.push(c);
    else if (d >= yesterday) groups[1].items.push(c);
    else if (d >= weekAgo) groups[2].items.push(c);
    else groups[3].items.push(c);
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function ConversationHistory({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNewChat,
}: ConversationHistoryProps) {
  const groups = groupByDate(conversations);

  return (
    <div style={{
      width: 220,
      borderRight: '1px solid #1a2638',
      background: '#0B0F14',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}>
      <button
        onClick={onNewChat}
        style={{
          margin: '10px 10px 6px',
          background: '#00E5A0',
          color: '#0B0F14',
          border: 'none',
          borderRadius: 8,
          padding: '7px 0',
          fontSize: 12,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        + New Chat
      </button>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 6px' }} className="scrollbar-hidden">
        {groups.map((group) => (
          <div key={group.label}>
            <div style={{
              fontSize: 9, color: '#556677', textTransform: 'uppercase',
              padding: '10px 6px 4px', fontWeight: 600,
            }}>
              {group.label}
            </div>
            {group.items.map((convo) => (
              <motion.div
                key={convo.id}
                onClick={() => onSelect(convo.id)}
                style={{
                  padding: '7px 8px',
                  borderRadius: 6,
                  fontSize: 11,
                  color: convo.id === activeId ? '#E8ECF1' : '#8899aa',
                  background: convo.id === activeId ? '#141920' : 'transparent',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 1,
                }}
                whileHover={{ background: '#141920' }}
              >
                <span style={{
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                }}>
                  {convo.title}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(convo.id); }}
                  style={{
                    background: 'none', border: 'none', color: '#556677',
                    cursor: 'pointer', fontSize: 12, padding: '0 2px',
                    opacity: 0.5, flexShrink: 0,
                  }}
                >
                  ×
                </button>
              </motion.div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire conversation history into ChatWindow**

In `frontend/src/components/chat/ChatWindow.tsx`, add imports:

```typescript
import { useConversationHistory } from '../../hooks/useConversationHistory';
import ConversationHistory from './ConversationHistory';
```

Inside the component, add the hook:

```typescript
const {
  conversations,
  activeId,
  saveCurrentConversation,
  loadConversation,
  deleteConversation,
  startNewConversation,
} = useConversationHistory();
```

Add auto-save effect — saves current conversation whenever messages change (debounced by checking length > 1):

```typescript
useEffect(() => {
  if (messages.length > 1) {
    saveCurrentConversation(messages);
  }
}, [messages, saveCurrentConversation]);
```

Add handlers:

```typescript
const handleLoadConversation = useCallback(
  (id: string) => {
    const msgs = loadConversation(id);
    if (msgs) setMessages(msgs);
  },
  [loadConversation, setMessages]
);

const handleNewChat = useCallback(() => {
  startNewConversation();
  setMessages([{
    id: 'greeting',
    role: 'bot',
    content: "Hello! I'm **RDM-Atlas**, your building health assistant. How can I help you today?",
  }]);
}, [startNewConversation, setMessages]);
```

In the JSX, wrap the existing body in a flex row when in fullscreen mode. Replace the `<div>` that wraps `MessageList` and `ChatInput` with:

```tsx
<div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
  {mode === 'fullscreen' && (
    <ConversationHistory
      conversations={conversations}
      activeId={activeId}
      onSelect={handleLoadConversation}
      onDelete={deleteConversation}
      onNewChat={handleNewChat}
    />
  )}
  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
    {/* existing MessageList, SuggestedPrompts, ChatInput go here */}
  </div>
</div>
```

- [ ] **Step 4: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useConversationHistory.ts frontend/src/components/chat/ConversationHistory.tsx frontend/src/components/chat/ChatWindow.tsx
git commit -m "feat: add conversation history sidebar with localStorage persistence"
```

---

## Task 8: Fullscreen Split View

**Files:**
- Modify: `frontend/src/store/useAppStore.ts`
- Modify: `frontend/src/components/chat/ChatHeader.tsx`
- Modify: `frontend/src/components/chat/ChatWidget.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Extend chatMode in store**

In `frontend/src/store/useAppStore.ts`, find the `chatMode` declaration. Currently it's typed inline. Update it:

Find `chatMode: 'panel' as const,` (around line 24 in initialState) — this stays the same since `'panel'` is a valid value.

Find the `setChatMode` action. The type for `chatMode` needs to accept `'split'`. Find where the type is used and update. The store likely infers the type from the initial value. To add `'split'`, find the `setChatMode` setter:

```typescript
setChatMode: (mode: 'panel' | 'fullscreen' | 'split') => set({ chatMode: mode }),
```

If the type is inferred as `string` from `as const`, it should already accept any string. If it's constrained, explicitly type the state field.

- [ ] **Step 2: Add split view toggle to ChatHeader**

In `frontend/src/components/chat/ChatHeader.tsx`, update the `ChatHeaderProps` interface to add the split mode info:

```typescript
interface ChatHeaderProps {
  mode: 'panel' | 'fullscreen' | 'split';
  onClose: () => void;
  onToggleMode: () => void;
  onSplitMode?: () => void;
  isMinimized?: boolean;
  onMinimize?: () => void;
}
```

Add a split-view toggle button between the fullscreen toggle and the close button. After the existing toggle button (around line 113), add:

```tsx
{/* Split view toggle */}
{onSplitMode && (
  <button
    onClick={onSplitMode}
    title="Split view"
    style={{
      width: 28,
      height: 28,
      borderRadius: 6,
      border: mode === 'split' ? '1px solid #00E5A0' : '1px solid #243040',
      background: mode === 'split' ? 'rgba(0,229,160,0.1)' : 'transparent',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
      color: mode === 'split' ? '#00E5A0' : '#556677',
    }}
  >
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="1" y="1" width="5" height="12" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="8" y="1" width="5" height="12" rx="1" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  </button>
)}
```

- [ ] **Step 3: Update ChatWidget for split mode**

In `frontend/src/components/chat/ChatWidget.tsx`, update the mode cycling logic.

Update `toggleExpanded`:

```typescript
const toggleExpanded = () => {
  if (chatMode === 'panel') setChatMode('fullscreen');
  else if (chatMode === 'fullscreen') setChatMode('panel');
  else setChatMode('panel'); // split → panel
};

const toggleSplit = () => {
  setChatMode(chatMode === 'split' ? 'panel' : 'split');
};
```

Update panel dimensions. The fixed-position panel is only used in `panel` mode. In `split` mode, ChatWidget should render differently — it fills its container in the split layout:

```typescript
const isSplit = chatMode === 'split';
const isExpanded = chatMode === 'fullscreen';
```

For `split` mode, don't render the fixed-position wrapper. Instead, render just `<ChatWindow>` with `style={{ height: '100%' }}`. The `split` layout container lives in `App.tsx`.

Update the `ChatWindow` props to pass `onSplitMode`:

```tsx
<ChatWindow
  mode={chatMode}
  onClose={handleClose}
  onToggleMode={toggleExpanded}
  onSplitMode={toggleSplit}
  messages={messages}
  setMessages={setMessages}
  isMinimized={isMinimized}
  onMinimize={() => setIsMinimized((v) => !v)}
/>
```

Pass `onSplitMode` through `ChatWindow` to `ChatHeader`.

When `isSplit`, render without fixed positioning:

```tsx
if (isSplit) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#0B0F14' }}>
      <ChatWindow
        mode="split"
        onClose={handleClose}
        onToggleMode={toggleExpanded}
        onSplitMode={toggleSplit}
        messages={messages}
        setMessages={setMessages}
        isMinimized={false}
        onMinimize={() => {}}
      />
    </div>
  );
}
```

- [ ] **Step 4: Update App.tsx for split layout**

In `frontend/src/App.tsx`, add the split view layout. Read `chatMode` from the store:

```typescript
const chatMode = useAppStore((s) => s.chatMode);
```

When `chatMode === 'split'`, wrap the main content and chat in a side-by-side flex layout. Around the root return (line 320), wrap conditionally:

```tsx
{chatMode === 'split' ? (
  <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
    <div style={{ flex: '0 0 40%', borderRight: '1px solid #1a2638' }}>
      <ChatWidget />
    </div>
    <div style={{ flex: 1, overflowY: 'auto' }} className="min-h-screen bg-[#0B0F14] text-[#E8ECF1]">
      {/* existing FilterBar + main content */}
    </div>
  </div>
) : (
  <div className="min-h-screen bg-[#0B0F14] text-[#E8ECF1]">
    {/* existing content */}
    <ChatWidget />
  </div>
)}
```

In split mode, `ChatWidget` renders without fixed positioning (handled in step 3). The existing floating `ChatBubbleButton` should be hidden in split mode.

- [ ] **Step 5: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 6: Start dev server and test split view**

```bash
cd frontend && npm run dev &
```

Open `http://localhost:3000`. Open chat → toggle to split view. Verify:
- Chat takes 40% left, dashboard 60% right
- Both sides scroll independently
- Toggle back to panel mode works

- [ ] **Step 7: Commit**

```bash
git add frontend/src/store/useAppStore.ts frontend/src/components/chat/ChatHeader.tsx frontend/src/components/chat/ChatWidget.tsx frontend/src/App.tsx
git commit -m "feat: add fullscreen split view — chat 40%% + dashboard 60%%"
```

---

## Layer 2: Work Order System

---

## Task 9: Polling Hook

**Files:**
- Create: `frontend/src/hooks/usePolling.ts`

- [ ] **Step 1: Create the usePolling hook**

Create `frontend/src/hooks/usePolling.ts`:

```typescript
import { useEffect, useRef, useCallback, useState } from 'react';

interface UsePollingOptions {
  enabled?: boolean;
  pauseWhenHidden?: boolean;
  onError?: (error: Error) => void;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  options: UsePollingOptions = {}
) {
  const { enabled = true, pauseWhenHidden = true, onError } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const backoffRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(async () => {
    if (pauseWhenHidden && document.hidden) return;

    try {
      const result = await fetcher();
      setData(result);
      setError(null);
      backoffRef.current = 0;
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      setError(err);
      onError?.(err);
      backoffRef.current = Math.min(backoffRef.current + 1, 5);
    }

    if (enabled) {
      const delay = intervalMs * Math.pow(2, backoffRef.current);
      timerRef.current = setTimeout(poll, Math.min(delay, 30000));
    }
  }, [fetcher, intervalMs, enabled, pauseWhenHidden, onError]);

  useEffect(() => {
    if (!enabled) {
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }

    poll();

    const handleVisibility = () => {
      if (!document.hidden && pauseWhenHidden) {
        if (timerRef.current) clearTimeout(timerRef.current);
        poll();
      }
    };

    if (pauseWhenHidden) {
      document.addEventListener('visibilitychange', handleVisibility);
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (pauseWhenHidden) {
        document.removeEventListener('visibilitychange', handleVisibility);
      }
    };
  }, [poll, enabled, pauseWhenHidden]);

  const refetch = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    poll();
  }, [poll]);

  return { data, error, refetch };
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/usePolling.ts
git commit -m "feat: add usePolling hook with visibility pause and exponential backoff"
```

---

## Task 10: Work Order Store Slice

**Files:**
- Modify: `frontend/src/store/useAppStore.ts`
- Modify: `frontend/src/components/dashboard/ModeToggle.tsx`

- [ ] **Step 1: Extend DashboardMode type**

In `frontend/src/store/useAppStore.ts`, update the `DashboardMode` type (line 29):

```typescript
export type DashboardMode = 'simple' | 'deepdive' | 'workorders';
```

- [ ] **Step 2: Add work order state to the store**

In the store, add these fields to the initial state and their setters:

```typescript
// In initialState, add:
workOrderPanelOpen: false,
workOrderDraftsCount: 0,

// In the store create(), add actions:
setWorkOrderPanelOpen: (open: boolean) => set({ workOrderPanelOpen: open }),
toggleWorkOrderPanel: () => set((s) => ({ workOrderPanelOpen: !s.workOrderPanelOpen })),
setWorkOrderDraftsCount: (count: number) => set({ workOrderDraftsCount: count }),
```

- [ ] **Step 3: Update ModeToggle to include Work Orders**

In `frontend/src/components/dashboard/ModeToggle.tsx`, update the `MODES` array (line 4):

```typescript
const MODES: DashboardMode[] = ['simple', 'deepdive', 'workorders'];
```

Update the label mapping (around line 35). Currently it's inline text. Add the work orders label:

Find where labels are assigned and add:
```typescript
const LABELS: Record<DashboardMode, string> = {
  simple: 'Simple Mode',
  deepdive: 'Deep Dive Mode',
  workorders: 'Work Orders',
};
```

The work orders mode should always be enabled (no device selection required, unlike deep dive). Update the `handleClick` logic to only gate deep dive behind device selection, not work orders.

- [ ] **Step 4: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/useAppStore.ts frontend/src/components/dashboard/ModeToggle.tsx
git commit -m "feat: extend store with work order state and add Work Orders to ModeToggle"
```

---

## Task 11: Work Order Badge and Slide-Out Panel

**Files:**
- Create: `frontend/src/components/workorders/WorkOrderBadge.tsx`
- Create: `frontend/src/components/workorders/WorkOrderPanelItem.tsx`
- Create: `frontend/src/components/workorders/WorkOrderPanel.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create WorkOrderPanelItem**

Create `frontend/src/components/workorders/WorkOrderPanelItem.tsx`:

```tsx
import type { WorkOrder } from '../../types/chat';
import { approveWorkOrder, dismissWorkOrder } from '../../api/client';
import { useState } from 'react';

interface WorkOrderPanelItemProps {
  workOrder: WorkOrder;
  onAction: () => void;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#FF4D4D',
  warning: '#FFB020',
  info: '#4DA6FF',
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function WorkOrderPanelItem({ workOrder, onAction }: WorkOrderPanelItemProps) {
  const [loading, setLoading] = useState(false);
  const color = SEVERITY_COLORS[workOrder.severity] ?? '#4DA6FF';

  const handleApprove = async () => {
    setLoading(true);
    try {
      await approveWorkOrder(workOrder.id);
      onAction();
    } finally {
      setLoading(false);
    }
  };

  const handleDismiss = async () => {
    setLoading(true);
    try {
      await dismissWorkOrder(workOrder.id);
      onAction();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      padding: '10px 14px',
      borderBottom: '1px solid #1a2638',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0,
        }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#E8ECF1', flex: 1 }}>
          {workOrder.ahu_id}
        </span>
        <span style={{ fontSize: 9, color: '#556677' }}>L{workOrder.level}</span>
        <span style={{
          fontSize: 9, color, textTransform: 'uppercase', fontWeight: 600,
        }}>
          {workOrder.severity}
        </span>
      </div>
      <p style={{ fontSize: 11, color: '#8899aa', margin: '0 0 6px' }}>
        {workOrder.title}
      </p>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 9, color: '#556677' }}>
          {timeAgo(workOrder.created_at)}
        </span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            disabled={loading}
            onClick={handleApprove}
            style={{
              background: '#00E5A0', color: '#0B0F14', border: 'none', borderRadius: 12,
              padding: '3px 10px', fontSize: 10, fontWeight: 600, cursor: 'pointer',
              opacity: loading ? 0.5 : 1,
            }}
          >
            Approve
          </button>
          <button
            disabled={loading}
            onClick={handleDismiss}
            style={{
              background: 'none', color: '#6d6e71', border: '1px solid #1a2638', borderRadius: 12,
              padding: '3px 10px', fontSize: 10, cursor: 'pointer',
              opacity: loading ? 0.5 : 1,
            }}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create WorkOrderPanel**

Create `frontend/src/components/workorders/WorkOrderPanel.tsx`:

```tsx
import { AnimatePresence, motion } from 'framer-motion';
import { useCallback } from 'react';
import { fetchWorkOrders } from '../../api/client';
import { usePolling } from '../../hooks/usePolling';
import { useAppStore } from '../../store/useAppStore';
import WorkOrderPanelItem from './WorkOrderPanelItem';

export default function WorkOrderPanel() {
  const panelOpen = useAppStore((s) => s.workOrderPanelOpen);
  const setPanel = useAppStore((s) => s.setWorkOrderPanelOpen);
  const setDraftsCount = useAppStore((s) => s.setWorkOrderDraftsCount);
  const setDashboardMode = useAppStore((s) => s.setDashboardMode);

  const fetcher = useCallback(() => fetchWorkOrders('draft'), []);
  const { data, refetch } = usePolling(fetcher, 60000, { pauseWhenHidden: true });

  // Sync drafts count to store
  if (data) {
    setDraftsCount(data.count);
  }

  const workOrders = data?.work_orders ?? [];

  const handleAction = () => {
    refetch();
  };

  const handleViewAll = () => {
    setPanel(false);
    setDashboardMode('workorders');
  };

  // Group by severity
  const critical = workOrders.filter((w) => w.severity === 'critical');
  const warning = workOrders.filter((w) => w.severity === 'warning');
  const info = workOrders.filter((w) => w.severity === 'info');
  const groups = [
    { label: 'Critical', items: critical, color: '#FF4D4D' },
    { label: 'Warning', items: warning, color: '#FFB020' },
    { label: 'Info', items: info, color: '#4DA6FF' },
  ].filter((g) => g.items.length > 0);

  return (
    <AnimatePresence>
      {panelOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setPanel(false)}
            style={{
              position: 'fixed', inset: 0, zIndex: 9997,
              background: 'rgba(5,9,15,0.5)',
            }}
          />
          {/* Panel */}
          <motion.div
            initial={{ x: 340 }}
            animate={{ x: 0 }}
            exit={{ x: 340 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0,
              width: 340, zIndex: 9998,
              background: '#0D1520',
              borderLeft: '1px solid #1a2638',
              display: 'flex', flexDirection: 'column',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '14px 16px', borderBottom: '1px solid #1a2638',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#E8ECF1' }}>
                Pending Work Orders
                {workOrders.length > 0 && (
                  <span style={{
                    marginLeft: 6, fontSize: 10, background: '#FF4D4D',
                    color: '#fff', borderRadius: 8, padding: '1px 6px',
                  }}>
                    {workOrders.length}
                  </span>
                )}
              </div>
              <button
                onClick={() => setPanel(false)}
                style={{
                  width: 28, height: 28, borderRadius: 6,
                  border: '1px solid #243040', background: 'transparent',
                  color: '#556677', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14,
                }}
              >
                ×
              </button>
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflowY: 'auto' }} className="scrollbar-hidden">
              {workOrders.length === 0 ? (
                <div style={{
                  padding: 24, textAlign: 'center', color: '#556677', fontSize: 12,
                }}>
                  No pending work orders
                </div>
              ) : (
                groups.map((group) => (
                  <div key={group.label}>
                    <div style={{
                      fontSize: 9, color: group.color, textTransform: 'uppercase',
                      fontWeight: 600, padding: '10px 14px 4px',
                    }}>
                      {group.label} ({group.items.length})
                    </div>
                    {group.items.map((wo) => (
                      <WorkOrderPanelItem
                        key={wo.id}
                        workOrder={wo}
                        onAction={handleAction}
                      />
                    ))}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div style={{
              padding: '10px 16px', borderTop: '1px solid #1a2638',
            }}>
              <button
                onClick={handleViewAll}
                style={{
                  width: '100%', background: 'transparent',
                  border: '1px solid #1a2638', borderRadius: 8,
                  color: '#8899aa', padding: '7px 0', fontSize: 11,
                  cursor: 'pointer',
                }}
              >
                View All Work Orders →
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 3: Create WorkOrderBadge**

Create `frontend/src/components/workorders/WorkOrderBadge.tsx`:

```tsx
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

export default function WorkOrderBadge() {
  const count = useAppStore((s) => s.workOrderDraftsCount);
  const togglePanel = useAppStore((s) => s.toggleWorkOrderPanel);

  return (
    <button
      onClick={togglePanel}
      title={`${count} pending work order${count !== 1 ? 's' : ''}`}
      style={{
        position: 'fixed',
        bottom: 80,
        right: 24,
        width: 44,
        height: 44,
        borderRadius: '50%',
        background: '#141920',
        border: '1px solid #1a2638',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9990,
        color: '#8899aa',
      }}
    >
      {/* Clipboard icon */}
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
        <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
      </svg>

      {/* Badge count */}
      <AnimatePresence>
        {count > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            style={{
              position: 'absolute',
              top: -2,
              right: -2,
              minWidth: 18,
              height: 18,
              borderRadius: 9,
              background: '#FF4D4D',
              color: '#fff',
              fontSize: 10,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0 4px',
            }}
          >
            {count}
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}
```

- [ ] **Step 4: Wire badge and panel into App.tsx**

In `frontend/src/App.tsx`, add imports:

```typescript
import WorkOrderBadge from './components/workorders/WorkOrderBadge';
import WorkOrderPanel from './components/workorders/WorkOrderPanel';
```

Render them alongside the `ChatWidget`. In the JSX (around line 441 where `<ChatWidget />` lives), add:

```tsx
<WorkOrderBadge />
<WorkOrderPanel />
<ChatWidget />
```

The badge is fixed-position (bottom: 80, right: 24) — above the chat bubble button.

- [ ] **Step 5: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workorders/WorkOrderBadge.tsx frontend/src/components/workorders/WorkOrderPanel.tsx frontend/src/components/workorders/WorkOrderPanelItem.tsx frontend/src/App.tsx
git commit -m "feat: add work order badge and slide-out panel with polling"
```

---

## Task 12: Work Orders Dashboard View — Stats Bar

**Files:**
- Create: `frontend/src/components/workorders/WorkOrderStatsBar.tsx`

- [ ] **Step 1: Create WorkOrderStatsBar**

Create `frontend/src/components/workorders/WorkOrderStatsBar.tsx`:

```tsx
import type { WorkOrder } from '../../types/chat';

interface WorkOrderStatsBarProps {
  workOrders: WorkOrder[];
}

interface StatCardProps {
  label: string;
  value: string | number;
  valueColor?: string;
  subtitle?: string;
}

function StatCard({ label, value, valueColor, subtitle }: StatCardProps) {
  return (
    <div style={{
      background: '#1a2234',
      border: '1px solid #2a3649',
      borderRadius: 10,
      padding: '10px 14px',
      flex: 1,
    }}>
      <div style={{
        fontSize: 9, textTransform: 'uppercase', color: '#556677',
        letterSpacing: 0.5, marginBottom: 4,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 20, fontWeight: 700, color: valueColor ?? '#E8ECF1',
        fontFamily: 'var(--font-display)',
      }}>
        {value}
      </div>
      {subtitle && (
        <div style={{
          fontSize: 9, color: '#445566', fontFamily: 'var(--font-mono)',
          marginTop: 2,
        }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}

export default function WorkOrderStatsBar({ workOrders }: WorkOrderStatsBarProps) {
  const open = workOrders.filter((w) => !['resolved', 'dismissed'].includes(w.status));
  const critical = workOrders.filter((w) => w.severity === 'critical' && !['resolved', 'dismissed'].includes(w.status));

  // Avg time to resolve (for resolved orders)
  const resolved = workOrders.filter((w) => w.status === 'resolved' && w.resolved_at);
  let avgResolveHrs = 0;
  if (resolved.length > 0) {
    const totalMs = resolved.reduce((acc, w) => {
      return acc + (new Date(w.resolved_at!).getTime() - new Date(w.created_at).getTime());
    }, 0);
    avgResolveHrs = Math.round(totalMs / resolved.length / 3600000);
  }

  // This week count
  const weekAgo = new Date(Date.now() - 7 * 86400000);
  const thisWeek = workOrders.filter((w) => new Date(w.created_at) >= weekAgo);

  return (
    <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
      <StatCard
        label="Total Open"
        value={open.length}
        valueColor={open.length > 0 ? '#E8ECF1' : '#00E5A0'}
      />
      <StatCard
        label="Critical"
        value={critical.length}
        valueColor={critical.length > 0 ? '#FF4D4D' : '#00E5A0'}
      />
      <StatCard
        label="Avg Resolve Time"
        value={resolved.length > 0 ? `${avgResolveHrs}h` : '—'}
        subtitle={resolved.length > 0 ? `${resolved.length} resolved` : 'No data'}
      />
      <StatCard
        label="This Week"
        value={thisWeek.length}
        subtitle={`vs ${workOrders.length - thisWeek.length} older`}
      />
    </div>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workorders/WorkOrderStatsBar.tsx
git commit -m "feat: add WorkOrderStatsBar with open/critical/resolve-time/weekly stats"
```

---

## Task 13: Work Orders Dashboard View — Table and Filters

**Files:**
- Create: `frontend/src/components/workorders/WorkOrderFilters.tsx`
- Create: `frontend/src/components/workorders/WorkOrderTable.tsx`

- [ ] **Step 1: Create WorkOrderFilters**

Create `frontend/src/components/workorders/WorkOrderFilters.tsx`:

```tsx
interface WorkOrderFiltersProps {
  statusFilter: string[];
  severityFilter: string[];
  onStatusChange: (statuses: string[]) => void;
  onSeverityChange: (severities: string[]) => void;
}

const STATUSES = ['draft', 'pending_approval', 'approved', 'in_progress', 'resolved', 'dismissed'];
const SEVERITIES = ['critical', 'warning', 'info'];

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#FF4D4D',
  warning: '#FFB020',
  info: '#4DA6FF',
};

function toggleItem(arr: string[], item: string): string[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
}

export default function WorkOrderFilters({
  statusFilter,
  severityFilter,
  onStatusChange,
  onSeverityChange,
}: WorkOrderFiltersProps) {
  return (
    <div style={{
      display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        <span style={{ fontSize: 10, color: '#556677', marginRight: 4 }}>STATUS</span>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => onStatusChange(toggleItem(statusFilter, s))}
            style={{
              fontSize: 10,
              padding: '3px 8px',
              borderRadius: 12,
              border: statusFilter.includes(s) ? '1px solid #00E5A0' : '1px solid #1a2638',
              background: statusFilter.includes(s) ? 'rgba(0,229,160,0.1)' : 'transparent',
              color: statusFilter.includes(s) ? '#00E5A0' : '#6d6e71',
              cursor: 'pointer',
            }}
          >
            {s.replace('_', ' ')}
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        <span style={{ fontSize: 10, color: '#556677', marginRight: 4 }}>SEVERITY</span>
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => onSeverityChange(toggleItem(severityFilter, s))}
            style={{
              fontSize: 10,
              padding: '3px 8px',
              borderRadius: 12,
              border: severityFilter.includes(s)
                ? `1px solid ${SEVERITY_COLORS[s]}`
                : '1px solid #1a2638',
              background: severityFilter.includes(s)
                ? `${SEVERITY_COLORS[s]}18`
                : 'transparent',
              color: severityFilter.includes(s) ? SEVERITY_COLORS[s] : '#6d6e71',
              cursor: 'pointer',
            }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create WorkOrderTable**

Create `frontend/src/components/workorders/WorkOrderTable.tsx`:

```tsx
import { useState } from 'react';
import { motion } from 'framer-motion';
import type { WorkOrder } from '../../types/chat';

interface WorkOrderTableProps {
  workOrders: WorkOrder[];
  onRowClick: (id: number) => void;
}

type SortKey = 'id' | 'ahu_id' | 'level' | 'severity' | 'status' | 'created_at' | 'trigger_source';
type SortDir = 'asc' | 'desc';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#FF4D4D',
  warning: '#FFB020',
  info: '#4DA6FF',
};

const STATUS_COLORS: Record<string, string> = {
  draft: '#8899aa',
  pending_approval: '#FFB020',
  approved: '#00E5A0',
  in_progress: '#4DA6FF',
  resolved: '#556677',
  dismissed: '#3a3a3a',
};

const COLUMNS: { key: SortKey; label: string; width?: number }[] = [
  { key: 'id', label: 'ID', width: 50 },
  { key: 'ahu_id', label: 'AHU', width: 70 },
  { key: 'level', label: 'Level', width: 50 },
  { key: 'severity', label: 'Severity', width: 80 },
  { key: 'status', label: 'Status', width: 110 },
  { key: 'created_at', label: 'Created' },
  { key: 'trigger_source', label: 'Source', width: 80 },
];

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-AU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export default function WorkOrderTable({ workOrders, onRowClick }: WorkOrderTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = [...workOrders].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;
    const cmp = typeof aVal === 'number' ? aVal - (bVal as number) : String(aVal).localeCompare(String(bVal));
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(sorted.length / pageSize);

  return (
    <div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  style={{
                    textAlign: 'left',
                    padding: '8px 10px',
                    fontSize: 9,
                    textTransform: 'uppercase',
                    color: sortKey === col.key ? '#00E5A0' : '#556677',
                    borderBottom: '1px solid #1a2638',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    width: col.width,
                    userSelect: 'none',
                  }}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span style={{ marginLeft: 4 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((wo, i) => (
              <motion.tr
                key={wo.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.02 }}
                onClick={() => onRowClick(wo.id)}
                style={{
                  cursor: 'pointer',
                  borderBottom: '1px solid #141920',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background = '#141920';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background = 'transparent';
                }}
              >
                <td style={{ padding: '8px 10px', color: '#556677' }}>#{wo.id}</td>
                <td style={{ padding: '8px 10px', color: '#E8ECF1', fontWeight: 600 }}>{wo.ahu_id}</td>
                <td style={{ padding: '8px 10px', color: '#8899aa' }}>{wo.level}</td>
                <td style={{ padding: '8px 10px' }}>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    color: SEVERITY_COLORS[wo.severity] ?? '#8899aa',
                    fontSize: 11,
                  }}>
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: SEVERITY_COLORS[wo.severity] ?? '#8899aa',
                    }} />
                    {wo.severity}
                  </span>
                </td>
                <td style={{ padding: '8px 10px' }}>
                  <span style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 10,
                    border: `1px solid ${STATUS_COLORS[wo.status] ?? '#556677'}44`,
                    color: STATUS_COLORS[wo.status] ?? '#556677',
                  }}>
                    {wo.status.replace('_', ' ')}
                  </span>
                </td>
                <td style={{ padding: '8px 10px', color: '#8899aa', fontSize: 11 }}>
                  {formatDate(wo.created_at)}
                </td>
                <td style={{ padding: '8px 10px', color: '#556677', fontSize: 11 }}>
                  {wo.trigger_source}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{
          display: 'flex', justifyContent: 'center', gap: 8, padding: '12px 0',
        }}>
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            style={{
              background: 'none', border: '1px solid #1a2638', borderRadius: 6,
              padding: '4px 10px', fontSize: 11, color: '#8899aa', cursor: 'pointer',
              opacity: page === 0 ? 0.3 : 1,
            }}
          >
            Prev
          </button>
          <span style={{ fontSize: 11, color: '#556677', lineHeight: '28px' }}>
            {page + 1} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            style={{
              background: 'none', border: '1px solid #1a2638', borderRadius: 6,
              padding: '4px 10px', fontSize: 11, color: '#8899aa', cursor: 'pointer',
              opacity: page >= totalPages - 1 ? 0.3 : 1,
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workorders/WorkOrderFilters.tsx frontend/src/components/workorders/WorkOrderTable.tsx
git commit -m "feat: add WorkOrderFilters and WorkOrderTable components"
```

---

## Task 14: Work Orders Dashboard View — Detail Modal and Status Timeline

**Files:**
- Create: `frontend/src/components/workorders/StatusTimeline.tsx`
- Create: `frontend/src/components/workorders/WorkOrderDetailModal.tsx`

- [ ] **Step 1: Create StatusTimeline**

Create `frontend/src/components/workorders/StatusTimeline.tsx`:

```tsx
const STATUS_ORDER = ['draft', 'pending_approval', 'approved', 'in_progress', 'resolved'];

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft Created',
  pending_approval: 'Pending Approval',
  approved: 'Approved',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  dismissed: 'Dismissed',
};

interface StatusTimelineProps {
  currentStatus: string;
  createdAt: string;
  updatedAt: string;
  resolvedAt: string | null;
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-AU', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

export default function StatusTimeline({ currentStatus, createdAt, updatedAt, resolvedAt }: StatusTimelineProps) {
  const isDismissed = currentStatus === 'dismissed';
  const steps = isDismissed
    ? ['draft', 'dismissed']
    : STATUS_ORDER;

  const currentIdx = steps.indexOf(currentStatus);

  return (
    <div style={{ padding: '8px 0' }}>
      {steps.map((step, i) => {
        const isComplete = i <= currentIdx;
        const isCurrent = i === currentIdx;
        const color = isComplete ? '#00E5A0' : '#2a3649';

        let time = '';
        if (step === 'draft' || step === steps[0]) time = formatTime(createdAt);
        else if (step === currentStatus && step === 'resolved' && resolvedAt) time = formatTime(resolvedAt);
        else if (step === currentStatus) time = formatTime(updatedAt);

        return (
          <div key={step} style={{ display: 'flex', gap: 10, minHeight: 36 }}>
            {/* Line + dot */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 16 }}>
              <div style={{
                width: isCurrent ? 10 : 8,
                height: isCurrent ? 10 : 8,
                borderRadius: '50%',
                background: color,
                border: isCurrent ? '2px solid #00E5A0' : 'none',
                flexShrink: 0,
                marginTop: 2,
              }} />
              {i < steps.length - 1 && (
                <div style={{
                  width: 1, flex: 1, background: i < currentIdx ? '#00E5A0' : '#2a3649',
                }} />
              )}
            </div>
            {/* Label + time */}
            <div style={{ paddingBottom: 8 }}>
              <div style={{
                fontSize: 12,
                color: isComplete ? '#E8ECF1' : '#556677',
                fontWeight: isCurrent ? 600 : 400,
              }}>
                {STATUS_LABELS[step] ?? step}
              </div>
              {time && (
                <div style={{ fontSize: 9, color: '#556677', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
                  {time}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create WorkOrderDetailModal**

Create `frontend/src/components/workorders/WorkOrderDetailModal.tsx`:

```tsx
import { AnimatePresence, motion } from 'framer-motion';
import type { WorkOrder } from '../../types/chat';
import { approveWorkOrder, dismissWorkOrder } from '../../api/client';
import { useState } from 'react';
import StatusTimeline from './StatusTimeline';

interface WorkOrderDetailModalProps {
  workOrder: WorkOrder | null;
  onClose: () => void;
  onAction: () => void;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#FF4D4D',
  warning: '#FFB020',
  info: '#4DA6FF',
};

export default function WorkOrderDetailModal({ workOrder, onClose, onAction }: WorkOrderDetailModalProps) {
  const [loading, setLoading] = useState(false);

  if (!workOrder) return null;

  const color = SEVERITY_COLORS[workOrder.severity] ?? '#4DA6FF';
  const isDraft = workOrder.status === 'draft' || workOrder.status === 'pending_approval';
  const isActive = workOrder.status === 'approved' || workOrder.status === 'in_progress';

  const handleApprove = async () => {
    setLoading(true);
    try {
      await approveWorkOrder(workOrder.id);
      onAction();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleDismiss = async () => {
    setLoading(true);
    try {
      await dismissWorkOrder(workOrder.id);
      onAction();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {workOrder && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, zIndex: 9998,
              background: 'rgba(5,9,15,0.72)',
              backdropFilter: 'blur(4px)',
            }}
          />
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'fixed',
              top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 'min(520px, 92vw)',
              maxHeight: '80vh',
              background: '#0D1520',
              border: `1px solid ${color}33`,
              borderRadius: 14,
              zIndex: 9999,
              display: 'flex', flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '16px 20px', borderBottom: '1px solid #1a2638',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%', background: color,
                }} />
                <span style={{ fontSize: 15, fontWeight: 600, color: '#E8ECF1' }}>
                  Work Order #{workOrder.id}
                </span>
                <span style={{
                  fontSize: 10, color, textTransform: 'uppercase', fontWeight: 600,
                }}>
                  {workOrder.severity}
                </span>
              </div>
              <button
                onClick={onClose}
                style={{
                  width: 28, height: 28, borderRadius: 6,
                  border: '1px solid #243040', background: 'transparent',
                  color: '#556677', cursor: 'pointer', fontSize: 14,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                ×
              </button>
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }} className="scrollbar-hidden">
              {/* Info grid */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16,
              }}>
                <div>
                  <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 2 }}>AHU</div>
                  <div style={{ fontSize: 13, color: '#E8ECF1', fontWeight: 600 }}>{workOrder.ahu_id}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 2 }}>Level</div>
                  <div style={{ fontSize: 13, color: '#E8ECF1' }}>{workOrder.level}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 2 }}>Source</div>
                  <div style={{ fontSize: 13, color: '#8899aa' }}>{workOrder.trigger_source}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 2 }}>Created By</div>
                  <div style={{ fontSize: 13, color: '#8899aa' }}>{workOrder.created_by}</div>
                </div>
              </div>

              {/* Title & description */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 4 }}>Title</div>
                <div style={{ fontSize: 13, color: '#E8ECF1' }}>{workOrder.title}</div>
                {workOrder.description && (
                  <>
                    <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 4, marginTop: 12 }}>Description</div>
                    <div style={{ fontSize: 12, color: '#8899aa', lineHeight: 1.5 }}>{workOrder.description}</div>
                  </>
                )}
              </div>

              {/* FAIR snapshot */}
              {workOrder.fair_snapshot && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 6 }}>FAIR Scores</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {['F', 'A', 'I', 'R'].map((key) => {
                      const val = workOrder.fair_snapshot?.[key] ?? 0;
                      return (
                        <div key={key} style={{ flex: 1 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#556677', marginBottom: 2 }}>
                            <span>{key}</span><span>{val}</span>
                          </div>
                          <div style={{ height: 4, borderRadius: 2, background: '#1a2638' }}>
                            <div style={{
                              height: '100%', width: `${val}%`, borderRadius: 2,
                              background: val >= 70 ? '#00E5A0' : val >= 40 ? '#FFB020' : '#FF4D4D',
                            }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Status timeline */}
              <div>
                <div style={{ fontSize: 9, color: '#556677', textTransform: 'uppercase', marginBottom: 6 }}>Status History</div>
                <StatusTimeline
                  currentStatus={workOrder.status}
                  createdAt={workOrder.created_at}
                  updatedAt={workOrder.updated_at}
                  resolvedAt={workOrder.resolved_at}
                />
              </div>
            </div>

            {/* Footer actions */}
            {(isDraft || isActive) && (
              <div style={{
                padding: '12px 20px', borderTop: '1px solid #1a2638',
                display: 'flex', gap: 8, justifyContent: 'flex-end',
              }}>
                {isDraft && (
                  <>
                    <button
                      disabled={loading}
                      onClick={handleDismiss}
                      style={{
                        background: 'none', color: '#6d6e71', border: '1px solid #1a2638',
                        borderRadius: 8, padding: '7px 16px', fontSize: 12, cursor: 'pointer',
                        opacity: loading ? 0.5 : 1,
                      }}
                    >
                      Dismiss
                    </button>
                    <button
                      disabled={loading}
                      onClick={handleApprove}
                      style={{
                        background: '#00E5A0', color: '#0B0F14', border: 'none',
                        borderRadius: 8, padding: '7px 16px', fontSize: 12, fontWeight: 600,
                        cursor: 'pointer', opacity: loading ? 0.5 : 1,
                      }}
                    >
                      {loading ? '...' : 'Approve'}
                    </button>
                  </>
                )}
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workorders/StatusTimeline.tsx frontend/src/components/workorders/WorkOrderDetailModal.tsx
git commit -m "feat: add StatusTimeline and WorkOrderDetailModal components"
```

---

## Task 15: Work Orders Dashboard View — Main Container

**Files:**
- Create: `frontend/src/components/workorders/WorkOrdersView.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create WorkOrdersView**

Create `frontend/src/components/workorders/WorkOrdersView.tsx`:

```tsx
import { useState, useCallback } from 'react';
import { fetchWorkOrders } from '../../api/client';
import { usePolling } from '../../hooks/usePolling';
import type { WorkOrder } from '../../types/chat';
import WorkOrderStatsBar from './WorkOrderStatsBar';
import WorkOrderFilters from './WorkOrderFilters';
import WorkOrderTable from './WorkOrderTable';
import WorkOrderDetailModal from './WorkOrderDetailModal';

export default function WorkOrdersView() {
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const fetcher = useCallback(() => fetchWorkOrders(), []);
  const { data, refetch } = usePolling(fetcher, 60000, { pauseWhenHidden: true });

  const allWorkOrders: WorkOrder[] = data?.work_orders ?? [];

  // Apply filters
  const filtered = allWorkOrders.filter((wo) => {
    if (statusFilter.length > 0 && !statusFilter.includes(wo.status)) return false;
    if (severityFilter.length > 0 && !severityFilter.includes(wo.severity)) return false;
    return true;
  });

  const selectedWorkOrder = selectedId
    ? allWorkOrders.find((w) => w.id === selectedId) ?? null
    : null;

  return (
    <div>
      <div style={{
        fontSize: 18, fontWeight: 700, color: '#E8ECF1',
        fontFamily: 'var(--font-display)', marginBottom: 16,
      }}>
        Work Orders
      </div>

      <WorkOrderStatsBar workOrders={allWorkOrders} />
      <WorkOrderFilters
        statusFilter={statusFilter}
        severityFilter={severityFilter}
        onStatusChange={setStatusFilter}
        onSeverityChange={setSeverityFilter}
      />
      <WorkOrderTable
        workOrders={filtered}
        onRowClick={setSelectedId}
      />

      <WorkOrderDetailModal
        workOrder={selectedWorkOrder}
        onClose={() => setSelectedId(null)}
        onAction={refetch}
      />
    </div>
  );
}
```

- [ ] **Step 2: Wire WorkOrdersView into App.tsx**

In `frontend/src/App.tsx`, add lazy import at the top with the other lazy imports:

```typescript
const WorkOrdersView = React.lazy(() => import('./components/workorders/WorkOrdersView'));
```

In the `AnimatePresence` block (around line 349), add a third branch for `dashboardMode === 'workorders'`:

After the deepdive branch (around line 433), add:

```tsx
{dashboardMode === 'workorders' && (
  <motion.div
    key="workorders"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    transition={{ duration: 0.2 }}
  >
    <React.Suspense fallback={<div style={{ padding: 24, color: '#556677' }}>Loading...</div>}>
      <WorkOrdersView />
    </React.Suspense>
  </motion.div>
)}
```

Note: The existing `AnimatePresence` uses `mode="wait"` and conditions on `dashboardMode === 'simple'` vs else (deepdive). Update the logic to handle three modes:

Change from:
```tsx
{dashboardMode === 'simple' ? (
  <motion.div key="simple">...</motion.div>
) : (
  <motion.div key="deepdive">...</motion.div>
)}
```

To:
```tsx
{dashboardMode === 'simple' && (
  <motion.div key="simple">...</motion.div>
)}
{dashboardMode === 'deepdive' && (
  <motion.div key="deepdive">...</motion.div>
)}
{dashboardMode === 'workorders' && (
  <motion.div key="workorders">...</motion.div>
)}
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 4: Start dev server and test**

```bash
cd frontend && npm run dev &
```

Open `http://localhost:3000`. Use ModeToggle to switch to "Work Orders". Verify:
- Stats bar renders (may show empty/zero data without backend)
- Filters render and toggle
- Table renders (empty state)
- Mode switching between all three modes works

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workorders/WorkOrdersView.tsx frontend/src/App.tsx
git commit -m "feat: add Work Orders dashboard view with stats, filters, table, and detail modal"
```

---

## Layer 3: Polish

---

## Task 16: Toast Notifications

**Files:**
- Create: `frontend/src/hooks/useToast.ts`
- Create: `frontend/src/components/shared/Toast.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create useToast hook**

Create `frontend/src/hooks/useToast.ts`:

```typescript
import { useState, useCallback } from 'react';

export interface ToastItem {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

let toastListeners: Array<(toast: ToastItem) => void> = [];

export function showToast(message: string, type: ToastItem['type'] = 'info') {
  const toast: ToastItem = { id: `toast-${Date.now()}`, message, type };
  toastListeners.forEach((fn) => fn(toast));
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((toast: ToastItem) => {
    setToasts((prev) => [...prev, toast]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== toast.id));
    }, 3000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Register listener
  useState(() => {
    toastListeners.push(addToast);
    return () => {
      toastListeners = toastListeners.filter((fn) => fn !== addToast);
    };
  });

  return { toasts, removeToast };
}
```

- [ ] **Step 2: Create Toast component**

Create `frontend/src/components/shared/Toast.tsx`:

```tsx
import { AnimatePresence, motion } from 'framer-motion';
import { useToast } from '../../hooks/useToast';

const TYPE_COLORS: Record<string, string> = {
  success: '#00E5A0',
  error: '#FF4D4D',
  info: '#4DA6FF',
};

export default function ToastContainer() {
  const { toasts, removeToast } = useToast();

  return (
    <div style={{
      position: 'fixed',
      bottom: 24,
      right: 80,
      zIndex: 10000,
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      pointerEvents: 'none',
    }}>
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 40 }}
            transition={{ duration: 0.2 }}
            style={{
              background: '#0D1520',
              border: `1px solid ${TYPE_COLORS[toast.type] ?? '#1a2638'}44`,
              borderRadius: 8,
              padding: '8px 14px',
              fontSize: 12,
              color: '#E8ECF1',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              pointerEvents: 'auto',
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              maxWidth: 320,
            }}
          >
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: TYPE_COLORS[toast.type] ?? '#4DA6FF',
              flexShrink: 0,
            }} />
            <span style={{ flex: 1 }}>{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              style={{
                background: 'none', border: 'none', color: '#556677',
                cursor: 'pointer', fontSize: 12, padding: 0,
              }}
            >
              ×
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 3: Wire ToastContainer into App.tsx**

In `frontend/src/App.tsx`, import and render:

```typescript
import ToastContainer from './components/shared/Toast';
```

Add `<ToastContainer />` at the end of the root JSX (alongside ChatWidget, WorkOrderBadge, WorkOrderPanel).

- [ ] **Step 4: Add toast calls to WorkOrderCard approve/dismiss**

In `frontend/src/components/chat/cards/WorkOrderCard.tsx`, import `showToast`:

```typescript
import { showToast } from '../../../hooks/useToast';
```

In `handleApprove`, after `await approveWorkOrder(woId)`:
```typescript
showToast('Work order approved', 'success');
```

In `handleDismiss`, after `await dismissWorkOrder(woId)`:
```typescript
showToast('Work order dismissed', 'info');
```

In both catch blocks:
```typescript
showToast('Action failed — please try again', 'error');
```

Do the same in `WorkOrderPanelItem.tsx` and `WorkOrderDetailModal.tsx`.

- [ ] **Step 5: Build to verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useToast.ts frontend/src/components/shared/Toast.tsx frontend/src/App.tsx frontend/src/components/chat/cards/WorkOrderCard.tsx frontend/src/components/workorders/WorkOrderPanelItem.tsx frontend/src/components/workorders/WorkOrderDetailModal.tsx
git commit -m "feat: add toast notification system with success/error/info variants"
```

---

## Task 17: Final Verification

- [ ] **Step 1: Run TypeScript build**

```bash
cd frontend && npm run build 2>&1 | tail -30
```

Expected: build succeeds with no errors.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm test -- --passWithNoTests 2>&1 | tail -20
```

Expected: existing tests still pass.

- [ ] **Step 3: Start dev server and run through verification plan**

```bash
cd frontend && npm run dev &
```

Open `http://localhost:3000`. Test each layer:

**Layer 1 — Chat:**
1. Open chat → suggested prompts visible based on current level
2. Send message → response appears (streaming if backend supports SSE, fallback otherwise)
3. In fullscreen mode → conversation history sidebar visible on left
4. Toggle split view → chat 40% left, dashboard 60% right

**Layer 2 — Work Orders:**
1. Click work order badge → slide-out panel opens
2. Panel shows pending work orders grouped by severity
3. Switch to Work Orders mode via ModeToggle → table view renders
4. Click table row → detail modal opens with status timeline

**Layer 3 — Polish:**
1. Approve a work order → toast "Work order approved" appears bottom-right
2. Toast auto-dismisses after 3 seconds
3. Mode switching animates between views

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: complete frontend agentic upgrade — chat evolution, work orders, polish"
```
