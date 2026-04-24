"""
Tests for bot/identity/store.py — IdentityStore (DuckDB-backed).

Each test gets a fresh IdentityStore backed by a temp file so all
`_connect()` calls within the same test share the same DuckDB database.
The temp file is deleted after each test.
"""

from __future__ import annotations

import os
import sys

# Ensure backend/ is on the path for bare imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import pytest

from bot.identity.store import BotUser, IdentityStore, role_satisfies


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def store(tmp_path) -> IdentityStore:
    """Fresh IdentityStore backed by a temp DuckDB file for each test."""
    db_file = str(tmp_path / "test_identity.duckdb")
    return IdentityStore(db_path=db_file)


# ── Tests: CRUD ───────────────────────────────────────────────────────────────


def test_create_and_get_user(store: IdentityStore) -> None:
    """Insert a user, retrieve by ID, verify all fields round-trip correctly."""
    created = store.create_user(
        user_id="111",
        telegram_username="alice",
        display_name="Alice Smith",
        role="technician",
    )

    assert created.user_id == "111"
    assert created.telegram_username == "alice"
    assert created.display_name == "Alice Smith"
    assert created.role == "technician"
    assert created.status == "pending"
    assert created.registered_at is not None

    fetched = store.get_user("111")
    assert fetched is not None
    assert fetched.user_id == "111"
    assert fetched.telegram_username == "alice"
    assert fetched.display_name == "Alice Smith"
    assert fetched.role == "technician"
    assert fetched.status == "pending"
    assert fetched.registered_at is not None
    assert fetched.approved_by is None


def test_get_user_not_found(store: IdentityStore) -> None:
    """get_user returns None for an unknown user_id."""
    assert store.get_user("999999") is None


def test_get_user_accepts_int_id(store: IdentityStore) -> None:
    """get_user coerces integer IDs to strings correctly."""
    store.create_user(
        user_id="222",
        telegram_username="bob",
        display_name="Bob Jones",
        role="admin",
    )
    fetched = store.get_user(222)  # integer, not string
    assert fetched is not None
    assert fetched.user_id == "222"


# ── Tests: upsert_admin ────────────────────────────────────────────────────────


def test_upsert_admin_creates_active_admin(store: IdentityStore) -> None:
    """upsert_admin creates an active admin user when not present."""
    store.upsert_admin(user_id="333", display_name="Super Admin")

    user = store.get_user("333")
    assert user is not None
    assert user.role == "admin"
    assert user.status == "active"
    assert user.display_name == "Super Admin"


def test_upsert_admin_idempotent(store: IdentityStore) -> None:
    """Calling upsert_admin twice for the same user_id does not error."""
    store.upsert_admin(user_id="444", display_name="Admin One")
    store.upsert_admin(user_id="444", display_name="Admin One")  # second call must not raise

    user = store.get_user("444")
    assert user is not None
    assert user.role == "admin"
    assert user.status == "active"


def test_upsert_admin_promotes_existing_user(store: IdentityStore) -> None:
    """upsert_admin upgrades a pending technician to active admin."""
    store.create_user(
        user_id="555",
        telegram_username="charlie",
        display_name="Charlie",
        role="technician",
    )
    store.upsert_admin(user_id="555", display_name="Charlie")

    user = store.get_user("555")
    assert user is not None
    assert user.role == "admin"
    assert user.status == "active"


# ── Tests: approve / disable ───────────────────────────────────────────────────


def test_approve_user(store: IdentityStore) -> None:
    """Approving a pending user sets status='active' and records approved_by."""
    store.create_user(
        user_id="666",
        telegram_username="dana",
        display_name="Dana Lee",
        role="technician",
    )

    result = store.approve_user("666", approved_by="admin_001")
    assert result is True

    user = store.get_user("666")
    assert user is not None
    assert user.status == "active"
    assert user.approved_by == "admin_001"
    assert user.approved_at is not None


def test_approve_nonexistent_user(store: IdentityStore) -> None:
    """Approving a user that doesn't exist returns False."""
    result = store.approve_user("no_such_user", approved_by="admin_001")
    assert result is False


def test_disable_user(store: IdentityStore) -> None:
    """deactivate_user sets status to 'disabled' for an active user."""
    store.create_user(
        user_id="777",
        telegram_username="evan",
        display_name="Evan Park",
        role="technician",
    )
    # Approve first so we have an active user
    store.approve_user("777", approved_by="admin_001")

    result = store.deactivate_user("777")
    assert result is True

    user = store.get_user("777")
    assert user is not None
    assert user.status == "disabled"


def test_reject_user(store: IdentityStore) -> None:
    """reject_user sets a pending user's status to 'disabled'."""
    store.create_user(
        user_id="888",
        telegram_username="fiona",
        display_name="Fiona Ray",
        role="technician",
    )

    result = store.reject_user("888")
    assert result is True

    user = store.get_user("888")
    assert user is not None
    assert user.status == "disabled"


# ── Tests: list_pending ────────────────────────────────────────────────────────


def test_list_pending(store: IdentityStore) -> None:
    """list_users(status='pending') returns only pending users."""
    store.create_user("p1", "user_p1", "Pending One", "technician")
    store.create_user("p2", "user_p2", "Pending Two", "admin")
    store.create_user("a1", "user_a1", "Active One", "technician")
    # Approve a1 so it becomes active
    store.approve_user("a1", approved_by="admin_seed")

    pending = store.list_users(status="pending")
    pending_ids = {u.user_id for u in pending}
    assert pending_ids == {"p1", "p2"}


def test_list_pending_empty_when_none(store: IdentityStore) -> None:
    """list_users(status='pending') returns empty list when no pending users."""
    pending = store.list_users(status="pending")
    assert pending == []


def test_list_users_by_role(store: IdentityStore) -> None:
    """list_users(role='admin') filters correctly by role."""
    store.create_user("t1", "tech_1", "Tech One", "technician")
    store.upsert_admin("adm1", "Admin One")

    admins = store.list_users(role="admin")
    assert len(admins) == 1
    assert admins[0].user_id == "adm1"


# ── Tests: audit log ──────────────────────────────────────────────────────────


def test_log_audit_no_error(store: IdentityStore) -> None:
    """log_audit runs without raising an exception."""
    store.log_audit(
        actor_id="999",
        action="register",
        ticket_no=None,
        details={"role": "technician"},
    )


def test_log_audit_retrievable(store: IdentityStore) -> None:
    """Logged audit entries are retrievable via list_audit."""
    store.log_audit(
        actor_id="aaa",
        action="approve_registration",
        ticket_no="TKT-001",
        details={"target_user_id": "bbb"},
    )

    entries = store.list_audit(actor_id="aaa")
    assert len(entries) == 1
    entry = entries[0]
    assert entry["actor_id"] == "aaa"
    assert entry["action"] == "approve_registration"
    assert entry["ticket_no"] == "TKT-001"
    assert entry["details"] == {"target_user_id": "bbb"}


def test_log_audit_multiple_entries(store: IdentityStore) -> None:
    """Multiple audit entries for the same actor all appear in list_audit."""
    for i in range(3):
        store.log_audit(actor_id="multi_actor", action=f"action_{i}")

    entries = store.list_audit(actor_id="multi_actor")
    assert len(entries) == 3


def test_log_audit_filter_by_action(store: IdentityStore) -> None:
    """list_audit filters by action correctly."""
    store.log_audit(actor_id="x1", action="register")
    store.log_audit(actor_id="x2", action="approve_registration")

    entries = store.list_audit(action="register")
    assert len(entries) == 1
    assert entries[0]["action"] == "register"


# ── Tests: role_satisfies ──────────────────────────────────────────────────────


def test_role_satisfies_admin_satisfies_technician() -> None:
    """An admin user satisfies a 'technician' requirement."""
    assert role_satisfies("admin", "technician") is True


def test_role_satisfies_admin_satisfies_admin() -> None:
    """An admin user satisfies an 'admin' requirement."""
    assert role_satisfies("admin", "admin") is True


def test_role_satisfies_technician_satisfies_technician() -> None:
    """A technician user satisfies a 'technician' requirement."""
    assert role_satisfies("technician", "technician") is True


def test_role_satisfies_technician_does_not_satisfy_admin() -> None:
    """A technician user does NOT satisfy an 'admin' requirement."""
    assert role_satisfies("technician", "admin") is False


def test_role_satisfies_unknown_role() -> None:
    """An unrecognised role satisfies nothing."""
    assert role_satisfies("unknown_role", "technician") is False
    assert role_satisfies("unknown_role", "admin") is False
