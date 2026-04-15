from __future__ import annotations

"""
llm/translator.py
─────────────────
Converts natural language → validated StructuredQuery using local Qwen via LM Studio.

Flow:
  1. Send user query + system prompt to QwenClient
  2. Parse the JSON response
  3. Pass through middleware validator
  4. Return (StructuredQuery | None, error_message | None)

Production notes:
  - LLM is disabled by default for local development
  - Set ENABLE_LLM=true to enable AI translation
  - Queries will use rule-based parsing instead of AI translation when disabled
"""

import json
import re
from typing import Union

from config import settings
from core.logger import get_logger
from llm.prompts import SYSTEM_PROMPT
from middleware.validator import validate_raw_dict
from models.schemas import AHU_LEVEL_CONFIG, QueryType, StructuredQuery

# Disable LLM by default for local development
# Set ENABLE_LLM=true to enable AI translation via Gemini
LLM_ENABLED = settings.enable_llm

logger = get_logger(__name__)


def _extract_json(text: str) -> dict | None:
    """
    Robustly extract a JSON object from LLM output.
    Handles: raw JSON, ```json fences, stray text before/after.
    """
    # Strip thinking tags that qwen3 models sometimes emit
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding a bare JSON object anywhere in the text
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


async def translate_query(user_query: str) -> tuple[StructuredQuery | None, str | None]:
    """
    Main entry point. Converts a natural language string to a validated StructuredQuery.

    LLM translation is disabled by default for local development.
    Set ENABLE_LLM=true to enable AI translation via Gemini.

    When LLM is disabled, queries are parsed using rule-based extraction
    from the structured query schemas.

    Returns:
        (StructuredQuery, None)        — success
        (None, error_message: str)     — failure with user-friendly message
    """
    # If LLM is disabled (default for local development), use rule-based parsing
    if not LLM_ENABLED:
        return _parse_query_rules(user_query)

    from llm.client_factory import get_chat_client
    client = get_chat_client()

    try:
        raw_text = await client.generate_text(
            prompt=user_query,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=256,
        )
    except Exception as e:
        return None, f"Could not reach LM Studio. ({e})"

    # Extract JSON from the response
    parsed = _extract_json(raw_text)

    if parsed is None:
        return None, (
            "The AI returned an unexpected response format. Please rephrase your question."
        )

    # Check if the LLM itself returned an error object
    if "error" in parsed:
        return None, parsed["error"]

    # Run through the middleware validator
    query, validation_result = validate_raw_dict(parsed)

    if not validation_result.is_valid:
        return None, validation_result.user_message

    return query, None


def _parse_query_rules(user_query: str) -> tuple[Union[StructuredQuery, None], Union[str, None]]:
    """
    Rule-based query parser (production path when ENABLE_LLM=false).

    Uses resolve_metric() from schemas.py for metric resolution.
    """
    import re
    from models.schemas import QueryType, AHU_LEVEL_CONFIG, resolve_metric

    query_lower = user_query.lower().strip()

    # ── Extract device IDs (e0101, e0202, etc.) ──────────────────────────────
    devices = re.findall(r'\be\d{4}\b', query_lower)

    # ── Extract levels (e.g., "level 3", "level 03") ────────────────────────
    level_pattern = r'levels?\s+(.+?)(?:\bfor\b|$)'
    level_matches = re.findall(level_pattern, query_lower)
    levels_expanded: list[str] = []
    for match in level_matches:
        for level_str in re.findall(r'\b(0?[1-9]|1[01])\b', match):
            level_num = int(level_str)
            if 1 <= level_num <= 11:
                levels_expanded.append(f"{level_num:02d}")

    # ── Resolve metric via registry ──────────────────────────────────────────
    resolved = resolve_metric(query_lower)
    default_metric = resolved if resolved else "power_total"

    # ── Extract time range ───────────────────────────────────────────────────
    if 'today' in query_lower or '24h' in query_lower:
        default_time_range = "last_24h"
    elif 'week' in query_lower or '7d' in query_lower:
        default_time_range = "last_7d"
    elif 'month' in query_lower or '30 days' in query_lower or 'past 30 days' in query_lower or 'last 30d' in query_lower:
        default_time_range = "last_30d"
    elif 'all time' in query_lower or 'entire' in query_lower:
        default_time_range = "all_time"
    else:
        default_time_range = "last_7d"

    # ── Determine query type ─────────────────────────────────────────────────
    is_ranking = any(word in query_lower for word in [
        'rank', 'top', 'compare', 'worst', 'lowest', 'highest',
        'devices have', 'comparison', 'comparing'
    ])

    prediction_keywords = {
        'predict', 'forecast', 'next', 'upcoming', 'future',
        'ahead', 'will', 'tomorrow', 'expect', 'projection', 'estimate', 'spike'
    }
    is_prediction = any(kw in query_lower for kw in prediction_keywords)

    health_index_keywords = {
        'health index', 'health score', 'fair score', 'ahu score',
        'health trend', 'score trend', 'overall health'
    }
    is_health_index = any(kw in query_lower for kw in health_index_keywords)

    if is_health_index:
        query_type = QueryType.health_index
    elif is_prediction:
        query_type = QueryType.prediction
    elif is_ranking:
        query_type = QueryType.ranking
    else:
        query_type = QueryType.time_series

    # ── Auto-upgrade to ranking: metric + level, no devices, no time intent ──
    time_keywords = {
        'today', '24h', 'week', '7d', 'month', '30 days',
        'all time', 'entire', 'trend', 'over time', 'history', 'past'
    }
    has_time_intent = any(kw in query_lower for kw in time_keywords)

    if (
        query_type == QueryType.time_series
        and levels_expanded
        and not devices
        and resolved is not None
        and not has_time_intent
    ):
        query_type = QueryType.ranking

    # ── Determine top_n for ranking ──────────────────────────────────────────
    top_n = None
    if query_type == QueryType.ranking:
        top_n_match = re.search(r'top\s+(\d+)', query_lower)
        if top_n_match:
            top_n = int(top_n_match.group(1))
        elif any(word in query_lower for word in ['all', 'every', 'whole']):
            top_n = None
        elif 'compare' in query_lower and not any(word in query_lower for word in ['top', 'highest', 'lowest', 'best', 'worst']):
            top_n = None
        else:
            top_n = 10

    # ── Confidence gate ──────────────────────────────────────────────────────
    understood_anything = (
        bool(devices)
        or bool(levels_expanded)
        or is_ranking
        or is_prediction
        or is_health_index
        or resolved is not None
    )

    if not understood_anything:
        return None, (
            "I couldn't understand that query. Try asking something like: "
            "'show power for e0101', 'top 10 AHUs by energy level 3', "
            "'forecast power for level 5', or 'health index level 2'."
        )

    # ── Build device_ids ─────────────────────────────────────────────────────
    device_ids: list[str] = []

    # Expand levels to device IDs
    if levels_expanded and not devices:
        for level_str in levels_expanded:
            level_int = int(level_str)
            if level_int in AHU_LEVEL_CONFIG:
                device_ids.extend(AHU_LEVEL_CONFIG[level_int]['device_ids'])
        device_ids = list(dict.fromkeys(device_ids))  # deduplicate

    # Handle "all devices/levels" for ranking
    if query_type == QueryType.ranking:
        has_all_levels = any(phrase in query_lower for phrase in [
            'all levels', 'across all', 'all ahus', 'all devices',
            'every level', 'entire building', 'building-wide'
        ])
        if has_all_levels and not levels_expanded:
            device_ids = []  # empty means "all" for ranking

    # Fall back to explicit device IDs or default
    if not device_ids and not (query_type == QueryType.ranking and not levels_expanded and not devices):
        device_ids = devices if devices else ["e0101"]

    try:
        return StructuredQuery(
            query_type=query_type,
            device_ids=device_ids,
            metric=default_metric,
            time_range=default_time_range,
            top_n=top_n,
        ), None
    except Exception as e:
        return None, f"Could not parse query: {user_query}. Error: {e}"
