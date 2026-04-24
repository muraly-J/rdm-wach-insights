# Telegram Bot UX Upgrade — Refined Design

**Intended spec location (post-plan-mode):** `docs/superpowers/specs/2026-04-22-telegram-bot-ux-upgrade-design.md`
**Plan mode file:** this file. Move + commit after `ExitPlanMode`.

**Status:** Draft — refined from brainstorming. Awaiting implementation-plan phase.
**Author:** Jinendra Muraly (via Claude / Antigravity)
**Date:** 2026-04-22 (refined 2026-04-23)
**Prior art:** `docs/superpowers/specs/2026-04-20-telegram-bot-design.md` (base bot, implemented).

---

## Context

WACH Insight has a working Telegram bot (`python-telegram-bot >=21.0`) that surfaces work-order lifecycle events to group chats. The current bot has three roles (managers / engineers / technicians) with chat-ID-based guards.

**This refinement simplifies the model to two roles and introduces a proper ticket lifecycle:**
- The **Agent** auto-generates tickets based on AHU health anomalies.
- **Technicians** verify and approve agent-drafted tickets.
- **Admin/Managers** set priority, status, and have final approval authority.

---

## Key Changes from Original Plan

| Area | Original | Refined |
|---|---|---|
| Roles | Technician, Engineer, Manager, Admin | **Technician, Admin/Manager** (2 roles only) |
| Group chats | 3 chats (techs, engineers, managers) | **2 chats** (Technicians, Admin/Managers) |
| Engineer role | Full handler set, review/edit flow | **Removed entirely** |
| Ticket creation | Agent → Manager approval → assign | **Agent → Technician verify/approve → Admin sets priority/status** |
| Status updates | Direct by technicians | **Technician drafts → Admin approves** |
| Ticket fields | id, title, description, severity, status | **TCK-YYYY-NNN, Subject, Category, Priority, Status, User, Role** |

---

## Decisions Locked

| Area | Choice |
|---|---|
| Roles | `technician` and `admin` (admin = manager). No engineer role. |
| Chats | 2 group chats: `TECHNICIANS_CHAT_ID`, `ADMIN_CHAT_ID` (replaces `MANAGERS_CHAT_ID`) |
| Ticket ID format | `TCK-NNN` (e.g. `TCK-001`) — ever-incrementing, no yearly reset |
| Ticket lifecycle | Agent drafts → Technician claims + verifies + approves → Admin sets priority & status |
| Status update flow | Technician proposes change → Admin approves |
| Identity | DuckDB `bot_users` + `/register` + admin approval |
| Menu UX | Reply-keyboard + inline cards + per-role `setMyCommands` |
| Tone | Friendly-but-brief, emoji on headers not every line |

---

## Ticket Schema

### Fields (as displayed in Telegram cards)

```
Ticket No.: TCK-2026-001
Subject:    Testing Create Ticket
Category:   Bug Report
Priority:   Low | Medium | High | Not Set
Status:     Open | In Progress | Resolved | Closed
User:       Agent  →  (technician name after approval)
Role:       Agent  →  (technician role after approval)
Created:    2026-04-23 10:30
Last Updated: 2026-04-23 14:15
```

### Agent-filled fields (on ticket creation)

The agent fills only these fields. All are **editable by the technician** before approving:

| Agent field name | Final ticket field | Notes |
|---|---|---|
| Title | **Subject** | Short summary of the issue |
| Subject Category | **Category** | E.g. "Bug Report", "Maintenance", "Performance Degradation" |
| Message | **Description** (body) | Detailed description of the work order |
| *(none)* | **Attachments** | Optional — for technician to add photos/docs if needed |

### DB schema changes (`work_orders` table)

```sql
-- New/renamed columns (migration from current schema)
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS ticket_no VARCHAR;        -- TCK-YYYY-NNN
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS category VARCHAR;         -- Bug Report, Maintenance, etc.
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS priority VARCHAR DEFAULT 'not_set';  -- low|medium|high|not_set
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS claimed_by VARCHAR;       -- telegram user_id of claiming tech
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS attachments JSON;         -- [{filename, file_id, mime}]

-- Status values change:
--   OLD: draft, pending_engineer_review, pending_approval, approved, in_progress, resolved, dismissed
--   NEW: draft, pending_tech_review, open, in_progress, resolved, closed
```

### Valid status transitions (new)

```python
_VALID_TRANSITIONS = {
    "draft":              {"pending_tech_review"},          # Agent → Technicians group
    "pending_tech_review": {"open", "dismissed"},           # Technician approves → Open; or rejects
    "open":               {"in_progress", "closed"},       # Admin sets status
    "in_progress":        {"resolved", "open"},            # Tech proposes resolved; or Admin reopens
    "resolved":           {"closed", "open"},              # Admin closes; or reopens
    "closed":             set(),                           # Terminal
    "dismissed":          set(),                           # Terminal
}
```

---

## Flow 1: Ticket Generation

### Sequence

```
1. Agent detects anomaly → creates work order (status='draft')
     - Fills: Title (→Subject), Subject Category (→Category), Message (→Description)
     - Auto-generates ticket_no: TCK-{year}-{seq}
     - Sets: User='Agent', Role='Agent'

2. Bot posts DRAFT card to Technicians group chat:
     ┌─────────────────────────────────────────┐
     │ 📋 New Draft Ticket — TCK-2026-014      │
     │                                         │
     │ Subject: AHU e0507 supply temp anomaly  │
     │ Category: Performance Degradation       │
     │ AHU: e0507 · Level 5                    │
     │                                         │
     │ Agent detected: Supply temp 8°C above   │
     │ setpoint for 2+ hours.                  │
     │                                         │
     │ Created by: 🤖 Agent                    │
     │                                         │
     │ [🙋 I'll Investigate]                   │
     └─────────────────────────────────────────┘

3. A technician taps [🙋 I'll Investigate]
     - First tap wins (claim). Others get toast: "📌 Claimed by @tech_name"
     - Card updates to show claimer:
     ┌─────────────────────────────────────────┐
     │ 📋 Claimed — TCK-2026-014              │
     │ 🔧 Investigating: @alice_tech           │
     │                                         │
     │ Subject: AHU e0507 supply temp anomaly  │
     │ Category: Performance Degradation       │
     │                                         │
     │ [✏️ Edit & Review]  [❌ Reject Ticket]  │
     └─────────────────────────────────────────┘

4. Technician taps [✏️ Edit & Review]
     - Opens ConversationHandler flow:
       a. "Current Subject: 'AHU e0507 supply temp anomaly'
           Send new Subject, or /skip to keep it."
       b. "Current Category: 'Performance Degradation'
           Send new Category, or /skip."
       c. "Current Description: '...'
           Send new description, or /skip."
       d. "Attach a photo/document, or /skip."
     - Shows preview card with changes:
     ┌─────────────────────────────────────────┐
     │ 📋 Review — TCK-2026-014               │
     │                                         │
     │ Subject: AHU e0507 supply temp ▼changed │
     │ Category: Maintenance         ▼changed  │
     │ Description: (updated)                  │
     │ Attachment: photo_01.jpg                │
     │                                         │
     │ [✅ Approve & Send to Admin]  [↩ Edit]  │
     └─────────────────────────────────────────┘

5. Technician taps [✅ Approve & Send to Admin]
     - Status: pending_tech_review → open
     - User field: Agent → technician's display name
     - Role field: Agent → Technician
     - Bot posts APPROVED card to Admin/Managers group:
     ┌─────────────────────────────────────────┐
     │ 🎫 New Ticket — TCK-2026-014           │
     │                                         │
     │ Subject: AHU e0507 supply temp anomaly  │
     │ Category: Maintenance                   │
     │ Priority: ⚪ Not Set                    │
     │ Status: 🟢 Open                         │
     │ AHU: e0507 · Level 5                    │
     │                                         │
     │ Verified by: @alice_tech (Technician)   │
     │                                         │
     │ [🔴 High] [🟡 Medium] [🟢 Low]         │
     │ [▶️ In Progress] [🔒 Close] [🌐 View]  │
     └─────────────────────────────────────────┘

6. Admin/Manager taps priority button (e.g. [🔴 High])
     - Priority: not_set → high
     - Card updates inline to reflect new priority

7. Admin/Manager taps status button (e.g. [▶️ In Progress])
     - Status: open → in_progress
     - Both groups get status-update notification
```

### Reject flow (step 3 alternative)

```
Technician taps [❌ Reject Ticket]
  → Confirm: "⚠️ Reject TCK-2026-014? [✅ Yes] [❌ Cancel]"
  → Status: pending_tech_review → dismissed
  → Card edits: "❌ TCK-2026-014 dismissed by @alice_tech"
  → Admin group notified of dismissal
```

---

## Flow 2: Status Update

### Sequence

```
1. Technician initiates status change:
     /update <ticket_no> <new_status>
     e.g. /update TCK-2026-014 resolved

   Or via inline button on their active work card:
     [✅ Mark Resolved]

2. Bot creates a STATUS CHANGE REQUEST:
     ┌─────────────────────────────────────────┐
     │ 📝 Status Change Request — TCK-2026-014│
     │                                         │
     │ Requested by: @alice_tech (Technician)  │
     │ Current Status: 🔵 In Progress          │
     │ Proposed Status: ✅ Resolved             │
     │                                         │
     │ Note: "Replaced faulty sensor, tested   │
     │ for 2 hours — readings normal."         │
     │                                         │
     │ [✅ Approve Change] [❌ Reject Change]   │
     └─────────────────────────────────────────┘

   This card is posted to Admin/Managers group.

3. Admin taps [✅ Approve Change]
     - Status transitions: in_progress → resolved
     - Both groups notified:
       Technicians: "✅ TCK-2026-014 status updated to Resolved. Approved by @admin."
       Admins: card edits to "✅ Status change approved by @admin_name"

4. Admin taps [❌ Reject Change]
     - Status unchanged
     - Technician notified: "❌ Status change for TCK-2026-014 rejected by @admin."
     - Optional: admin can add a reason
```

### Admin direct status changes (no approval needed)

Admins can change status directly without a request:
- `/setstatus <ticket_no> <status>` — immediate change
- Inline buttons on admin cards — immediate change

---

## Phasing

**Phase 1 — Foundation: Identity DB + Role System + Schema Migration.**
No visible UX change. Creates the foundation tables + decorators.

**Phase 2 — Ticket Generation Flow (Flow 1).**
Agent drafts → Technician claims + verifies → Admin sets priority/status.

**Phase 3 — Status Update Flow (Flow 2) + Polish.**
Technician proposes → Admin approves + confirmations + pagination.

**Phase 4 — `/ask` Agent Wiring (read-only, feature-flagged).**

Each phase is independently shippable.

---

## Architecture

### Module layout

```
backend/bot/
├── main.py                 # updated: use handler_registry(); remove engineers
├── config.py               # +FRONTEND_BASE_URL, +BOT_ADMIN_IDS, +ADMIN_CHAT_ID (replaces MANAGERS_CHAT_ID)
├── api_client.py           # +update_ticket, +set_priority, +claim_ticket
├── groups.py               # simplified: 2 groups only → DELETE in Phase 2
│
├── identity/               # Phase 1
│   ├── __init__.py
│   ├── store.py            # DuckDB CRUD: bot_users, audit
│   ├── registration.py     # /register ConversationHandler + admin approval cb
│   └── decorators.py       # @require_role(...), @require_admin
│
├── handlers/
│   ├── __init__.py         # handler_registry() aggregates all modules
│   ├── common.py           # /start, /help, /menu, /cancel
│   ├── admin.py            # /pending, /setstatus, /setpriority, /summary, /activity
│   │                       # cb: approve_change, reject_change, set_priority, set_status
│   ├── technicians.py      # REFACTORED: /mywork, /update, /status
│   │                       # cb: claim_ticket, edit_review, approve_ticket, reject_ticket
│   └── ask.py              # Phase 4 — /ask handler
│
├── ui/                     # Phase 2/3
│   ├── __init__.py
│   ├── keyboards.py        # inline keyboard factories per card type
│   ├── cards.py            # card renderers: draft_card, claimed_card, review_card,
│   │                       # ticket_card, status_change_card
│   ├── pagination.py       # generic paginate(items, page, per_page)
│   └── messages.py         # i18n-ready stub
│
├── push/
│   └── notifier.py         # simplified: emit(event, ticket) → 2 groups only
│
├── agent/                  # Phase 4
│   └── ask.py              # thin wrapper over POST /api/chat
│
└── rate_limit.py           # in-memory per-user token buckets
```

### DB delta (DuckDB, same file as work_orders)

```sql
-- Phase 1: Identity tables
CREATE TABLE IF NOT EXISTS bot_users (
  user_id           TEXT PRIMARY KEY,      -- Telegram user ID
  telegram_username TEXT,
  display_name      TEXT NOT NULL,
  role              TEXT NOT NULL,          -- technician | admin
  status            TEXT NOT NULL DEFAULT 'pending',  -- pending | active | disabled
  registered_at     TIMESTAMP DEFAULT NOW(),
  approved_by       TEXT,
  approved_at       TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_audit (
  id           BIGINT PRIMARY KEY,
  actor_id     TEXT NOT NULL,
  action       TEXT NOT NULL,
  ticket_no    TEXT,
  details      JSON,
  created_at   TIMESTAMP DEFAULT NOW()
);

-- Phase 2: Ticket number sequence
CREATE SEQUENCE IF NOT EXISTS ticket_no_seq START 1;

-- Phase 2: Status change requests
CREATE TABLE IF NOT EXISTS status_change_requests (
  id              BIGINT PRIMARY KEY,
  ticket_no       TEXT NOT NULL,
  work_order_id   INTEGER NOT NULL,
  requested_by    TEXT NOT NULL,           -- telegram user_id
  current_status  TEXT NOT NULL,
  proposed_status TEXT NOT NULL,
  notes           TEXT,
  decision        TEXT,                    -- approved | rejected | NULL (pending)
  decided_by      TEXT,
  decided_at      TIMESTAMP,
  created_at      TIMESTAMP DEFAULT NOW()
);

CREATE SEQUENCE IF NOT EXISTS status_change_seq START 1;

-- Phase 2: work_orders migration columns
-- (ALTER TABLE statements in _init_tables migration)
```

### Env changes

```bash
# REMOVED
# ENGINEERS_CHAT_ID=...          # No longer needed

# RENAMED
ADMIN_CHAT_ID=...                # was MANAGERS_CHAT_ID

# KEPT
TELEGRAM_BOT_TOKEN=...
TECHNICIANS_CHAT_ID=...
API_BASE_URL=http://localhost:8081

# NEW
FRONTEND_BASE_URL=https://wach-insight.app
BOT_ADMIN_IDS=123456789,987654321
BOT_AGENT_ENABLED=true
BOT_RATE_LIMIT_DEFAULT=30
BOT_RATE_LIMIT_ASK=5
```

---

## Identity & Registration

### Roles

Two roles: `technician` and `admin`. Admin is a superset of technician permissions.

```python
ROLE_HIERARCHY = {
    "admin": {"admin", "technician"},   # admin can do everything
    "technician": {"technician"},
}

def role_satisfies(user_role: str, required: str) -> bool:
    return required in ROLE_HIERARCHY.get(user_role, set())
```

### `/register` flow (DM-only)

```
User DMs bot / sends /start while unregistered
  → Inline card: [🔧 Technician] [👔 Admin/Manager]
User taps → callback register_role:{role}
  → ForceReply: "Display name?"
User replies
  → Inserts bot_users(status='pending') + bot_audit(action='register')
  → Posts registration card to Admin group:
      "👋 New registration
       @alice_c wants Technician — 'Alice Chen' — ID 123456789
       [✅ Approve] [❌ Reject]"
Admin taps Approve
  → bot_users.status='active', approved_by, approved_at
  → DM user: "You're approved as Technician. Tap /menu to begin."
  → setMyCommands(BotCommandScopeChat(user_id)) with role-specific list
  → bot_audit(action='approve_registration')
```

### Decorators

```python
def require_role(*roles):
    def deco(fn):
        async def wrapper(update, ctx):
            user = await identity.store.get_by_user_id(update.effective_user.id)
            if not user or user.status != 'active':
                await update.effective_message.reply_text(
                    "Not authorized. Tap /register if you're new.")
                return
            if not any(role_satisfies(user.role, r) for r in roles):
                return
            ctx.bot_user = user
            return await fn(update, ctx)
        return wrapper
    return deco

require_admin = require_role('admin')
```

---

## Commands & Menus

### Slash scopes

- **Default (unregistered):** `/start /help /register /cancel`
- **Technician:** + `/mywork /status <ahu> /update <ticket_no> <status> /done <ticket_no>`
- **Admin:** + `/pending /setstatus <ticket_no> <status> /setpriority <ticket_no> <priority> /summary /activity /ask <q>`

### Reply keyboard (DM only)

- **Technician:** `[📋 My Work] [📊 Status] [❓ Help]`
- **Admin:** `[🚨 Pending] [📈 Summary] [🤖 Ask]` / `[👥 Users] [📖 Menu]`

---

## Card Templates

### Draft ticket card (to Technicians group)

```
📋 New Draft Ticket — {ticket_no}

Subject: {subject}
Category: {category}
AHU: {ahu_id} · Level {level}

{description — max 200 chars}

Created by: 🤖 Agent · {created_relative}

[🙋 I'll Investigate]
```

### Claimed ticket card (edited in place)

```
📋 Claimed — {ticket_no}
🔧 Investigating: @{tech_username}

Subject: {subject}
Category: {category}

[✏️ Edit & Review]  [❌ Reject Ticket]
```

### Approved ticket card (to Admin group)

```
🎫 New Ticket — {ticket_no}

Subject: {subject}
Category: {category}
Priority: {priority_icon} {priority}
Status: 🟢 Open
AHU: {ahu_id} · Level {level}

Verified by: @{tech_username} (Technician)

[🔴 High] [🟡 Medium] [🟢 Low]
[▶️ In Progress] [🔒 Close] [🌐 View]
```

### Status change request card (to Admin group)

```
📝 Status Change Request — {ticket_no}

Requested by: @{tech_username} (Technician)
Current Status: {current_status_icon} {current_status}
Proposed Status: {proposed_status_icon} {proposed_status}

Note: "{notes}"

[✅ Approve Change] [❌ Reject Change]
```

### Priority icons

- 🔴 High
- 🟡 Medium
- 🟢 Low
- ⚪ Not Set

### Status icons

- 📋 Draft / Pending Review
- 🟢 Open
- 🔵 In Progress
- ✅ Resolved
- 🔒 Closed
- ❌ Dismissed

---

## Ticket Number Generation

```python
def generate_ticket_no(db) -> str:
    """Generate ever-incrementing TCK-NNN format ticket number."""
    with db._connect() as conn:
        seq = conn.execute("SELECT nextval('ticket_no_seq')").fetchone()[0]
    return f"TCK-{seq:03d}"
```

Ever-incrementing, no yearly reset. Sequence persisted via `agent_state` key `ticket_seq` to survive restarts.

### Predefined Categories

```python
TICKET_CATEGORIES = [
    "Bug Report",
    "System Error",
    "New Idea or Features",
    "Other Inquiry",
]
```

Technician selects from this list during edit/review (inline keyboard buttons). Agent also picks from this list when drafting.

---

## `/ask` Agent Wiring (Phase 4)

### Scope

- Admin only (technicians excluded this pass).
- Rate-limited: 5 per 5 min.
- `send_chat_action('typing')`, 30s timeout.
- Read-only mode enforced.

### Wrapper

```python
async def ask(question: str, user: BotUser, read_only: bool = True) -> AgentResponse:
    payload = {
        "message": question,
        "session_id": f"tg:{user.user_id}",
        "context": {"source": "telegram", "role": user.role, "read_only": read_only},
    }
    return await api_client.post("/api/chat", payload, timeout=30)
```

### Feature flag

`BOT_AGENT_ENABLED=false` → `/ask` hidden from scopes, handler replies "Assistant disabled."

---

## Files Touched

### Modify

- `backend/bot/main.py` — remove engineers import; use `handler_registry()`.
- `backend/bot/config.py` — rename `MANAGERS_CHAT_ID` → `ADMIN_CHAT_ID`; remove `ENGINEERS_CHAT_ID`; add new env vars.
- `backend/bot/handlers/technicians.py` — complete rewrite: claim flow, edit/review ConversationHandler, status update proposals.
- `backend/bot/push/notifier.py` — remove `notify_engineers`; rename `notify_managers` → `notify_admins`; add `emit()` dispatcher.
- `backend/core/agentdb.py` — add migration columns (ticket_no, category, priority, claimed_by, claimed_at, attachments); new status transitions; add `status_change_requests` table.
- `backend/tools/action_tools.py` — update `handle_create_work_order` to generate ticket_no and set `status='draft'` (→ `pending_tech_review` after notify).
- `.env.example` — updated vars.

### Create

- `backend/bot/identity/{__init__.py, store.py, registration.py, decorators.py}`
- `backend/bot/handlers/{__init__.py, common.py, admin.py, ask.py}`
- `backend/bot/ui/{__init__.py, keyboards.py, cards.py, pagination.py, messages.py}`
- `backend/bot/agent/{__init__.py, ask.py}`
- `backend/bot/rate_limit.py`

### Delete

- `backend/bot/handlers/engineers.py` — removed role.
- `backend/bot/groups.py` — replaced by identity decorators.

---

## Testing

### Unit tests

- `tests/bot/identity/test_store.py, test_decorators.py`
- `tests/bot/ui/test_keyboards.py, test_cards.py, test_pagination.py`
- `tests/bot/test_rate_limit.py`

### Handler tests (PTB mocked)

- `test_handlers_common.py` — `/start` in all user states.
- `test_handlers_registration.py` — full flow + double-approve race.
- `test_handlers_technicians.py` — claim flow, edit/review, status update proposal.
- `test_handlers_admin.py` — approve/reject status change, set priority, direct status change.
- `test_handlers_ask.py` — rate-limited, mocked agent.

### Integration

- `test_flow1_ticket_generation.py` — Agent creates → tech claims → tech edits → tech approves → admin gets card.
- `test_flow2_status_update.py` — Tech proposes → admin approves → both groups notified.
- `test_registration_roundtrip.py` — end-to-end with BotCommands scope refresh.

### Coverage targets

- Core (identity, ui, tickets): **90%**
- Handlers: **80%**
- Overall bot package: **85%**

---

## Verification

### Phase 1 (Identity)

- Fresh DB, admin IDs set, bot boots.
- Unregistered DM → registration card → submit → admin approves → user DM'd + scopes set.
- `bot_audit` rows written for register + approve.
- `pytest backend/tests/bot/identity/` green.

### Phase 2 (Ticket Generation — Flow 1)

- Agent creates work order → technicians group gets draft card.
- Tech taps "I'll Investigate" → card edits to claimed.
- Second tech taps → toast "Already claimed".
- Tech taps "Edit & Review" → ConversationHandler → can edit Subject, Category, Description, attach file.
- Tech taps "Approve & Send to Admin" → admin group gets full ticket card.
- Admin taps priority button → priority updates inline.
- Admin taps status button → status transitions, both groups notified.

### Phase 3 (Status Update — Flow 2)

- Tech types `/update TCK-2026-014 resolved` → status change request card in admin group.
- Admin approves → status changes, both groups notified.
- Admin rejects → tech notified, status unchanged.
- Admin direct `/setstatus` → immediate change, no approval needed.

### Phase 4 (`/ask`)

- Admin `/ask why did e0507 fail` → typing → answer card.
- Rate-limit: 6th in 5 min → throttle message.
- `bot_audit(action='ask')` rows appear.

---

## Resolved Decisions (2026-04-23)

| Question | Decision |
|---|---|
| Category taxonomy | **Predefined list:** Bug Report, System Error, New Idea or Features, Other Inquiry |
| Technicians see each other's claimed tickets? | **Yes** — all techs can see who claimed what |
| Auto-assignment logic | **Future phase** — manual claim-only for now |
| Ticket number reset | **Ever-incrementing** — no yearly reset (TCK-001, TCK-002, ...) |
| Attachment storage | **Telegram `file_id`** stored as a pointer in DuckDB (no object storage download) |
