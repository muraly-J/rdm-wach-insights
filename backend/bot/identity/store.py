from __future__ import annotations

"""
bot/identity/store.py
─────────────────────
DuckDB-backed store for bot users and audit log.

Uses the same DuckDB file as the main AgentDB (healthdb.duckdb).
Tables are isolated — no conflict.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import duckdb
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BotUser:
    """Represents a registered bot user."""
    user_id: str
    telegram_username: str | None
    display_name: str
    role: str  # "technician" | "admin"
    status: str  # "pending" | "active" | "disabled"
    registered_at: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None


# ── Role hierarchy ─────────────────────────────────────────────────────────────

ROLE_HIERARCHY: dict[str, set[str]] = {
    "admin": {"admin", "technician"},  # admin can do everything
    "technician": {"technician"},
}


def role_satisfies(user_role: str, required: str) -> bool:
    """Check if user_role satisfies the required role."""
    return required in ROLE_HIERARCHY.get(user_role, set())


# ── Schema ─────────────────────────────────────────────────────────────────────

_IDENTITY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bot_users (
    user_id           VARCHAR PRIMARY KEY,
    telegram_username VARCHAR,
    display_name      VARCHAR NOT NULL,
    role              VARCHAR NOT NULL,
    status            VARCHAR NOT NULL DEFAULT 'pending',
    registered_at     TIMESTAMPTZ NOT NULL,
    approved_by       VARCHAR,
    approved_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS bot_audit (
    id         INTEGER PRIMARY KEY,
    actor_id   VARCHAR NOT NULL,
    action     VARCHAR NOT NULL,
    ticket_no  VARCHAR,
    details    JSON,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS bot_audit_id_seq START 1;
"""


class IdentityStore:
    """DuckDB-backed store for bot_users and bot_audit tables."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from config import settings
            if settings.app_env != "development":
                db_path = "/tmp/healthdb.duckdb"
            else:
                db_path = str(settings.data_dir / "healthdb.duckdb")
        self._path = db_path
        self._init_tables()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self._path)

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(_IDENTITY_SCHEMA_SQL)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Bot Users ──────────────────────────────────────────────────────────────

    def create_user(
        self,
        user_id: str,
        telegram_username: str | None,
        display_name: str,
        role: str,
    ) -> BotUser:
        """Register a new user with status='pending'."""
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bot_users
                    (user_id, telegram_username, display_name, role, status, registered_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                ON CONFLICT (user_id) DO NOTHING
                """,
                [user_id, telegram_username, display_name, role, now],
            )
        return BotUser(
            user_id=user_id,
            telegram_username=telegram_username,
            display_name=display_name,
            role=role,
            status="pending",
            registered_at=now,
        )

    def get_user(self, user_id: str | int) -> BotUser | None:
        """Get a user by Telegram user_id. Returns None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM bot_users WHERE user_id = ?",
                [str(user_id)],
            ).fetchone()
        if not row:
            return None
        cols = [
            "user_id", "telegram_username", "display_name",
            "role", "status", "registered_at", "approved_by", "approved_at",
        ]
        data = dict(zip(cols, row))  # noqa: B905
        # Convert datetime objects to strings
        for k in ("registered_at", "approved_at"):
            if data[k] and hasattr(data[k], "isoformat"):
                data[k] = data[k].isoformat()
        return BotUser(**data)

    def approve_user(self, user_id: str, approved_by: str) -> bool:
        """Set user status to 'active'. Returns True if user existed."""
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE bot_users
                SET status = 'active', approved_by = ?, approved_at = ?
                WHERE user_id = ? AND status = 'pending'
                """,
                [approved_by, now, str(user_id)],
            )
            # DuckDB doesn't return rowcount easily, so verify
            updated = conn.execute(
                "SELECT status FROM bot_users WHERE user_id = ?",
                [str(user_id)],
            ).fetchone()
        return updated is not None and updated[0] == "active"

    def reject_user(self, user_id: str) -> bool:
        """Set user status to 'disabled'. Returns True if user existed."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE bot_users SET status = 'disabled' WHERE user_id = ? AND status = 'pending'",
                [str(user_id)],
            )
            updated = conn.execute(
                "SELECT status FROM bot_users WHERE user_id = ?",
                [str(user_id)],
            ).fetchone()
        return updated is not None and updated[0] == "disabled"

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate an active user."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE bot_users SET status = 'disabled' WHERE user_id = ?",
                [str(user_id)],
            )
            updated = conn.execute(
                "SELECT status FROM bot_users WHERE user_id = ?",
                [str(user_id)],
            ).fetchone()
        return updated is not None and updated[0] == "disabled"

    def list_users(self, status: str | None = None, role: str | None = None) -> list[BotUser]:
        """List users, optionally filtered by status and/or role."""
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if role:
            conditions.append("role = ?")
            params.append(role)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM bot_users {where} ORDER BY registered_at DESC",
                params,
            ).fetchall()
        cols = [
            "user_id", "telegram_username", "display_name",
            "role", "status", "registered_at", "approved_by", "approved_at",
        ]
        users = []
        for row in rows:
            data = dict(zip(cols, row))  # noqa: B905
            for k in ("registered_at", "approved_at"):
                if data[k] and hasattr(data[k], "isoformat"):
                    data[k] = data[k].isoformat()
            users.append(BotUser(**data))
        return users

    def upsert_admin(self, user_id: str, display_name: str = "Admin") -> None:
        """Upsert a user as admin with status='active'. Used for seeding from BOT_ADMIN_IDS."""
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bot_users
                    (user_id, telegram_username, display_name, role, status, registered_at)
                VALUES (?, NULL, ?, 'admin', 'active', ?)
                ON CONFLICT (user_id) DO UPDATE SET
                    role = 'admin',
                    status = 'active'
                """,
                [str(user_id), display_name, now],
            )

    # ── Audit Log ──────────────────────────────────────────────────────────────

    def log_audit(
        self,
        actor_id: str,
        action: str,
        ticket_no: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Write an audit log entry."""
        now = self._now()
        details_json = json.dumps(details) if details else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bot_audit (id, actor_id, action, ticket_no, details, created_at)
                VALUES (nextval('bot_audit_id_seq'), ?, ?, ?, ?, ?)
                """,
                [str(actor_id), action, ticket_no, details_json, now],
            )

    def list_audit(
        self,
        actor_id: str | None = None,
        action: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """List recent audit entries, optionally filtered."""
        conditions: list[str] = []
        params: list[Any] = []
        if actor_id:
            conditions.append("actor_id = ?")
            params.append(str(actor_id))
        if action:
            conditions.append("action = ?")
            params.append(action)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM bot_audit {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
        cols = ["id", "actor_id", "action", "ticket_no", "details", "created_at"]
        results = []
        for row in rows:
            d = dict(zip(cols, row))  # noqa: B905
            if d["details"] and isinstance(d["details"], str):
                d["details"] = json.loads(d["details"])
            if d["created_at"] and hasattr(d["created_at"], "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            results.append(d)
        return results


# ── Module-level singleton ─────────────────────────────────────────────────────

_store_instance: IdentityStore | None = None


def get_store(db_path: str | None = None) -> IdentityStore:
    """Get or create the singleton IdentityStore."""
    global _store_instance
    if _store_instance is None:
        _store_instance = IdentityStore(db_path)
    return _store_instance
