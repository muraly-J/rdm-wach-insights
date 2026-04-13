"""
Unit tests for StructuredQuery allowlist validation.

Tests validate_query() and validate_raw_dict() from middleware/validator.py.
Uses values from models.schemas to stay in sync with allowlists.

NOTE: StructuredQuery has Pydantic validators that check allowlists at construction time.
This test suite focuses on:
  1. validate_query() — business logic validation (top_n range, device count warnings)
  2. validate_raw_dict() — parsing + validation of untrusted input (LLM output)
"""
import pytest
from middleware.validator import validate_query, validate_raw_dict
from models.schemas import (
    ALLOWED_DEVICES,
    ALLOWED_METRICS,
    ALLOWED_TIME_RANGES,
    QueryType,
    StructuredQuery,
)


def _valid_query(**overrides) -> StructuredQuery:
    """Return a known-valid StructuredQuery, with optional field overrides."""
    defaults = dict(
        query_type=QueryType.time_series,
        metric="power_total",
        device_ids=["e0101"],
        time_range=list(ALLOWED_TIME_RANGES.keys())[0],  # first allowed range
    )
    defaults.update(overrides)
    return StructuredQuery(**defaults)


class TestValidateQuery:
    def test_valid_query_passes(self):
        """A valid time_series query should pass all checks."""
        result = validate_query(_valid_query())
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_ranking_query(self):
        """A valid ranking query with top_n=10 should pass."""
        result = validate_query(_valid_query(
            query_type=QueryType.ranking,
            device_ids=[],
            top_n=10,
        ))
        assert result.is_valid is True
        assert result.errors == []

    def test_ranking_top_n_too_large_fails(self):
        """A ranking query with top_n > 50 should fail."""
        result = validate_query(_valid_query(
            query_type=QueryType.ranking,
            device_ids=[],
            top_n=999,
        ))
        assert result.is_valid is False
        assert any("top_n" in e for e in result.errors)

    def test_ranking_top_n_too_small_fails(self):
        """A ranking query with top_n < 1 should fail."""
        result = validate_query(_valid_query(
            query_type=QueryType.ranking,
            device_ids=[],
            top_n=0,
        ))
        assert result.is_valid is False
        assert any("top_n" in e for e in result.errors)

    def test_ranking_query_without_top_n_warns(self):
        """A ranking query without top_n should have a warning but still be valid."""
        result = validate_query(_valid_query(
            query_type=QueryType.ranking,
            device_ids=[],
            top_n=None,
        ))
        # Should be valid but have a warning
        assert result.is_valid is True
        assert any("top_n" in w for w in result.warnings)

    def test_time_series_with_many_devices_warns(self):
        """A time_series query with >5 devices should warn."""
        result = validate_query(_valid_query(
            device_ids=["e0101", "e0102", "e0103", "e0104", "e0105", "e0106"],
        ))
        # Should be valid but have a warning
        assert result.is_valid is True
        assert any("may be slow" in w for w in result.warnings)


class TestValidateRawDict:
    def test_valid_dict_parses_and_validates(self):
        """A valid raw dict should parse and validate successfully."""
        raw = {
            "query_type": "time_series",
            "metric": "power_total",
            "device_ids": ["e0101"],
            "time_range": "last_24h",
        }
        query, result = validate_raw_dict(raw)
        assert query is not None
        assert result.is_valid is True

    def test_malformed_dict_parsing_fails(self):
        """A dict missing required fields should fail parsing."""
        raw = {"query_type": "time_series"}  # missing metric, device_ids, time_range
        query, result = validate_raw_dict(raw)
        assert query is None
        assert result.is_valid is False
        assert result.errors != []

    def test_invalid_metric_fails_parsing(self):
        """A dict with an invalid metric should fail parsing."""
        raw = {
            "query_type": "time_series",
            "metric": "__evil_metric__",
            "device_ids": ["e0101"],
            "time_range": "last_24h",
        }
        query, result = validate_raw_dict(raw)
        assert query is None
        assert result.is_valid is False
        assert any("metric" in e.lower() for e in result.errors)

    def test_invalid_device_fails_parsing(self):
        """A dict with an invalid device ID should fail parsing."""
        raw = {
            "query_type": "time_series",
            "metric": "power_total",
            "device_ids": ["z9999"],
            "time_range": "last_24h",
        }
        query, result = validate_raw_dict(raw)
        assert query is None
        assert result.is_valid is False
        assert any("device" in e.lower() or "z9999" in e for e in result.errors)

    def test_invalid_time_range_fails_parsing(self):
        """A dict with an invalid time_range should fail parsing."""
        raw = {
            "query_type": "time_series",
            "metric": "power_total",
            "device_ids": ["e0101"],
            "time_range": "last_100d",
        }
        query, result = validate_raw_dict(raw)
        assert query is None
        assert result.is_valid is False
        assert any("time_range" in e.lower() or "last_100d" in e for e in result.errors)
