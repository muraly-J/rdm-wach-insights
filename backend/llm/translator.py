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
"""

import os
import json
import re
import logging
from typing import Optional, Union
from openai import AsyncOpenAI

from backend.llm.prompts import SYSTEM_PROMPT
from backend.middleware.validator import validate_raw_dict
from backend.models.schemas import StructuredQuery
from backend.config import get_lms_base_url, get_lms_model, get_lms_api_key
from backend.core.floor_ward_map import resolve_floor_ids, resolve_ward_ids
from backend.utils.error_handler import handle_llm_error

logger = logging.getLogger(__name__)

_LMS_BASE_URL = get_lms_base_url()
_LMS_MODEL    = get_lms_model()
_LMS_API_KEY  = get_lms_api_key()   # LM Studio ignores this but the SDK requires something


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=_LMS_BASE_URL, api_key=_LMS_API_KEY)


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

    Returns:
        (StructuredQuery, None)        — success
        (None, error_message: str)     — failure with user-friendly message
    """
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
        return handle_llm_error(e)

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

    # Resolve floor/ward names to device IDs if needed
    from backend.core.floor_ward_map import resolve_floor_or_ward
    query.device_ids = resolve_floor_or_ward(user_query, query.device_ids)

    return query, None