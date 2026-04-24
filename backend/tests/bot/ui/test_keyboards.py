"""Tests for bot/ui/keyboards.py — inline keyboard factories."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import pytest
from telegram import InlineKeyboardMarkup


# ── Helpers ────────────────────────────────────────────────────────────────────

def _all_buttons(markup: InlineKeyboardMarkup) -> list:
    """Flatten all buttons from an InlineKeyboardMarkup."""
    return [btn for row in markup.inline_keyboard for btn in row]


def _callback_data_set(markup: InlineKeyboardMarkup) -> set[str]:
    return {btn.callback_data for btn in _all_buttons(markup)}


# ── draft_ticket_keyboard ──────────────────────────────────────────────────────

def test_draft_ticket_keyboard_returns_markup():
    from bot.ui.keyboards import draft_ticket_keyboard
    result = draft_ticket_keyboard(42)
    assert isinstance(result, InlineKeyboardMarkup)


def test_draft_ticket_keyboard_has_claim_button():
    from bot.ui.keyboards import draft_ticket_keyboard
    markup = draft_ticket_keyboard(42)
    buttons = _all_buttons(markup)
    assert len(buttons) == 1
    assert buttons[0].callback_data == "claim_ticket:42"
    assert "🙋" in buttons[0].text


# ── claimed_ticket_keyboard ────────────────────────────────────────────────────

def test_claimed_ticket_keyboard_returns_markup():
    from bot.ui.keyboards import claimed_ticket_keyboard
    result = claimed_ticket_keyboard(7)
    assert isinstance(result, InlineKeyboardMarkup)


def test_claimed_ticket_keyboard_has_edit_and_reject():
    from bot.ui.keyboards import claimed_ticket_keyboard
    markup = claimed_ticket_keyboard(7)
    data = _callback_data_set(markup)
    assert "edit_review:7" in data
    assert "reject_ticket:7" in data


# ── review_ticket_keyboard ─────────────────────────────────────────────────────

def test_review_ticket_keyboard_returns_markup():
    from bot.ui.keyboards import review_ticket_keyboard
    result = review_ticket_keyboard(3)
    assert isinstance(result, InlineKeyboardMarkup)


def test_review_ticket_keyboard_has_approve_and_edit():
    from bot.ui.keyboards import review_ticket_keyboard
    markup = review_ticket_keyboard(3)
    data = _callback_data_set(markup)
    assert "approve_ticket:3" in data
    assert "edit_review:3" in data


# ── admin_ticket_keyboard ──────────────────────────────────────────────────────

def test_admin_ticket_keyboard_returns_markup():
    from bot.ui.keyboards import admin_ticket_keyboard
    result = admin_ticket_keyboard(99)
    assert isinstance(result, InlineKeyboardMarkup)


def test_admin_ticket_keyboard_has_priority_buttons():
    from bot.ui.keyboards import admin_ticket_keyboard
    markup = admin_ticket_keyboard(99)
    data = _callback_data_set(markup)
    assert "set_priority:99:high" in data
    assert "set_priority:99:medium" in data
    assert "set_priority:99:low" in data


def test_admin_ticket_keyboard_has_status_buttons():
    from bot.ui.keyboards import admin_ticket_keyboard
    markup = admin_ticket_keyboard(99)
    data = _callback_data_set(markup)
    assert "set_status:99:in_progress" in data
    assert "set_status:99:closed" in data


def test_admin_ticket_keyboard_has_two_rows():
    from bot.ui.keyboards import admin_ticket_keyboard
    markup = admin_ticket_keyboard(99)
    assert len(markup.inline_keyboard) == 2


# ── status_change_keyboard ─────────────────────────────────────────────────────

def test_status_change_keyboard_returns_markup():
    from bot.ui.keyboards import status_change_keyboard
    result = status_change_keyboard(55)
    assert isinstance(result, InlineKeyboardMarkup)


def test_status_change_keyboard_has_approve_and_reject():
    from bot.ui.keyboards import status_change_keyboard
    markup = status_change_keyboard(55)
    data = _callback_data_set(markup)
    assert "approve_change:55" in data
    assert "reject_change:55" in data


# ── reject_confirm_keyboard ────────────────────────────────────────────────────

def test_reject_confirm_keyboard_returns_markup():
    from bot.ui.keyboards import reject_confirm_keyboard
    result = reject_confirm_keyboard(11)
    assert isinstance(result, InlineKeyboardMarkup)


def test_reject_confirm_keyboard_has_confirm_and_cancel():
    from bot.ui.keyboards import reject_confirm_keyboard
    markup = reject_confirm_keyboard(11)
    data = _callback_data_set(markup)
    assert "confirm_reject:11" in data
    assert "cancel_reject:11" in data


# ── wo_id is embedded correctly in all keyboards ───────────────────────────────

@pytest.mark.parametrize("wo_id", [1, 100, 9999])
def test_draft_ticket_keyboard_uses_correct_wo_id(wo_id):
    from bot.ui.keyboards import draft_ticket_keyboard
    markup = draft_ticket_keyboard(wo_id)
    buttons = _all_buttons(markup)
    assert buttons[0].callback_data == f"claim_ticket:{wo_id}"


@pytest.mark.parametrize("req_id", [1, 50, 200])
def test_status_change_keyboard_uses_correct_req_id(req_id):
    from bot.ui.keyboards import status_change_keyboard
    markup = status_change_keyboard(req_id)
    data = _callback_data_set(markup)
    assert f"approve_change:{req_id}" in data
    assert f"reject_change:{req_id}" in data
