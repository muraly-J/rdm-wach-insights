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
    assert "no pending" in text.lower()


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
