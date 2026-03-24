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


@pytest.mark.parametrize("query,expected_metric", [
    ("show phase imbalance for e0101", "current_unbalance"),
    ("voltage unbalance level 3", "volts_unbalance"),
    ("thd l3 for e0101", "current_l3_thd"),
    ("show energy consumption level 5", "energy_import"),
    ("voltage readings e0201", "volts_l_n_avg"),
])
def test_metric_patterns(query, expected_metric):
    from llm.translator import _parse_query_rules
    q, err = _parse_query_rules(query)
    assert err is None
    assert q.metric == expected_metric


def test_health_index_query_does_not_silently_return_power_total():
    """Guard: health index queries should not silently default to power_total.
    This test is a forward-looking stub — update to assert q.query_type == QueryType.health_index
    once Task 5 adds QueryType.health_index.
    """
    from llm.translator import _parse_query_rules
    q, err = _parse_query_rules("show health index for level 3")
    # Until Task 5: either returns an error OR returns something other than power_total
    assert q is None or q.metric != "power_total"


def test_show_level_expands_devices():
    """Existing behaviour — confirm level expansion still works."""
    from llm.translator import _parse_query_rules
    from models.schemas import AHU_LEVEL_CONFIG

    q, err = _parse_query_rules("show level 3 power")
    assert err is None
    assert len(q.device_ids) > 0
    # All devices should match the configured level 3 devices
    expected_level_3_devices = AHU_LEVEL_CONFIG[3]['device_ids']
    assert set(q.device_ids) == set(expected_level_3_devices)


def test_prediction_query_does_not_crash():
    """Before Task 5: prediction queries fall through to time_series gracefully.
    After Task 5 wires QueryType.prediction, update this to assert time_series → prediction.
    """
    from llm.translator import _parse_query_rules
    from models.schemas import QueryType
    q, err = _parse_query_rules("forecast power for e0101 next week")
    # Before Task 5: falls through to time_series (is_prediction computed but not yet routed)
    assert q is not None
    assert q.query_type == QueryType.time_series
