import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.tool_registry import TOOLS, dispatch_tool


def test_tools_list_has_six_entries():
    # Updated: 6 query tools + 3 action tools = 9
    assert len(TOOLS) == 9


def test_all_tools_have_required_fields():
    for tool in TOOLS:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]


def test_tool_names_are_correct():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == {
        "query_building_summary",
        "query_health_scores",
        "query_live_readings",
        "query_ranking",
        "query_financial_impact",
        "search_docs",
        "create_work_order",
        "send_notification",
        "update_work_order",
    }


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_error():
    result = await dispatch_tool("nonexistent_tool", {})
    assert "error" in result
    assert "nonexistent_tool" in result["error"]
