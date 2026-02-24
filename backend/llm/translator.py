"""
llm/translator.py
─────────────────
Converts natural language → validated StructuredQuery using LM Studio.

LM Studio exposes an OpenAI-compatible API at http://localhost:1234/v1,
so we use the openai SDK pointed at the local server.

Flow:
  1. Send user query + system prompt to LM Studio
  2. Parse the JSON response
  3. Pass through middleware validator
  4. Return (StructuredQuery | None, error_message | None)

Production notes:
  - In Vercel, LLM is disabled by default (IN_PRODUCTION env var)
  - Queries will use rule-based parsing instead of AI translation
"""

import os
import json
import re
from typing import Optional, Union

# Detect production environment (Vercel sets VERCEL env var)
IN_PRODUCTION = os.getenv("VERCEL") == "1" or os.getenv("APP_ENV") == "production"

# Disable LLM in production if not explicitly enabled
LLM_ENABLED = os.getenv("ENABLE_LLM", "false").lower() == "true"

if LLM_ENABLED and not IN_PRODUCTION:
    # Only import if in development with LLM enabled
    from openai import AsyncOpenAI

from backend.llm.prompts import SYSTEM_PROMPT
from backend.middleware.validator import validate_raw_dict
from backend.models.schemas import StructuredQuery, QueryType
from backend.config import get_lms_base_url, get_lms_model, get_lms_api_key

_LMS_BASE_URL = None
_LMS_MODEL = None
_LMS_API_KEY = None


def _get_client() -> Optional['AsyncOpenAI']:
    """Get OpenAI client - only available when LLM_ENABLED is True."""
    if not LLM_ENABLED:
        return None
    try:
        from openai import AsyncOpenAI
        return AsyncOpenAI(base_url=_LMS_BASE_URL, api_key=_LMS_API_KEY)
    except ImportError:
        return None


# Configure LLM settings when module loads
if LLM_ENABLED:
    _LMS_BASE_URL = get_lms_base_url()
    _LMS_MODEL = get_lms_model()
    _LMS_API_KEY = get_lms_api_key()


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

    In production (Vercel), LLM translation is disabled by default and queries are parsed
    using rule-based extraction from the structured query schemas.
    
    In development, LLM translation is enabled if ENABLE_LLM=true.

    Returns:
        (StructuredQuery, None)        — success
        (None, error_message: str)     — failure with user-friendly message
    """
    # If LLM is disabled (production mode), try to parse the query using rules
    if not LLM_ENABLED:
        return _parse_query_rules(user_query)

    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model=_LMS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_query},
            ],
            temperature=0.0,     # deterministic — we want consistent JSON
            max_tokens=256,      # JSON output is small; this keeps responses fast
        )
    except Exception as e:
        return None, f"Could not reach the LM Studio server. Is it running? ({e})"

    raw_text = response.choices[0].message.content or ""

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
    from backend.models.schemas import QueryType
    
    query_lower = user_query.lower().strip()
    
    # Default device and metric from common patterns
    default_device = None
    default_metric = "power_total"
    default_time_range = "last_7d"
    
    # Extract device IDs (e0101, e0202, etc.)
    device_pattern = r'\be(0[1-9]|1[0-1])\d{2}\b'
    devices = re.findall(device_pattern, query_lower)
    
    # Convert e01 to e0101 format
    device_ids = []
    for match in devices:
        if len(match) == 2:  # e01 pattern
            for suffix in range(1, 99):
                device_ids.append(f"e{match}{suffix:02d}")
            break  # Only add one device group per query
    
    if not devices:
        # Try to find full eXXXX patterns
        device_pattern = r'\be\d{4}\b'
        devices = re.findall(device_pattern, query_lower)
    
    # Extract metric keywords
    metric_map = {
        'power': 'power_total',
        'energy': 'energy_import', 
        'reactive': 'reactive_power_total',
        'apparent': 'apparent_power_total',
        'current': 'current_avg',
        'voltage': 'volts_l_n_avg',
        'factor': 'power_factor_avg',
        'unbalance': 'current_unbalance',
        'thd': 'current_l1_thd',
    }
    
    for keyword, metric in metric_map.items():
        if keyword in query_lower:
            default_metric = metric
            break
    
    # Extract time range keywords
    if 'today' in query_lower or '24' in query_lower:
        default_time_range = "last_24h"
    elif 'week' in query_lower or '7 day' in query_lower:
        default_time_range = "last_7d"
    elif 'month' in query_lower or '30 day' in query_lower:
        default_time_range = "last_30d"
    elif 'all time' in query_lower or 'entire' in query_lower:
        default_time_range = "all_time"
    
    # Determine query type
    is_ranking = any(word in query_lower for word in ['rank', 'top', 'compare'])
    query_type = QueryType.ranking if is_ranking else QueryType.time_series
    
    # Build structured query
    try:
        device_ids = devices if devices else ["e0101"]  # Default to first device
        if len(device_ids) > 50:
            device_ids = device_ids[:50]
            
        structured_query = StructuredQuery(
            query_type=query_type,
            device_ids=device_ids,
            metric=default_metric,
            time_range=default_time_range,
            top_n=10 if is_ranking else None
        )
        
        return structured_query, None
        
    except Exception as e:
        return None, f"Could not parse query: {user_query}. Error: {e}"