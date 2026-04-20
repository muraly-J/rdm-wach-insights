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
    assert "F:42" in text


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
    from bot.push import notifier
    mock_instance = AsyncMock()
    with patch.object(notifier, "Bot", return_value=mock_instance):
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
        mock_nm.assert_called_once_with(SAMPLE_WO, token="test-token")
