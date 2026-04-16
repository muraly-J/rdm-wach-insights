from __future__ import annotations

"""
agents/router.py
────────────────
Triage router — classifies each user message as "analysis" or "resolution".

Uses a two-step approach:
  1. Deterministic keyword scoring (fast, no LLM cost)
  2. LLM classification (only when step 1 is ambiguous)

Returns "analysis" (→ Analysis Agent) or "resolution" (→ Resolution Agent).
"""

from core.logger import get_logger

logger = get_logger(__name__)

# Keywords that strongly indicate action intent → Resolution Agent
_ACTION_KEYWORDS = {
    "ticket", "work order", "workorder", "notify", "notification", "alert",
    "send", "report", "schedule", "create", "approve", "submit",
    "fix", "resolve", "escalate", "assign", "dispatch", "email",
    "message", "tell", "inform", "contact",
}

# Keywords that strongly indicate query intent → Analysis Agent
_QUERY_KEYWORDS = {
    "show", "what", "why", "compare", "rank", "trend", "how", "explain",
    "which", "list", "get", "display", "tell me", "check", "review",
    "analyse", "analyze", "summarize", "summarise", "describe", "status",
    "health", "score", "level", "floor", "building",
}


def _score_keywords(text: str) -> tuple[int, int]:
    """Return (action_score, query_score) based on keyword hits."""
    lower = text.lower()
    action = sum(1 for kw in _ACTION_KEYWORDS if kw in lower)
    query = sum(1 for kw in _QUERY_KEYWORDS if kw in lower)
    # "tell me" matches both "tell" (action) and "tell me" (query).
    # If "tell me" is present, cancel out the "tell" action hit.
    if "tell me" in lower:
        action = max(0, action - 1)
    return action, query


def classify_intent(
    message: str,
    history: list[dict] | None = None,
) -> str:
    """
    Classify user message intent.

    Args:
        message: Current user message.
        history: Conversation history (list of {role, content} dicts). Used for
                 context in LLM fallback, not for deterministic scoring.

    Returns:
        "analysis" or "resolution"
    """
    if not message.strip():
        return "analysis"

    action_score, query_score = _score_keywords(message)

    # Clear winner — skip LLM call
    if action_score > 0 and query_score == 0:
        logger.debug(f"router: action_score={action_score} query_score={query_score} → resolution")
        return "resolution"
    if query_score > 0 and action_score == 0:
        logger.debug(f"router: action_score={action_score} query_score={query_score} → analysis")
        return "analysis"
    if action_score > query_score:
        return "resolution"
    if query_score > action_score:
        return "analysis"

    # Ambiguous — fall back to LLM (only if LLM is enabled)
    try:
        return _llm_classify(message, history or [])
    except Exception as e:
        logger.warning(f"router: LLM fallback failed ({e}), defaulting to analysis")
        return "analysis"


def _llm_classify(message: str, history: list[dict]) -> str:
    """
    Use Qwen to classify ambiguous messages.
    Returns "analysis" or "resolution".
    """
    from config import settings
    if not settings.enable_llm:
        return "analysis"

    import asyncio

    from llm.client_factory import get_chat_client

    system_prompt = (
        "Classify the user message. "
        'If the user wants information, analysis, or explanation, output exactly: {"agent": "analysis"}\n'
        'If the user wants an action taken (create ticket, send notification, update status), output exactly: {"agent": "resolution"}\n'
        "Output only the JSON, nothing else."
    )
    user_msg = f"/no_think {message}"

    client = get_chat_client()

    async def _call():
        return await client.generate_text(
            prompt=user_msg,
            system_instruction=system_prompt,
            max_output_tokens=20,
        )

    try:
        loop = asyncio.get_event_loop()
        raw = loop.run_until_complete(_call())
        import json
        import re as re2
        match = re2.search(r'\{[^}]+\}', raw)
        if match:
            parsed = json.loads(match.group())
            result = parsed.get("agent", "analysis")
            if result in ("analysis", "resolution"):
                logger.debug(f"router: LLM classified as {result!r}")
                return result
    except Exception as e:
        logger.warning(f"router: LLM classify parse error: {e}")

    return "analysis"
