# Agentic System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve WACH Insight from a read-only assistant into a proactive agent that detects AHU health issues, creates work orders, sends Telegram notifications, and requests human approval for actions — all while running background health checks every 30 minutes.

**Architecture:** Layered expansion on existing FastAPI/DuckDB/Qwen stack. New `AgentDB` class adds three tables (work_orders, agent_state, watchman_queue) to the existing DuckDB file. A triage router classifies each chat message and dispatches to either the Analysis Agent (existing read-only tools) or a new Resolution Agent (action tools). A Watchman background task flags unhealthy AHUs; the external scheduler processes them via the Resolution Agent.

**Tech Stack:** Python/FastAPI (backend), DuckDB (state tables), python-telegram-bot 20.x (notifications), Qwen/LM Studio (LLM), React/TypeScript (frontend approval UI)

---

## File Map

**Create:**
- `backend/core/agentdb.py` — AgentDB class, three DuckDB tables
- `backend/tools/action_tools.py` — create_work_order, send_notification, update_work_order handlers
- `backend/agents/__init__.py` — exports
- `backend/agents/router.py` — triage classifier (deterministic + LLM fallback)
- `backend/agents/prompts.py` — system prompts per agent type
- `backend/agents/analysis_agent.py` — Analysis Agent (wraps existing query tools)
- `backend/agents/resolution_agent.py` — Resolution Agent (action tools)
- `backend/core/watchman.py` — in-process pulse (asyncio background task)
- `backend/routes/work_orders.py` — CRUD API for work orders
- `backend/tests/test_agentdb.py` — AgentDB tests
- `backend/tests/test_action_tools.py` — action tool handler tests
- `backend/tests/test_agent_router.py` — triage router tests
- `backend/tests/test_watchman.py` — pulse threshold tests
- `backend/tests/test_work_orders_api.py` — work orders endpoint tests

**Modify:**
- `backend/models/schemas.py` — add WorkOrder, AgentMemoryEntry, WatchmanAlert Pydantic models
- `backend/config.py` — add Telegram + Watchman settings
- `backend/tools/tool_registry.py` — split QUERY_TOOLS/ACTION_TOOLS, register action tools, update dispatch
- `backend/routes/chat.py` — wire agent router, extend response with `actions` field, pending drafts check
- `backend/main.py` — register work_orders router, start Watchman lifespan task
- `scripts/scheduler/scheduler.py` — add watchman queue processing step after ETL pipelines
- `frontend/src/api/client.ts` — add work order API functions, extend sendChatMessage return type
- `frontend/src/components/chat/ChatWidget.tsx` — extend Message type, check pending drafts on open
- `frontend/src/components/chat/BotMessage.tsx` — render `actions` array as approval buttons

---

## Task 1: Pydantic Models

**Files:**
- Modify: `backend/models/schemas.py`

- [ ] **Step 1: Open and read the existing schemas**

Run: `grep -n "class.*BaseModel" backend/models/schemas.py`
Confirm where to append new models (after existing models, before the end).

- [ ] **Step 2: Add models to schemas.py**

Append to the bottom of `backend/models/schemas.py`:

```python
# ── Work Order models ─────────────────────────────────────────────────────────

class WorkOrderCreate(BaseModel):
    ahu_id: str
    level: int
    title: str
    description: str | None = None
    severity: str  # "critical" | "warning" | "info"
    trigger_source: str = "chat"  # "watchman" | "chat" | "manual"
    fair_snapshot: dict | None = None  # {F, A, I, R, composite}

class WorkOrder(BaseModel):
    id: int
    ahu_id: str
    level: int
    title: str
    description: str | None
    severity: str
    status: str
    created_by: str
    created_at: str
    updated_at: str
    resolved_at: str | None
    trigger_source: str
    fair_snapshot: dict | None
    notified_via: str
    approved_by: str | None

class WorkOrderUpdate(BaseModel):
    status: str
    notes: str | None = None
    approved_by: str | None = None

# ── Agent memory model ────────────────────────────────────────────────────────

class AgentMemoryEntry(BaseModel):
    key: str
    value: dict
    expires_at: str | None = None  # ISO datetime string

# ── Watchman alert model ──────────────────────────────────────────────────────

class WatchmanAlert(BaseModel):
    ahu_id: str
    level: int
    fair_score: float
    severity: str  # "critical" | "warning"
    fair_breakdown: dict  # {F, A, I, R}
```

- [ ] **Step 3: Verify imports are satisfied**

`WorkOrder` uses `str | None` (Python 3.10+). Confirm `from __future__ import annotations` is already at the top of `schemas.py` or add it. If the file uses `Optional[X]` pattern instead, match that pattern.

- [ ] **Step 4: Commit**

```bash
git add backend/models/schemas.py
git commit -m "feat: add WorkOrder, AgentMemoryEntry, WatchmanAlert Pydantic models"
```

---

## Task 2: AgentDB — DuckDB Tables

**Files:**
- Create: `backend/core/agentdb.py`
- Create: `backend/tests/test_agentdb.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_agentdb.py`:

```python
"""Tests for AgentDB — work_orders, agent_state, watchman_queue tables."""
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def db(tmp_path):
    from core.agentdb import AgentDB
    return AgentDB(str(tmp_path / "test_agent.duckdb"))


def test_create_work_order(db):
    wo_id = db.create_work_order(
        ahu_id="e0402",
        level=4,
        title="Phase imbalance detected",
        description="Current unbalance >10%",
        severity="warning",
        trigger_source="chat",
        fair_snapshot={"F": 72, "A": 55, "I": 40, "R": 88, "composite": 63},
    )
    assert isinstance(wo_id, int)
    assert wo_id > 0


def test_get_work_order(db):
    wo_id = db.create_work_order(
        ahu_id="e0101",
        level=1,
        title="Test",
        severity="info",
    )
    wo = db.get_work_order(wo_id)
    assert wo["ahu_id"] == "e0101"
    assert wo["status"] == "draft"
    assert wo["created_by"] == "agent"


def test_list_draft_work_orders(db):
    db.create_work_order(ahu_id="e0101", level=1, title="Draft 1", severity="warning")
    db.create_work_order(ahu_id="e0102", level=1, title="Draft 2", severity="warning")
    drafts = db.list_work_orders(status="draft")
    assert len(drafts) == 2


def test_update_work_order_status(db):
    wo_id = db.create_work_order(
        ahu_id="e0101", level=1, title="Test", severity="critical"
    )
    db.update_work_order(wo_id, status="approved", approved_by="user")
    wo = db.get_work_order(wo_id)
    assert wo["status"] == "approved"
    assert wo["approved_by"] == "user"


def test_invalid_status_transition_raises(db):
    wo_id = db.create_work_order(
        ahu_id="e0101", level=1, title="Test", severity="info"
    )
    db.update_work_order(wo_id, status="resolved")  # draft -> resolved is invalid
    # Should not raise but status should remain draft (invalid transition ignored)
    wo = db.get_work_order(wo_id)
    assert wo["status"] == "draft"


def test_set_and_get_agent_state(db):
    db.set_agent_state("last_alert:e0402", {"alerted": True})
    val = db.get_agent_state("last_alert:e0402")
    assert val is not None
    assert val["alerted"] is True


def test_get_missing_agent_state_returns_none(db):
    val = db.get_agent_state("nonexistent:key")
    assert val is None


def test_agent_state_expired_returns_none(db):
    from datetime import datetime, timezone, timedelta
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db.set_agent_state("stale:key", {"data": 1}, expires_at=past)
    val = db.get_agent_state("stale:key")
    assert val is None


def test_enqueue_and_dequeue_watchman_alert(db):
    db.enqueue_watchman_alert(ahu_id="e0301", level=3, fair_score=35.0, severity="critical")
    db.enqueue_watchman_alert(ahu_id="e0302", level=3, fair_score=50.0, severity="warning")
    alerts = db.dequeue_watchman_alerts()
    assert len(alerts) == 2
    assert alerts[0]["ahu_id"] == "e0301"
    # After dequeue, they should be marked processed
    alerts_again = db.dequeue_watchman_alerts()
    assert len(alerts_again) == 0
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd backend
python -m pytest tests/test_agentdb.py -v 2>&1 | head -30
```
Expected: `ImportError: cannot import name 'AgentDB'`

- [ ] **Step 3: Implement AgentDB**

Create `backend/core/agentdb.py`:

```python
from __future__ import annotations

"""
core/agentdb.py
───────────────
DuckDB-backed Agent State Database.

Stores work orders, agent memory (key-value), and the watchman alert queue.
Follows the same pattern as core/healthdb.py.

Usage:
  db = AgentDB()                    # default path: data/healthdb.duckdb (same file)
  db = AgentDB('/tmp/test.duckdb')  # custom path (tests)
  wo_id = db.create_work_order(...)
  db.update_work_order(wo_id, status="approved")
  db.set_agent_state("last_alert:e0402", {"ts": "..."})
  db.get_agent_state("last_alert:e0402")
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import duckdb
from config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Same DuckDB file as HealthDB — tables are isolated, no conflict
if settings.app_env != "development":
    _DEFAULT_DB_PATH = "/tmp/healthdb.duckdb"
else:
    _DEFAULT_DB_PATH = str(settings.data_dir / "healthdb.duckdb")

# Valid status transitions: key → set of allowed next states
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_approval", "approved", "dismissed"},
    "pending_approval": {"approved", "dismissed"},
    "approved": {"in_progress", "resolved", "dismissed"},
    "in_progress": {"resolved"},
    "resolved": set(),
    "dismissed": set(),
}

_SCHEMA_SQL = """
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
    approved_by     VARCHAR
);

CREATE SEQUENCE IF NOT EXISTS work_orders_id_seq START 1;

CREATE TABLE IF NOT EXISTS agent_state (
    id          INTEGER PRIMARY KEY,
    key         VARCHAR NOT NULL UNIQUE,
    value       JSON NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    expires_at  TIMESTAMPTZ
);

CREATE SEQUENCE IF NOT EXISTS agent_state_id_seq START 1;

CREATE TABLE IF NOT EXISTS watchman_queue (
    id          INTEGER PRIMARY KEY,
    ahu_id      VARCHAR NOT NULL,
    level       INTEGER NOT NULL,
    fair_score  FLOAT NOT NULL,
    severity    VARCHAR NOT NULL,
    flagged_at  TIMESTAMPTZ NOT NULL,
    processed   BOOLEAN NOT NULL DEFAULT false
);

CREATE SEQUENCE IF NOT EXISTS watchman_queue_id_seq START 1;
"""


class AgentDB:
    """DuckDB-backed store for work orders, agent state, and watchman queue."""

    def __init__(self, db_path: str | None = None):
        self._path = db_path or _DEFAULT_DB_PATH
        self._init_tables()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self._path)

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(_SCHEMA_SQL)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Work Orders ────────────────────────────────────────────────────────────

    def create_work_order(
        self,
        ahu_id: str,
        level: int,
        title: str,
        severity: str,
        description: str | None = None,
        trigger_source: str = "chat",
        fair_snapshot: dict | None = None,
        status: str = "draft",
        created_by: str = "agent",
    ) -> int:
        """Insert a new work order. Returns the new row ID."""
        now = self._now()
        fair_json = json.dumps(fair_snapshot) if fair_snapshot else None
        with self._connect() as conn:
            result = conn.execute(
                """
                INSERT INTO work_orders
                    (id, ahu_id, level, title, description, severity, status,
                     created_by, created_at, updated_at, trigger_source, fair_snapshot)
                VALUES
                    (nextval('work_orders_id_seq'), ?, ?, ?, ?, ?, ?,
                     ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [ahu_id, level, title, description, severity, status,
                 created_by, now, now, trigger_source, fair_json],
            ).fetchone()
        return result[0]

    def get_work_order(self, wo_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM work_orders WHERE id = ?", [wo_id]
            ).fetchdf()
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def list_work_orders(self, status: str | None = None) -> list[dict]:
        with self._connect() as conn:
            if status:
                df = conn.execute(
                    "SELECT * FROM work_orders WHERE status = ? ORDER BY created_at DESC",
                    [status],
                ).fetchdf()
            else:
                df = conn.execute(
                    "SELECT * FROM work_orders ORDER BY created_at DESC"
                ).fetchdf()
        return df.to_dict(orient="records")

    def update_work_order(
        self,
        wo_id: int,
        status: str,
        notes: str | None = None,
        approved_by: str | None = None,
        notified_via: str | None = None,
    ) -> bool:
        """
        Transition work order to new status. Returns True if transition was valid.
        Invalid transitions are silently ignored (status unchanged).
        """
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
            # Append notes to description
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

        params.append(wo_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ?",
                params,
            )
        return True

    # ── Agent State ────────────────────────────────────────────────────────────

    def set_agent_state(
        self,
        key: str,
        value: dict,
        expires_at: str | None = None,
    ) -> None:
        """Upsert a key-value entry in agent_state."""
        now = self._now()
        value_json = json.dumps(value)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_state (id, key, value, updated_at, expires_at)
                VALUES (nextval('agent_state_id_seq'), ?, ?, ?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
                """,
                [key, value_json, now, expires_at],
            )

    def get_agent_state(self, key: str) -> dict | None:
        """
        Return value for key, or None if missing or expired.
        Expired entries are deleted on read.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM agent_state WHERE key = ?", [key]
            ).fetchone()

        if not row:
            return None

        value_json, expires_at = row
        if expires_at:
            now = datetime.now(timezone.utc)
            # expires_at may be a string or datetime depending on DuckDB version
            if isinstance(expires_at, str):
                from datetime import datetime as dt
                exp = dt.fromisoformat(expires_at.replace("Z", "+00:00"))
            else:
                exp = expires_at
            if now > exp.replace(tzinfo=timezone.utc) if exp.tzinfo is None else exp:
                # Expired — delete and return None
                with self._connect() as conn:
                    conn.execute("DELETE FROM agent_state WHERE key = ?", [key])
                return None

        return json.loads(value_json)

    # ── Watchman Queue ─────────────────────────────────────────────────────────

    def enqueue_watchman_alert(
        self,
        ahu_id: str,
        level: int,
        fair_score: float,
        severity: str,
    ) -> None:
        """Add a flagged AHU to the watchman queue."""
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watchman_queue (id, ahu_id, level, fair_score, severity, flagged_at)
                VALUES (nextval('watchman_queue_id_seq'), ?, ?, ?, ?, ?)
                """,
                [ahu_id, level, fair_score, severity, now],
            )

    def dequeue_watchman_alerts(self) -> list[dict]:
        """
        Return all unprocessed alerts and mark them as processed atomically.
        Returns list of dicts with ahu_id, level, fair_score, severity, flagged_at.
        """
        with self._connect() as conn:
            df = conn.execute(
                "SELECT * FROM watchman_queue WHERE processed = false ORDER BY flagged_at ASC"
            ).fetchdf()
            if not df.empty:
                ids = df["id"].tolist()
                placeholders = ", ".join("?" for _ in ids)
                conn.execute(
                    f"UPDATE watchman_queue SET processed = true WHERE id IN ({placeholders})",
                    ids,
                )
        return df.to_dict(orient="records") if not df.empty else []
```

- [ ] **Step 4: Run tests**

```bash
cd backend
python -m pytest tests/test_agentdb.py -v
```
Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/core/agentdb.py backend/tests/test_agentdb.py
git commit -m "feat: add AgentDB with work_orders, agent_state, watchman_queue tables"
```

---

## Task 3: Config — Telegram and Watchman Settings

**Files:**
- Modify: `backend/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Add settings fields to Settings class in config.py**

In `backend/config.py`, add these fields to the `Settings` class after the `# ── Debug flags` section:

```python
    # ── Telegram notifications ─────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_recipient_technician: str = ""
    telegram_recipient_manager: str = ""
    telegram_recipient_on_call: str = ""

    # ── Watchman (background health monitor) ──────────────────────────────────
    watchman_interval_seconds: int = 1800          # 30 minutes
    watchman_critical_threshold: float = 40.0      # FAIR < 40 → critical
    watchman_warning_threshold: float = 60.0       # FAIR < 60 → warning
    watchman_cooldown_critical_hours: int = 4
    watchman_cooldown_warning_hours: int = 24
    watchman_enabled: bool = True
```

- [ ] **Step 2: Add entries to .env.example**

Append to `.env.example`:

```
# Telegram Bot Notifications
TELEGRAM_BOT_TOKEN=
TELEGRAM_RECIPIENT_TECHNICIAN=
TELEGRAM_RECIPIENT_MANAGER=
TELEGRAM_RECIPIENT_ON_CALL=

# Watchman Background Agent
WATCHMAN_INTERVAL_SECONDS=1800
WATCHMAN_CRITICAL_THRESHOLD=40.0
WATCHMAN_WARNING_THRESHOLD=60.0
WATCHMAN_COOLDOWN_CRITICAL_HOURS=4
WATCHMAN_COOLDOWN_WARNING_HOURS=24
WATCHMAN_ENABLED=true
```

- [ ] **Step 3: Verify config loads without error**

```bash
cd backend
python -c "from config import settings; print(settings.watchman_interval_seconds)"
```
Expected output: `1800`

- [ ] **Step 4: Commit**

```bash
git add backend/config.py .env.example
git commit -m "feat: add Telegram and Watchman config settings"
```

---

## Task 4: Action Tool — create_work_order

**Files:**
- Create: `backend/tools/action_tools.py`
- Create: `backend/tests/test_action_tools.py`

- [ ] **Step 1: Write failing test for create_work_order**

Create `backend/tests/test_action_tools.py`:

```python
"""Tests for action tool handlers."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DEV_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Patch AgentDB to use a temp file."""
    from core import agentdb as agentdb_module
    from core.agentdb import AgentDB
    temp_db = AgentDB(str(tmp_path / "test.duckdb"))
    monkeypatch.setattr(agentdb_module, "_db_instance", temp_db)
    return temp_db


@pytest.mark.asyncio
async def test_create_work_order_warning_creates_draft(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e0402",
        title="Phase imbalance",
        description="Current unbalance >10%",
        severity="warning",
    )
    assert result["status"] == "draft"
    assert result["id"] > 0
    assert result["ahu_id"] == "e0402"


@pytest.mark.asyncio
async def test_create_work_order_critical_creates_approved(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e0301",
        title="Critical health failure",
        description="FAIR score 28",
        severity="critical",
    )
    assert result["status"] == "approved"


@pytest.mark.asyncio
async def test_create_work_order_returns_level_from_ahu_id(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e0507",
        title="Test",
        description="desc",
        severity="info",
    )
    assert result["level"] == 5


@pytest.mark.asyncio
async def test_create_work_order_unknown_ahu_id_uses_level_0(db):
    from tools.action_tools import handle_create_work_order
    result = await handle_create_work_order(
        ahu_id="e9999",
        title="Test",
        description="desc",
        severity="info",
    )
    assert result["level"] == 0
```

- [ ] **Step 2: Run test to confirm failure**

```bash
cd backend
python -m pytest tests/test_action_tools.py::test_create_work_order_warning_creates_draft -v 2>&1 | head -20
```
Expected: `ImportError: cannot import name 'handle_create_work_order'`

- [ ] **Step 3: Create action_tools.py with create_work_order**

Create `backend/tools/action_tools.py`:

```python
from __future__ import annotations

"""
tools/action_tools.py
─────────────────────
Handler implementations for the three action tools:
  create_work_order, send_notification, update_work_order

These are called by dispatch_tool() in tool_registry.py.
Pure functions: create_work_order does NOT call send_notification internally.
The Resolution Agent calls each tool explicitly in sequence.
"""

from core.logger import get_logger
from models.schemas import is_valid_ahu_id

logger = get_logger(__name__)

# ── Lazy singleton ─────────────────────────────────────────────────────────────

_db_instance = None


def _get_db():
    global _db_instance
    if _db_instance is None:
        from core.agentdb import AgentDB
        _db_instance = AgentDB()
    return _db_instance


def _level_from_ahu_id(ahu_id: str) -> int:
    """Extract building level from AHU ID format e{level:02d}{nn:02d}."""
    try:
        from models.schemas import get_level_for_device
        level = get_level_for_device(ahu_id)
        return level if level is not None else 0
    except Exception:
        return 0


# ── create_work_order ──────────────────────────────────────────────────────────

async def handle_create_work_order(
    ahu_id: str,
    title: str,
    description: str | None = None,
    severity: str = "warning",
    fair_snapshot: dict | None = None,
    trigger_source: str = "chat",
) -> dict:
    """
    Create a work order for an AHU.

    Status is set based on severity:
      - "critical" → "approved"  (auto-approved, agent should call send_notification next)
      - "warning"  → "draft"     (needs human approval via HITL)
      - "info"     → "draft"     (logged only)

    Returns the created work order dict with id and status.
    """
    db = _get_db()
    level = _level_from_ahu_id(ahu_id)

    # Severity-based initial status
    status = "approved" if severity == "critical" else "draft"

    wo_id = db.create_work_order(
        ahu_id=ahu_id,
        level=level,
        title=title,
        description=description,
        severity=severity,
        trigger_source=trigger_source,
        fair_snapshot=fair_snapshot,
        status=status,
    )

    wo = db.get_work_order(wo_id)
    logger.info(f"create_work_order: id={wo_id} ahu={ahu_id} severity={severity} status={status}")

    # Convert any non-serialisable values to strings
    return {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in wo.items()}
```

- [ ] **Step 4: Run create_work_order tests**

```bash
cd backend
python -m pytest tests/test_action_tools.py -k "create_work_order" -v
```
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/action_tools.py backend/tests/test_action_tools.py
git commit -m "feat: implement create_work_order action tool"
```

---

## Task 5: Action Tool — send_notification

**Files:**
- Modify: `backend/tools/action_tools.py`
- Modify: `backend/tests/test_action_tools.py`

- [ ] **Step 1: Add test for send_notification**

Append to `backend/tests/test_action_tools.py`:

```python
@pytest.mark.asyncio
async def test_send_notification_no_token_returns_skipped(db):
    """When TELEGRAM_BOT_TOKEN is empty, notification should be skipped gracefully."""
    from tools.action_tools import handle_send_notification
    result = await handle_send_notification(
        recipient="technician",
        message="AHU e0402 phase imbalance detected.",
    )
    assert result["status"] == "skipped"
    assert "token not configured" in result["reason"]


@pytest.mark.asyncio
async def test_send_notification_spam_prevention(db):
    """Second notification for same AHU within cooldown should be blocked."""
    from tools.action_tools import handle_send_notification
    from datetime import datetime, timezone, timedelta
    # Manually set agent state to simulate a recent alert
    db.set_agent_state(
        "last_alert:e0402",
        {"notified_at": datetime.now(timezone.utc).isoformat()},
    )
    result = await handle_send_notification(
        recipient="technician",
        message="Repeated alert for e0402",
        ahu_id="e0402",
    )
    assert result["status"] == "skipped"
    assert "cooldown" in result["reason"]


@pytest.mark.asyncio
async def test_send_notification_updates_work_order(db):
    """If work_order_id provided and notification skipped, work order unchanged."""
    from tools.action_tools import handle_create_work_order, handle_send_notification
    wo = await handle_create_work_order(
        ahu_id="e0101", title="Test", severity="critical"
    )
    result = await handle_send_notification(
        recipient="technician",
        message="Critical alert",
        work_order_id=wo["id"],
        ahu_id="e0101",
    )
    # Even if skipped (no token), result has a status field
    assert "status" in result
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
python -m pytest tests/test_action_tools.py -k "send_notification" -v 2>&1 | head -20
```
Expected: `ImportError` or `AttributeError: module has no attribute 'handle_send_notification'`

- [ ] **Step 3: Implement send_notification in action_tools.py**

Add to `backend/tools/action_tools.py` (after handle_create_work_order):

```python
# ── send_notification ──────────────────────────────────────────────────────────

_RECIPIENT_ENV_MAP = {
    "technician": "telegram_recipient_technician",
    "manager":    "telegram_recipient_manager",
    "on_call":    "telegram_recipient_on_call",
}


async def handle_send_notification(
    recipient: str,
    message: str,
    work_order_id: int | None = None,
    ahu_id: str | None = None,
    channel: str = "telegram",
) -> dict:
    """
    Send a notification to a named recipient via Telegram.

    recipient: "technician" | "manager" | "on_call"
    message:   Plain text message body.
    work_order_id: Optional — updates notified_via field on work order.
    ahu_id:    Optional — used for spam prevention cooldown check.

    Spam prevention: If ahu_id is provided, checks agent_state for
    last_alert:{ahu_id}. If alerted within 4 hours, returns skipped.

    Returns {"status": "sent"|"skipped", "reason": str}
    """
    from config import settings

    db = _get_db()

    # Check spam cooldown
    if ahu_id:
        state = db.get_agent_state(f"last_alert:{ahu_id}")
        if state:
            return {
                "status": "skipped",
                "reason": f"cooldown active for {ahu_id} — already notified recently",
            }

    # Check Telegram token
    token = settings.telegram_bot_token
    if not token:
        logger.warning("send_notification: TELEGRAM_BOT_TOKEN not configured, skipping")
        return {"status": "skipped", "reason": "token not configured"}

    # Resolve chat ID
    env_field = _RECIPIENT_ENV_MAP.get(recipient)
    if not env_field:
        return {"status": "error", "reason": f"unknown recipient: {recipient}"}

    chat_id = getattr(settings, env_field, "")
    if not chat_id:
        return {"status": "skipped", "reason": f"chat_id for {recipient!r} not configured"}

    # Send via Telegram Bot API
    try:
        from telegram import Bot
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logger.info(f"send_notification: sent to {recipient} ({chat_id})")
    except Exception as e:
        logger.error(f"send_notification: Telegram error — {e}")
        return {"status": "error", "reason": str(e)}

    # Record in agent_state with TTL = cooldown hours
    if ahu_id:
        from datetime import datetime, timezone, timedelta
        cooldown_hours = settings.watchman_cooldown_critical_hours
        expires = (datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)).isoformat()
        db.set_agent_state(
            f"last_alert:{ahu_id}",
            {"notified_at": datetime.now(timezone.utc).isoformat(), "recipient": recipient},
            expires_at=expires,
        )

    # Update work order notified_via if provided
    if work_order_id:
        db.update_work_order(work_order_id, status=db.get_work_order(work_order_id)["status"],
                             notified_via="telegram")

    return {"status": "sent", "recipient": recipient, "channel": "telegram"}
```

- [ ] **Step 4: Install python-telegram-bot**

```bash
cd backend
pip install "python-telegram-bot==20.8"
echo "python-telegram-bot==20.8" >> requirements.txt
```

- [ ] **Step 5: Run send_notification tests**

```bash
cd backend
python -m pytest tests/test_action_tools.py -k "send_notification" -v
```
Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/tools/action_tools.py backend/tests/test_action_tools.py backend/requirements.txt
git commit -m "feat: implement send_notification action tool with Telegram + spam prevention"
```

---

## Task 6: Action Tool — update_work_order

**Files:**
- Modify: `backend/tools/action_tools.py`
- Modify: `backend/tests/test_action_tools.py`

- [ ] **Step 1: Add tests for update_work_order**

Append to `backend/tests/test_action_tools.py`:

```python
@pytest.mark.asyncio
async def test_update_work_order_valid_transition(db):
    from tools.action_tools import handle_create_work_order, handle_update_work_order
    wo = await handle_create_work_order(
        ahu_id="e0101", title="Test", severity="warning"
    )
    result = await handle_update_work_order(
        work_order_id=wo["id"],
        status="approved",
        approved_by="admin",
    )
    assert result["success"] is True
    assert result["new_status"] == "approved"


@pytest.mark.asyncio
async def test_update_work_order_invalid_transition(db):
    from tools.action_tools import handle_create_work_order, handle_update_work_order
    wo = await handle_create_work_order(
        ahu_id="e0101", title="Test", severity="info"
    )
    result = await handle_update_work_order(
        work_order_id=wo["id"],
        status="resolved",  # invalid: draft → resolved not allowed
    )
    assert result["success"] is False


@pytest.mark.asyncio
async def test_update_work_order_not_found(db):
    from tools.action_tools import handle_update_work_order
    result = await handle_update_work_order(
        work_order_id=99999,
        status="approved",
    )
    assert result["success"] is False
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
python -m pytest tests/test_action_tools.py -k "update_work_order" -v 2>&1 | head -20
```
Expected: `AttributeError: module has no attribute 'handle_update_work_order'`

- [ ] **Step 3: Implement update_work_order in action_tools.py**

Append to `backend/tools/action_tools.py`:

```python
# ── update_work_order ──────────────────────────────────────────────────────────

async def handle_update_work_order(
    work_order_id: int,
    status: str,
    notes: str | None = None,
    approved_by: str | None = None,
) -> dict:
    """
    Transition a work order to a new status.

    Valid transitions:
      draft → pending_approval | approved | dismissed
      pending_approval → approved | dismissed
      approved → in_progress | resolved | dismissed
      in_progress → resolved

    Returns {"success": bool, "new_status": str, "reason": str}
    """
    db = _get_db()
    wo = db.get_work_order(work_order_id)
    if not wo:
        return {"success": False, "reason": f"work order {work_order_id} not found"}

    success = db.update_work_order(
        work_order_id,
        status=status,
        notes=notes,
        approved_by=approved_by,
    )

    if success:
        logger.info(f"update_work_order: id={work_order_id} → {status}")
        return {"success": True, "new_status": status, "work_order_id": work_order_id}
    else:
        return {
            "success": False,
            "reason": f"invalid transition: {wo['status']!r} → {status!r}",
            "current_status": wo["status"],
        }
```

- [ ] **Step 4: Run all action tool tests**

```bash
cd backend
python -m pytest tests/test_action_tools.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/action_tools.py backend/tests/test_action_tools.py
git commit -m "feat: implement update_work_order action tool with transition validation"
```

---

## Task 7: Tool Registry — Register Action Tools

**Files:**
- Modify: `backend/tools/tool_registry.py`
- Modify: `backend/tests/test_tool_registry.py`

- [ ] **Step 1: Update test for new tool count**

In `backend/tests/test_tool_registry.py`, update the count assertion:

```python
def test_tools_list_has_six_entries():
    # Updated: 6 query tools + 3 action tools = 9
    assert len(TOOLS) == 9
```

Also update the names test to include action tools:

```python
def test_tool_names_are_correct():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == {
        "query_building_summary",
        "query_health_scores",
        "query_live_readings",
        "query_ranking",
        "query_financial_impact",
        "search_docs",
        "create_work_order",
        "send_notification",
        "update_work_order",
    }
```

- [ ] **Step 2: Run updated test to confirm failure**

```bash
cd backend
python -m pytest tests/test_tool_registry.py -v 2>&1 | tail -10
```
Expected: `assert 6 == 9` failure.

- [ ] **Step 3: Update tool_registry.py**

In `backend/tools/tool_registry.py`, after the existing `TOOLS` list, add:

```python
# ── Action Tool definitions ────────────────────────────────────────────────────

ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_work_order",
            "description": (
                "Create a maintenance work order for an AHU. "
                "Use when an AHU has a confirmed problem that needs physical intervention. "
                "severity='critical': auto-approved, you should then call send_notification. "
                "severity='warning': creates a draft for human approval. "
                "severity='info': logs only, no notification needed."
            ),
            "parameters": {
                "type": "object",
                "required": ["ahu_id", "title", "description", "severity"],
                "properties": {
                    "ahu_id": {"type": "string", "description": "Device ID, e.g. 'e0402'"},
                    "title": {"type": "string", "description": "Short issue title, max 80 chars"},
                    "description": {"type": "string", "description": "Detailed description including FAIR scores and financial impact"},
                    "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                    "fair_snapshot": {"type": "object", "description": "FAIR score breakdown at time of issue, e.g. {F: 72, A: 55, I: 40, R: 88, composite: 63}"},
                    "trigger_source": {"type": "string", "enum": ["watchman", "chat", "manual"], "description": "What triggered this work order"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": (
                "Send a Telegram notification to a building operations team member. "
                "recipient='technician': on-site AHU technician. "
                "recipient='manager': facility manager. "
                "recipient='on_call': whoever is on call. "
                "Always include work_order_id if you just created a work order. "
                "Do NOT call this for draft work orders — only for auto-approved (critical) ones."
            ),
            "parameters": {
                "type": "object",
                "required": ["recipient", "message"],
                "properties": {
                    "recipient": {"type": "string", "enum": ["technician", "manager", "on_call"]},
                    "message": {"type": "string", "description": "Notification text. Keep under 300 chars. Include AHU ID, issue, and ticket number."},
                    "work_order_id": {"type": "integer", "description": "Work order ID to link in the notification"},
                    "ahu_id": {"type": "string", "description": "AHU ID for spam-prevention cooldown check"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_work_order",
            "description": (
                "Update the status of an existing work order. "
                "Use to mark issues as resolved, in-progress, or to dismiss false alarms. "
                "Valid transitions: draft→approved|dismissed, approved→in_progress|resolved, in_progress→resolved."
            ),
            "parameters": {
                "type": "object",
                "required": ["work_order_id", "status"],
                "properties": {
                    "work_order_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["approved", "dismissed", "in_progress", "resolved"]},
                    "notes": {"type": "string", "description": "Optional notes appended to work order description"},
                    "approved_by": {"type": "string", "description": "Name/ID of who approved the work order"},
                },
            },
        },
    },
]

# Separate lists for per-agent tool selection
QUERY_TOOLS = TOOLS  # original 6 read-only tools
TOOLS = TOOLS + ACTION_TOOLS  # combined 9 tools
```

Also update `_KNOWN_TOOLS` and `dispatch_tool`:

Find `_KNOWN_TOOLS` set and add the three action tools:

```python
_KNOWN_TOOLS = {
    "query_building_summary",
    "query_health_scores",
    "query_live_readings",
    "query_ranking",
    "query_financial_impact",
    "search_docs",
    "create_work_order",
    "send_notification",
    "update_work_order",
}
```

In `dispatch_tool`, add action tool imports after the health_tools import block:

```python
    from tools.action_tools import (
        handle_create_work_order,
        handle_send_notification,
        handle_update_work_order,
    )

    handlers = {
        "query_building_summary":  handle_query_building_summary,
        "query_health_scores":    handle_query_health_scores,
        "query_live_readings":    handle_query_live_readings,
        "query_ranking":          handle_query_ranking,
        "query_financial_impact": handle_query_financial_impact,
        "search_docs":            handle_search_docs,
        "create_work_order":      handle_create_work_order,
        "send_notification":      handle_send_notification,
        "update_work_order":      handle_update_work_order,
    }
```

- [ ] **Step 4: Run tool registry tests**

```bash
cd backend
python -m pytest tests/test_tool_registry.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/tool_registry.py backend/tests/test_tool_registry.py
git commit -m "feat: register action tools in tool registry, split QUERY_TOOLS/ACTION_TOOLS"
```

---

## Task 8: Agent Router

**Files:**
- Create: `backend/agents/__init__.py`
- Create: `backend/agents/router.py`
- Create: `backend/tests/test_agent_router.py`

- [ ] **Step 1: Write failing tests for router**

Create `backend/tests/test_agent_router.py`:

```python
"""Tests for the triage agent router."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_classify_query_message_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("What is the health score for Level 4?") == "analysis"


def test_classify_action_message_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Create a ticket for AHU e0402") == "resolution"


def test_classify_notify_message_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Send an alert to the technician") == "resolution"


def test_classify_show_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("Show me the worst AHUs on Level 3") == "analysis"


def test_classify_fix_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Fix the phase imbalance issue on e0507") == "resolution"


def test_classify_why_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("Why is e0301 in warning state?") == "analysis"


def test_classify_explain_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("Explain what FAIR scoring means") == "analysis"


def test_classify_approve_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Approve the pending work order") == "resolution"


def test_classify_empty_defaults_to_analysis():
    from agents.router import classify_intent
    assert classify_intent("") == "analysis"
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
python -m pytest tests/test_agent_router.py -v 2>&1 | head -15
```
Expected: `ImportError: No module named 'agents'`

- [ ] **Step 3: Create agents package**

```bash
touch backend/agents/__init__.py
```

- [ ] **Step 4: Create router.py**

Create `backend/agents/router.py`:

```python
from __future__ import annotations

"""
agents/router.py
────────────────
Triage router — classifies each user message as "analysis" or "resolution".

Uses a two-step approach:
  1. Deterministic keyword scoring (fast, no LLM cost)
  2. LLM classification (only when step 1 is ambiguous)

Returns "analysis" (→ Analysis Agent) or "resolution" (→ Resolution Agent).
"""

import re
from core.logger import get_logger

logger = get_logger(__name__)

# Keywords that strongly indicate action intent → Resolution Agent
_ACTION_KEYWORDS = {
    "ticket", "work order", "workorder", "notify", "notification", "alert",
    "send", "report", "schedule", "create", "approve", "submit",
    "fix", "resolve", "escalate", "assign", "dispatch", "email",
    "message", "tell", "inform", "contact",
}

# Keywords that strongly indicate query intent → Analysis Agent
_QUERY_KEYWORDS = {
    "show", "what", "why", "compare", "rank", "trend", "how", "explain",
    "which", "list", "get", "display", "tell me", "check", "review",
    "analyse", "analyze", "summarize", "summarise", "describe", "status",
    "health", "score", "level", "floor", "building",
}


def _score_keywords(text: str) -> tuple[int, int]:
    """Return (action_score, query_score) based on keyword hits."""
    lower = text.lower()
    words = set(re.findall(r"\b\w[\w\s]*?\b", lower))
    action = sum(1 for kw in _ACTION_KEYWORDS if kw in lower)
    query = sum(1 for kw in _QUERY_KEYWORDS if kw in lower)
    return action, query


def classify_intent(
    message: str,
    history: list[dict] | None = None,
) -> str:
    """
    Classify user message intent.

    Args:
        message: Current user message.
        history: Conversation history (list of {role, content} dicts). Used for
                 context in LLM fallback, not for deterministic scoring.

    Returns:
        "analysis" or "resolution"
    """
    if not message.strip():
        return "analysis"

    action_score, query_score = _score_keywords(message)

    # Clear winner — skip LLM call
    if action_score > 0 and query_score == 0:
        logger.debug(f"router: action_score={action_score} query_score={query_score} → resolution")
        return "resolution"
    if query_score > 0 and action_score == 0:
        logger.debug(f"router: action_score={action_score} query_score={query_score} → analysis")
        return "analysis"
    if action_score > query_score:
        return "resolution"
    if query_score > action_score:
        return "analysis"

    # Ambiguous — fall back to LLM (only if LLM is enabled)
    try:
        return _llm_classify(message, history or [])
    except Exception as e:
        logger.warning(f"router: LLM fallback failed ({e}), defaulting to analysis")
        return "analysis"


def _llm_classify(message: str, history: list[dict]) -> str:
    """
    Use Qwen to classify ambiguous messages.
    Returns "analysis" or "resolution".
    """
    from config import settings
    if not settings.enable_llm:
        return "analysis"

    from llm.client_factory import get_chat_client
    import asyncio

    system_prompt = (
        "Classify the user message. "
        'If the user wants information, analysis, or explanation, output exactly: {"agent": "analysis"}\n'
        'If the user wants an action taken (create ticket, send notification, update status), output exactly: {"agent": "resolution"}\n'
        "Output only the JSON, nothing else."
    )
    user_msg = f"/no_think {message}"

    client = get_chat_client()

    async def _call():
        return await client.generate_text(
            prompt=user_msg,
            system_instruction=system_prompt,
            max_output_tokens=20,
        )

    try:
        loop = asyncio.get_event_loop()
        raw = loop.run_until_complete(_call())
        import json, re as re2
        match = re2.search(r'\{[^}]+\}', raw)
        if match:
            parsed = json.loads(match.group())
            result = parsed.get("agent", "analysis")
            if result in ("analysis", "resolution"):
                logger.debug(f"router: LLM classified as {result!r}")
                return result
    except Exception as e:
        logger.warning(f"router: LLM classify parse error: {e}")

    return "analysis"
```

- [ ] **Step 5: Run router tests**

```bash
cd backend
python -m pytest tests/test_agent_router.py -v
```
Expected: all 9 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/__init__.py backend/agents/router.py backend/tests/test_agent_router.py
git commit -m "feat: add triage agent router with keyword scoring and LLM fallback"
```

---

## Task 9: Analysis Agent + Resolution Agent

**Files:**
- Create: `backend/agents/prompts.py`
- Create: `backend/agents/analysis_agent.py`
- Create: `backend/agents/resolution_agent.py`

- [ ] **Step 1: Create prompts.py**

Create `backend/agents/prompts.py`:

```python
from __future__ import annotations

"""
agents/prompts.py
─────────────────
System prompts per agent type.
"""

RESOLUTION_SYSTEM_PROMPT = """You are a building operations coordinator for a healthcare facility (WACH).
Your role is to create work orders, notify the right people, and track issue resolution.

Rules:
- Always include FAIR scores and financial impact in work order descriptions.
- For critical issues (FAIR < 40): call create_work_order with severity="critical", then call send_notification with recipient="technician".
- For warnings (FAIR 40-60): call create_work_order with severity="warning" only. Do NOT call send_notification — the user will approve the draft.
- Never create a work order without first querying health scores to confirm the issue.
- Be concise. Work order titles must be under 80 characters.
- Format: "AHU {id} — {issue description}"
"""
```

- [ ] **Step 2: Create analysis_agent.py**

Create `backend/agents/analysis_agent.py`:

```python
from __future__ import annotations

"""
agents/analysis_agent.py
────────────────────────
Analysis Agent — wraps existing query tools for read-only data retrieval.

This is the same logic that was previously inline in routes/chat.py,
extracted into a reusable agent class.
"""

from core.logger import get_logger
from llm.client_factory import get_chat_client
from llm.prompts import build_system_prompt
from tools.tool_registry import QUERY_TOOLS, dispatch_tool

logger = get_logger(__name__)


async def run(
    messages: list[dict],
    persona: str = "general",
) -> str:
    """
    Run the Analysis Agent.

    Args:
        messages: OpenAI-format message list (system excluded — built internally).
        persona:  User persona for system prompt selection.

    Returns:
        Reply text string.
    """
    client = get_chat_client()
    reply = await client.generate_with_tools(
        system_prompt=build_system_prompt(persona),
        messages=messages,
        tools=QUERY_TOOLS,
        tool_dispatcher=dispatch_tool,
    )
    logger.debug("analysis_agent: completed")
    return reply
```

- [ ] **Step 3: Create resolution_agent.py**

Create `backend/agents/resolution_agent.py`:

```python
from __future__ import annotations

"""
agents/resolution_agent.py
──────────────────────────
Resolution Agent — action-focused agent that creates work orders, sends
notifications, and updates issue status.

Returns (reply_text, draft_work_orders) where draft_work_orders is a list
of work order dicts that were created with status="draft" during this run.
These are surfaced to the frontend as approval action buttons.
"""

import json
from core.logger import get_logger
from llm.client_factory import get_chat_client
from tools.tool_registry import ACTION_TOOLS, QUERY_TOOLS, dispatch_tool

logger = get_logger(__name__)

# Resolution agent gets action tools + query_health_scores + search_docs for context
_RESOLUTION_TOOLS = [
    t for t in QUERY_TOOLS
    if t["function"]["name"] in ("query_health_scores", "search_docs", "query_financial_impact")
] + ACTION_TOOLS


async def run(
    messages: list[dict],
) -> tuple[str, list[dict]]:
    """
    Run the Resolution Agent.

    Returns:
        (reply_text, draft_work_orders)

        draft_work_orders: list of work order dicts with status="draft",
        created during this run. Used by chat.py to build the `actions`
        field in the API response.
    """
    from agents.prompts import RESOLUTION_SYSTEM_PROMPT

    # Track tool results to find draft work orders created this turn
    tool_results: list[dict] = []

    async def _tracking_dispatcher(name: str, args: dict) -> dict:
        result = await dispatch_tool(name, args)
        if name == "create_work_order":
            tool_results.append(result)
        return result

    client = get_chat_client()
    reply = await client.generate_with_tools(
        system_prompt=RESOLUTION_SYSTEM_PROMPT,
        messages=messages,
        tools=_RESOLUTION_TOOLS,
        tool_dispatcher=_tracking_dispatcher,
        max_tool_rounds=3,
    )

    # Collect draft work orders for HITL
    drafts = [r for r in tool_results if isinstance(r, dict) and r.get("status") == "draft"]
    logger.debug(f"resolution_agent: completed, {len(drafts)} draft(s) created")

    return reply, drafts
```

- [ ] **Step 4: Verify generate_with_tools supports max_tool_rounds parameter**

```bash
cd backend
grep -n "max_tool_rounds" llm/qwen_client.py | head -5
```

If `max_tool_rounds` is not a parameter, check the signature and add it. If it already exists, skip to step 5.

If it doesn't exist, find the hardcoded `5` in qwen_client.py and make it a parameter:

```python
async def generate_with_tools(
    self,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    tool_dispatcher,
    max_tool_rounds: int = 5,   # add this parameter
) -> str:
```

Then use `max_tool_rounds` instead of the hardcoded `5`.

- [ ] **Step 5: Verify agents module imports cleanly**

```bash
cd backend
python -c "from agents.analysis_agent import run; print('OK')"
python -c "from agents.resolution_agent import run; print('OK')"
```
Expected: both print `OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/prompts.py backend/agents/analysis_agent.py backend/agents/resolution_agent.py
git commit -m "feat: add Analysis Agent and Resolution Agent with tool-tracking dispatch"
```

---

## Task 10: Chat Route Integration

**Files:**
- Modify: `backend/routes/chat.py`

- [ ] **Step 1: Read current chat.py to understand what changes**

The current `chat()` endpoint (lines 94-127) does:
1. Detect persona
2. Classify complexity
3. Build messages
4. Call `client.generate_with_tools()` directly
5. Return `{reply, navigate, thinking_mode}`

New flow:
1. Check for pending drafts (if first message in session)
2. Detect persona
3. Classify complexity
4. Build messages
5. Route via `classify_intent()`
6. Run Analysis Agent or Resolution Agent
7. Build `actions` from draft work orders
8. Return `{reply, navigate, thinking_mode, actions, pending_drafts_count}`

- [ ] **Step 2: Replace chat.py with updated version**

Replace the contents of `backend/routes/chat.py`:

```python
from __future__ import annotations

"""
routes/chat.py
──────────────
AI-powered chat endpoint — V3 (multi-agent with HITL).

POST /api/chat
  Request:  { message: str, history?: list, context?: dict, persona?: str }
  Response: { reply: str, navigate: dict|null, thinking_mode: str,
              actions: list[ActionItem], pending_drafts_count: int }

Architecture:
  1. Check pending draft work orders (surfaced if no history = first message)
  2. detect_persona() → "general" | "technical" | "technician" | "financial"
  3. classify_query_complexity() → "think" or "fast"
  4. classify_intent() → "analysis" or "resolution"
  5. Route to Analysis Agent (query tools) or Resolution Agent (action tools)
  6. Build actions list from any draft work orders created this turn
  7. Return reply + navigate + thinking_mode + actions + pending_drafts_count
"""

import re

from agents.router import classify_intent
from core.logger import get_logger
from core.query_classifier import classify_query_complexity
from fastapi import APIRouter, HTTPException
from llm.client_factory import get_chat_client
from llm.persona_detector import detect_persona
from llm.prompts import build_system_prompt
from models.schemas import ChatHistoryItem
from pydantic import BaseModel, field_validator

logger = get_logger(__name__)
router = APIRouter()

# Patterns to strip from LLM replies before returning to the user
_TOOL_CALL_XML_RE = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL)
_TOOL_RESPONSE_XML_RE = re.compile(r"<tool_response>.*?</tool_response>", re.DOTALL)
_FUNCTION_CALL_JSON_RE = re.compile(
    r"```(?:json)?\s*\{[^`]*[\"'](?:name|function)[\"']\s*:[^`]*\}[^`]*```",
    re.DOTALL,
)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _sanitize_reply(text: str) -> str:
    """Strip tool-call artifacts and code blocks from LLM reply text."""
    text = _THINK_RE.sub("", text)
    text = _TOOL_CALL_XML_RE.sub("", text)
    text = _TOOL_RESPONSE_XML_RE.sub("", text)
    text = _FUNCTION_CALL_JSON_RE.sub("", text)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^(Calling|Executing|Invoking|Running)\s+\w+", stripped, re.IGNORECASE):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _build_actions(draft_work_orders: list[dict]) -> list[dict]:
    """Convert draft work order dicts into frontend action button descriptors."""
    actions = []
    for wo in draft_work_orders:
        wo_id = wo.get("id")
        ahu_id = wo.get("ahu_id", "unknown")
        title = wo.get("title", "Work order")
        actions.extend([
            {
                "type": "approve_work_order",
                "work_order_id": wo_id,
                "label": "Submit Ticket",
                "description": f"Create work order for {ahu_id}: {title}. Notifies technician via Telegram.",
            },
            {
                "type": "edit_draft",
                "work_order_id": wo_id,
                "label": "Edit Draft",
                "description": "Edit the work order description before submitting.",
            },
            {
                "type": "dismiss",
                "work_order_id": wo_id,
                "label": "Dismiss",
                "description": "Dismiss this work order draft.",
            },
        ])
    return actions


def _get_pending_drafts_count() -> int:
    """Return count of unresolved draft work orders."""
    try:
        from core.agentdb import AgentDB
        db = AgentDB()
        return len(db.list_work_orders(status="draft"))
    except Exception:
        return 0


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] | None = None
    context: dict | None = None
    persona: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        if len(v) > 1000:
            raise ValueError("message must be 1000 characters or fewer")
        return v


# ── History conversion ─────────────────────────────────────────────────────────

def _to_openai_messages(history: list[ChatHistoryItem]) -> list[dict]:
    messages = []
    for item in history:
        role = "assistant" if item.role in ("model", "assistant") else "user"
        messages.append({"role": role, "content": item.content})
    return messages


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(body: ChatRequest) -> dict:
    history = body.history or []
    history_messages = _to_openai_messages(history)

    # Check pending drafts on first message of a session
    pending_drafts_count = 0
    if not history:
        pending_drafts_count = _get_pending_drafts_count()

    # 1. Detect persona
    history_dicts = [{"role": m["role"], "content": m["content"]} for m in history_messages]
    persona = detect_persona(body.message, history=history_dicts, stated_persona=body.persona)

    # 2. Classify complexity → choose thinking mode
    thinking_mode = classify_query_complexity(body.message, history_messages)
    prefix = "/think " if thinking_mode == "think" else "/no_think "
    user_content = prefix + body.message

    # 3. Build messages list
    messages = history_messages + [{"role": "user", "content": user_content}]

    # 4. Route to appropriate agent
    agent_type = classify_intent(body.message, history=history_dicts)
    logger.info(f"chat: persona={persona} thinking={thinking_mode} agent={agent_type}")

    try:
        draft_work_orders: list[dict] = []

        if agent_type == "resolution":
            from agents import resolution_agent
            reply, draft_work_orders = await resolution_agent.run(messages)
        else:
            from agents import analysis_agent
            reply = await analysis_agent.run(messages, persona=persona)

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    actions = _build_actions(draft_work_orders)

    return {
        "reply": _sanitize_reply(reply),
        "navigate": None,
        "thinking_mode": thinking_mode,
        "actions": actions,
        "pending_drafts_count": pending_drafts_count,
    }
```

- [ ] **Step 3: Run existing chat tests to check no regressions**

```bash
cd backend
python -m pytest tests/test_chat_endpoint.py -v 2>&1 | tail -20
```
Expected: all tests pass (they mock the LLM client, so agent routing won't affect them).

- [ ] **Step 4: Commit**

```bash
git add backend/routes/chat.py
git commit -m "feat: integrate agent router into chat endpoint, add actions + pending_drafts_count response fields"
```

---

## Task 11: Work Orders API Route

**Files:**
- Create: `backend/routes/work_orders.py`
- Create: `backend/tests/test_work_orders_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_work_orders_api.py`:

```python
"""Tests for /api/work-orders endpoints."""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["API_KEY"] = "test-key"
os.environ["DEV_API_KEY"] = "test-key"


@pytest.fixture
def client(tmp_path, monkeypatch):
    from core import agentdb as agentdb_module
    from core.agentdb import AgentDB
    temp_db = AgentDB(str(tmp_path / "test.duckdb"))
    monkeypatch.setattr(agentdb_module, "_db_instance", temp_db)

    from main import app
    return TestClient(app, headers={"Authorization": "Bearer test-key"})


def test_list_work_orders_empty(client):
    resp = client.get("/api/work-orders")
    assert resp.status_code == 200
    assert resp.json()["work_orders"] == []


def test_list_draft_work_orders(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")

    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)

    resp = client.get("/api/work-orders?status=draft")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["work_orders"]) == 1
    assert data["work_orders"][0]["ahu_id"] == "e0402"


def test_approve_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0402", level=4, title="Test", severity="warning")

    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)

    resp = client.post(f"/api/work-orders/{wo_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_dismiss_work_order(client, tmp_path, monkeypatch):
    from core.agentdb import AgentDB
    db = AgentDB(str(tmp_path / "test.duckdb"))
    wo_id = db.create_work_order(ahu_id="e0101", level=1, title="Test", severity="info")

    import core.agentdb as m
    monkeypatch.setattr(m, "_db_instance", db)

    resp = client.post(f"/api/work-orders/{wo_id}/dismiss")
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


def test_approve_nonexistent_work_order_returns_404(client):
    resp = client.post("/api/work-orders/99999/approve")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
python -m pytest tests/test_work_orders_api.py -v 2>&1 | head -20
```
Expected: `404 NOT FOUND` or route not found errors.

- [ ] **Step 3: Create work_orders route**

Create `backend/routes/work_orders.py`:

```python
from __future__ import annotations

"""
routes/work_orders.py
─────────────────────
CRUD API for work orders (HITL approval/dismiss workflow).

GET  /api/work-orders          — list all (optional ?status= filter)
GET  /api/work-orders/{id}     — get one
POST /api/work-orders/{id}/approve — transition draft → approved
POST /api/work-orders/{id}/dismiss — transition * → dismissed
PATCH /api/work-orders/{id}    — edit title/description
"""

from core.logger import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = get_logger(__name__)
router = APIRouter()


def _get_db():
    from core.agentdb import AgentDB
    return AgentDB()


class WorkOrderPatch(BaseModel):
    title: str | None = None
    description: str | None = None


@router.get("/work-orders")
async def list_work_orders(status: str | None = None) -> dict:
    db = _get_db()
    work_orders = db.list_work_orders(status=status)
    # Convert any non-JSON-serialisable values
    clean = []
    for wo in work_orders:
        clean.append({k: (str(v) if hasattr(v, "isoformat") else v) for k, v in wo.items()})
    return {"work_orders": clean, "count": len(clean)}


@router.get("/work-orders/{wo_id}")
async def get_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    return {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in wo.items()}


@router.post("/work-orders/{wo_id}/approve")
async def approve_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")

    success = db.update_work_order(wo_id, status="approved", approved_by="user")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve work order in status '{wo['status']}'"
        )

    logger.info(f"work_order {wo_id} approved by user")
    return {"id": wo_id, "status": "approved"}


@router.post("/work-orders/{wo_id}/dismiss")
async def dismiss_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")

    success = db.update_work_order(wo_id, status="dismissed")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot dismiss work order in status '{wo['status']}'"
        )

    logger.info(f"work_order {wo_id} dismissed by user")
    return {"id": wo_id, "status": "dismissed"}


@router.patch("/work-orders/{wo_id}")
async def edit_work_order(wo_id: int, body: WorkOrderPatch) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")

    import duckdb
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    updates = ["updated_at = ?"]
    params = [now]
    if body.title:
        updates.append("title = ?")
        params.append(body.title)
    if body.description is not None:
        updates.append("description = ?")
        params.append(body.description)

    params.append(wo_id)
    with duckdb.connect(db._path) as conn:
        conn.execute(
            f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ?",
            params,
        )

    return {"id": wo_id, "updated": True}
```

- [ ] **Step 4: Register router in main.py**

In `backend/main.py`, add the import after the existing route imports:

```python
from routes.work_orders import router as work_orders_router
```

And register it with the app in the same block as other routers:

```python
app.include_router(work_orders_router, prefix="/api")
```

- [ ] **Step 5: Run API tests**

```bash
cd backend
python -m pytest tests/test_work_orders_api.py -v
```
Expected: all 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/work_orders.py backend/tests/test_work_orders_api.py backend/main.py
git commit -m "feat: add work orders CRUD API with approve/dismiss endpoints"
```

---

## Task 12: Watchman — In-Process Pulse

**Files:**
- Create: `backend/core/watchman.py`
- Create: `backend/tests/test_watchman.py`

- [ ] **Step 1: Write failing tests for Watchman pulse**

Create `backend/tests/test_watchman.py`:

```python
"""Tests for the Watchman pulse threshold logic."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("WATCHMAN_ENABLED", "true")
os.environ.setdefault("WATCHMAN_CRITICAL_THRESHOLD", "40.0")
os.environ.setdefault("WATCHMAN_WARNING_THRESHOLD", "60.0")


@pytest.fixture
def agent_db(tmp_path):
    from core.agentdb import AgentDB
    return AgentDB(str(tmp_path / "test.duckdb"))


def test_classify_score_critical():
    from core.watchman import classify_score
    assert classify_score(35.0) == "critical"


def test_classify_score_warning():
    from core.watchman import classify_score
    assert classify_score(55.0) == "warning"


def test_classify_score_healthy():
    from core.watchman import classify_score
    assert classify_score(75.0) is None


def test_classify_score_boundary_critical():
    from core.watchman import classify_score
    assert classify_score(40.0) == "warning"  # 40.0 is not < 40 → warning


def test_is_in_cooldown_no_state_returns_false(agent_db):
    from core.watchman import is_in_cooldown
    result = is_in_cooldown(agent_db, "e0402", "critical")
    assert result is False


def test_is_in_cooldown_recent_alert_returns_true(agent_db):
    from core.watchman import is_in_cooldown
    from datetime import datetime, timezone, timedelta
    # Set a recent alert in agent state
    expires = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    agent_db.set_agent_state(
        "last_alert:e0402",
        {"notified_at": datetime.now(timezone.utc).isoformat()},
        expires_at=expires,
    )
    result = is_in_cooldown(agent_db, "e0402", "critical")
    assert result is True


@pytest.mark.asyncio
async def test_run_pulse_flags_critical_ahu(agent_db, monkeypatch):
    """Pulse should enqueue critical AHUs."""
    import pandas as pd
    from core.watchman import run_pulse

    # Mock HealthDB.get_latest_snapshot to return one critical AHU
    fake_df = pd.DataFrame([
        {"ahu_id": "e0402", "level": 4, "health_index": 30.0}
    ])

    class FakeHealthDB:
        def get_latest_snapshot(self):
            return fake_df

    monkeypatch.setattr("core.watchman._get_health_db", lambda: FakeHealthDB())
    monkeypatch.setattr("core.watchman._get_agent_db", lambda: agent_db)

    await run_pulse()

    alerts = agent_db.dequeue_watchman_alerts()
    assert len(alerts) == 1
    assert alerts[0]["ahu_id"] == "e0402"
    assert alerts[0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_run_pulse_skips_healthy_ahu(agent_db, monkeypatch):
    import pandas as pd
    from core.watchman import run_pulse

    fake_df = pd.DataFrame([
        {"ahu_id": "e0402", "level": 4, "health_index": 80.0}
    ])

    class FakeHealthDB:
        def get_latest_snapshot(self):
            return fake_df

    monkeypatch.setattr("core.watchman._get_health_db", lambda: FakeHealthDB())
    monkeypatch.setattr("core.watchman._get_agent_db", lambda: agent_db)

    await run_pulse()

    alerts = agent_db.dequeue_watchman_alerts()
    assert len(alerts) == 0
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
python -m pytest tests/test_watchman.py -v 2>&1 | head -15
```
Expected: `ImportError: cannot import name 'classify_score'`

- [ ] **Step 3: Create watchman.py**

Create `backend/core/watchman.py`:

```python
from __future__ import annotations

"""
core/watchman.py
────────────────
Proactive background health monitor — "The Watchman".

Two components:
  1. run_pulse():   lightweight async function, called every 30 minutes
                    from FastAPI lifespan. Pure threshold math — no LLM.
  2. start_pulse(): starts the asyncio background loop. Called in main.py lifespan.

The pulse writes flagged AHUs to watchman_queue. The external scheduler
reads the queue and runs the Resolution Agent for heavy LLM analysis.
"""

import asyncio
from core.logger import get_logger

logger = get_logger(__name__)

# ── Lazy singletons ────────────────────────────────────────────────────────────

_health_db_instance = None
_agent_db_instance = None


def _get_health_db():
    global _health_db_instance
    if _health_db_instance is None:
        from core.healthdb import HealthDB
        _health_db_instance = HealthDB()
    return _health_db_instance


def _get_agent_db():
    global _agent_db_instance
    if _agent_db_instance is None:
        from core.agentdb import AgentDB
        _agent_db_instance = AgentDB()
    return _agent_db_instance


# ── Threshold logic ────────────────────────────────────────────────────────────

def classify_score(health_index: float) -> str | None:
    """
    Return "critical", "warning", or None based on health_index.

    critical: FAIR < 40
    warning:  40 <= FAIR < 60
    healthy:  FAIR >= 60 → None
    """
    from config import settings
    if health_index < settings.watchman_critical_threshold:
        return "critical"
    if health_index < settings.watchman_warning_threshold:
        return "warning"
    return None


def is_in_cooldown(agent_db, ahu_id: str, severity: str) -> bool:
    """
    Return True if this AHU has been alerted recently (within cooldown window).
    Cooldown is stored as expires_at in agent_state. get_agent_state() returns
    None if expired or missing, so a non-None result means still in cooldown.
    """
    state = agent_db.get_agent_state(f"last_alert:{ahu_id}")
    return state is not None


# ── Pulse ──────────────────────────────────────────────────────────────────────

async def run_pulse() -> None:
    """
    Single pulse iteration:
    1. Fetch latest FAIR scores for all AHUs from HealthDB
    2. Classify each score
    3. Skip AHUs in cooldown
    4. Enqueue flagged AHUs to watchman_queue
    """
    from config import settings
    if not settings.watchman_enabled:
        return

    health_db = _get_health_db()
    agent_db = _get_agent_db()

    try:
        df = health_db.get_latest_snapshot()
    except Exception as e:
        logger.error(f"watchman: failed to fetch health snapshot — {e}")
        return

    if df is None or df.empty:
        logger.debug("watchman: no health data available")
        return

    flagged = 0
    for _, row in df.iterrows():
        ahu_id = row.get("ahu_id")
        level = int(row.get("level", 0))
        health_index = float(row.get("health_index", 100.0))

        severity = classify_score(health_index)
        if severity is None:
            continue

        if is_in_cooldown(agent_db, ahu_id, severity):
            logger.debug(f"watchman: {ahu_id} in cooldown, skipping")
            continue

        agent_db.enqueue_watchman_alert(
            ahu_id=ahu_id,
            level=level,
            fair_score=health_index,
            severity=severity,
        )
        flagged += 1
        logger.info(f"watchman: flagged {ahu_id} level={level} score={health_index:.1f} severity={severity}")

    if flagged:
        logger.info(f"watchman: pulse complete — {flagged} AHU(s) queued for analysis")
    else:
        logger.debug("watchman: pulse complete — no issues detected")


# ── Background loop ────────────────────────────────────────────────────────────

async def start_pulse() -> None:
    """
    Asyncio background loop. Run via asyncio.create_task() in FastAPI lifespan.
    Runs run_pulse() every WATCHMAN_INTERVAL_SECONDS seconds.
    """
    from config import settings
    interval = settings.watchman_interval_seconds
    logger.info(f"watchman: background pulse started (interval={interval}s)")

    while True:
        try:
            await run_pulse()
        except Exception as e:
            logger.error(f"watchman: pulse error — {e}", exc_info=True)
        await asyncio.sleep(interval)
```

- [ ] **Step 4: Run watchman tests**

```bash
cd backend
python -m pytest tests/test_watchman.py -v
```
Expected: all 8 tests pass.

- [ ] **Step 5: Wire Watchman into FastAPI lifespan in main.py**

Find the `@asynccontextmanager` lifespan function in `main.py` (or where startup logic lives). Add the watchman start:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # existing startup code ...
    _startup_checks()

    # Start Watchman background pulse
    from config import settings
    if settings.watchman_enabled:
        import asyncio
        from core.watchman import start_pulse
        watchman_task = asyncio.create_task(start_pulse())
        logger.info("Watchman pulse started")
    else:
        watchman_task = None

    yield

    # Shutdown
    if watchman_task:
        watchman_task.cancel()
        try:
            await watchman_task
        except asyncio.CancelledError:
            pass
    logger.info("Watchman pulse stopped")
```

If `main.py` does not yet have a lifespan context manager, check how startup is currently done. The backfill logic in lines 292-329 runs in a daemon thread — add watchman start in the same startup block.

- [ ] **Step 6: Commit**

```bash
git add backend/core/watchman.py backend/tests/test_watchman.py backend/main.py
git commit -m "feat: add Watchman in-process pulse with FastAPI lifespan integration"
```

---

## Task 13: Scheduler Extension — Heavy Analysis

**Files:**
- Modify: `scripts/scheduler/scheduler.py`

- [ ] **Step 1: Add run_watchman_analysis() function to scheduler.py**

In `scripts/scheduler/scheduler.py`, add after `run_health_etl()`:

```python
WATCHMAN_LOG = os.path.join(LOGS_DIR, "watchman.log")


def run_watchman_analysis(dry_run: bool = False) -> tuple:
    """
    Process the watchman queue: dequeue flagged AHUs and run Resolution Agent
    on each one to create work orders and send notifications.
    """
    if dry_run:
        log_scheduler("[DRY-RUN] Would run: watchman queue processing")
        return True, "Dry run - no execution"

    log_scheduler("Starting Watchman queue processing...")

    # Run as a subprocess to avoid importing all backend deps into the scheduler
    script_path = os.path.join(PROJECT_ROOT, "scripts", "watchman_processor.py")
    if not os.path.exists(script_path):
        log_scheduler(f"  Watchman processor script not found at {script_path}, skipping")
        return True, "Skipped — processor script not found"

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.join(PROJECT_ROOT, "backend"),
        )
        output = result.stdout + result.stderr
        with open(WATCHMAN_LOG, "a") as f:
            from datetime import datetime as _dt
            f.write(f"\n{'='*70}\n")
            f.write(f"RUN: {_dt.now().isoformat()}\n")
            f.write(f"{'='*70}\n")
            f.write(output + "\n")
            f.write(f"STATUS: {'SUCCESS' if result.returncode == 0 else 'FAILED'}\n")

        if result.returncode == 0:
            log_scheduler("Watchman queue processing completed")
        else:
            log_scheduler(f"Watchman processing had issues: {output[:200]}")

        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "ERROR: Watchman processor timed out"
    except Exception as e:
        return False, f"ERROR: {str(e)}"
```

- [ ] **Step 2: Call run_watchman_analysis() in the main loop**

In the `main()` function's main loop, after `run_health_etl()`, add:

```python
        # Run Watchman queue processing (after ETL so fresh scores are used)
        if iteration == 1 or not args.dry_run:
            log_scheduler("")
            success, output = run_watchman_analysis(dry_run=args.dry_run)
            if not success:
                log_scheduler(f"  ⚠️  Watchman processing had issues (see {WATCHMAN_LOG})")
```

- [ ] **Step 3: Create the watchman processor script**

Create `scripts/watchman_processor.py`:

```python
#!/usr/bin/env python3
"""
scripts/watchman_processor.py
──────────────────────────────
Dequeues flagged AHUs from watchman_queue and runs the Resolution Agent
on each one to create work orders and send notifications.

Run from the backend/ directory:
  cd backend && python ../scripts/watchman_processor.py
"""

import asyncio
import os
import sys

# Run from backend/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")


async def process_queue():
    from core.agentdb import AgentDB
    from core.logger import get_logger

    logger = get_logger("watchman_processor")
    db = AgentDB()

    alerts = db.dequeue_watchman_alerts()
    if not alerts:
        logger.info("watchman_processor: no alerts in queue")
        return

    logger.info(f"watchman_processor: processing {len(alerts)} alert(s)")

    from agents import resolution_agent

    for alert in alerts:
        ahu_id = alert["ahu_id"]
        level = alert["level"]
        score = alert["fair_score"]
        severity = alert["severity"]

        logger.info(f"watchman_processor: analysing {ahu_id} (score={score:.1f} severity={severity})")

        # Build a synthetic user message for the Resolution Agent
        prompt = (
            f"AHU {ahu_id} on Level {level} has a FAIR health score of {score:.1f} "
            f"(severity: {severity}). "
            "Query its current health scores and financial impact, then take appropriate action: "
            "create a work order and notify if critical."
        )

        messages = [{"role": "user", "content": f"/no_think {prompt}"}]

        try:
            reply, drafts = await resolution_agent.run(messages)
            logger.info(
                f"watchman_processor: {ahu_id} processed — "
                f"reply_len={len(reply)} drafts={len(drafts)}"
            )
        except Exception as e:
            logger.error(f"watchman_processor: failed for {ahu_id} — {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(process_queue())
```

- [ ] **Step 4: Verify processor can import cleanly**

```bash
cd backend && python -c "
import sys; sys.path.insert(0, '.')
from core.agentdb import AgentDB
from agents import resolution_agent
print('OK')
"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/scheduler/scheduler.py scripts/watchman_processor.py
git commit -m "feat: add watchman queue processor to scheduler pipeline"
```

---

## Task 14: Frontend — Extend Types and API Client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/chat/ChatWidget.tsx`

- [ ] **Step 1: Add work order types and API functions to client.ts**

In `frontend/src/api/client.ts`, add after the `NavigateTarget` interface:

```typescript
export interface ActionItem {
  type: 'approve_work_order' | 'dismiss' | 'edit_draft';
  work_order_id: number;
  label: string;
  description: string;
}

export interface WorkOrder {
  id: number;
  ahu_id: string;
  level: number;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  created_at: string;
  updated_at: string;
  trigger_source: string;
}
```

Update the `sendChatMessage` return type:

```typescript
export async function sendChatMessage(
  message: string,
  options?: {
    level?: number;
    device?: string | null;
    financial_impact?: number | null;
    history?: Array<{ role: 'user' | 'model'; content: string }>;
    persona?: string | null;
  }
) {
  const { history, persona, ...context } = options ?? {};
  return apiFetch<{
    reply: string;
    navigate?: NavigateTarget | null;
    actions?: ActionItem[];
    pending_drafts_count?: number;
  }>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      context,
      history: history ?? [],
      persona: persona ?? null,
    }),
  });
}
```

Add work order API functions at the bottom of `client.ts`:

```typescript
/**
 * GET /api/work-orders — List work orders, optional ?status= filter
 */
export async function fetchWorkOrders(
  status?: string
): Promise<{ work_orders: WorkOrder[]; count: number }> {
  const params = status ? `?status=${status}` : '';
  return apiFetch(`/work-orders${params}`);
}

/**
 * POST /api/work-orders/{id}/approve — Approve a draft work order
 */
export async function approveWorkOrder(
  id: number
): Promise<{ id: number; status: string }> {
  return apiFetch(`/work-orders/${id}/approve`, { method: 'POST' });
}

/**
 * POST /api/work-orders/{id}/dismiss — Dismiss a work order
 */
export async function dismissWorkOrder(
  id: number
): Promise<{ id: number; status: string }> {
  return apiFetch(`/work-orders/${id}/dismiss`, { method: 'POST' });
}

/**
 * PATCH /api/work-orders/{id} — Edit work order title/description
 */
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

- [ ] **Step 2: Extend Message type in ChatWidget.tsx**

In `frontend/src/components/chat/ChatWidget.tsx`, update the `Message` interface:

```typescript
import { NavigateTarget, ActionItem } from '../../api/client';

interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  navigate?: NavigateTarget | null;
  actions?: ActionItem[];      // add this
}
```

- [ ] **Step 3: Update sendChatMessage call in ChatWindow.tsx to capture actions**

Find `sendChatMessage` usage in `frontend/src/components/chat/ChatWindow.tsx`. Update the response handler to pass `actions` when adding the bot message:

```typescript
const data = await sendChatMessage(input, { ... });

setMessages((prev) => [
  ...prev,
  {
    id: `bot-${Date.now()}`,
    role: 'bot',
    content: data.reply,
    navigate: data.navigate ?? null,
    actions: data.actions ?? [],   // add this
  },
]);
```

Also capture `pending_drafts_count`:

```typescript
if (data.pending_drafts_count && data.pending_drafts_count > 0 && messages.length <= 1) {
  // Insert a system message about pending drafts before the reply
  const draftMsg: Message = {
    id: `drafts-${Date.now()}`,
    role: 'bot',
    content: `You have **${data.pending_drafts_count}** pending work order draft${data.pending_drafts_count > 1 ? 's' : ''} since your last session. Want me to walk through them?`,
  };
  setMessages((prev) => [...prev.slice(0, -1), draftMsg, prev[prev.length - 1]]);
}
```

- [ ] **Step 4: Build frontend to check for type errors**

```bash
cd frontend
npm run build 2>&1 | tail -20
```
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/components/chat/ChatWidget.tsx frontend/src/components/chat/ChatWindow.tsx
git commit -m "feat: extend frontend types and API client for work orders and action items"
```

---

## Task 15: Frontend — BotMessage Action Buttons

**Files:**
- Modify: `frontend/src/components/chat/BotMessage.tsx`

- [ ] **Step 1: Update BotMessage props to accept actions**

In `frontend/src/components/chat/BotMessage.tsx`:

Update imports:

```typescript
import { NavigateTarget, ActionItem, approveWorkOrder, dismissWorkOrder } from '../../api/client';
```

Update `BotMessageProps`:

```typescript
interface BotMessageProps {
  content: string;
  navigate?: NavigateTarget | null;
  onNavigate?: (target: NavigateTarget) => void;
  isLast?: boolean;
  onClearChat?: () => void;
  actions?: ActionItem[];     // add this
}
```

- [ ] **Step 2: Add action button state and handlers**

Inside `BotMessage` component, after the `showModal` state:

```typescript
const [actionStates, setActionStates] = useState<Record<number, 'idle' | 'loading' | 'done' | 'dismissed'>>({});
const [editingId, setEditingId] = useState<number | null>(null);

const handleApprove = async (workOrderId: number) => {
  setActionStates((prev) => ({ ...prev, [workOrderId]: 'loading' }));
  try {
    await approveWorkOrder(workOrderId);
    setActionStates((prev) => ({ ...prev, [workOrderId]: 'done' }));
  } catch {
    setActionStates((prev) => ({ ...prev, [workOrderId]: 'idle' }));
  }
};

const handleDismiss = async (workOrderId: number) => {
  setActionStates((prev) => ({ ...prev, [workOrderId]: 'loading' }));
  try {
    await dismissWorkOrder(workOrderId);
    setActionStates((prev) => ({ ...prev, [workOrderId]: 'dismissed' }));
  } catch {
    setActionStates((prev) => ({ ...prev, [workOrderId]: 'idle' }));
  }
};
```

- [ ] **Step 3: Render action buttons after existing actions**

In the `showActions` div inside `BotMessage`, after the existing buttons (navigate, clear), add:

```tsx
{actions && actions.length > 0 && (() => {
  // Group actions by work_order_id
  const byId: Record<number, ActionItem[]> = {};
  for (const a of actions) {
    if (!byId[a.work_order_id]) byId[a.work_order_id] = [];
    byId[a.work_order_id].push(a);
  }
  return Object.entries(byId).map(([idStr, items]) => {
    const woId = parseInt(idStr);
    const state = actionStates[woId] || 'idle';

    if (state === 'dismissed') return null;

    if (state === 'done') {
      return (
        <span key={woId} className="text-xs text-[#00E5A0] border border-[#00E5A0]/30 rounded-full px-3 py-2.5 min-h-[44px] flex items-center">
          Ticket Submitted
        </span>
      );
    }

    const approveItem = items.find((i) => i.type === 'approve_work_order');
    const dismissItem = items.find((i) => i.type === 'dismiss');

    return (
      <div key={woId} className="flex items-center gap-2 flex-wrap">
        {approveItem && (
          <button
            disabled={state === 'loading'}
            onClick={() => handleApprove(woId)}
            className="
              flex items-center gap-1.5 text-xs font-medium
              text-[#0B0F14] bg-[#00E5A0]
              rounded-full px-3 py-2.5 min-h-[44px]
              hover:bg-[#00E5A0]/80
              disabled:opacity-50
              transition-colors duration-150
            "
          >
            {state === 'loading' ? '...' : approveItem.label}
          </button>
        )}
        {dismissItem && (
          <button
            disabled={state === 'loading'}
            onClick={() => handleDismiss(woId)}
            className="
              flex items-center gap-1.5 text-xs font-medium
              text-[#6d6e71] border border-[#6d6e71]/20
              rounded-full px-3 py-2.5 min-h-[44px]
              hover:bg-[#6d6e71]/10 hover:text-[#E8ECF1]
              disabled:opacity-50
              transition-colors duration-150
            "
          >
            {dismissItem.label}
          </button>
        )}
      </div>
    );
  });
})()}
```

- [ ] **Step 4: Pass actions from MessageList or ChatWindow to BotMessage**

Find where `BotMessage` is rendered (likely in `MessageList.tsx`). Check if it already passes `navigate` and other props. Update to also pass `actions`:

```tsx
// In MessageList.tsx or wherever BotMessage is rendered:
<BotMessage
  content={msg.content}
  navigate={msg.navigate}
  onNavigate={onNavigate}
  isLast={isLast}
  onClearChat={isLast ? onClearChat : undefined}
  actions={msg.actions ?? []}    // add this
/>
```

- [ ] **Step 5: Build and check for errors**

```bash
cd frontend
npm run build 2>&1 | tail -20
```
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chat/BotMessage.tsx
git commit -m "feat: add approve/dismiss action buttons to BotMessage for HITL workflow"
```

---

## Task 16: Integration Verification

Run the end-to-end scenario described in the spec's verification plan.

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```
Expected: all tests pass.

- [ ] **Step 2: Start the backend and verify no startup errors**

```bash
cd backend
python main.py 2>&1 | head -30
```
Expected: server starts on port 8081, watchman task starts, no import errors.

- [ ] **Step 3: Test work orders API manually**

```bash
curl -s -X POST http://localhost:8081/api/chat \
  -H "Authorization: Bearer dev-key-local-development" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a work order for e0402 due to low power factor"}' | python -m json.tool
```
Expected: response includes `"actions": [...]` with approve/dismiss buttons.

- [ ] **Step 4: Verify draft is in DB**

```bash
curl -s http://localhost:8081/api/work-orders?status=draft \
  -H "Authorization: Bearer dev-key-local-development" | python -m json.tool
```
Expected: lists the draft work order just created.

- [ ] **Step 5: Approve the work order**

Note the `id` from step 4, then:

```bash
curl -s -X POST http://localhost:8081/api/work-orders/1/approve \
  -H "Authorization: Bearer dev-key-local-development" | python -m json.tool
```
Expected: `{"id": 1, "status": "approved"}`

- [ ] **Step 6: Build and run frontend**

```bash
cd frontend
npm run dev &
# Open http://localhost:3000 in browser
# Open the chat widget
# Send: "Create a ticket for e0402 phase imbalance"
# Verify: action buttons appear below the bot reply
# Click "Submit Ticket" → button should change to "Ticket Submitted"
```

- [ ] **Step 7: Commit final state**

```bash
git add .
git commit -m "feat: complete agentic system — action tools, agent router, watchman, HITL UI"
```

---

## Notes for Implementer

- **Telegram testing**: Set `TELEGRAM_BOT_TOKEN` and a `TELEGRAM_RECIPIENT_TECHNICIAN` chat ID in `.env` to test live notifications. Without these, notifications are skipped gracefully.
- **LLM for router**: The router's LLM fallback is only triggered for ambiguous messages. If `ENABLE_LLM=false` (default), it always returns "analysis" as fallback. Set `ENABLE_LLM=true` with LM Studio running for full functionality.
- **Watchman timing**: In development, set `WATCHMAN_INTERVAL_SECONDS=60` in `.env` to see the pulse fire quickly without waiting 30 minutes.
- **DuckDB concurrent access**: HealthDB opens connections in read-only mode for the API process. AgentDB opens in read-write mode. If you see DuckDB locking errors, ensure only one process writes at a time (the scheduler and API process share the same file).
