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
    import importlib

    import llm.translator as t
    importlib.reload(t)
    query, error = await t.translate_query("show power for e0101 last week")
    assert error is None
    assert query is not None
    assert query.metric == "power_total"
    assert "e0101" in query.device_ids


@pytest.mark.asyncio
async def test_llm_translation_returns_structured_query():
    """When ENABLE_LLM=true, QwenClient must return a valid StructuredQuery.
    Requires LM Studio running locally — skipped otherwise."""
    import importlib
    import os as _os
    if not _os.getenv("LMS_ENABLED"):
        pytest.skip("LMS_ENABLED not set — LM Studio integration test skipped")
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
    """Health index queries should route to health_index type, not silently return power_total."""
    from llm.translator import _parse_query_rules
    from models.schemas import QueryType
    q, err = _parse_query_rules("show health index for level 3")
    assert err is None
    assert q is not None
    assert q.query_type == QueryType.health_index  # Not power_total garbage


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


def test_prediction_query_detected():
    """Prediction queries should now route to QueryType.prediction."""
    from llm.translator import _parse_query_rules
    from models.schemas import QueryType
    q, err = _parse_query_rules("forecast power for e0101 next week")
    assert err is None
    assert q is not None
    assert q.query_type == QueryType.prediction


def test_health_index_query_detected():
    """Health index queries should route to QueryType.health_index."""
    from llm.translator import _parse_query_rules
    from models.schemas import QueryType
    q, err = _parse_query_rules("show health index for level 3")
    assert err is None
    assert q is not None
    assert q.query_type == QueryType.health_index


def test_metric_plus_level_implies_ranking():
    """'power level 1' should be a ranking query (bar chart of all Level 1 AHUs)."""
    from llm.translator import _parse_query_rules
    from models.schemas import QueryType
    q, err = _parse_query_rules("power level 1")
    assert err is None
    assert q is not None
    assert q.query_type == QueryType.ranking
    assert len(q.device_ids) > 0  # Level 1 devices should be expanded


def test_metric_plus_level_with_time_stays_timeseries():
    """'power level 1 last week' should remain a time_series query."""
    from llm.translator import _parse_query_rules
    from models.schemas import QueryType
    q, err = _parse_query_rules("power level 1 last week")
    assert err is None
    assert q is not None
    assert q.query_type == QueryType.time_series


def test_unrecognised_query_returns_error():
    """Completely unrelated queries should return an error, not silent default data."""
    from llm.translator import _parse_query_rules
    q, err = _parse_query_rules("what is the weather today")
    assert q is None
    assert err is not None
    assert "try asking" in err.lower() or "understand" in err.lower() or "couldn't" in err.lower()


def test_empty_query_returns_error():
    """Empty string should return an error."""
    from llm.translator import _parse_query_rules
    q, err = _parse_query_rules("")
    assert q is None
    assert err is not None
