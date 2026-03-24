"""
llm/translator.py
─────────────────
Converts natural language → validated StructuredQuery using Gemini.

Flow:
  1. Send user query + system prompt to Gemini
  2. Parse the JSON response
  3. Pass through middleware validator
  4. Return (StructuredQuery | None, error_message | None)

Production notes:
  - LLM is disabled by default for local development
  - Set ENABLE_LLM=true to enable AI translation
  - Queries will use rule-based parsing instead of AI translation when disabled
"""

import os
import json
import re
import logging
from typing import Optional, Union

# Disable LLM by default for local development
# Set ENABLE_LLM=true to enable AI translation via Gemini
LLM_ENABLED = os.getenv("ENABLE_LLM", "false").lower() == "true"

logger = logging.getLogger(__name__)

from llm.prompts import SYSTEM_PROMPT
from middleware.validator import validate_raw_dict
from models.schemas import StructuredQuery, QueryType, AHU_LEVEL_CONFIG, ALLOWED_DEVICES


def _extract_json(text: str) -> Optional[dict]:
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


async def translate_query(user_query: str) -> tuple[Union[StructuredQuery, None], Union[str, None]]:
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

    from llm.gemini_client import GeminiClient
    client = GeminiClient()

    try:
        raw_text = await client.generate_text(
            prompt=user_query,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=256,
        )
    except Exception as e:
        return None, f"Could not reach Gemini API. ({e})"

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
    Rule-based query parser for production (when LLM is disabled).

    Extracts device_id, metric, and time_range from the query using pattern matching.
    Returns a StructuredQuery or an error message.

    This is a fallback when the LLM server is not available in production.
    """
    import re
    from models.schemas import QueryType

    query_lower = user_query.lower().strip()

    # Default device and metric from common patterns
    default_device = None
    default_metric = "power_total"
    default_time_range = "last_7d"

    # Extract device IDs (e0101, e0202, etc.) - match full pattern first
    device_pattern = r'\be\d{4}\b'
    devices = re.findall(device_pattern, query_lower)

    # Extract Level keywords and expand to all device IDs for that level
    # Pattern: "Level X" or "Level 0X" where X is 1-11
    # Capture everything after 'levels?' until 'for' or end of string
    level_pattern = r'levels?\s+(.+?)(?:\bfor\b|$)'
    level_matches = re.findall(level_pattern, query_lower)

    # Convert to zero-padded level (e.g., "1" -> "01", "7" -> "07")
    levels_expanded = []
    for match in level_matches:
        # Extract all level numbers from the captured text
        for level_str in re.findall(r'\b(0?[1-9]|1[01])\b', match):
            level_num = int(level_str)
            if 1 <= level_num <= 11:
                levels_expanded.append(f"{level_num:02d}")
    # Extract metric keywords
    # Order matters! Check more specific patterns first to avoid ambiguous matches.
    # For example, "apparent_power_total" contains both "apparent" and "power",
    # so we must check "apparent power" before just "power".
    # Also, "current_l1_thd" contains both "current" and "thd", so check specific patterns first.
    # NOTE: The current implementation only supports current_l1_thd (not l3) due to keyword matching
    # limitations. For more complex mappings, use the full metric name or LLM translation.
    metric_map = {
        # Full underscore names first (most specific)
        'apparent_power_total':  'apparent_power_total',
        'power_factor_avg':      'power_factor_avg',
        'reactive_power_total':  'reactive_power_total',
        'current_l1_thd':        'current_l1_thd',
        'current_l3_thd':        'current_l3_thd',
        'volts_unbalance':       'volts_unbalance',
        'current_unbalance':     'current_unbalance',
        # Natural-language phrases (multi-word before single-word — order matters for substring matching)
        'phase imbalance':       'current_unbalance',
        'phase unbalance':       'current_unbalance',
        'voltage unbalance':     'volts_unbalance',
        'voltage imbalance':     'volts_unbalance',
        'apparent power':        'apparent_power_total',
        'power factor':          'power_factor_avg',
        'reactive power':        'reactive_power_total',
        'thd l3':                'current_l3_thd',
        'thd l1':                'current_l1_thd',
        'energy consumption':    'energy_import',
        'energy usage':          'energy_import',
        'energy import':         'energy_import',
        # Single keywords (last, least specific)
        'power_total':           'power_total',
        'energy_import':         'energy_import',
        'current_avg':           'current_avg',
        'volts_l_n_avg':         'volts_l_n_avg',
        'voltage':               'volts_l_n_avg',
        'current':               'current_avg',
        'energy':                'energy_import',
        'thd':                   'current_l1_thd',
        'unbalance':             'current_unbalance',
    }

    for keyword, metric in metric_map.items():
        if keyword in query_lower:
            default_metric = metric
            break

    # Extract time range keywords
    if 'today' in query_lower or '24h' in query_lower:
        default_time_range = "last_24h"
    elif 'week' in query_lower or '7d' in query_lower:
        default_time_range = "last_7d"
    elif 'month' in query_lower or '30 days' in query_lower or 'past 30 days' in query_lower or 'last 30d' in query_lower:
        default_time_range = "last_30d"
    elif 'all time' in query_lower or 'entire' in query_lower:
        default_time_range = "all_time"

    # Determine query type
    # Check for ranking keywords - queries that rank/compare devices
    is_ranking = any(word in query_lower for word in [
        'rank', 'top', 'compare', 'worst', 'lowest', 'highest', 
        'devices have', 'comparison', 'comparing'
    ])
    query_type = QueryType.ranking if is_ranking else QueryType.time_series

    # Determine top_n for ranking queries
    # If user asks for "all", "every", or "whole" devices, don't limit
    # If user says "compare" without specifying count, assume they want all devices
    top_n = None
    if is_ranking:
        # Check for "top N" pattern (e.g., "top 5", "top 10")
        top_n_match = re.search(r'top\s+(\d+)', query_lower)
        if top_n_match:
            top_n = int(top_n_match.group(1))
        elif any(word in query_lower for word in ['all', 'every', 'whole']):
            # User wants all devices, no limit
            top_n = None
        elif 'compare' in query_lower and not any(word in query_lower for word in ['top', 'highest', 'lowest', 'best', 'worst']):
            # "Compare" without top/bottom qualifiers means all devices
            top_n = None
        else:
            # Default to 10 for ranking queries (top/bottom N)
            top_n = 10

    # Build structured query
    try:
        device_ids = []  # Initialize to avoid undefined variable error

        # Check if query asks for "all levels" or "across all levels"
        # In that case, device_ids should be empty (meaning ALL devices for ranking)
        if is_ranking:
            has_all_levels = any(phrase in query_lower for phrase in [
                'all levels', 'across all', 'all ahus', 'all devices',
                'every level', 'entire building', 'building-wide'
            ])
            if has_all_levels and not levels_expanded:
                # For ranking queries with "all" language, use empty device_ids to mean ALL devices
                device_ids = []
            elif levels_expanded and not devices:
                # Get all device IDs for the specified level(s) (convert to int keys)
                for level_str in levels_expanded:
                    level_int = int(level_str)
                    if level_int in AHU_LEVEL_CONFIG:
                        device_ids.extend(AHU_LEVEL_CONFIG[level_int]['device_ids'])
                # Remove duplicates (don't limit here - let top_n handle it)
                device_ids = list(dict.fromkeys(device_ids))
        elif levels_expanded and not devices:
            # For non-ranking queries with specific levels
            for level_str in levels_expanded:
                level_int = int(level_str)
                if level_int in AHU_LEVEL_CONFIG:
                    device_ids.extend(AHU_LEVEL_CONFIG[level_int]['device_ids'])
            # Remove duplicates
            device_ids = list(dict.fromkeys(device_ids))

        if not devices and not levels_expanded:
            # Default to first device if no level or specific device mentioned
            devices = ["e0101"]

        # Check if query asks for "all levels" or "across all levels"
        # In that case, device_ids should be empty (meaning ALL devices for ranking)
        if is_ranking and not levels_expanded:
            has_all_levels = any(phrase in query_lower for phrase in [
                'all levels', 'across all', 'all ahus', 'all devices',
                'every level', 'entire building', 'building-wide'
            ])
            if has_all_levels:
                # For ranking queries with "all" language, use empty device_ids to mean ALL devices
                device_ids = []
            else:
                # Combine any level-based device IDs with explicitly mentioned devices
                if levels_expanded and devices:
                    # Both level and specific devices - keep both
                    pass  # Keep as is
                if not device_ids:
                    device_ids = devices if devices else ["e0101"]
        else:
            # Combine any level-based device IDs with explicitly mentioned devices
            if levels_expanded and devices:
                # Both level and specific devices - keep both
                pass  # Keep as is
            if not device_ids:
                device_ids = devices if devices else ["e0101"]

        structured_query = StructuredQuery(
            query_type=query_type,
            device_ids=device_ids,
            metric=default_metric,
            time_range=default_time_range,
            top_n=top_n
        )
        
        return structured_query, None
        
    except Exception as e:
        return None, f"Could not parse query: {user_query}. Error: {e}"
