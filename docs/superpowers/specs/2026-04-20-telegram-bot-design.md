# WACH Insight Telegram Bot Design

**Date:** 2026-04-20
**Status:** Draft
**Scope:** Interactive Telegram bot serving 3 separate groups — Managers, Engineers, Technicians

---

## Context

The agentic system (spec: `2026-04-14-agentic-system-design.md`) already plans `send_notification()` to push one-way Telegram alerts. This spec extends that into a fully interactive bot: each group receives push alerts AND can issue commands back. The bot runs as a separate process (`backend/bot/`) and communicates exclusively via WACH's own REST API.

---

## Architecture

### File Structure

```
backend/
└── bot/
    ├── main.py              # Entry point, Application setup, polling loop
    ├── config.py            # Chat IDs, bot token, API base URL
    ├── groups.py            # Maps chat_id → role (managers/engineers/technicians)
    ├── api_client.py        # Thin async wrapper around WACH REST API
    ├── handlers/
    │   ├── managers.py      # Manager commands + inline button callbacks
    │   ├── engineers.py     # Engineer commands + conversation flows
    │   └── technicians.py   # Technician commands + status updates
    └── push/
        └── notifier.py      # Called by send_notification() to push alerts
```

### Config (`bot/config.py`)

```python
MANAGERS_CHAT_ID    = -100xxx
ENGINEERS_CHAT_ID   = -100xxx
TECHNICIANS_CHAT_ID = -100xxx
TELEGRAM_BOT_TOKEN  = "..."
API_BASE_URL        = "http://localhost:8081"  # Railway URL in prod
```

### Group Identity

Every handler checks `update.effective_chat.id` against the 3 known chat IDs. Messages from unknown chats are silently ignored. Wrong command in wrong group: silently ignored — no noise.

Permissions model: **group membership = full group permissions**. No per-user roles within a group.

### Process Isolation

Bot runs as a separate Python process (`python bot/main.py`) using `python-telegram-bot>=21.0` long-polling. It calls WACH's REST API as a client — no direct DB or model imports. A `bot` service is added to `docker-compose.yml`.

### Push Integration

`bot/push/notifier.py` exposes:
- `notify_managers(work_order)` — sends alert with Approve/Dismiss/Push to Engineers buttons
- `notify_engineers(work_order)` — sends review request with Edit/Send Back buttons
- `notify_technicians(work_order, technician_id=None)` — sends assignment (specific or "any")

These are called by the existing `send_notification()` action tool in `backend/tools/action_tools.py`.

---

## Work Order Flow

```
Watchman detects issue
        ↓
  create_work_order()
        ↓
  send_notification() → notifier.notify_managers() → Managers group
        ↓
  [✅ Approve] [❌ Dismiss] [🔍 Push to Engineers]
        ↓                ↓                ↓
   assign tech      dismissed        Engineers group
   (any / pick)                  [📝 Edit] [✅ Send Back]
        ↓                                  ↓
  Technicians group              Managers group again
  (any or named)              [✅ Approve] [❌ Dismiss]
        ↓
  [▶️ Start] [✅ Done + notes]
        ↓
   work order → resolved
```

### Work Order Status Extension

The existing statuses are extended with one new state:

| Status | Meaning |
|---|---|
| `draft` | Created by agent, pushed to managers |
| `pending_engineer_review` | Manager pushed to engineers for fact-check |
| `pending_approval` | Engineer sent back to manager |
| `approved` | Manager approved, assigned to technician(s) |
| `in_progress` | Technician started work |
| `resolved` | Technician marked done |
| `dismissed` | Manager dismissed at any point |

Add `pending_engineer_review` to the status enum in `backend/models/schemas.py` and update transition validation in `update_work_order()`.

### Technician Assignment

When a manager hits Approve, the bot sends a follow-up inline keyboard:
```
[👷 Any Technician]  [👤 Pick Specific]
```
"Pick Specific" → bot replies with known technician names as inline buttons. Technician list stored in `bot/config.py` as a simple dict: `{"Alice": 123456, "Bob": 789012, ...}`.

---

## Commands Per Group

### Managers

| Command | Action |
|---|---|
| `/pending` | List all work orders awaiting approval |
| `/workorder <id>` | Full details of a specific work order |
| `/summary` | Today's building health snapshot (health scores by level) |
| `/help` | List available commands |

**Inline buttons on push alerts:**
`[✅ Approve]` `[❌ Dismiss]` `[🔍 Push to Engineers]`

After Approve:
`[👷 Any Technician]` `[👤 Pick Specific]`

---

### Engineers

| Command | Action |
|---|---|
| `/review <id>` | Fetch work order details + live FAIR scores for that AHU |
| `/edit <id>` | Guided conversation — bot asks new title, then description |
| `/sendback <id>` | Send edited work order back to managers (includes diff of changes) |
| `/query <ahu_id>` | Live AHU health data (calls `/api/health-scores`) |
| `/level <N>` | Overview of all AHUs on a building level |
| `/help` | List available commands |

**Inline buttons on review alerts:**
`[📝 Edit]` `[✅ Send Back to Manager]`

---

### Technicians

| Command | Action |
|---|---|
| `/mywork` | List work orders assigned to "any" or specifically to them |
| `/start <id>` | Mark work order `in_progress` |
| `/done <id>` | Mark `resolved` — bot prompts for short completion note |
| `/status <ahu_id>` | Current health score + last sensor reading for a device |
| `/help` | List available commands |

**Inline buttons on assignment alerts:**
`[▶️ Start]` `[✅ Done]`

---

## Push Alert Message Formats

### Manager Alert
```
🚨 CRITICAL — Level 4 · e0402

Title: Chiller coil overtemperature
FAIR: F:42 A:38 I:61 R:55 · Composite: 49

Created by: Watchman · 20 Apr 2026 09:14

[✅ Approve]  [❌ Dismiss]  [🔍 Push to Engineers]
```

### Engineer Review
```
🔍 Review Requested — Work Order #12

Title: Chiller coil overtemperature
Description: FAIR composite dropped below threshold over 3h window...
AHU: e0402 · Level 4
FAIR snapshot: F:42 A:38 I:61 R:55

[📝 Edit]  [✅ Send Back to Manager]
```

### Technician Assignment
```
🔧 New Work Order Assigned — #12

Title: Chiller coil overtemperature
AHU: e0402 · Level 4
Approved by: Manager

[▶️ Start]  [✅ Done]
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| WACH API unreachable | "⚠️ WACH backend unavailable. Try again shortly." |
| Unknown command in wrong group | Silent ignore |
| `/edit` conversation abandoned | 5 min timeout → "Edit cancelled." |
| Duplicate alert for same AHU | Blocked by existing 4h cooldown in `send_notification()` |
| Invalid AHU ID in `/status` or `/query` | "❌ Unknown device ID. Use format e0101." |
| Work order not found | "❌ Work order #N not found." |

---

## Dependencies

- `python-telegram-bot>=21.0` — already in `backend/requirements.txt`
- No new Python packages required
- New env vars: `TELEGRAM_BOT_TOKEN`, `MANAGERS_CHAT_ID`, `ENGINEERS_CHAT_ID`, `TECHNICIANS_CHAT_ID`
- New work order status: `pending_engineer_review` — requires schema + validation update

---

## Out of Scope

- Per-user permissions within a group (group membership = full access)
- PDF report generation via bot
- Voice/media message handling
- Web dashboard SSO via Telegram
