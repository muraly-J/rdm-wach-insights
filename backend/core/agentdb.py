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
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_approval", "approved", "dismissed"},
    "pending_approval": {"approved", "dismissed"},
    "approved": {"in_progress", "resolved", "dismissed"},
    "in_progress": {"resolved"},
    "resolved": set(),
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
