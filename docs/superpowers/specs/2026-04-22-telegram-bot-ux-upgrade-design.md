# Telegram Bot UX Upgrade — Design

**Location:** `docs/superpowers/specs/2026-04-22-telegram-bot-ux-upgrade-design.md`

**Status:** Draft — approved in brainstorming. Awaiting implementation-plan phase.
**Author:** Jinendra Muraly (via Claude)
**Date:** 2026-04-22
**Prior art:** `docs/superpowers/specs/2026-04-20-telegram-bot-design.md` (base bot, implemented).

---

## Context

WACH Insight has a working Telegram bot (`python-telegram-bot >=21.0`) that surfaces work-order lifecycle events to three role-scoped group chats (managers / engineers / technicians). Roles are inferred by `chat_id == X_CHAT_ID` guards. Users interact via `/commands` and a small set of inline callbacks.

The bot is functional but feels bolted-on:
- Identity is group-chat-based, so DMs, per-user routing, and role changes are impossible without env edits + restart.
- Inline-button UX dead-ends on `Edit` / `Done` (tells user to type the slash command instead).
- No `/start` menu, no persistent keyboard, no `setMyCommands` scope per role — users memorise slashes.
- Every role in a group gets notified identically; "Alice assigned" still pings the whole technicians chat.
- No filtering/pagination/confirmation/deep-linking.
- The WACH RAG agent (Gemini 2.0 Flash + Qwen + ChromaDB) is not wired to Telegram.

**Goal of this pass:** make the bot Telegram-native, smarter, and ready for business-flow refinement by colleagues. Add per-user identity, claim-based channel routing, role-scoped menus and keyboards, read-only `/ask` assistant, and core polish (confirm/paginate/filter/deep-link/summary/audit/rate-limit). Leave hooks for future business-flow work so it's a data-change, not a rewrite.

**Non-goals (this pass):**
- Conversational DM / `[Explain]` button / agent mutations (plumbing only; flag-gated).
- i18n content (scaffold-only; deferred).
- Email/SMS notifications (router contract supports, not implemented).
- Frontend changes (beyond existing `/ahu/{ahu_id}?wo={wo_id}` URL schema).

---

## Decisions Locked

| Area | Choice |
|---|---|
| Identity | DuckDB `bot_users` + `/register` + manager approval |
| Channels | Group chats + per-user DMs; pluggable router defaulting to claim-then-DM |
| Menu UX | Reply-keyboard (top 3) + menu-button long tail + inline cards + per-role `setMyCommands` |
| Assistant | `/ask <q>` slash-only, read-only, per-user session memory |
| Polish | Confirm destructive, pagination, filter chips, deep-link URL, rich `/summary`, `/activity`, rate-limit + snooze |
| Tone | Friendly-but-brief, emoji on headers not every line |
| Phasing | P1 Foundation-first: Identity → Routing+Menus → Polish → Agent → Business-flow hooks |

---

## Phasing

**Phase 1 — Identity DB + `/register` + admin + scoped BotCommands.** No visible UX change. Foundation.
**Phase 2 — Routing layer + claim-then-DM + menu button + reply keyboard + card/keyboard factories.** Visible.
**Phase 3 — Polish: confirm, paginate, filters, deep-link, `/summary`, `/activity`, rate-limit + snooze.**
**Phase 4 — `/ask` agent wiring (read-only, feature-flagged).**
**Phase 5 — Business-flow refinement with colleagues (hooks already in place).**

Each phase is independently shippable. No rework between phases — Phase 1 is the boundary that enables the rest.

---

## Architecture

### Module layout

```
backend/bot/
├── main.py                 # unchanged entrypoint; uses handler_registry()
├── config.py               # +FRONTEND_BASE_URL, +BOT_ADMIN_IDS, +BOT_AGENT_ENABLED, +BOT_DEFAULT_ROUTE, ...
├── api_client.py           # unchanged
├── groups.py               # DELETE in Phase 2 (replaced by identity.decorators)
│
├── identity/               # Phase 1
│   ├── __init__.py
│   ├── store.py            # DuckDB CRUD: bot_users, audit, prefs
│   ├── registration.py     # /register ConversationHandler + manager-approval cb
│   └── decorators.py       # @require_role(...), @require_admin
│
├── routing/                # Phase 2
│   ├── __init__.py
│   ├── router.py           # route(event, wo, meta) -> list[Recipient]   (pure)
│   ├── recipients.py       # Recipient dataclass
│   ├── matrix.py           # ROUTE_MATRIX dict: Event -> RouteStrategy
│   └── claims.py           # atomic claim/release over wo_claims table
│
├── handlers/
│   ├── __init__.py         # handler_registry() aggregates all modules
│   ├── common.py           # /start, /help, /menu, /settings, /cancel
│   ├── managers.py         # refactored: @require_role('manager')
│   ├── engineers.py        # refactored
│   ├── technicians.py      # refactored
│   ├── admin.py            # /users, /promote, /deactivate, /pending_users,
│   │                       # /snooze, /unsnooze, /activity
│   └── ask.py              # Phase 4 — /ask handler
│
├── ui/                     # Phase 2/3
│   ├── __init__.py
│   ├── keyboards.py        # inline_kb_for(event, wo, role, claim_state) factory
│   ├── reply_keyboard.py   # role-aware persistent bottom keyboard (DM only)
│   ├── menu_button.py      # setChatMenuButton + setMyCommands per-chat scope
│   ├── cards.py            # per-Event card renderers (replaces push/notifier._format_*)
│   ├── pagination.py       # generic paginate(items, page, per_page)
│   └── messages.py         # i18n-ready stub (English-only this pass)
│
├── push/
│   └── notifier.py         # slimmed: emit(event, wo) -> router + cards + send
│
├── agent/                  # Phase 4
│   └── ask.py              # thin wrapper over POST /api/chat
│
└── rate_limit.py           # in-memory per-user token buckets
```

### DB delta (DuckDB, same file as work_orders)

```sql
CREATE TABLE IF NOT EXISTS bot_users (
  user_id           TEXT PRIMARY KEY,
  telegram_username TEXT,
  display_name      TEXT NOT NULL,
  role              TEXT NOT NULL,             -- technician|engineer|manager|admin
  status            TEXT NOT NULL DEFAULT 'pending',  -- pending|active|disabled
  tone_preference   TEXT DEFAULT 'friendly',
  registered_at     TIMESTAMP DEFAULT NOW(),
  approved_by       TEXT,
  approved_at       TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_audit (
  id           BIGINT PRIMARY KEY,
  actor_id     TEXT NOT NULL,
  action       TEXT NOT NULL,
  work_order_id TEXT,
  details      JSON,
  created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wo_claims (
  work_order_id TEXT NOT NULL,
  event         TEXT NOT NULL,
  claimed_by    TEXT,
  claimed_at    TIMESTAMP,
  expires_at    TIMESTAMP,
  PRIMARY KEY (work_order_id, event)
);

CREATE TABLE IF NOT EXISTS user_prefs (
  user_id        TEXT PRIMARY KEY,
  filter_default JSON,
  page_size      INT DEFAULT 5,
  snooze_until   TIMESTAMP,
  onboarded_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bot_audit_actor   ON bot_audit(actor_id);
CREATE INDEX IF NOT EXISTS idx_bot_audit_wo      ON bot_audit(work_order_id);
CREATE INDEX IF NOT EXISTS idx_wo_claims_expires ON wo_claims(expires_at);
```

All tables additive. Rollback = drop 4 tables.

### Env additions (`.env.example`)

```
FRONTEND_BASE_URL=https://wach-insight.app
BOT_ADMIN_IDS=123456789,987654321
BOT_AGENT_ENABLED=true
BOT_DEFAULT_ROUTE=claim_then_dm
BOT_CLAIM_EXPIRY_MINUTES=30
BOT_RATE_LIMIT_DEFAULT=30
BOT_RATE_LIMIT_ASK=5
BOT_CONFIRM_TIMEOUT_SECONDS=60
```

---

## Identity & Registration

### Roles

`technician | engineer | manager | admin`. Admin = superset. Hierarchy resolved by `role_satisfies(user_role, required) -> bool` with editable `ROLE_HIERARCHY` map. Admin IDs seeded from `BOT_ADMIN_IDS` on boot.

### `/register` flow (DM-only)

```
User DMs bot / sends /start while unregistered
  → Inline card: [🔧 Technician] [⚙️ Engineer] [👔 Manager]
User taps → callback register_role:{role}
  → ForceReply: "Display name?"
User replies
  → Inserts bot_users(status='pending') + bot_audit(action='register')
  → Posts registration card to managers group:
      "👋 New registration
       @alice_c wants Engineer — 'Alice Chen' — ID 123456789
       [✅ Approve] [❌ Reject]"
Manager taps Approve
  → bot_users.status='active', approved_by, approved_at
  → DM user: "You're approved as Engineer. Tap /menu to begin."
  → setMyCommands(BotCommandScopeChat(user_id)) with role-specific list
  → setChatMenuButton(BotCommandScopeChat(user_id))
  → bot_audit(action='approve_registration')
```

Reject: `status='disabled'`, optional reason DM. Second tap on approved card: toast "Already approved by @X".

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

### Bootstrap sequence

```
1. Load env
2. Connect DuckDB → ensure_schema()
3. Seed admins from BOT_ADMIN_IDS (upsert role=admin, status=active)
4. Seed technicians from TECHNICIANS_JSON (one-shot; only if row missing)
5. Build Application → register handlers via handler_registry()
6. Register default-scope BotCommands
7. For each active bot_user: set_my_commands(role-scoped, BotCommandScopeChat)
8. setChatMenuButton per user
9. Start polling
```

Steps 7–8 re-run on approve/promote/deactivate via `identity.refresh_user_scopes(user_id)`.

---

## Routing Layer

### Contract

```python
# routing/router.py
def route(event: Event, wo: WorkOrder | None = None,
          meta: dict | None = None) -> list[Recipient]:
    """Pure function. No I/O. Looks up ROUTE_MATRIX, returns recipients."""
```

`Recipient(kind: 'group'|'dm', chat_id: int, role: str, claim_state: ClaimState | None)`.

`ClaimState` = `{claimed_by: str, claimed_at: datetime, expires_at: datetime}` or `None` when unclaimed.

### Events (enum)

`WO_CREATED, WO_APPROVED, WO_PUSHED_TO_ENG, WO_SENT_BACK, WO_ASSIGNED, WO_STARTED, WO_RESOLVED, USER_REGISTERED`.

New events = add enum value + matrix row + card renderer + keyboard builder. Nothing else.

### Matrix (`routing/matrix.py`)

```python
ROUTE_MATRIX: dict[Event, RouteStrategy] = {
    Event.WO_CREATED:       ClaimThenDM(role='manager'),
    Event.WO_APPROVED:      Broadcast('managers') + DM(assignee=True),
    Event.WO_PUSHED_TO_ENG: ClaimThenDM(role='engineer'),
    Event.WO_SENT_BACK:     Broadcast('managers'),
    Event.WO_ASSIGNED:      Broadcast('technicians') + DM(assignee=True),
    Event.WO_STARTED:       Broadcast('managers', low_priority=True),
    Event.WO_RESOLVED:      Broadcast('managers', 'technicians'),
    Event.USER_REGISTERED:  Broadcast('managers'),
}
```

### Claim mechanics

- Atomic `INSERT ... ON CONFLICT DO NOTHING` on `wo_claims(work_order_id, event)`.
- First tap wins, loser receives `answerCallbackQuery(text="📌 Claimed by @X 2m ago")` toast.
- Expiry default 30 min (`BOT_CLAIM_EXPIRY_MINUTES`). Expired claim re-claimable.
- Per-event claim (approve-claim independent from resolve-claim).
- `[🔓 Release claim]` button on DM card for voluntary release.

### Notifier collapse

`push/notifier.py` shrinks to ~30 lines:

```python
async def emit(event, wo=None, meta=None):
    recipients = router.route(event, wo, meta)
    card = cards.render(event, wo, meta)
    for r in recipients:
        kb = keyboards.inline_kb_for(event, wo, role=r.role, claim=r.claim_state)
        await bot.send_message(chat_id=r.chat_id, text=card, reply_markup=kb,
                               parse_mode='Markdown')
```

Backwards-compat during Phase 2: keep `notify_managers/engineers/technicians` as thin shims.

---

## Commands & Menus

### Slash scopes (`setMyCommands` per `BotCommandScopeChat(user_id)`)

- **Default:** `/start /help /menu /register /cancel`
- **Technician:** + `/mywork /go <id> /done <id> /status <ahu>`
- **Engineer:** + `/review <id> /edit <id> /sendback <id> /query <ahu> /level <N> /ask <q>`
- **Manager:** + `/pending /workorder <id> /summary /activity /ask <q>`
- **Admin:** + `/users /promote /deactivate /pending_users /snooze /unsnooze`

`/start` → reclaims Telegram-standard greeting. Technician's former `/start <id>` → renamed `/go <id>`.

### Reply keyboard (DM only)

Role-aware, persistent, `resize_keyboard=True, one_time_keyboard=False`.

- Technician: `[📋 My Work] [📊 Status] [❓ Help]` / `[⚙️ Settings] [📖 Menu]`
- Engineer: `[🔍 Review] [🤖 Ask] [📊 Level]` / `[⚙️ Settings] [📖 Menu]`
- Manager: `[🚨 Pending] [📈 Summary] [🤖 Ask]` / `[👥 Users] [📖 Menu]`
- Admin: Manager set + direct `/users` / `/activity` shortcuts.

Taps send plain text matching the label; `MessageHandler(regex=...)` dispatches to the same handler as the slash command. Reply-keyboard shortcuts for commands that normally take an argument (e.g., `/review <id>`, `/level <N>`) open a picker card — paginated list of eligible WOs/levels — instead of erroring on missing args.

Group chats get no reply keyboard.

### Menu button (`setChatMenuButton`)

Labelled "📖 Menu". Opens inline menu card rendered by `cards.render_menu_card(user)` — buttons chosen by role.

### `/start` dispatcher

- Unregistered → registration prompt
- Pending → "Waiting for manager approval."
- Active → menu card + reply keyboard + onboarding (one-time)
- Disabled → "Your account is disabled. Contact an admin."

### `/settings`

Inline card showing role, tone, default filter, page size, snoozed AHUs. Buttons: change page size, clear filters, snooze self.

---

## Keyboards, Cards, Confirmations

### Card template

```
{severity_icon} {title}               #{wo_id}
AHU {ahu_id} · L{level} · {created_rel}

{body — max 200 chars}

F:{f} A:{a} I:{i} R:{r} · Composite: {c}

Status: {status_chip}
```

Severity: 🔴 Critical, 🟡 Maintenance, 🔵 Monitor. Status chips: 🟠 Pending, 🟢 Approved, 🟣 In progress, ✅ Resolved, ⚫ Dismissed.

### Keyboard factory

`ui/keyboards.inline_kb_for(event, wo, role, claim_state) -> InlineKeyboardMarkup`. Pure, dispatches on `(event, role, wo.status)`.

### Key flows

- **Manager WO_CREATED (group, unclaimed):** `[✅ Approve] [❌ Dismiss] [🔍 Push to Eng]` / `[🌐 Open in dashboard]`
- **Manager Approve → assignment sub-card:** `[👥 Any technician] [👤 Pick specific ▸]` / `[↩ Back]`. Pick-specific = paginated active technicians.
- **Engineer WO_PUSHED_TO_ENG:** `[✏️ Edit] [↩ Send back] [🤖 Ask why]` / `[🌐 Open in dashboard]`. `Edit` **enters ConversationHandler directly** (fixes current dead-end). `Ask why` prefills `/ask` with `"Why was work order #{id} flagged?"`.
- **Technician WO_ASSIGNED (DM):** `[▶️ Start work] [🙋 Not me? Reassign]` / `[🌐 Open in dashboard]`
- **Technician in_progress (DM):** `[✅ Done] [⏸ Pause] [💬 Add note]`. `Done` enters Done ConversationHandler with `ForceReply` for note.

### Destructive confirmation

Shared `render_confirm(action, wo)` + `confirm_kb(action, wo_id)`. Applied to Dismiss WO, Deactivate user, Reject registration, Release claim, global Unsnooze. 60s timeout (message edits to "Confirmation expired").

Pattern: tap → edit message with banner `⚠️ Dismiss #1234? This cannot be undone.` + `[✅ Yes, dismiss] [❌ Cancel]`. Callback data: `confirm:{action}:{id}` / `confirm:cancel:{id}`.

### Pagination (`ui/pagination.py`)

Generic. `per_page=5` default; `user_prefs.page_size` override. Nav row: `[◀ Prev] page N/M [Next ▶]` / `[🔽 Filter] [🔄 Refresh] [❌ Close]`. State in `callback_data`: `list:{kind}:{page}:{filter_hash}`. No server-side pagination state.

### Filter chips

`[Severity: any ▾] [Level: any ▾]` → multiselect sub-card. Persists to `user_prefs.filter_default`.

### Deep-link

URL button `[🌐 Open in dashboard]` → `{FRONTEND_BASE_URL}/ahu/{ahu_id}?wo={wo_id}`. Hidden when env unset.

---

## `/ask` Agent Wiring

### Handler (`handlers/ask.py`)

- Scope: engineer, manager, admin (technicians excluded this pass).
- Rate-limited via `rate_limit.allow(user_id, bucket='ask')` — 5 per 5 min default.
- `send_chat_action('typing')`, 30 s timeout.
- Writes `bot_audit(action='ask', details={question, latency_ms, tokens})`.

### Wrapper (`agent/ask.py`)

```python
async def ask(question: str, user: BotUser, read_only: bool = True) -> AgentResponse:
    payload = {
        "message": question,
        "session_id": f"tg:{user.user_id}",
        "context": {"source": "telegram", "role": user.role, "read_only": read_only},
    }
    return await api_client.post("/api/chat", payload, timeout=30)
```

`session_id="tg:{user_id}"` → per-user backend session memory (conversational continuity without conversational UX).

### Read-only enforcement

Two layers:
1. Bot sends `context.read_only=true`.
2. Backend `/api/chat` strips mutation tools from registry when `read_only=true`. Only read tools remain (`get_health_scores`, `list_work_orders`, `get_ahu_status`, RAG lookup).

If mutation required: agent replies "I can tell you, but can't change anything from here. Use /pending or /workorder."

### Response card

```
🤖 Alice asked:
"<question>"
─────────────────────────
<answer>
─────────────────────────
Sources: N docs · session tg:{user_id}
```

Buttons: `[🔍 #WO_ID]` for referenced WOs, `[🌐 Open L5 dashboard]`, `[🔄 Ask follow-up]` (ForceReply; same session).

### Feature flag

`BOT_AGENT_ENABLED=false` → `/ask` hidden from scopes, handler replies "Assistant disabled."

### Future hooks (flag-flips, no rewrite)

- Conversational DM: non-command text in DM → `agent.ask` (flag `BOT_AGENT_MODE=slash_plus_dm`)
- `[Explain this]` button on WO cards (flag `..._plus_explain`, auto-prompt per WO)
- Agent mutations with confirm (flag `BOT_AGENT_ALLOW_MUTATIONS=true`, needs `pending_tool_calls` table)

---

## Polish

### Rich `/summary` card (pinnable in managers group)

```
📈 WACH Summary — 2026-04-22 14:32
─────────────────────────────────
Active: 37
🔴 4  🟡 19  🔵 14

Top 3 worst AHUs (24h):
  e0507  L5  score 38 ▼12  · 2 open
  e0812  L8  score 44 ▼08  · 1 open
  e0301  L3  score 51 ▼05  · 3 open

Trend (7d): ▁▂▃▅▇▆▅    stable

Resolved today: 6  ·  Avg TTR: 3.2h
─────────────────────────────────
[🔄 Refresh] [🚨 Show pending] [📊 Dashboard]
Last updated: 14:32 by @alice
```

Sparkline = unicode block chars over 7d health index. `[🔄 Refresh]` → `editMessageText` in place. Cached `message_id` in `agent_state` for auto-edit on re-invocation. Data assembled client-side from existing `/health-scores` + `/dashboard/ranking` (no new endpoint).

### `/activity` feed

`manager` + `admin`. Paginated list of last N `bot_audit` rows with filter-by-user / filter-by-action chips. Every mutation handler writes one row; `/activity` queries by `created_at DESC`.

### Rate-limit + snooze

- **Token buckets** in-memory (`rate_limit.py`). Buckets: `default` (30/min), `ask` (5/5min), `admin` (60/min). No persistence — acceptable for resets on restart.
- **Alert suppression:**
  - `/snooze <ahu_id> <minutes>` (admin): writes `agent_state` key `snooze:{ahu_id}` (reuses existing pre-Phase-1 KV table — same one that holds `last_alert:{ahu_id}` for the 4h AHU cooldown). Router checks before emitting WO_CREATED for that AHU.
  - `/unsnooze <ahu_id>` (admin, destructive-confirm).
  - `/snooze_user @user <minutes>` (admin): `user_prefs.snooze_until`. Router skips DMs to user; group still fires.
  - `/settings` shows current snoozes. `/summary` shows count.

### Error handling (cross-cutting)

- **DB unreachable** → "⚠️ Temporarily unavailable." + `bot_audit(action='error')`.
- **Backend API fail** → `api_client.WACHAPIError` → `@safe_handler` decorator → friendly reply + log.
- **LLM timeout** → 30 s → friendly message.
- **Telegram API error** → global PTB `error_handler` → log + DM to `BOT_ADMIN_IDS[0]`.
- **Stale callback** (e.g., approve on resolved WO) → `answerCallbackQuery(text="Already resolved", show_alert=true)`.

### i18n (deferred, scaffold only)

`ui/messages.py` stub dict keyed by locale. Strings inline this pass. Migration later = codemod, not redesign.

---

## Files Touched

### Modify

- `backend/bot/main.py` — use `handler_registry()` from `handlers/__init__.py`; add bootstrap seeding.
- `backend/bot/config.py` — new env vars.
- `backend/bot/handlers/managers.py` — replace chat-id gates with `@require_role`; use `keyboards.inline_kb_for`; direct-enter ConversationHandlers from callbacks.
- `backend/bot/handlers/engineers.py` — same refactor; fix `cb_edit` dead-end.
- `backend/bot/handlers/technicians.py` — same refactor; rename `/start` → `/go`; fix `cb_done` dead-end.
- `backend/bot/push/notifier.py` — collapse to `emit(event, wo)` dispatcher.
- `backend/tools/action_tools.py` — route via `routing.router` instead of calling `notify_*` directly. Keep 4h AHU cooldown.
- `backend/routes/chat.py` — honour `context.read_only` by filtering mutation tools. Confirm `session_id` support.
- `.env.example` — new vars.
- `docker-compose.yml` — env passthrough (no new services).

### Create

- `backend/bot/identity/{__init__.py,store.py,registration.py,decorators.py}`
- `backend/bot/routing/{__init__.py,router.py,recipients.py,matrix.py,claims.py}`
- `backend/bot/handlers/{__init__.py,common.py,admin.py,ask.py}`
- `backend/bot/ui/{__init__.py,keyboards.py,reply_keyboard.py,menu_button.py,cards.py,pagination.py,messages.py}`
- `backend/bot/agent/{__init__.py,ask.py}`
- `backend/bot/rate_limit.py`
- `backend/tests/bot/**` per Testing section.

### Delete (Phase 2)

- `backend/bot/groups.py` — dead after decorator migration.

---

## Hooks for Business Flow (Colleagues Later)

| Hook | Mechanism | Add-a-feature cost |
|---|---|---|
| New WO status | `WorkOrderStatus` enum + matrix row + card renderer | 3 edits, no new code |
| New route strategy | `routing/matrix.py` dict + optional `Strategy` class | Data or 1 new class |
| New role | `ROLE_HIERARCHY` map + scope registration | Map entry |
| New card template | `CARD_RENDERERS[Event.X]` | 1 function |
| New keyboard | `inline_kb_for` dispatch table | 1 builder |
| Agent modes (B/C/mutations) | `BOT_AGENT_MODE` flag | Flag flip |
| Per-region routing | `bot_users.region` column + `DMByRegion` strategy | Column + strategy |
| Email/SMS recipient | `Recipient(kind='email', ...)` + notifier dispatcher | Notifier switch |
| Quiet hours / tz | `user_prefs` JSON keys | Data only |
| Multi-group per building | new `bot_channels` table + router read | 1 table, 1 edit |
| SLA breach escalation | background worker emits `WO_SLA_BREACH` event | 1 worker, 1 matrix row |

---

## Testing

### Unit tests

- `tests/bot/identity/test_store.py, test_decorators.py`
- `tests/bot/routing/test_router.py, test_claims.py, test_matrix.py`
- `tests/bot/ui/test_keyboards.py, test_pagination.py, test_cards.py`
- `tests/bot/test_rate_limit.py, test_audit.py`

### Handler tests (PTB mocked)

- `test_handlers_common.py` — `/start` in all 4 user states.
- `test_handlers_registration.py` — full flow + race on double-approve.
- `test_handlers_managers.py` — paginated `/pending`, filter chips, approve→assign, dismiss→confirm.
- `test_handlers_engineers.py` — `Edit` callback enters conversation directly (regression).
- `test_handlers_technicians.py` — `/mywork` filters by user_id, `/go` / `/done` flows.
- `test_handlers_admin.py` — promote, deactivate, snooze + confirm, `/activity`.
- `test_handlers_ask.py` — rate-limited, mocked agent, `read_only=true` forwarded.

### Integration

- `test_integration_claim_then_dm.py` — WO_CREATED → group msg → tap → group edited + DM sent + claim row + audit row.
- `test_integration_registration_roundtrip.py` — end-to-end with BotCommands scope refresh.
- `test_integration_snooze.py` — snoozed AHU skips DM fanout.

### Regression guards

- No direct `effective_chat.id ==` in handlers (grep-style lint).
- `notify_technicians` honours `assigned_to` (DM target asserted).

### Coverage targets

- Core (identity, routing, keyboards, pagination): **90%**
- Handlers: **80%**
- Overall bot package: **85%**

Run: `pytest backend/tests/bot/ -v --cov=backend.bot --cov-report=term-missing`.

### Manual smoke script

`scripts/smoke_test_bot.md` — 5-step manual check covering bootstrap, registration, WO lifecycle, `/ask`, `/activity`.

---

## Verification

### Per-phase acceptance

**Phase 1 (Identity):**
- Fresh DB, admin IDs set, bot boots. Admin `/start` shows admin menu.
- Unregistered DM → registration card → submit → manager approves → user DM'd + scopes set.
- `bot_audit` rows written for register + approve.
- `docker-compose up` clean; `pytest backend/tests/bot/identity/` green.

**Phase 2 (Routing + Menus):**
- Trigger fake WO via `POST /api/work-orders` → managers group gets card + buttons.
- First manager taps Approve → group edits to "claimed by @X" → @X DM gets full card.
- Second manager taps → toast "Already claimed".
- Reply keyboard visible in DM, hidden in group.
- `/help` shows role-specific command list.
- `pytest backend/tests/bot/routing/ backend/tests/bot/ui/` green.

**Phase 3 (Polish):**
- `/pending` paginated, filter chips persist across calls.
- Dismiss → confirm card → Yes dismisses + edits, No restores.
- `[🌐 Open in dashboard]` opens frontend at correct AHU.
- `/summary` pinned, `[🔄 Refresh]` edits in place.
- `/activity` shows correct audit trail, filterable.
- Rate-limit fires on 31st command/min.
- `/snooze e0507 10` suppresses DMs for 10 min.

**Phase 4 (`/ask`):**
- Engineer `/ask why did e0507 fail` → typing indicator → answer card within 30s.
- Rate-limit: 6th `/ask` in 5 min gets "⏳" reply.
- `read_only=true` verified by backend log.
- `bot_audit(action='ask')` rows appear in `/activity`.

### Overall smoke

1. Boot clean DB.
2. Admin + 3 users register + approved.
3. Create 5 WOs via API (mix severities).
4. Walk through full lifecycle: create → approve → assign → start → done.
5. Run `/summary`, `/activity`, `/ask`.
6. `/snooze` + verify silence.
7. Deactivate user → verify handler rejection.

All paths should emit structured logs (`bot.register`, `bot.route`, `bot.claim`, `bot.ask`, `bot.error`) queryable by a single `grep`.

---

## Open Questions for Colleagues (Phase 5 input)

Deliberately leaving these for business-flow discussion:

- Exact severity escalation rules (who approves Critical vs. Maintenance)?
- SLA times per severity?
- Assignment algorithm: round-robin? skill-based? manual-only?
- Vendor dispatch lifecycle (new status?)?
- Manager-of-manager approval chain?
- Per-building / per-region routing?
- Quiet hours policy (hard cutoff, escalate if critical?)?

Each of these maps to one of the Hook 1–11 mechanisms above and is a data change, not a rewrite.
