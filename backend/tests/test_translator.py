"""Tests for backend/llm/translator.py — Gemini-backed query translation."""
import os
import pytest
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def test_translate_query_imports():
    from llm.translator import translate_query
    assert callable(translate_query)


@pytest.mark.asyncio
async def test_rule_based_fallback_returns_structured_query(monkeypatch):
    """When ENABLE_LLM=false, rule-based parser must return a valid StructuredQuery."""
    monkeypatch.setenv("ENABLE_LLM", "false")
    import importlib, llm.translator as t
    importlib.reload(t)
    query, error = await t.translate_query("show power for e0101 last week")
    assert error is None
    assert query is not None
    assert query.metric == "power_total"
    assert "e0101" in query.device_ids


@pytest.mark.asyncio
async def test_gemini_translation_returns_structured_query():
    """When ENABLE_LLM=true, Gemini must return a valid StructuredQuery."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    import importlib
    import os as _os
    _os.environ["ENABLE_LLM"] = "true"
    import llm.translator as t
    importlib.reload(t)
    query, error = await t.translate_query("show power total for e0101 last 7 days")
    assert error is None
    assert query is not None
    assert query.query_type is not None
