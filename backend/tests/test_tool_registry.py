import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.tool_registry import TOOLS, dispatch_tool


def test_tools_list_has_five_entries():
    assert len(TOOLS) == 5


def test_all_tools_have_required_fields():
    for tool in TOOLS:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]


def test_tool_names_are_correct():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == {
        "query_health_scores",
        "query_live_readings",
        "query_ranking",
        "query_financial_impact",
        "search_docs",
    }


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_error():
    result = await dispatch_tool("nonexistent_tool", {})
    assert "error" in result
    assert "nonexistent_tool" in result["error"]
