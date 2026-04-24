"""Tests for bot/ui/cards.py — card text renderers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import pytest

SAMPLE_WO = {
    "id": 12,
    "ahu_id": "e0402",
    "level": 4,
    "title": "Chiller coil overtemperature",
    "description": "FAIR composite dropped below threshold",
    "category": "System Error",
    "status": "open",
    "priority": "medium",
}


# ── draft_card ─────────────────────────────────────────────────────────────────

def test_draft_card_returns_string():
    from bot.ui.cards import draft_card
    result = draft_card("#12", SAMPLE_WO)
    assert isinstance(result, str)


def test_draft_card_contains_ticket_no():
    from bot.ui.cards import draft_card
    result = draft_card("#12", SAMPLE_WO)
    assert "📋 New Draft Ticket — #12" in result


def test_draft_card_contains_subject():
    from bot.ui.cards import draft_card
    result = draft_card("#12", SAMPLE_WO)
    assert "Subject: Chiller coil overtemperature" in result


def test_draft_card_contains_category():
    from bot.ui.cards import draft_card
    result = draft_card("#12", SAMPLE_WO)
    assert "Category: System Error" in result


def test_draft_card_contains_ahu_and_level():
    from bot.ui.cards import draft_card
    result = draft_card("#12", SAMPLE_WO)
    assert "AHU: e0402 · Level 4" in result


def test_draft_card_contains_description():
    from bot.ui.cards import draft_card
    result = draft_card("#12", SAMPLE_WO)
    assert "FAIR composite dropped below threshold" in result


def test_draft_card_contains_agent_creator():
    from bot.ui.cards import draft_card
    result = draft_card("#12", SAMPLE_WO)
    assert "🤖 Agent" in result


def test_draft_card_truncates_description_at_200_chars():
    from bot.ui.cards import draft_card
    long_desc = "B" * 300
    wo = {**SAMPLE_WO, "description": long_desc}
    result = draft_card("#12", wo)
    # 200 'B' characters should be present
    assert "B" * 200 in result
    # 201 should not appear
    assert "B" * 201 not in result


def test_draft_card_handles_none_description():
    from bot.ui.cards import draft_card
    wo = {**SAMPLE_WO, "description": None}
    result = draft_card("#12", wo)
    assert isinstance(result, str)
    assert "🤖 Agent" in result


# ── claimed_card ───────────────────────────────────────────────────────────────

def test_claimed_card_returns_string():
    from bot.ui.cards import claimed_card
    result = claimed_card("#12", SAMPLE_WO, "alice_tech")
    assert isinstance(result, str)


def test_claimed_card_contains_ticket_no():
    from bot.ui.cards import claimed_card
    result = claimed_card("#12", SAMPLE_WO, "alice_tech")
    assert "#12" in result


def test_claimed_card_contains_username():
    from bot.ui.cards import claimed_card
    result = claimed_card("#12", SAMPLE_WO, "alice_tech")
    assert "@alice_tech" in result


def test_claimed_card_contains_subject():
    from bot.ui.cards import claimed_card
    result = claimed_card("#12", SAMPLE_WO, "alice_tech")
    assert "Subject: Chiller coil overtemperature" in result


def test_claimed_card_contains_category():
    from bot.ui.cards import claimed_card
    result = claimed_card("#12", SAMPLE_WO, "alice_tech")
    assert "Category: System Error" in result


# ── approved_ticket_card ───────────────────────────────────────────────────────

def test_approved_ticket_card_returns_string():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert isinstance(result, str)


def test_approved_ticket_card_contains_ticket_header():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert "🎫 New Ticket — #12" in result


def test_approved_ticket_card_contains_subject():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert "Subject: Chiller coil overtemperature" in result


def test_approved_ticket_card_contains_category():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert "Category: System Error" in result


def test_approved_ticket_card_contains_priority_icon():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert "🟡" in result  # medium priority icon


def test_approved_ticket_card_contains_open_status():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert "🟢 Open" in result


def test_approved_ticket_card_contains_ahu_and_level():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert "AHU: e0402 · Level 4" in result


def test_approved_ticket_card_contains_verified_by():
    from bot.ui.cards import approved_ticket_card
    result = approved_ticket_card("#12", SAMPLE_WO, "alice_tech")
    assert "Verified by: @alice_tech (Technician)" in result


@pytest.mark.parametrize("priority,expected_icon", [
    ("high", "🔴"),
    ("medium", "🟡"),
    ("low", "🟢"),
    ("not_set", "⚪"),
])
def test_approved_ticket_card_priority_icons(priority, expected_icon):
    from bot.ui.cards import approved_ticket_card
    wo = {**SAMPLE_WO, "priority": priority}
    result = approved_ticket_card("#12", wo, "bob")
    assert expected_icon in result


# ── status_change_card ─────────────────────────────────────────────────────────

def test_status_change_card_returns_string():
    from bot.ui.cards import status_change_card
    result = status_change_card("#12", SAMPLE_WO, "alice_tech", "resolved", None)
    assert isinstance(result, str)


def test_status_change_card_contains_ticket_no():
    from bot.ui.cards import status_change_card
    result = status_change_card("#12", SAMPLE_WO, "alice_tech", "resolved", None)
    assert "📝 Status Change Request — #12" in result


def test_status_change_card_contains_tech_username():
    from bot.ui.cards import status_change_card
    result = status_change_card("#12", SAMPLE_WO, "alice_tech", "resolved", None)
    assert "@alice_tech" in result
    assert "(Technician)" in result


def test_status_change_card_contains_current_status():
    from bot.ui.cards import status_change_card
    result = status_change_card("#12", SAMPLE_WO, "alice_tech", "resolved", None)
    assert "Current:" in result
    assert "Open" in result  # "open" title-cased


def test_status_change_card_contains_proposed_status():
    from bot.ui.cards import status_change_card
    result = status_change_card("#12", SAMPLE_WO, "alice_tech", "resolved", None)
    assert "Proposed:" in result
    assert "Resolved" in result


def test_status_change_card_includes_notes_when_provided():
    from bot.ui.cards import status_change_card
    result = status_change_card("#12", SAMPLE_WO, "alice_tech", "resolved", "Fixed the fan belt.")
    assert "Fixed the fan belt." in result


def test_status_change_card_omits_notes_when_none():
    from bot.ui.cards import status_change_card
    result = status_change_card("#12", SAMPLE_WO, "alice_tech", "resolved", None)
    assert "Note:" not in result


# ── PRIORITY_ICONS and STATUS_ICONS exports ────────────────────────────────────

def test_priority_icons_dict_has_expected_keys():
    from bot.ui.cards import PRIORITY_ICONS
    assert "high" in PRIORITY_ICONS
    assert "medium" in PRIORITY_ICONS
    assert "low" in PRIORITY_ICONS
    assert "not_set" in PRIORITY_ICONS


def test_status_icons_dict_has_expected_keys():
    from bot.ui.cards import STATUS_ICONS
    for status in ("draft", "pending_tech_review", "open", "in_progress", "resolved", "closed", "dismissed"):
        assert status in STATUS_ICONS
