from __future__ import annotations

"""
agents/resolution_agent.py
──────────────────────────
Resolution Agent — action-focused agent that creates work orders, sends
notifications, and updates issue status.

Returns (reply_text, draft_work_orders) where draft_work_orders is a list
of work order dicts that were created with status="draft" during this run.
These are surfaced to the frontend as approval action buttons.
"""

from core.logger import get_logger
from llm.client_factory import get_chat_client
from tools.tool_registry import ACTION_TOOLS, QUERY_TOOLS, dispatch_tool

logger = get_logger(__name__)

# Resolution agent gets action tools + query_health_scores + search_docs + query_financial_impact for context
_RESOLUTION_TOOLS = [
    t for t in QUERY_TOOLS
    if t["function"]["name"] in ("query_health_scores", "search_docs", "query_financial_impact")
] + ACTION_TOOLS


async def run(
    messages: list[dict],
) -> tuple[str, list[dict]]:
    """
    Run the Resolution Agent.

    Returns:
        (reply_text, draft_work_orders)

        draft_work_orders: list of work order dicts with status="draft",
        created during this run. Used by chat.py to build the `actions`
        field in the API response.
    """
    from agents.prompts import RESOLUTION_SYSTEM_PROMPT

    # Track tool results to find draft work orders created this turn
    tool_results: list[dict] = []

    async def _tracking_dispatcher(name: str, args: dict) -> dict:
        result = await dispatch_tool(name, args)
        if name == "create_work_order":
            tool_results.append(result)
        return result

    client = get_chat_client()
    reply = await client.generate_with_tools(
        system_prompt=RESOLUTION_SYSTEM_PROMPT,
        messages=messages,
        tools=_RESOLUTION_TOOLS,
        tool_dispatcher=_tracking_dispatcher,
        max_tool_rounds=3,
    )

    # Collect draft work orders for HITL
    drafts = [r for r in tool_results if isinstance(r, dict) and r.get("status") == "draft"]
    logger.debug(f"resolution_agent: completed, {len(drafts)} draft(s) created")

    return reply, drafts
