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
from typing import Optional, Union
from dotenv import load_dotenv
from openai import OpenAI

from llm.prompts import SYSTEM_PROMPT
from middleware.validator import validate_raw_dict
from models.schemas import StructuredQuery

load_dotenv()

_LMS_BASE_URL = os.getenv("LMS_BASE_URL", "http://localhost:1234/v1")
_LMS_MODEL    = os.getenv("LMS_MODEL", "qwen/qwen3-coder-next")
_LMS_API_KEY  = "lm-studio"   # LM Studio ignores this but the SDK requires something


def _get_client() -> OpenAI:
    return OpenAI(base_url=_LMS_BASE_URL, api_key=_LMS_API_KEY)


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


def translate_query(user_query: str) -> tuple[Union[StructuredQuery, None], Union[str, None]]:
    """
    Main entry point. Converts a natural language string to a validated StructuredQuery.

    Returns:
        (StructuredQuery, None)        — success
        (None, error_message: str)     — failure with user-friendly message
    """
    client = _get_client()

    try:
        response = client.chat.completions.create(
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