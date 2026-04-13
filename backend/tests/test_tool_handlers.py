import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.asyncio
async def test_query_health_scores_returns_dict():
    """handle_query_health_scores returns a dict with a 'rows' key."""
    mock_db = MagicMock()
    mock_db.get_latest_snapshot.return_value = pd.DataFrame([{
        "ahu_id": "e0101", "level": 1, "health_index": 85.0,
        "tier": "Healthy", "timestamp": pd.Timestamp("2026-03-27", tz="UTC"),
    }])

    with patch("tools.health_tools._get_db", return_value=mock_db):
        from tools.health_tools import handle_query_health_scores
        result = await handle_query_health_scores(level=1)

    assert "rows" in result
    assert isinstance(result["rows"], list)
    assert result["rows"][0]["ahu_id"] == "e0101"


@pytest.mark.asyncio
async def test_query_ranking_returns_dict():
    """handle_query_ranking returns a dict with a 'ranking' key."""
    mock_db = MagicMock()
    mock_db.get_ranking.return_value = pd.DataFrame([
        {"ahu_id": "e0102", "level": 1, "health_index": 58.0,
         "timestamp": pd.Timestamp("2026-03-27", tz="UTC")},
        {"ahu_id": "e0101", "level": 1, "health_index": 83.0,
         "timestamp": pd.Timestamp("2026-03-27", tz="UTC")},
    ])

    with patch("tools.health_tools._get_db", return_value=mock_db):
        from tools.health_tools import handle_query_ranking
        result = await handle_query_ranking(level=1, metric="health_index")

    assert "ranking" in result
    assert result["ranking"][0]["ahu_id"] == "e0102"


@pytest.mark.asyncio
async def test_search_docs_returns_dict():
    """handle_search_docs returns a dict with a 'documents' key."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=["Doc chunk 1", "Doc chunk 2"])

    with patch("tools.health_tools._get_retriever", return_value=mock_retriever):
        from tools.health_tools import handle_search_docs
        result = await handle_search_docs(query="what causes high THD")

    assert "documents" in result
    assert len(result["documents"]) == 2


@pytest.mark.asyncio
async def test_search_docs_no_retriever_returns_empty():
    """handle_search_docs returns empty list when RAG not configured."""
    with patch("tools.health_tools._get_retriever", return_value=None):
        from tools.health_tools import handle_search_docs
        result = await handle_search_docs(query="any query")

    assert result == {"documents": [], "note": "No documents indexed in RAG."}
