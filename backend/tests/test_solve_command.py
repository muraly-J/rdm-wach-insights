import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.asyncio
async def test_solve_returns_rag_suggestion():
    mock_db = MagicMock()
    mock_db.get_work_order_by_ticket_no.return_value = {
        "id": 1,
        "ticket_no": "TCK-001",
        "ahu_id": "e0101",
        "title": "High THD on AHU e0101",
        "description": "Total harmonic distortion exceeded 15% threshold",
        "severity": "Critical",
        "status": "open",
    }
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[
        "THD above 15% indicates harmonic filter degradation. Replace capacitor bank C3."
    ])
    mock_update = MagicMock()
    mock_update.message.text = "/solve TCK-001"
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()

    with patch("bot.handlers.technicians._get_db", return_value=mock_db), \
         patch("bot.handlers.technicians._get_retriever", return_value=mock_retriever):
        from bot.handlers.technicians import solve_handler
        await solve_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    reply = mock_update.message.reply_text.call_args[0][0]
    assert "TCK-001" in reply


@pytest.mark.asyncio
async def test_solve_unknown_ticket():
    mock_db = MagicMock()
    mock_db.get_work_order_by_ticket_no.return_value = None
    mock_update = MagicMock()
    mock_update.message.text = "/solve TCK-999"
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()

    with patch("bot.handlers.technicians._get_db", return_value=mock_db):
        from bot.handlers.technicians import solve_handler
        await solve_handler(mock_update, mock_context)

    reply = mock_update.message.reply_text.call_args[0][0]
    assert "TCK-999" in reply or "not found" in reply.lower()


@pytest.mark.asyncio
async def test_solve_no_ticket_arg():
    mock_update = MagicMock()
    mock_update.message.text = "/solve"
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()

    from bot.handlers.technicians import solve_handler
    await solve_handler(mock_update, mock_context)

    reply = mock_update.message.reply_text.call_args[0][0]
    assert "usage" in reply.lower() or "TCK" in reply
