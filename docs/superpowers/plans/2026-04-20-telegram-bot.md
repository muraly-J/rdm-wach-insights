# Telegram Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Telegram bot serving Managers, Engineers, and Technicians in 3 separate group chats — push alerts with inline keyboards + pull commands, all talking to the WACH REST API.

**Architecture:** Separate bot process (`backend/bot/`) polling Telegram via `python-telegram-bot>=21.0`. Bot is a pure API client — reads/writes work orders via `http://localhost:8081/api/`. `notifier.py` handles rich message formatting with inline keyboards and is shared between the bot process and `action_tools.py`.

**Tech Stack:** `python-telegram-bot>=21.0`, `httpx>=0.27`, FastAPI (existing), DuckDB (existing), `pytest-asyncio`

---

## File Map

| Action | File |
|---|---|
| Modify | `backend/core/agentdb.py` — add `assigned_to` column, `pending_engineer_review` transitions |
| Modify | `backend/routes/work_orders.py` — add 4 new routes |
| Modify | `backend/config.py` — add group chat ID + technician dict fields |
| Modify | `backend/tools/action_tools.py` — route to `notifier.py` for rich alerts |
| Create | `backend/bot/__init__.py` |
| Create | `backend/bot/config.py` — env var reads for bot |
| Create | `backend/bot/groups.py` — chat_id → role mapping |
| Create | `backend/bot/api_client.py` — async httpx wrapper |
| Create | `backend/bot/push/__init__.py` |
| Create | `backend/bot/push/notifier.py` — formatted messages + inline keyboards |
| Create | `backend/bot/handlers/__init__.py` |
| Create | `backend/bot/handlers/managers.py` — manager commands + callbacks |
| Create | `backend/bot/handlers/engineers.py` — engineer commands + ConversationHandler |
| Create | `backend/bot/handlers/technicians.py` — technician commands + callbacks |
| Create | `backend/bot/main.py` — Application setup, handler registration, polling |
| Modify | `docker-compose.yml` — add `bot` service |
| Modify | `.env.example` — add new env vars |
| Modify | `backend/tests/test_agentdb.py` — new transition tests |
| Modify | `backend/tests/test_work_orders_api.py` — new route tests |
| Create | `backend/tests/bot/__init__.py` |
| Create | `backend/tests/bot/test_groups.py` |
| Create | `backend/tests/bot/test_api_client.py` |
| Create | `backend/tests/bot/test_notifier.py` |
| Create | `backend/tests/bot/test_handlers_managers.py` |
| Create | `backend/tests/bot/test_handlers_engineers.py` |
| Create | `backend/tests/bot/test_handlers_technicians.py` |

---

## Task 1: Extend AgentDB — assigned_to + pending_engineer_review

**Files:**
- Modify: `backend/core/agentdb.py:29-36` (transitions), `:41-83` (schema SQL), `:158-209` (update_work_order)
- Modify: `backend/tests/test_agentdb.py`

- [ ] **Step 1: Write failing tests for new transitions and assigned_to**

Add to `backend/tests/test_agentdb.py`:

```python
def test_push_to_engineers_transition(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    result = db.update_work_order(wo_id, status="pending_engineer_review")
    assert result is True
    assert db.get_work_order(wo_id)["status"] == "pending_engineer_review"


def test_engineer_sendback_transition(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="pending_engineer_review")
    result = db.update_work_order(wo_id, status="pending_approval")
    assert result is True
    assert db.get_work_order(wo_id)["status"] == "pending_approval"


def test_engineer_review_to_approved(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="pending_engineer_review")
    db.update_work_order(wo_id, status="pending_approval")
    result = db.update_work_order(wo_id, status="approved", approved_by="manager")
    assert result is True


def test_assigned_to_stored_and_retrieved(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="approved", assigned_to="any")
    wo = db.get_work_order(wo_id)
    assert wo["assigned_to"] == "any"


def test_assigned_to_specific_technician(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="approved", assigned_to="123456789")
    wo = db.get_work_order(wo_id)
    assert wo["assigned_to"] == "123456789"


def test_list_work_orders_by_assigned_to(db):
    wo1 = db.create_work_order(ahu_id="e0101", level=1, title="T1", severity="warning")
    wo2 = db.create_work_order(ahu_id="e0102", level=1, title="T2", severity="warning")
    db.update_work_order(wo1, status="approved", assigned_to="any")
    db.update_work_order(wo2, status="approved", assigned_to="999")
    results = db.list_work_orders(assigned_to="any")
    assert len(results) == 1
    assert results[0]["id"] == wo1


def test_invalid_transition_from_resolved(db):
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="T", severity="warning")
    db.update_work_order(wo_id, status="approved")
    db.update_work_order(wo_id, status="in_progress")
    db.update_work_order(wo_id, status="resolved")
    result = db.update_work_order(wo_id, status="in_progress")
    assert result is False
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/test_agentdb.py::test_push_to_engineers_transition tests/test_agentdb.py::test_assigned_to_stored_and_retrieved tests/test_agentdb.py::test_list_work_orders_by_assigned_to -v
```

Expected: `FAILED` — `pending_engineer_review` not in transitions, `assigned_to` column missing.

- [ ] **Step 3: Update _VALID_TRANSITIONS in agentdb.py:29-36**

Replace:
```python
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_approval", "approved", "dismissed"},
    "pending_approval": {"approved", "dismissed"},
    "approved": {"in_progress", "resolved", "dismissed"},
    "in_progress": {"resolved"},
    "resolved": set(),
    "dismissed": set(),
}
```

With:
```python
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_engineer_review", "pending_approval", "approved", "dismissed"},
    "pending_engineer_review": {"pending_approval", "dismissed"},
    "pending_approval": {"approved", "dismissed"},
    "approved": {"in_progress", "resolved", "dismissed"},
    "in_progress": {"resolved"},
    "resolved": set(),
    "dismissed": set(),
}
```

- [ ] **Step 4: Add assigned_to column to schema SQL in agentdb.py**

In `_SCHEMA_SQL`, add `assigned_to` to the `work_orders` table definition. Locate the CREATE TABLE block (~line 41) and add after the `approved_by` line:

```sql
CREATE TABLE IF NOT EXISTS work_orders (
    id              INTEGER PRIMARY KEY,
    ahu_id          VARCHAR NOT NULL,
    level           INTEGER NOT NULL,
    title           VARCHAR NOT NULL,
    description     VARCHAR,
    severity        VARCHAR NOT NULL,
    status          VARCHAR NOT NULL DEFAULT 'draft',
    created_by      VARCHAR NOT NULL DEFAULT 'agent',
    created_at      TIMESTAMPTZ NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL,
    resolved_at     TIMESTAMPTZ,
    trigger_source  VARCHAR NOT NULL DEFAULT 'chat',
    fair_snapshot   JSON,
    notified_via    VARCHAR NOT NULL DEFAULT 'none',
    approved_by     VARCHAR,
    assigned_to     VARCHAR
);
```

Then add a migration guard in `_init_tables()` — after `conn.execute(_SCHEMA_SQL)`, add:

```python
try:
    conn.execute("ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS assigned_to VARCHAR")
except Exception:
    pass  # column already exists or DB doesn't support IF NOT EXISTS
```

- [ ] **Step 5: Update update_work_order() to accept assigned_to**

In `agentdb.py`, find `update_work_order()` (~line 158). Add `assigned_to: str | None = None` to the signature and handle it in the updates block:

```python
def update_work_order(
    self,
    wo_id: int,
    status: str,
    notes: str | None = None,
    approved_by: str | None = None,
    notified_via: str | None = None,
    assigned_to: str | None = None,
) -> bool:
    wo = self.get_work_order(wo_id)
    if not wo:
        logger.warning(f"update_work_order: id={wo_id} not found")
        return False

    current = wo["status"]
    allowed = _VALID_TRANSITIONS.get(current, set())
    if status not in allowed:
        logger.warning(
            f"update_work_order: invalid transition {current!r} → {status!r} for id={wo_id}"
        )
        return False

    now = self._now()
    resolved_at = now if status == "resolved" else None

    updates = ["status = ?", "updated_at = ?"]
    params: list[Any] = [status, now]

    if notes:
        new_desc = (wo.get("description") or "") + f"\n[{now}] {notes}"
        updates.append("description = ?")
        params.append(new_desc)
    if approved_by:
        updates.append("approved_by = ?")
        params.append(approved_by)
    if resolved_at:
        updates.append("resolved_at = ?")
        params.append(resolved_at)
    if notified_via:
        updates.append("notified_via = ?")
        params.append(notified_via)
    if assigned_to is not None:
        updates.append("assigned_to = ?")
        params.append(assigned_to)

    params.append(wo_id)
    with self._connect() as conn:
        conn.execute(
            f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ?",
            params,
        )
    return True
```

- [ ] **Step 6: Update list_work_orders() to support assigned_to filter**

Find `list_work_orders()` (~line 145). Update to accept `assigned_to` parameter:

```python
def list_work_orders(
    self,
    status: str | None = None,
    assigned_to: str | None = None,
) -> list[dict]:
    with self._connect() as conn:
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if assigned_to is not None:
            conditions.append("assigned_to = ?")
            params.append(assigned_to)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        df = conn.execute(
            f"SELECT * FROM work_orders {where} ORDER BY created_at DESC",
            params,
        ).fetchdf()
    return df.to_dict(orient="records")
```

- [ ] **Step 7: Run tests to confirm they pass**

```bash
cd backend && python -m pytest tests/test_agentdb.py -v
```

Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
cd backend && git add core/agentdb.py tests/test_agentdb.py
git commit -m "feat: add assigned_to column and pending_engineer_review status transition"
```

---

## Task 2: New Work Order API Routes

**Files:**
- Modify: `backend/routes/work_orders.py`
- Modify: `backend/tests/test_work_orders_api.py`

- [ ] **Step 1: Write failing tests for new routes**

Add to `backend/tests/test_work_orders_api.py`:

```python
def test_push_to_engineers(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/push-to-engineers")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_engineer_review"


def test_start_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="approved", assigned_to="any")
    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_resolve_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="approved")
    db.update_work_order(wo_id, status="in_progress")
    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/resolve", json={"notes": "Fixed the fan."})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_assign_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="approved")
    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/assign", json={"assigned_to": "123456789"})
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] == "123456789"


def test_list_work_orders_filter_assigned_to(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo1 = db.create_work_order(ahu_id="e0101", level=1, title="T1", severity="warning")
    wo2 = db.create_work_order(ahu_id="e0102", level=1, title="T2", severity="warning")
    db.update_work_order(wo1, status="approved", assigned_to="any")
    db.update_work_order(wo2, status="approved", assigned_to="999")
    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.get("/api/work-orders?assigned_to=any")
    assert resp.status_code == 200
    assert len(resp.json()["work_orders"]) == 1
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/test_work_orders_api.py::test_push_to_engineers tests/test_work_orders_api.py::test_start_work_order -v
```

Expected: `FAILED` — routes don't exist yet.

- [ ] **Step 3: Add new routes to routes/work_orders.py**

Add after the existing `dismiss_work_order` route (after line 89):

```python
class WorkOrderAssign(BaseModel):
    assigned_to: str  # "any" or a Telegram user_id string


class WorkOrderResolve(BaseModel):
    notes: str | None = None


@router.post("/work-orders/{wo_id}/push-to-engineers")
async def push_work_order_to_engineers(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="pending_engineer_review")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot push work order in status '{wo['status']}' to engineers",
        )
    logger.info(f"work_order {wo_id} pushed to engineers")
    return {"id": wo_id, "status": "pending_engineer_review"}


@router.post("/work-orders/{wo_id}/start")
async def start_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="in_progress")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start work order in status '{wo['status']}'",
        )
    logger.info(f"work_order {wo_id} started")
    return {"id": wo_id, "status": "in_progress"}


@router.post("/work-orders/{wo_id}/resolve")
async def resolve_work_order(wo_id: int, body: WorkOrderResolve) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="resolved", notes=body.notes)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resolve work order in status '{wo['status']}'",
        )
    logger.info(f"work_order {wo_id} resolved")
    return {"id": wo_id, "status": "resolved"}


@router.post("/work-orders/{wo_id}/assign")
async def assign_work_order(wo_id: int, body: WorkOrderAssign) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    if wo["status"] not in ("approved", "in_progress"):
        raise HTTPException(
            status_code=400,
            detail=f"Can only assign approved or in_progress work orders, got '{wo['status']}'",
        )
    import duckdb
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with duckdb.connect(db._path) as conn:
        conn.execute(
            "UPDATE work_orders SET assigned_to = ?, updated_at = ? WHERE id = ?",
            [body.assigned_to, now, wo_id],
        )
    logger.info(f"work_order {wo_id} assigned to {body.assigned_to}")
    return {"id": wo_id, "assigned_to": body.assigned_to}
```

Also update `list_work_orders` route to support `assigned_to` query param:

```python
@router.get("/work-orders")
async def list_work_orders(
    status: str | None = None,
    assigned_to: str | None = None,
) -> dict:
    db = _get_db()
    work_orders = db.list_work_orders(status=status, assigned_to=assigned_to)
    clean = []
    for wo in work_orders:
        clean.append({k: (str(v) if hasattr(v, "isoformat") else v) for k, v in wo.items()})
    return {"work_orders": clean, "count": len(clean)}
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_work_orders_api.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/work_orders.py backend/tests/test_work_orders_api.py
git commit -m "feat: add push-to-engineers, start, resolve, assign work order routes"
```

---

## Task 3: Config + action_tools Updates

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/tools/action_tools.py`
- Modify: `.env.example`

- [ ] **Step 1: Add new fields to config.py**

In `backend/config.py`, in the `# ── Telegram notifications` section (~line 88), add after the existing telegram fields:

```python
    # Group chat IDs (bot interactive mode)
    managers_chat_id: str = ""
    engineers_chat_id: str = ""
    technicians_chat_id: str = ""
    # JSON dict of technician names → telegram user IDs, e.g. '{"Alice": "123456"}'
    technicians_json: str = "{}"
```

- [ ] **Step 2: Update action_tools.py to route rich notifications**

In `backend/tools/action_tools.py`, update `handle_send_notification` to call `notifier.py` when group chat IDs are configured and a `work_order_id` is provided. Find the "Send via Telegram Bot API" block (~line 147) and replace the entire send block with:

```python
    # Route to group notifier if group chat IDs are configured and work order provided
    if work_order_id:
        from config import settings as _settings
        has_group = (
            (recipient == "manager" and _settings.managers_chat_id) or
            (recipient == "engineers" and _settings.engineers_chat_id) or
            (recipient == "technician" and _settings.technicians_chat_id)
        )
        if has_group:
            try:
                from bot.push.notifier import notify_group
                wo = db.get_work_order(work_order_id)
                if wo:
                    clean_wo = {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in wo.items()}
                    await notify_group(recipient, clean_wo, token)
                    if ahu_id:
                        from datetime import datetime, timedelta, timezone
                        cooldown_hours = settings.watchman_cooldown_critical_hours
                        expires = (datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)).isoformat()
                        db.set_agent_state(
                            f"last_alert:{ahu_id}",
                            {"notified_at": datetime.now(timezone.utc).isoformat(), "recipient": recipient},
                            expires_at=expires,
                        )
                    return {"status": "sent", "recipient": recipient, "channel": "telegram"}
            except ImportError:
                pass  # bot module not available, fall through to plain text

    # Plain text fallback
    try:
        from telegram import Bot
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logger.info(f"send_notification: sent to {recipient} ({chat_id})")
    except Exception as e:
        logger.error(f"send_notification: Telegram error — {e}")
        return {"status": "error", "reason": str(e)}
```

- [ ] **Step 3: Update .env.example**

Add to `.env.example`:

```bash
# Telegram Bot (interactive group mode)
TELEGRAM_BOT_TOKEN=your-bot-token-here
MANAGERS_CHAT_ID=-1001234567890
ENGINEERS_CHAT_ID=-1001234567891
TECHNICIANS_CHAT_ID=-1001234567892
# JSON dict: technician name → telegram user ID
TECHNICIANS_JSON={"Alice": "123456789", "Bob": "987654321"}
```

- [ ] **Step 4: Run existing action_tools tests to confirm no regression**

```bash
cd backend && python -m pytest tests/test_action_tools.py -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add backend/config.py backend/tools/action_tools.py .env.example
git commit -m "feat: add group chat ID config fields and route rich notifications in action_tools"
```

---

## Task 4: Bot Package Scaffold

**Files:**
- Create: `backend/bot/__init__.py`
- Create: `backend/bot/config.py`
- Create: `backend/bot/groups.py`
- Create: `backend/bot/api_client.py`
- Create: `backend/tests/bot/__init__.py`
- Create: `backend/tests/bot/test_groups.py`
- Create: `backend/tests/bot/test_api_client.py`

- [ ] **Step 1: Write failing tests for groups.py**

Create `backend/tests/bot/__init__.py` (empty):
```python
```

Create `backend/tests/bot/test_groups.py`:

```python
"""Tests for bot group identity resolution."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_managers_group_recognized(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    # Re-import to pick up monkeypatched env
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-1001111) == "managers"


def test_engineers_group_recognized(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-1002222) == "engineers"


def test_technicians_group_recognized(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-1003333) == "technicians"


def test_unknown_chat_returns_none(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-9999999) is None
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/bot/test_groups.py -v
```

Expected: `FAILED` — `bot.groups` doesn't exist.

- [ ] **Step 3: Create bot/__init__.py**

Create `backend/bot/__init__.py`:
```python
```

- [ ] **Step 4: Create bot/config.py**

Create `backend/bot/config.py`:

```python
from __future__ import annotations

"""
bot/config.py
─────────────
Standalone env var config for the Telegram bot process.
Does NOT import from backend config.py — bot is a separate process.
"""

import json
import os

BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MANAGERS_CHAT_ID: int = int(os.environ.get("MANAGERS_CHAT_ID", "0"))
ENGINEERS_CHAT_ID: int = int(os.environ.get("ENGINEERS_CHAT_ID", "0"))
TECHNICIANS_CHAT_ID: int = int(os.environ.get("TECHNICIANS_CHAT_ID", "0"))
API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://localhost:8081")

# Dict of technician display name → telegram user_id (as string)
# env: TECHNICIANS_JSON='{"Alice": "123456789", "Bob": "987654321"}'
TECHNICIANS: dict[str, str] = json.loads(os.environ.get("TECHNICIANS_JSON", "{}"))
```

- [ ] **Step 5: Create bot/groups.py**

Create `backend/bot/groups.py`:

```python
from __future__ import annotations

"""
bot/groups.py
─────────────
Maps Telegram chat_id → group role.
Reading config at module load so tests can reload after monkeypatching env.
"""

import os

_MANAGERS_CHAT_ID: int = int(os.environ.get("MANAGERS_CHAT_ID", "0"))
_ENGINEERS_CHAT_ID: int = int(os.environ.get("ENGINEERS_CHAT_ID", "0"))
_TECHNICIANS_CHAT_ID: int = int(os.environ.get("TECHNICIANS_CHAT_ID", "0"))

_CHAT_ID_MAP: dict[int, str] = {}
if _MANAGERS_CHAT_ID:
    _CHAT_ID_MAP[_MANAGERS_CHAT_ID] = "managers"
if _ENGINEERS_CHAT_ID:
    _CHAT_ID_MAP[_ENGINEERS_CHAT_ID] = "engineers"
if _TECHNICIANS_CHAT_ID:
    _CHAT_ID_MAP[_TECHNICIANS_CHAT_ID] = "technicians"


def get_group(chat_id: int) -> str | None:
    """Return the group role for a chat_id, or None if unknown."""
    return _CHAT_ID_MAP.get(chat_id)
```

- [ ] **Step 6: Create bot/api_client.py**

Create `backend/bot/api_client.py`:

```python
from __future__ import annotations

"""
bot/api_client.py
─────────────────
Async httpx wrapper around the WACH REST API.
All methods raise WACHAPIError on non-2xx responses.
"""

from typing import Any

import httpx

from bot.config import API_BASE_URL


class WACHAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"WACH API {status_code}: {detail}")


async def _get(path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.get(path, params=params)
    if not resp.is_success:
        raise WACHAPIError(resp.status_code, resp.text[:200])
    return resp.json()


async def _post(path: str, json: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.post(path, json=json or {})
    if not resp.is_success:
        raise WACHAPIError(resp.status_code, resp.text[:200])
    return resp.json()


async def _patch(path: str, json: dict) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.patch(path, json=json)
    if not resp.is_success:
        raise WACHAPIError(resp.status_code, resp.text[:200])
    return resp.json()


# ── Work order helpers ─────────────────────────────────────────────────────────

async def list_work_orders(
    status: str | None = None,
    assigned_to: str | None = None,
) -> list[dict]:
    params: dict = {}
    if status:
        params["status"] = status
    if assigned_to is not None:
        params["assigned_to"] = assigned_to
    data = await _get("/api/work-orders", params=params)
    return data["work_orders"]


async def get_work_order(wo_id: int) -> dict:
    return await _get(f"/api/work-orders/{wo_id}")


async def approve_work_order(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/approve")


async def dismiss_work_order(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/dismiss")


async def push_to_engineers(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/push-to-engineers")


async def start_work_order(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/start")


async def resolve_work_order(wo_id: int, notes: str | None = None) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/resolve", json={"notes": notes})


async def assign_work_order(wo_id: int, assigned_to: str) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/assign", json={"assigned_to": assigned_to})


async def edit_work_order(wo_id: int, title: str | None = None, description: str | None = None) -> dict:
    payload: dict = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    return await _patch(f"/api/work-orders/{wo_id}", json=payload)


async def get_health_scores() -> dict:
    return await _get("/api/health-scores")


async def get_ahu_status(ahu_id: str) -> dict:
    return await _get(f"/api/measurements/{ahu_id}")
```

- [ ] **Step 7: Write api_client tests**

Create `backend/tests/bot/test_api_client.py`:

```python
"""Tests for bot API client error handling."""
import os
import sys

import pytest
import httpx
import respx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

os.environ.setdefault("API_BASE_URL", "http://localhost:8081")


@respx.mock
@pytest.mark.asyncio
async def test_list_work_orders_success():
    respx.get("http://localhost:8081/api/work-orders").mock(
        return_value=httpx.Response(200, json={"work_orders": [{"id": 1}], "count": 1})
    )
    from bot.api_client import list_work_orders
    result = await list_work_orders()
    assert result == [{"id": 1}]


@respx.mock
@pytest.mark.asyncio
async def test_list_work_orders_api_error():
    respx.get("http://localhost:8081/api/work-orders").mock(
        return_value=httpx.Response(503, text="Service unavailable")
    )
    from bot.api_client import list_work_orders, WACHAPIError
    with pytest.raises(WACHAPIError) as exc:
        await list_work_orders()
    assert exc.value.status_code == 503


@respx.mock
@pytest.mark.asyncio
async def test_approve_work_order():
    respx.post("http://localhost:8081/api/work-orders/5/approve").mock(
        return_value=httpx.Response(200, json={"id": 5, "status": "approved"})
    )
    from bot.api_client import approve_work_order
    result = await approve_work_order(5)
    assert result["status"] == "approved"
```

Note: `respx` is a mock library for `httpx`. Add it to `requirements-dev.txt`:
```
respx>=0.21.0
```

- [ ] **Step 8: Install respx and run tests**

```bash
cd backend && pip install respx
python -m pytest tests/bot/test_groups.py tests/bot/test_api_client.py -v
```

Expected: All pass.

- [ ] **Step 9: Commit**

```bash
git add backend/bot/__init__.py backend/bot/config.py backend/bot/groups.py backend/bot/api_client.py backend/tests/bot/__init__.py backend/tests/bot/test_groups.py backend/tests/bot/test_api_client.py backend/requirements-dev.txt
git commit -m "feat: add bot package scaffold — config, groups, api_client"
```

---

## Task 5: Push Notifier

**Files:**
- Create: `backend/bot/push/__init__.py`
- Create: `backend/bot/push/notifier.py`
- Create: `backend/tests/bot/test_notifier.py`

- [ ] **Step 1: Write failing tests for notifier message formatting**

Create `backend/tests/bot/test_notifier.py`:

```python
"""Tests for push notifier message formatting."""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

os.environ.setdefault("MANAGERS_CHAT_ID", "-1001111")
os.environ.setdefault("ENGINEERS_CHAT_ID", "-1002222")
os.environ.setdefault("TECHNICIANS_CHAT_ID", "-1003333")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")


SAMPLE_WO = {
    "id": 12,
    "ahu_id": "e0402",
    "level": 4,
    "title": "Chiller coil overtemperature",
    "description": "FAIR composite dropped below threshold",
    "severity": "Critical",
    "status": "draft",
    "fair_snapshot": '{"F": 42, "A": 38, "I": 61, "R": 55, "composite": 49}',
    "created_at": "2026-04-20T09:14:00+00:00",
}


def test_format_manager_alert_contains_title():
    from bot.push.notifier import _format_manager_alert
    text = _format_manager_alert(SAMPLE_WO)
    assert "Chiller coil overtemperature" in text
    assert "e0402" in text
    assert "Level 4" in text


def test_format_manager_alert_contains_fair():
    from bot.push.notifier import _format_manager_alert
    text = _format_manager_alert(SAMPLE_WO)
    assert "F:42" in text or "42" in text


def test_format_engineer_review_contains_work_order_id():
    from bot.push.notifier import _format_engineer_review
    text = _format_engineer_review(SAMPLE_WO)
    assert "#12" in text
    assert "e0402" in text


def test_format_technician_assignment_contains_ahu():
    from bot.push.notifier import _format_technician_assignment
    text = _format_technician_assignment(SAMPLE_WO)
    assert "e0402" in text
    assert "#12" in text


@pytest.mark.asyncio
async def test_notify_managers_calls_send_message():
    with patch("bot.push.notifier.Bot") as MockBot:
        mock_instance = AsyncMock()
        MockBot.return_value = mock_instance
        from bot.push import notifier
        import importlib
        importlib.reload(notifier)
        from bot.push.notifier import notify_managers
        await notify_managers(SAMPLE_WO)
        mock_instance.send_message.assert_called_once()
        call_kwargs = mock_instance.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == -1001111


@pytest.mark.asyncio
async def test_notify_group_routes_manager():
    with patch("bot.push.notifier.notify_managers", new_callable=AsyncMock) as mock_nm:
        from bot.push.notifier import notify_group
        await notify_group("manager", SAMPLE_WO, "test-token")
        mock_nm.assert_called_once_with(SAMPLE_WO)
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/bot/test_notifier.py -v
```

Expected: `FAILED` — `bot.push.notifier` doesn't exist.

- [ ] **Step 3: Create bot/push/__init__.py**

Create `backend/bot/push/__init__.py`:
```python
```

- [ ] **Step 4: Create bot/push/notifier.py**

Create `backend/bot/push/notifier.py`:

```python
from __future__ import annotations

"""
bot/push/notifier.py
─────────────────────
Formats and sends rich Telegram alerts with inline keyboards.
Called by action_tools.handle_send_notification() and directly by bot handlers.

No backend model imports — only telegram lib and os.environ.
"""

import json
import os
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

_MANAGERS_CHAT_ID: int = int(os.environ.get("MANAGERS_CHAT_ID", "0"))
_ENGINEERS_CHAT_ID: int = int(os.environ.get("ENGINEERS_CHAT_ID", "0"))
_TECHNICIANS_CHAT_ID: int = int(os.environ.get("TECHNICIANS_CHAT_ID", "0"))
_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")


# ── Message formatters ─────────────────────────────────────────────────────────

def _parse_fair(fair_snapshot: str | dict | None) -> str:
    """Return 'F:42 A:38 I:61 R:55 · Composite: 49' or empty string."""
    if not fair_snapshot:
        return ""
    try:
        data = json.loads(fair_snapshot) if isinstance(fair_snapshot, str) else fair_snapshot
        f = int(data.get("F", data.get("f", "?")))
        a = int(data.get("A", data.get("a", "?")))
        i = int(data.get("I", data.get("i", "?")))
        r = int(data.get("R", data.get("r", "?")))
        c = int(data.get("composite", "?"))
        return f"F:{f} A:{a} I:{i} R:{r} · Composite: {c}"
    except Exception:
        return ""


def _format_manager_alert(wo: dict[str, Any]) -> str:
    severity_icon = "🚨" if str(wo.get("severity", "")).lower() == "critical" else "⚠️"
    fair_str = _parse_fair(wo.get("fair_snapshot"))
    created = str(wo.get("created_at", ""))[:16].replace("T", " ")
    lines = [
        f"{severity_icon} {wo.get('severity', 'ALERT').upper()} — Level {wo.get('level')} · {wo.get('ahu_id')}",
        "",
        f"Title: {wo.get('title')}",
    ]
    if fair_str:
        lines.append(f"FAIR: {fair_str}")
    lines += ["", f"Created by: Agent · {created}"]
    return "\n".join(lines)


def _format_engineer_review(wo: dict[str, Any]) -> str:
    fair_str = _parse_fair(wo.get("fair_snapshot"))
    lines = [
        f"🔍 Review Requested — Work Order #{wo.get('id')}",
        "",
        f"Title: {wo.get('title')}",
        f"Description: {wo.get('description') or 'No description'}",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
    ]
    if fair_str:
        lines.append(f"FAIR snapshot: {fair_str}")
    return "\n".join(lines)


def _format_technician_assignment(wo: dict[str, Any]) -> str:
    lines = [
        f"🔧 New Work Order Assigned — #{wo.get('id')}",
        "",
        f"Title: {wo.get('title')}",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
        "Approved by: Manager",
    ]
    return "\n".join(lines)


# ── Inline keyboards ───────────────────────────────────────────────────────────

def _manager_alert_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{wo_id}"),
            InlineKeyboardButton("❌ Dismiss", callback_data=f"dismiss:{wo_id}"),
            InlineKeyboardButton("🔍 Push to Engineers", callback_data=f"push_engineers:{wo_id}"),
        ]
    ])


def _assignment_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👷 Any Technician", callback_data=f"assign_any:{wo_id}"),
            InlineKeyboardButton("👤 Pick Specific", callback_data=f"assign_pick:{wo_id}"),
        ]
    ])


def _engineer_review_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Edit", callback_data=f"edit:{wo_id}"),
            InlineKeyboardButton("✅ Send Back to Manager", callback_data=f"sendback:{wo_id}"),
        ]
    ])


def _technician_assignment_keyboard(wo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Start", callback_data=f"start:{wo_id}"),
            InlineKeyboardButton("✅ Done", callback_data=f"done:{wo_id}"),
        ]
    ])


# ── Public send functions ──────────────────────────────────────────────────────

async def notify_managers(wo: dict[str, Any], token: str | None = None) -> None:
    """Send work order alert to managers group with approve/dismiss/engineers buttons."""
    if not _MANAGERS_CHAT_ID:
        return
    bot = Bot(token=token or _BOT_TOKEN)
    await bot.send_message(
        chat_id=_MANAGERS_CHAT_ID,
        text=_format_manager_alert(wo),
        reply_markup=_manager_alert_keyboard(wo["id"]),
    )


async def notify_engineers(wo: dict[str, Any], token: str | None = None) -> None:
    """Send review request to engineers group with edit/sendback buttons."""
    if not _ENGINEERS_CHAT_ID:
        return
    bot = Bot(token=token or _BOT_TOKEN)
    await bot.send_message(
        chat_id=_ENGINEERS_CHAT_ID,
        text=_format_engineer_review(wo),
        reply_markup=_engineer_review_keyboard(wo["id"]),
    )


async def notify_technicians(
    wo: dict[str, Any],
    token: str | None = None,
    assigned_to: str | None = None,
) -> None:
    """Send assignment alert to technicians group with start/done buttons."""
    if not _TECHNICIANS_CHAT_ID:
        return
    bot = Bot(token=token or _BOT_TOKEN)
    await bot.send_message(
        chat_id=_TECHNICIANS_CHAT_ID,
        text=_format_technician_assignment(wo),
        reply_markup=_technician_assignment_keyboard(wo["id"]),
    )


async def notify_group(
    recipient: str,
    wo: dict[str, Any],
    token: str,
) -> None:
    """Route a group notification by recipient name."""
    if recipient == "manager":
        await notify_managers(wo, token=token)
    elif recipient == "engineers":
        await notify_engineers(wo, token=token)
    elif recipient == "technician":
        await notify_technicians(wo, token=token)
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/bot/test_notifier.py -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add backend/bot/push/__init__.py backend/bot/push/notifier.py backend/tests/bot/test_notifier.py
git commit -m "feat: add push notifier with formatted messages and inline keyboards"
```

---

## Task 6: Manager Handlers

**Files:**
- Create: `backend/bot/handlers/__init__.py`
- Create: `backend/bot/handlers/managers.py`
- Create: `backend/tests/bot/test_handlers_managers.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/bot/test_handlers_managers.py`:

```python
"""Tests for manager handler helper functions."""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def _make_update(chat_id: int, text: str = "", user_id: int = 1) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_context() -> MagicMock:
    ctx = MagicMock()
    ctx.args = []
    return ctx


def test_format_pending_list_empty():
    from bot.handlers.managers import _format_pending_list
    text = _format_pending_list([])
    assert "No pending" in text.lower() or text.strip() != ""


def test_format_pending_list_with_items():
    from bot.handlers.managers import _format_pending_list
    orders = [
        {"id": 1, "ahu_id": "e0402", "level": 4, "title": "Fan fault", "severity": "Critical"},
        {"id": 2, "ahu_id": "e0101", "level": 1, "title": "Low airflow", "severity": "warning"},
    ]
    text = _format_pending_list(orders)
    assert "#1" in text
    assert "e0402" in text
    assert "#2" in text


def test_format_work_order_detail():
    from bot.handlers.managers import _format_work_order_detail
    wo = {
        "id": 5, "ahu_id": "e0507", "level": 5, "title": "Phase imbalance",
        "description": "Current >10%", "severity": "warning", "status": "draft",
        "fair_snapshot": None, "created_at": "2026-04-20T10:00:00+00:00",
    }
    text = _format_work_order_detail(wo)
    assert "#5" in text
    assert "e0507" in text
    assert "Phase imbalance" in text
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/bot/test_handlers_managers.py -v
```

Expected: `FAILED` — `bot.handlers.managers` doesn't exist.

- [ ] **Step 3: Create bot/handlers/__init__.py**

Create `backend/bot/handlers/__init__.py`:
```python
```

- [ ] **Step 4: Create bot/handlers/managers.py**

Create `backend/bot/handlers/managers.py`:

```python
from __future__ import annotations

"""
bot/handlers/managers.py
─────────────────────────
Telegram handlers for the managers group.

Commands:
  /pending   — list work orders awaiting approval
  /workorder <id> — details of a specific work order
  /summary   — building health snapshot
  /help      — available commands

Inline callbacks:
  approve:{id}        — approve work order
  dismiss:{id}        — dismiss work order
  push_engineers:{id} — push to engineers
  assign_any:{id}     — assign to any technician
  assign_pick:{id}    — show specific technician picker
  assign_tech:{id}:{user_id} — assign to specific technician
"""

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from bot import api_client
from bot.config import MANAGERS_CHAT_ID, TECHNICIANS
from bot.groups import get_group
from bot.push.notifier import notify_technicians

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."
_ERR_NOT_FOUND = "❌ Work order #{} not found."


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_pending_list(orders: list[dict[str, Any]]) -> str:
    if not orders:
        return "✅ No pending work orders."
    lines = ["*Pending Work Orders*\n"]
    for wo in orders:
        icon = "🚨" if str(wo.get("severity", "")).lower() == "critical" else "⚠️"
        lines.append(
            f"{icon} *#{wo['id']}* — {wo.get('ahu_id')} (Level {wo.get('level')})\n"
            f"  {wo.get('title')}"
        )
    return "\n".join(lines)


def _format_work_order_detail(wo: dict[str, Any]) -> str:
    lines = [
        f"*Work Order #{wo['id']}*",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
        f"Title: {wo.get('title')}",
        f"Description: {wo.get('description') or '—'}",
        f"Severity: {wo.get('severity')}",
        f"Status: {wo.get('status')}",
        f"Created: {str(wo.get('created_at', ''))[:16].replace('T', ' ')}",
    ]
    return "\n".join(lines)


# ── Guards ─────────────────────────────────────────────────────────────────────

def _is_managers_group(update: Update) -> bool:
    return update.effective_chat.id == MANAGERS_CHAT_ID


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    try:
        orders = await api_client.list_work_orders(status="draft")
        # Also include pending_approval (returned from engineers)
        orders += await api_client.list_work_orders(status="pending_approval")
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_pending_list(orders), parse_mode="Markdown")


async def cmd_workorder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /workorder <id>")
        return
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return
    try:
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_work_order_detail(wo), parse_mode="Markdown")


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    try:
        data = await api_client.get_health_scores()
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    scores = data if isinstance(data, list) else data.get("scores", data.get("levels", []))
    if not scores:
        await update.message.reply_text("No health score data available.")
        return
    lines = ["*Building Health Summary*\n"]
    for item in scores:
        level = item.get("level", item.get("Level", "?"))
        score = item.get("score", item.get("composite", item.get("health_score", "?")))
        try:
            score_int = int(float(score))
            icon = "🔴" if score_int < 40 else ("🟡" if score_int < 60 else "🟢")
        except (TypeError, ValueError):
            icon = "⚪"
            score_int = score
        lines.append(f"{icon} Level {level}: {score_int}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_managers_group(update):
        return
    text = (
        "*Managers — Available Commands*\n\n"
        "/pending — List work orders awaiting approval\n"
        "/workorder <id> — Details of a work order\n"
        "/summary — Building health snapshot\n"
        "/help — This message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Inline callback handlers ───────────────────────────────────────────────────

async def cb_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != MANAGERS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.approve_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not approve: {e.detail}")
        return
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👷 Any Technician", callback_data=f"assign_any:{wo_id}"),
            InlineKeyboardButton("👤 Pick Specific", callback_data=f"assign_pick:{wo_id}"),
        ]
    ])
    await query.edit_message_text(
        f"✅ Work Order #{wo_id} approved.\n\nAssign to:",
        reply_markup=keyboard,
    )


async def cb_dismiss(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != MANAGERS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.dismiss_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not dismiss: {e.detail}")
        return
    await query.edit_message_text(f"❌ Work Order #{wo_id} dismissed.")


async def cb_push_engineers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != MANAGERS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.push_to_engineers(wo_id)
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not push: {e.detail}")
        return
    from bot.push.notifier import notify_engineers
    await notify_engineers(wo)
    await query.edit_message_text(f"🔍 Work Order #{wo_id} sent to engineers for review.")


async def cb_assign_any(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != MANAGERS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.assign_work_order(wo_id, assigned_to="any")
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not assign: {e.detail}")
        return
    await notify_technicians(wo)
    await query.edit_message_text(f"🔧 Work Order #{wo_id} assigned to any available technician.")


async def cb_assign_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != MANAGERS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    if not TECHNICIANS:
        await query.edit_message_text("⚠️ No technicians configured. Set TECHNICIANS_JSON env var.")
        return
    buttons = [
        [InlineKeyboardButton(name, callback_data=f"assign_tech:{wo_id}:{user_id}")]
        for name, user_id in TECHNICIANS.items()
    ]
    await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))


async def cb_assign_tech(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != MANAGERS_CHAT_ID:
        await query.answer()
        return
    _, wo_id_str, user_id = query.data.split(":", 2)
    wo_id = int(wo_id_str)
    await query.answer()
    tech_name = next((n for n, uid in TECHNICIANS.items() if uid == user_id), user_id)
    try:
        await api_client.assign_work_order(wo_id, assigned_to=user_id)
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not assign: {e.detail}")
        return
    await notify_technicians(wo)
    await query.edit_message_text(f"🔧 Work Order #{wo_id} assigned to {tech_name}.")


# ── Handler registration ───────────────────────────────────────────────────────

def get_handlers() -> list:
    return [
        CommandHandler("pending", cmd_pending),
        CommandHandler("workorder", cmd_workorder),
        CommandHandler("summary", cmd_summary),
        CommandHandler("help", cmd_help),
        CallbackQueryHandler(cb_approve, pattern=r"^approve:\d+$"),
        CallbackQueryHandler(cb_dismiss, pattern=r"^dismiss:\d+$"),
        CallbackQueryHandler(cb_push_engineers, pattern=r"^push_engineers:\d+$"),
        CallbackQueryHandler(cb_assign_any, pattern=r"^assign_any:\d+$"),
        CallbackQueryHandler(cb_assign_pick, pattern=r"^assign_pick:\d+$"),
        CallbackQueryHandler(cb_assign_tech, pattern=r"^assign_tech:\d+:.+$"),
    ]
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/bot/test_handlers_managers.py -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add backend/bot/handlers/__init__.py backend/bot/handlers/managers.py backend/tests/bot/test_handlers_managers.py
git commit -m "feat: add manager bot handlers — commands and inline callbacks"
```

---

## Task 7: Engineer Handlers

**Files:**
- Create: `backend/bot/handlers/engineers.py`
- Create: `backend/tests/bot/test_handlers_engineers.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/bot/test_handlers_engineers.py`:

```python
"""Tests for engineer handler helper functions."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_format_review_detail_contains_ahu():
    from bot.handlers.engineers import _format_review_detail
    wo = {
        "id": 7, "ahu_id": "e0507", "level": 5, "title": "Low airflow",
        "description": "Airflow sensor below threshold",
        "fair_snapshot": '{"F": 55, "A": 30, "I": 70, "R": 80, "composite": 58}',
    }
    text = _format_review_detail(wo)
    assert "e0507" in text
    assert "#7" in text
    assert "Low airflow" in text


def test_format_review_detail_contains_fair():
    from bot.handlers.engineers import _format_review_detail
    wo = {
        "id": 7, "ahu_id": "e0507", "level": 5, "title": "Low airflow",
        "description": None,
        "fair_snapshot": '{"F": 55, "A": 30, "I": 70, "R": 80, "composite": 58}',
    }
    text = _format_review_detail(wo)
    assert "55" in text or "F:" in text


def test_format_edit_diff_shows_changes():
    from bot.handlers.engineers import _format_edit_diff
    old_wo = {"title": "Old title", "description": "Old description"}
    text = _format_edit_diff(old_wo, new_title="New title", new_description="New description")
    assert "Old title" in text
    assert "New title" in text
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/bot/test_handlers_engineers.py -v
```

Expected: `FAILED`.

- [ ] **Step 3: Create bot/handlers/engineers.py**

Create `backend/bot/handlers/engineers.py`:

```python
from __future__ import annotations

"""
bot/handlers/engineers.py
──────────────────────────
Telegram handlers for the engineers group.

Commands:
  /review <id>   — fetch work order details + live FAIR scores
  /edit <id>     — guided edit conversation (title then description)
  /sendback <id> — send edited work order back to managers
  /query <ahu_id> — live AHU health data
  /level <N>     — overview of all AHUs on a level
  /help          — available commands

Inline callbacks:
  edit:{id}      — start edit flow
  sendback:{id}  — send back to manager
"""

import json
from typing import Any

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot import api_client
from bot.config import ENGINEERS_CHAT_ID
from bot.push.notifier import _format_engineer_review, _parse_fair, notify_managers

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."
_ERR_NOT_FOUND = "❌ Work order #{} not found."

# ConversationHandler states
EDIT_TITLE = 0
EDIT_DESC = 1

# Context key for edit state
_EDIT_WO_KEY = "editing_wo_id"
_EDIT_OLD_WO_KEY = "editing_wo_old"


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_review_detail(wo: dict[str, Any]) -> str:
    fair_str = _parse_fair(wo.get("fair_snapshot"))
    lines = [
        f"*Work Order #{wo['id']} — Review*",
        f"AHU: {wo.get('ahu_id')} · Level {wo.get('level')}",
        f"Title: {wo.get('title')}",
        f"Description: {wo.get('description') or '—'}",
        f"Status: {wo.get('status')}",
    ]
    if fair_str:
        lines.append(f"FAIR: {fair_str}")
    return "\n".join(lines)


def _format_edit_diff(
    old_wo: dict[str, Any],
    new_title: str | None,
    new_description: str | None,
) -> str:
    lines = ["*Changes to be sent back:*\n"]
    if new_title and new_title != old_wo.get("title"):
        lines += [f"Title: ~~{old_wo.get('title')}~~ → {new_title}"]
    else:
        lines += [f"Title: {old_wo.get('title')} (unchanged)"]
    if new_description is not None and new_description != old_wo.get("description"):
        lines += [f"Description: updated"]
    else:
        lines += [f"Description: (unchanged)"]
    return "\n".join(lines)


# ── Guards ─────────────────────────────────────────────────────────────────────

def _is_engineers_group(update: Update) -> bool:
    return update.effective_chat.id == ENGINEERS_CHAT_ID


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /review <id>")
        return
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return
    try:
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_review_detail(wo), parse_mode="Markdown")


async def cmd_sendback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /sendback <id>")
        return
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return
    try:
        from bot.api_client import WACHAPIError
        # Transition to pending_approval
        import httpx
        async with httpx.AsyncClient(base_url=api_client.API_BASE_URL, timeout=10.0) as client:
            resp = await client.post(f"/api/work-orders/{wo_id}/approve",
                                     json={"status": "pending_approval"})
        # Use the push-to-engineers style status update instead
        # Actually call the correct endpoint: no direct pending_approval endpoint exists.
        # We use the approve endpoint but the agentdb transitions allow pending_engineer_review → pending_approval
        # We need a dedicated sendback route — use PATCH to update status field
        # The correct flow: POST /api/work-orders/{id}/sendback (not yet created)
        # For now, use update via action_tools — let's add a /sendback route in routes
        # This step will be completed once we add the sendback route below.
        wo = await api_client.get_work_order(wo_id)
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await notify_managers(wo)
    await update.message.reply_text(f"✅ Work Order #{wo_id} sent back to managers for approval.")


async def cmd_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /query <ahu_id>  e.g. /query e0402")
        return
    ahu_id = context.args[0].lower()
    import re
    if not re.match(r"^e\d{4}$", ahu_id):
        await update.message.reply_text("❌ Unknown device ID. Use format e0101.")
        return
    try:
        data = await api_client.get_ahu_status(ahu_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(f"❌ No data found for {ahu_id}.")
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    lines = [f"*AHU {ahu_id} — Live Status*"]
    if isinstance(data, dict):
        for key, val in list(data.items())[:8]:
            lines.append(f"{key}: {val}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /level <N>  e.g. /level 4")
        return
    try:
        level = int(context.args[0])
        if not 1 <= level <= 11:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Level must be 1–11.")
        return
    try:
        data = await api_client._get(f"/api/dashboard/ranking", params={"level": level, "range": "24h"})
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    lines = [f"*Level {level} — AHU Overview*\n"]
    items = data if isinstance(data, list) else data.get("rankings", data.get("ahus", []))
    for item in items[:10]:
        ahu = item.get("ahu_id", item.get("id", "?"))
        score = item.get("score", item.get("composite", "?"))
        try:
            score_int = int(float(score))
            icon = "🔴" if score_int < 40 else ("🟡" if score_int < 60 else "🟢")
        except (TypeError, ValueError):
            icon = "⚪"
            score_int = score
        lines.append(f"{icon} {ahu}: {score_int}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_engineers_group(update):
        return
    text = (
        "*Engineers — Available Commands*\n\n"
        "/review <id> — Work order details + FAIR scores\n"
        "/edit <id> — Edit work order title and description\n"
        "/sendback <id> — Send back to managers\n"
        "/query <ahu_id> — Live AHU health data\n"
        "/level <N> — AHU overview for a level\n"
        "/help — This message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Edit ConversationHandler ───────────────────────────────────────────────────

async def cmd_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /edit <id>"""
    if not _is_engineers_group(update):
        return ConversationHandler.END
    if not context.args:
        await update.message.reply_text("Usage: /edit <id>")
        return ConversationHandler.END
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return ConversationHandler.END
    try:
        wo = await api_client.get_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return ConversationHandler.END

    context.user_data[_EDIT_WO_KEY] = wo_id
    context.user_data[_EDIT_OLD_WO_KEY] = wo
    await update.message.reply_text(
        f"Editing Work Order #{wo_id}\n\n"
        f"Current title: *{wo.get('title')}*\n\n"
        f"Send the new title, or /cancel to abort.",
        parse_mode="Markdown",
    )
    return EDIT_TITLE


async def edit_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_title"] = update.message.text.strip()
    old_wo = context.user_data.get(_EDIT_OLD_WO_KEY, {})
    await update.message.reply_text(
        f"Title set to: *{context.user_data['new_title']}*\n\n"
        f"Current description: {old_wo.get('description') or '(none)'}\n\n"
        f"Send the new description, or /skip to keep it unchanged.",
        parse_mode="Markdown",
    )
    return EDIT_DESC


async def edit_receive_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_description"] = update.message.text.strip()
    return await _finish_edit(update, context)


async def edit_skip_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_description"] = None
    return await _finish_edit(update, context)


async def _finish_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    wo_id = context.user_data.get(_EDIT_WO_KEY)
    old_wo = context.user_data.get(_EDIT_OLD_WO_KEY, {})
    new_title = context.user_data.get("new_title")
    new_desc = context.user_data.get("new_description")
    try:
        await api_client.edit_work_order(wo_id, title=new_title, description=new_desc)
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return ConversationHandler.END
    diff = _format_edit_diff(old_wo, new_title, new_desc)
    await update.message.reply_text(
        f"✅ Work Order #{wo_id} updated.\n\n{diff}\n\n"
        f"Use /sendback {wo_id} to send it back to managers.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Edit cancelled.")
    return ConversationHandler.END


async def edit_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_message(
        chat_id=ENGINEERS_CHAT_ID,
        text="Edit cancelled — timed out.",
    )
    return ConversationHandler.END


# ── Inline callbacks ───────────────────────────────────────────────────────────

async def cb_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline button [📝 Edit] — route to edit conversation start."""
    query = update.callback_query
    if query.message.chat.id != ENGINEERS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    await query.message.reply_text(
        f"Use /edit {wo_id} to start editing Work Order #{wo_id}."
    )


async def cb_sendback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline button [✅ Send Back to Manager]"""
    query = update.callback_query
    if query.message.chat.id != ENGINEERS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        # Transition: pending_engineer_review → pending_approval
        # Uses the approve endpoint which allows this transition
        await api_client._post(f"/api/work-orders/{wo_id}/sendback")
        wo = await api_client.get_work_order(wo_id)
    except Exception:
        await query.edit_message_text(_ERR_UNAVAILABLE)
        return
    await notify_managers(wo)
    await query.edit_message_text(f"✅ Work Order #{wo_id} sent back to managers.")


# ── Handler registration ───────────────────────────────────────────────────────

def get_handlers() -> list:
    edit_conv = ConversationHandler(
        entry_points=[CommandHandler("edit", cmd_edit_start)],
        states={
            EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_title)],
            EDIT_DESC: [
                CommandHandler("skip", edit_skip_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_desc),
            ],
        },
        fallbacks=[CommandHandler("cancel", edit_cancel)],
        conversation_timeout=300,
    )
    return [
        CommandHandler("review", cmd_review),
        CommandHandler("sendback", cmd_sendback),
        CommandHandler("query", cmd_query),
        CommandHandler("level", cmd_level),
        CommandHandler("help", cmd_help),
        CallbackQueryHandler(cb_edit, pattern=r"^edit:\d+$"),
        CallbackQueryHandler(cb_sendback, pattern=r"^sendback:\d+$"),
        edit_conv,
    ]
```

Note: `cb_sendback` calls `/api/work-orders/{id}/sendback` — this route doesn't exist yet. Add it in routes/work_orders.py:

```python
@router.post("/work-orders/{wo_id}/sendback")
async def sendback_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="pending_approval")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send back work order in status '{wo['status']}'",
        )
    logger.info(f"work_order {wo_id} sent back to manager by engineer")
    return {"id": wo_id, "status": "pending_approval"}
```

Add this route to `backend/routes/work_orders.py` and add a test in `test_work_orders_api.py`:

```python
def test_sendback_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")
    db.update_work_order(wo_id, status="pending_engineer_review")
    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)
    resp = client.post(f"/api/work-orders/{wo_id}/sendback")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_approval"
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/bot/test_handlers_engineers.py tests/test_work_orders_api.py::test_sendback_work_order -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add backend/bot/handlers/engineers.py backend/routes/work_orders.py backend/tests/bot/test_handlers_engineers.py backend/tests/test_work_orders_api.py
git commit -m "feat: add engineer bot handlers and sendback route"
```

---

## Task 8: Technician Handlers

**Files:**
- Create: `backend/bot/handlers/technicians.py`
- Create: `backend/tests/bot/test_handlers_technicians.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/bot/test_handlers_technicians.py`:

```python
"""Tests for technician handler helper functions."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_format_my_work_empty():
    from bot.handlers.technicians import _format_my_work
    text = _format_my_work([])
    assert "no" in text.lower() or "assigned" in text.lower()


def test_format_my_work_with_items():
    from bot.handlers.technicians import _format_my_work
    orders = [
        {"id": 3, "ahu_id": "e0301", "level": 3, "title": "Vibration fault", "status": "approved"},
        {"id": 7, "ahu_id": "e0402", "level": 4, "title": "Overtemp", "status": "in_progress"},
    ]
    text = _format_my_work(orders)
    assert "#3" in text
    assert "e0301" in text
    assert "#7" in text


def test_format_ahu_status_contains_ahu_id():
    from bot.handlers.technicians import _format_ahu_status
    data = {"ahu_id": "e0402", "temperature": 22.5, "airflow": 1200}
    text = _format_ahu_status("e0402", data)
    assert "e0402" in text
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
cd backend && python -m pytest tests/bot/test_handlers_technicians.py -v
```

Expected: `FAILED`.

- [ ] **Step 3: Create bot/handlers/technicians.py**

Create `backend/bot/handlers/technicians.py`:

```python
from __future__ import annotations

"""
bot/handlers/technicians.py
────────────────────────────
Telegram handlers for the technicians group.

Commands:
  /mywork             — list work orders assigned to this user or "any"
  /start <id>         — mark work order in_progress
  /done <id>          — mark resolved (prompts for note)
  /status <ahu_id>    — current health + sensor reading
  /help               — available commands

Inline callbacks:
  start:{id}          — start work order
  done:{id}           — begin done flow
"""

import re
from typing import Any

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot import api_client
from bot.config import TECHNICIANS_CHAT_ID

_ERR_UNAVAILABLE = "⚠️ WACH backend unavailable. Try again shortly."
_ERR_NOT_FOUND = "❌ Work order #{} not found."

# ConversationHandler state
DONE_NOTE = 0
_DONE_WO_KEY = "done_wo_id"


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_my_work(orders: list[dict[str, Any]]) -> str:
    if not orders:
        return "✅ No work orders assigned to you or available for any technician."
    lines = ["*Your Work Orders*\n"]
    for wo in orders:
        status_icon = "▶️" if wo.get("status") == "in_progress" else "🔧"
        lines.append(
            f"{status_icon} *#{wo['id']}* — {wo.get('ahu_id')} (Level {wo.get('level')})\n"
            f"  {wo.get('title')} [{wo.get('status')}]"
        )
    return "\n".join(lines)


def _format_ahu_status(ahu_id: str, data: dict[str, Any]) -> str:
    lines = [f"*AHU {ahu_id} — Status*\n"]
    for key, val in list(data.items())[:10]:
        lines.append(f"{key}: {val}")
    return "\n".join(lines)


# ── Guards ─────────────────────────────────────────────────────────────────────

def _is_technicians_group(update: Update) -> bool:
    return update.effective_chat.id == TECHNICIANS_CHAT_ID


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_mywork(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    user_id = str(update.effective_user.id)
    try:
        # Work orders assigned to "any"
        any_orders = await api_client.list_work_orders(
            status="approved", assigned_to="any"
        )
        # Work orders assigned specifically to this user
        my_orders = await api_client.list_work_orders(assigned_to=user_id)
        # Also in_progress assigned to this user
        in_progress = await api_client.list_work_orders(
            status="in_progress", assigned_to=user_id
        )
        combined = {wo["id"]: wo for wo in any_orders + my_orders + in_progress}
        orders = list(combined.values())
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_my_work(orders), parse_mode="Markdown")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /start <id>")
        return
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return
    try:
        await api_client.start_work_order(wo_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(_ERR_NOT_FOUND.format(wo_id))
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(f"▶️ Work Order #{wo_id} marked as *in progress*.", parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /status <ahu_id>  e.g. /status e0402")
        return
    ahu_id = context.args[0].lower()
    if not re.match(r"^e\d{4}$", ahu_id):
        await update.message.reply_text("❌ Unknown device ID. Use format e0101.")
        return
    try:
        data = await api_client.get_ahu_status(ahu_id)
    except api_client.WACHAPIError as e:
        if e.status_code == 404:
            await update.message.reply_text(f"❌ No data found for {ahu_id}.")
        else:
            await update.message.reply_text(_ERR_UNAVAILABLE)
        return
    await update.message.reply_text(_format_ahu_status(ahu_id, data), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_technicians_group(update):
        return
    text = (
        "*Technicians — Available Commands*\n\n"
        "/mywork — List your assigned work orders\n"
        "/start <id> — Mark work order as in progress\n"
        "/done <id> — Mark work order as resolved\n"
        "/status <ahu_id> — Current AHU health data\n"
        "/help — This message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Done ConversationHandler ───────────────────────────────────────────────────

async def cmd_done_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_technicians_group(update):
        return ConversationHandler.END
    if not context.args:
        await update.message.reply_text("Usage: /done <id>")
        return ConversationHandler.END
    try:
        wo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID must be a number.")
        return ConversationHandler.END
    context.user_data[_DONE_WO_KEY] = wo_id
    await update.message.reply_text(
        f"Completing Work Order #{wo_id}.\n\nBriefly describe what was done (or /skip):"
    )
    return DONE_NOTE


async def done_receive_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    notes = update.message.text.strip()
    return await _finish_done(update, context, notes=notes)


async def done_skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _finish_done(update, context, notes=None)


async def _finish_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    notes: str | None,
) -> int:
    wo_id = context.user_data.get(_DONE_WO_KEY)
    try:
        await api_client.resolve_work_order(wo_id, notes=notes)
    except Exception:
        await update.message.reply_text(_ERR_UNAVAILABLE)
        return ConversationHandler.END
    await update.message.reply_text(f"✅ Work Order #{wo_id} marked as *resolved*.", parse_mode="Markdown")
    return ConversationHandler.END


async def done_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── Inline callbacks ───────────────────────────────────────────────────────────

async def cb_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.message.chat.id != TECHNICIANS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    try:
        await api_client.start_work_order(wo_id)
    except api_client.WACHAPIError as e:
        await query.edit_message_text(f"❌ Could not start: {e.detail}")
        return
    await query.edit_message_text(f"▶️ Work Order #{wo_id} — *in progress*.", parse_mode="Markdown")


async def cb_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline Done button — prompt to use /done command for note."""
    query = update.callback_query
    if query.message.chat.id != TECHNICIANS_CHAT_ID:
        await query.answer()
        return
    wo_id = int(query.data.split(":")[1])
    await query.answer()
    await query.message.reply_text(f"Use /done {wo_id} to complete this work order with a note.")


# ── Handler registration ───────────────────────────────────────────────────────

def get_handlers() -> list:
    done_conv = ConversationHandler(
        entry_points=[CommandHandler("done", cmd_done_start)],
        states={
            DONE_NOTE: [
                CommandHandler("skip", done_skip_note),
                MessageHandler(filters.TEXT & ~filters.COMMAND, done_receive_note),
            ],
        },
        fallbacks=[CommandHandler("cancel", done_cancel)],
        conversation_timeout=300,
    )
    return [
        CommandHandler("mywork", cmd_mywork),
        CommandHandler("start", cmd_start),
        CommandHandler("status", cmd_status),
        CommandHandler("help", cmd_help),
        CallbackQueryHandler(cb_start, pattern=r"^start:\d+$"),
        CallbackQueryHandler(cb_done, pattern=r"^done:\d+$"),
        done_conv,
    ]
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/bot/test_handlers_technicians.py -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add backend/bot/handlers/technicians.py backend/tests/bot/test_handlers_technicians.py
git commit -m "feat: add technician bot handlers — mywork, start, done, status commands"
```

---

## Task 9: Bot Entry Point + Docker

**Files:**
- Create: `backend/bot/main.py`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create bot/main.py**

Create `backend/bot/main.py`:

```python
from __future__ import annotations

"""
bot/main.py
───────────
Telegram bot entry point. Run: python bot/main.py (from backend/ directory)

Registers all handlers from handlers/managers.py, handlers/engineers.py,
handlers/technicians.py and starts long-polling.
"""

import logging
import os
import sys

# Ensure backend/ is on the path when running as python bot/main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.ext import Application

from bot.config import BOT_TOKEN
from bot.handlers import engineers, managers, technicians

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Add it to your .env file before starting the bot."
        )
    app = Application.builder().token(BOT_TOKEN).build()

    # Register all handlers — order matters for ConversationHandlers
    for handler in managers.get_handlers():
        app.add_handler(handler)
    for handler in engineers.get_handlers():
        app.add_handler(handler)
    for handler in technicians.get_handlers():
        app.add_handler(handler)

    logger.info("Bot handlers registered: managers, engineers, technicians")
    return app


def main() -> None:
    app = build_application()
    logger.info("Starting bot polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify bot starts without errors (dry run)**

With a real token in `.env`:
```bash
cd backend && TELEGRAM_BOT_TOKEN=your-token python bot/main.py
```

Expected: "Starting bot polling..." log line, then blocks waiting for updates. `Ctrl+C` to stop.

Without a token (confirms startup guard):
```bash
cd backend && TELEGRAM_BOT_TOKEN="" python bot/main.py
```

Expected: `RuntimeError: TELEGRAM_BOT_TOKEN is not set.`

- [ ] **Step 3: Add bot service to docker-compose.yml**

In `docker-compose.yml`, add after the `etl` service (before `volumes:`):

```yaml
  bot:
    build: .
    command: python bot/main.py
    volumes:
      - duckdb_data:/app/data
    env_file: .env
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
```

- [ ] **Step 4: Verify docker-compose config is valid**

```bash
docker compose config --quiet
```

Expected: No errors.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd backend && python -m pytest tests/ -v --ignore=tests/e2e -x
```

Expected: All pass (or only pre-existing failures).

- [ ] **Step 6: Commit**

```bash
git add backend/bot/main.py docker-compose.yml
git commit -m "feat: add bot entry point and docker-compose bot service"
```

---

## Self-Review

### Spec Coverage Check

| Spec Requirement | Task |
|---|---|
| 3 separate groups | Task 4 (groups.py), Task 6/7/8 (group guards) |
| Push alerts to managers with Approve/Dismiss/Engineers buttons | Task 5 (notifier.py) |
| Managers: /pending, /workorder, /summary, /help | Task 6 |
| Approve → assign any/specific | Task 6 (cb_approve, cb_assign_*) |
| Push to engineers button | Task 6 (cb_push_engineers) |
| Engineers: /review, /edit, /sendback, /query, /level, /help | Task 7 |
| Edit guided conversation (title → description) | Task 7 (ConversationHandler) |
| 5 min conversation timeout | Task 7 (conversation_timeout=300) |
| Sendback to manager with diff | Task 7 (cb_sendback, _format_edit_diff) |
| Technicians: /mywork, /start, /done, /status, /help | Task 8 |
| /mywork shows "any" + own orders | Task 8 (cmd_mywork) |
| /done prompts for note | Task 8 (ConversationHandler) |
| Inline [▶️ Start] [✅ Done] on assignment | Task 5 (notifier), Task 8 (cb_start, cb_done) |
| pending_engineer_review status | Task 1 |
| assigned_to column | Task 1 |
| New API routes (push-to-engineers, start, resolve, assign, sendback) | Task 2, Task 7 |
| Group chat IDs in config | Task 3 |
| Bot separate process | Task 9 |
| Docker-compose bot service | Task 9 |
| API unavailable error messages | Task 6/7/8 (WACHAPIError handling) |
| Wrong group silent ignore | Task 6/7/8 (_is_*_group guards) |
| 4h spam cooldown | Inherited from existing action_tools.py |
| Invalid AHU ID error | Task 7 (cmd_query), Task 8 (cmd_status) |

All spec requirements covered.

### Type Consistency

- `WACHAPIError` defined in `api_client.py`, imported as `api_client.WACHAPIError` in all handlers ✓
- `notify_managers`, `notify_engineers`, `notify_technicians` all accept `wo: dict[str, Any]` ✓
- `get_handlers()` returns `list` in all three handler modules ✓
- `_EDIT_WO_KEY`, `_DONE_WO_KEY` are string constants — consistent across handler and conversation ✓
- `assigned_to` is stored as string ("any" or telegram user_id as str) throughout ✓

### Known Gap to Address During Implementation

`cmd_sendback` in `engineers.py` has a comment block instead of a direct API call — the `/sendback` route is defined inline in Task 7. The implementer should add the `sendback` route to `routes/work_orders.py` first (as shown in the note in Task 7, Step 3) before implementing `cmd_sendback`.
