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
    assert "F:55" in text
    assert "Composite: 58" in text


def test_format_edit_diff_shows_changes():
    from bot.handlers.engineers import _format_edit_diff
    old_wo = {"title": "Old title", "description": "Old description"}
    text = _format_edit_diff(old_wo, new_title="New title", new_description="New description")
    assert "Old title" in text
    assert "New title" in text


@pytest.mark.asyncio
async def test_group_guard_rejects_non_engineer_chat():
    import os
    from unittest.mock import AsyncMock, MagicMock
    os.environ.setdefault("ENGINEERS_CHAT_ID", "-1002222")
    from bot.handlers.engineers import cmd_review
    update = MagicMock()
    update.effective_chat.id = -9999999  # not engineers group
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["1"]
    await cmd_review(update, context)
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_review_404_error():
    from unittest.mock import AsyncMock, MagicMock, patch

    from bot.api_client import WACHAPIError
    from bot.handlers.engineers import cmd_review

    update = MagicMock()
    update.effective_chat.id = -1002222
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["99"]

    with patch("bot.handlers.engineers._is_engineers_group", return_value=True), \
         patch("bot.handlers.engineers.api_client") as mock_api:
        mock_api.WACHAPIError = WACHAPIError
        mock_api.get_work_order = AsyncMock(side_effect=WACHAPIError(404, "not found"))
        await cmd_review(update, context)

    call_text = update.message.reply_text.call_args[0][0]
    assert "99" in call_text
    assert "not found" in call_text.lower() or "#99" in call_text
