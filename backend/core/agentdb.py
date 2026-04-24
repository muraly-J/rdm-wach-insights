from __future__ import annotations

"""
core/agentdb.py
───────────────
DuckDB-backed Agent State Database.

Stores work orders, agent memory (key-value), and the watchman alert queue.
Follows the same pattern as core/healthdb.py.
"""

import json
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
# Updated for 2-role model: Agent → Technician verify → Admin sets priority/status
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_tech_review", "dismissed"},
    "pending_tech_review": {"open", "dismissed"},
    "open": {"in_progress", "closed"},
    "in_progress": {"resolved", "open"},
    "resolved": {"closed", "open"},
    "closed": set(),
    "dismissed": set(),
}

# Module-level singleton — can be monkeypatched in tests
_db_instance: AgentDB | None = None

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
    approved_by     VARCHAR,
    assigned_to     VARCHAR
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

CREATE TABLE IF NOT EXISTS status_change_requests (
    id              INTEGER PRIMARY KEY,
    ticket_no       VARCHAR NOT NULL,
    work_order_id   INTEGER NOT NULL,
    requested_by    VARCHAR NOT NULL,
    current_status  VARCHAR NOT NULL,
    proposed_status VARCHAR NOT NULL,
    notes           VARCHAR,
    decision        VARCHAR,
    decided_by      VARCHAR,
    decided_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS status_change_seq START 1;
CREATE SEQUENCE IF NOT EXISTS ticket_no_seq START 1;
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
            # Migrations for new ticket columns
            migrations = [
                "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS assigned_to VARCHAR",
                "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS ticket_no VARCHAR",
                "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS category VARCHAR",
                "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS priority VARCHAR DEFAULT 'not_set'",
                "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS claimed_by VARCHAR",
                "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ",
                "ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS attachments JSON",
            ]
            for sql in migrations:
                try:
                    conn.execute(sql)
                except Exception as e:
                    logger.debug(f"_init_tables migration: {e}")

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

    def update_work_order(
        self,
        wo_id: int,
        status: str,
        notes: str | None = None,
        approved_by: str | None = None,
        notified_via: str | None = None,
        assigned_to: str | None = None,
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

    def assign_work_order(self, wo_id: int, assigned_to: str) -> bool:
        """Set assigned_to on an open or in_progress work order without status change."""
        wo = self.get_work_order(wo_id)
        if not wo:
            logger.warning(f"assign_work_order: id={wo_id} not found")
            return False
        if wo["status"] not in ("open", "in_progress"):
            logger.warning(
                f"assign_work_order: cannot assign work order in status '{wo['status']}'"
            )
            return False
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE work_orders SET assigned_to = ?, updated_at = ? WHERE id = ?",
                [assigned_to, now, wo_id],
            )
        return True

    # ── Ticket Number ──────────────────────────────────────────────────────────

    def generate_ticket_no(self) -> str:
        """Generate ever-incrementing TCK-NNN format ticket number."""
        with self._connect() as conn:
            seq = conn.execute("SELECT nextval('ticket_no_seq')").fetchone()[0]
        return f"TCK-{seq:03d}"

    # ── Claim ──────────────────────────────────────────────────────────────────

    def claim_work_order(self, wo_id: int, claimed_by: str) -> bool:
        """
        Atomically claim a work order for investigation. First-come-first-served.
        Returns True if claim succeeded, False if already claimed.
        """
        wo = self.get_work_order(wo_id)
        if not wo:
            return False
        if wo.get("claimed_by"):
            return False  # already claimed
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE work_orders
                SET claimed_by = ?, claimed_at = ?, updated_at = ?
                WHERE id = ? AND claimed_by IS NULL
                """,
                [claimed_by, now, now, wo_id],
            )
            # Verify we won the claim
            row = conn.execute(
                "SELECT claimed_by FROM work_orders WHERE id = ?", [wo_id]
            ).fetchone()
        return row is not None and row[0] == claimed_by

    # ── Edit Fields ────────────────────────────────────────────────────────────

    def edit_work_order_fields(
        self,
        wo_id: int,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        attachments: list[dict] | None = None,
    ) -> bool:
        """Update editable fields on a work order (used by technician review)."""
        wo = self.get_work_order(wo_id)
        if not wo:
            return False
        now = self._now()
        updates = ["updated_at = ?"]
        params: list[Any] = [now]
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if attachments is not None:
            updates.append("attachments = ?")
            params.append(json.dumps(attachments))
        params.append(wo_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ?",
                params,
            )
        return True

    # ── Priority ───────────────────────────────────────────────────────────────

    def set_priority(self, wo_id: int, priority: str) -> bool:
        """Set priority on a work order. Valid values: low, medium, high, not_set."""
        if priority not in ("low", "medium", "high", "not_set"):
            return False
        wo = self.get_work_order(wo_id)
        if not wo:
            return False
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE work_orders SET priority = ?, updated_at = ? WHERE id = ?",
                [priority, now, wo_id],
            )
        return True

    # ── Status Change Requests ─────────────────────────────────────────────────

    def create_status_change_request(
        self,
        ticket_no: str,
        work_order_id: int,
        requested_by: str,
        current_status: str,
        proposed_status: str,
        notes: str | None = None,
    ) -> int:
        """Create a status change request. Returns the request ID."""
        now = self._now()
        with self._connect() as conn:
            result = conn.execute(
                """
                INSERT INTO status_change_requests
                    (id, ticket_no, work_order_id, requested_by,
                     current_status, proposed_status, notes, created_at)
                VALUES (nextval('status_change_seq'), ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [ticket_no, work_order_id, requested_by,
                 current_status, proposed_status, notes, now],
            ).fetchone()
        return result[0]

    def get_status_change_request(self, request_id: int) -> dict | None:
        """Get a status change request by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM status_change_requests WHERE id = ?", [request_id]
            ).fetchone()
        if not row:
            return None
        cols = [
            "id", "ticket_no", "work_order_id", "requested_by",
            "current_status", "proposed_status", "notes",
            "decision", "decided_by", "decided_at", "created_at",
        ]
        d = dict(zip(cols, row))
        for k in ("decided_at", "created_at"):
            if d[k] and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
        return d

    def decide_status_change(
        self, request_id: int, decision: str, decided_by: str
    ) -> bool:
        """Approve or reject a status change request."""
        if decision not in ("approved", "rejected"):
            return False
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE status_change_requests
                SET decision = ?, decided_by = ?, decided_at = ?
                WHERE id = ? AND decision IS NULL
                """,
                [decision, decided_by, now, request_id],
            )
            row = conn.execute(
                "SELECT decision FROM status_change_requests WHERE id = ?",
                [request_id],
            ).fetchone()
        return row is not None and row[0] == decision

    def list_pending_status_changes(self) -> list[dict]:
        """List all pending (undecided) status change requests."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM status_change_requests
                WHERE decision IS NULL
                ORDER BY created_at DESC
                """
            ).fetchall()
        cols = [
            "id", "ticket_no", "work_order_id", "requested_by",
            "current_status", "proposed_status", "notes",
            "decision", "decided_by", "decided_at", "created_at",
        ]
        results = []
        for row in rows:
            d = dict(zip(cols, row))
            for k in ("decided_at", "created_at"):
                if d[k] and hasattr(d[k], "isoformat"):
                    d[k] = d[k].isoformat()
            results.append(d)
        return results

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
            if isinstance(expires_at, str):
                exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            else:
                exp = expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
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
