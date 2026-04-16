from __future__ import annotations

"""
agents/analysis_agent.py
────────────────────────
Analysis Agent — wraps existing query tools for read-only data retrieval.

This is the same logic that was previously inline in routes/chat.py,
extracted into a reusable agent class.
"""

from core.logger import get_logger
from llm.client_factory import get_chat_client
from llm.prompts import build_system_prompt
from tools.tool_registry import QUERY_TOOLS, dispatch_tool

logger = get_logger(__name__)


async def run(
    messages: list[dict],
    persona: str = "general",
) -> str:
    """
    Run the Analysis Agent.

    Args:
        messages: OpenAI-format message list (system excluded — built internally).
        persona:  User persona for system prompt selection.

    Returns:
        Reply text string.
    """
    client = get_chat_client()
    reply = await client.generate_with_tools(
        system_prompt=build_system_prompt(persona),
        messages=messages,
        tools=QUERY_TOOLS,
        tool_dispatcher=dispatch_tool,
    )
    logger.debug("analysis_agent: completed")
    return reply
