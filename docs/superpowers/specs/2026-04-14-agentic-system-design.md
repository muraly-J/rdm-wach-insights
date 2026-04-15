# WACH Insight Agentic System Design

**Date:** 2026-04-14
**Status:** Draft
**Scope:** Full agentic evolution — Action Layer, Proactive Watchman, Multi-Agent Architecture, Human-in-the-Loop

---

## Context

WACH Insight currently operates as an **assistant**: it answers questions about building health using 6 read-only `query_*` tools via a Qwen LLM tool-calling loop. The system has no ability to take action (create tickets, send notifications), no proactive monitoring (only responds when a user sends a message), and no approval workflows.

This spec defines the evolution from Assistant to **Agent** — a system that detects problems, proposes actions, and executes them with appropriate human oversight. The goal is to bridge the gap between "Insight" (what the system knows) and "Action" (what the system does about it).

---

## Architecture Overview

**Approach: Layered Expansion** — build on existing patterns, no new infrastructure dependencies.

Five layers, each building on the previous:

| Layer | What | Key Files |
|---|---|---|
| 1. Data Layer | State models, work orders, agent memory | `backend/models/schemas.py`, DuckDB |
| 2. Action Tools | `create_work_order`, `send_notification`, `update_work_order` | `backend/tools/action_tools.py` |
| 3. Agent Router | Triage + Analysis Agent + Resolution Agent | `backend/agents/` |
| 4. Watchman | In-process pulse + external heavy analysis | `backend/core/watchman.py`, `scripts/scheduler/` |
| 5. HITL | Draft & approve workflow, severity-based autonomy | `routes/chat.py`, `BotMessage.tsx` |

---

## Layer 1: Data Layer — State Models & Tables

### `work_orders` table (DuckDB)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `ahu_id` | TEXT NOT NULL | e.g. "e0402" |
| `level` | INTEGER NOT NULL | Building level 1-11 |
| `title` | TEXT NOT NULL | Short description |
| `description` | TEXT | Detailed context |
| `severity` | TEXT | `critical` \| `warning` \| `info` |
| `status` | TEXT DEFAULT 'draft' | `draft` \| `pending_approval` \| `approved` \| `in_progress` \| `resolved` \| `dismissed` |
| `created_by` | TEXT | `agent` \| `user` |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |
| `resolved_at` | TIMESTAMP | |
| `trigger_source` | TEXT | `watchman` \| `chat` \| `manual` |
| `fair_snapshot` | JSON | FAIR scores at time of creation |
| `notified_via` | TEXT | `telegram` \| `none` |
| `approved_by` | TEXT | User who approved (null if auto) |

### `agent_state` table (DuckDB)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `key` | TEXT UNIQUE | e.g. `last_alert:e0402`, `last_summary:level3` |
| `value` | TEXT | JSON blob |
| `updated_at` | TIMESTAMP | |
| `expires_at` | TIMESTAMP | Optional TTL for stale entries |

### `watchman_queue` table (DuckDB)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `ahu_id` | TEXT | |
| `level` | INTEGER | |
| `fair_score` | FLOAT | |
| `severity` | TEXT | `critical` \| `warning` |
| `flagged_at` | TIMESTAMP | |
| `processed` | BOOLEAN DEFAULT false | |

### New Pydantic models

Add to `backend/models/schemas.py`:

- `WorkOrder`, `WorkOrderCreate`, `WorkOrderUpdate` — request/response models for work order CRUD
- `AgentMemoryEntry` — key/value with TTL
- `WatchmanAlert` — flagged AHU data

---

## Layer 2: Action Tools

New file: `backend/tools/action_tools.py`
Registered in: `backend/tools/tool_registry.py`

### `create_work_order(ahu_id, title, description, severity, fair_snapshot?)`

- Creates row in `work_orders` table, storing `fair_snapshot` (JSON: `{F, A, I, R, composite}`) at time of creation
- Sets status based on severity:
  - `critical`: status = `approved` (auto-approved, agent will call `send_notification` next)
  - `warning`: status = `draft` (returned to chat for HITL approval)
  - `info`: status = `draft` (logged only)
- Does **not** call `send_notification` internally — the Resolution Agent calls both tools explicitly in sequence, keeping tools as pure functions
- Returns the work order object (including `id`) for agent to reference in subsequent tool calls

### `send_notification(channel, recipient, message, work_order_id?)`

- MVP: Telegram only via `python-telegram-bot` library
- Recipient mapping in config (`backend/config.py`):
  ```python
  NOTIFICATION_RECIPIENTS = {
      "technician": "<telegram_chat_id>",
      "manager": "<telegram_chat_id>",
      "on_call": "<telegram_chat_id>"
  }
  TELEGRAM_BOT_TOKEN = "<token>"
  ```
- Links back to `work_order_id` if applicable, updates `work_orders.notified_via`
- **Spam prevention**: Checks `agent_state` for `last_alert:{ahu_id}` — if alerted within 4 hours, returns "already notified" instead of sending

### `update_work_order(work_order_id, status, notes?)`

- Transitions work order status with validation:
  - `draft` → `approved` | `dismissed`
  - `approved` → `in_progress` | `resolved`
  - `in_progress` → `resolved`
  - No backwards transitions
- Used by HITL approval flow and by agent to mark resolution

### Not included (deferred)

`generate_report_pdf()` — PDF generation + email is a separate concern. The work order + notification combo covers 90% of action needs. Spec this separately when needed.

---

## Layer 3: Agent Architecture — Triage + Specialists

New module structure:

```
backend/agents/
├── __init__.py
├── router.py              # Triage logic
├── analysis_agent.py      # Query tools + reasoning
├── resolution_agent.py    # Action tools + work order management
└── prompts.py             # System prompts per agent type
```

### Triage Router (`router.py`)

Two-step classification — deterministic first, LLM fallback:

**Step 1: Keyword/intent scoring (no LLM cost)**
- Action keywords (`fix`, `ticket`, `notify`, `alert`, `send`, `report`, `schedule`, `create`, `approve`) → Resolution Agent
- Query keywords (`show`, `what`, `why`, `compare`, `rank`, `trend`, `how`, `explain`) → Analysis Agent
- Mixed or ambiguous → Step 2

**Step 2: LLM classification (only when ambiguous)**
- Short Qwen call with constrained output: `{"agent": "analysis" | "resolution", "reason": "..."}`
- Uses `/no_think` prefix for speed
- System prompt: "Classify this user message. If the user wants information, output analysis. If the user wants an action taken, output resolution."

**Override**: Watchman-originated tasks always route directly to Resolution Agent.

### Analysis Agent (`analysis_agent.py`)

Extracted from current `qwen_client.py` behavior:

- **Tools**: `query_building_summary`, `query_health_scores`, `query_live_readings`, `query_ranking`, `query_financial_impact`, `search_docs`
- **System prompt**: Current `build_system_prompt()` output (persona-aware, FAIR methodology, ward topology)
- **Max tool rounds**: 5 (existing behavior)

### Resolution Agent (`resolution_agent.py`)

New agent focused on action:

- **Tools**: `create_work_order`, `send_notification`, `update_work_order`, `query_health_scores` (needs data context), `search_docs` (needs maintenance history)
- **System prompt**: "You are a building operations coordinator for WACH. Your job is to create work orders, notify the right people, and track issue resolution. Always include FAIR scores and financial impact context in tickets. Be concise and actionable."
- **Max tool rounds**: 3 (actions should be fast)
- **Rule**: Resolution Agent can read data for context but must never be the primary analyst

### Chat route integration (`routes/chat.py`)

```python
# Current:
response = await qwen_client.generate_with_tools(messages, tools)

# New:
agent_type = router.classify(user_message, conversation_history)
if agent_type == "analysis":
    response = await analysis_agent.run(messages)
elif agent_type == "resolution":
    response = await resolution_agent.run(messages)
```

The `generate_with_tools()` loop in `qwen_client.py` stays unchanged — each agent calls it with different tool sets and system prompts.

### Mid-Conversation Agent Handover

The triage router is called **on every user message**, not just the first. This means:
- Conversation starts as analysis ("What's wrong with Level 4?") → Analysis Agent responds
- User follows up ("Create a ticket for e0402") → router re-classifies → Resolution Agent handles next turn
- The full conversation history is passed to whichever agent handles the current turn, so context is preserved
- No explicit "handover" mechanism needed — stateless routing per message is sufficient

---

## Layer 4: The Watchman — Proactive Background Agent

### In-Process Pulse (`backend/core/watchman.py`)

Runs inside FastAPI process via `asyncio.create_task()` in lifespan startup.

- **Frequency**: Every 30 minutes (aligned with ETL cycle)
- **Logic**:
  1. Query DuckDB for latest FAIR scores across all 121 AHUs
  2. Apply severity thresholds:
     - FAIR < 40 → `critical`
     - FAIR 40-60 → `warning`
     - FAIR > 60 → healthy, skip
  3. For each flagged AHU, check `agent_state` for `last_alert:{ahu_id}`:
     - Critical: cooldown = 4 hours
     - Warning: cooldown = 24 hours
     - Skip if within cooldown
  4. Write flagged AHUs to `watchman_queue` table

- **No LLM calls.** Pure threshold math. Fast, predictable, zero token cost.

### External Heavy Analysis (extended `scripts/scheduler/scheduler.py`)

New step added after existing ETL pipelines:

- **Trigger**: Reads unprocessed rows from `watchman_queue`
- **Logic**:
  1. For each flagged AHU, invokes Resolution Agent with context:
     > "AHU {id} on Level {n} has FAIR score {score}. Breakdown: F={f}, A={a}, I={i}, R={r}. Analyze and take appropriate action."
  2. Resolution Agent uses tools: queries financial impact, checks maintenance history via `search_docs`, creates work order, sends notification (if autonomy threshold allows)
  3. Updates `agent_state` with `last_alert:{ahu_id}` = now
  4. Marks `watchman_queue` row as processed

### Severity-Based Autonomy

| FAIR Score | Severity | Agent Behavior |
|---|---|---|
| < 40 | Critical | Auto-create work order (status=`approved`), auto-notify technician via Telegram, log to `agent_state` |
| 40-60 | Warning | Create work order (status=`draft`), surface for user approval in next chat session |
| > 60 | Healthy | No action |

---

## Layer 5: Human-in-the-Loop — Draft & Approve

### Extended Chat API Response

Current format:
```json
{"reply": "text", "navigate": {...}}
```

New format:
```json
{
  "reply": "markdown text",
  "navigate": {"level": 4, "device": "e0402"},
  "actions": [
    {
      "type": "approve_work_order",
      "work_order_id": 42,
      "label": "Submit Ticket",
      "description": "Create work order for e0402 phase imbalance + notify technician via Telegram"
    },
    {
      "type": "dismiss",
      "work_order_id": 42,
      "label": "Dismiss"
    },
    {
      "type": "edit_draft",
      "work_order_id": 42,
      "label": "Edit Draft"
    }
  ]
}
```

### New API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/work-orders/{id}/approve` | Transition draft → approved, trigger notification |
| `POST` | `/api/work-orders/{id}/dismiss` | Transition draft → dismissed |
| `GET` | `/api/work-orders?status=draft` | List pending drafts |
| `PATCH` | `/api/work-orders/{id}` | Edit title/description before approving |

### Frontend Changes (`BotMessage.tsx`)

Extend to render `actions` array below message text:

- `approve_work_order` → green/accent button → calls approve endpoint → becomes "Submitted" (disabled)
- `dismiss` → ghost/subtle button → calls dismiss endpoint → buttons disappear
- `edit_draft` → opens inline text edit for work order description, then Submit/Cancel

Same pattern as existing navigation button rendering — just more action types.

### Pending Drafts on Chat Open

When user opens chat and drafts exist (via `GET /api/work-orders?status=draft`), first bot message:
> "You have {n} pending work order drafts since your last session. Want me to walk through them?"

Ensures Watchman-created drafts don't get lost when user was away.

---

## Implementation Order

Recommended build sequence (each layer depends on the previous):

1. **Layer 1: Data Layer** — tables, models, migrations
2. **Layer 2: Action Tools** — tool handlers, registration, Telegram integration
3. **Layer 3: Agent Router** — triage classifier, agent extraction, prompt engineering
4. **Layer 4: Watchman** — in-process pulse, scheduler extension, queue processing
5. **Layer 5: HITL** — API endpoints, chat response format, frontend action buttons

---

## Verification Plan

### Layer 1
- Create tables, insert test rows, verify CRUD operations
- Validate Pydantic model serialization/deserialization

### Layer 2
- Unit test each tool handler with mock data
- Integration test: create work order → verify DB row → send test Telegram message
- Test spam prevention: create two alerts for same AHU within cooldown → second should be blocked

### Layer 3
- Unit test triage router with known action/query phrases
- Integration test: send chat message → verify correct agent handles it
- Test agent handover: query that starts as analysis but user then says "create a ticket for that"

### Layer 4
- Unit test pulse threshold logic with synthetic FAIR scores
- Integration test: inject low FAIR score → verify watchman_queue row created → scheduler processes it → work order exists
- Test cooldown: flag same AHU twice within 4 hours → second should be skipped

### Layer 5
- Test approve endpoint: draft → approved → notification sent
- Test dismiss endpoint: draft → dismissed → no notification
- Frontend: verify action buttons render, click approve → buttons update
- Test pending drafts: create drafts while chat closed → reopen → see prompt

### End-to-End Agentic Workflow
1. Inject AHU e0402 FAIR score = 35 into DuckDB
2. Watchman pulse detects critical → writes to queue
3. Scheduler picks up → Resolution Agent creates work order (auto-approved) + sends Telegram
4. User opens chat → sees "Ticket #42 created for e0402, technician notified"
5. User asks "show me level 4 health" → triage routes to Analysis Agent → normal query response

---

## Dependencies

| Dependency | Purpose | Install |
|---|---|---|
| `python-telegram-bot` | Telegram Bot API | `pip install python-telegram-bot` |

No other new infrastructure. DuckDB, Qwen/LM Studio, InfluxDB, ChromaDB all already in use.

---

## Configuration (new `.env` entries)

```
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_RECIPIENTS_TECHNICIAN=<chat_id>
TELEGRAM_RECIPIENTS_MANAGER=<chat_id>
TELEGRAM_RECIPIENTS_ON_CALL=<chat_id>
WATCHMAN_INTERVAL_SECONDS=1800
WATCHMAN_CRITICAL_THRESHOLD=40
WATCHMAN_WARNING_THRESHOLD=60
WATCHMAN_COOLDOWN_CRITICAL_HOURS=4
WATCHMAN_COOLDOWN_WARNING_HOURS=24
```

---

## Out of Scope (deferred)

- `generate_report_pdf()` tool — spec separately when needed
- Email/SMTP notifications — Telegram covers MVP
- WebSocket/SSE real-time push — polling on chat open is sufficient for now
- Dashboard work order widget — surface work orders in chat first, dashboard later
- n8n integration — may add later if workflow complexity grows
