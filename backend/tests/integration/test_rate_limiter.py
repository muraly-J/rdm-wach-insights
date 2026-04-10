"""
Integration tests for the per-IP rate limiter in routes/query.py.

Two tiers of testing:
1. Unit-style: call _check_rate_limit() directly — fast, no HTTP stack.
2. HTTP-layer: monkeypatch RATE_LIMIT=2, fire 3 requests, assert 3rd returns 429.

The HTTP test also mocks translate_query to avoid hitting the LLM for requests
1 and 2 (which must succeed to confirm the limiter only fires on request 3).
"""
import pytest
from collections import defaultdict
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient


AUTH = {"Authorization": "Bearer test-key"}


class TestCheckRateLimitDirect:
    """Tests _check_rate_limit() as a pure function — no HTTP stack."""

    def test_requests_within_limit_do_not_raise(self):
        from middleware.rate_limiter import make_rate_limiter
        check = make_rate_limiter(limit=20, window=60)
        # Fill up to the limit — should not raise
        for _ in range(20):
            check("test-direct-ip")

    def test_request_over_limit_raises_429(self):
        from middleware.rate_limiter import make_rate_limiter
        check = make_rate_limiter(limit=20, window=60)
        for _ in range(20):
            check("test-over-ip")

        with pytest.raises(HTTPException) as exc:
            check("test-over-ip")

        assert exc.value.status_code == 429

    def test_different_ips_have_independent_limits(self):
        from middleware.rate_limiter import make_rate_limiter
        check = make_rate_limiter(limit=20, window=60)
        for _ in range(20):
            check("ip-a")

        # ip-b has its own counter — should not raise
        check("ip-b")


class TestRateLimitHTTP:
    """Tests 429 response over HTTP with rate limit patched to 2."""

    @pytest.fixture
    def client_with_low_limit(self, monkeypatch):
        import routes.query as qmod
        from middleware.rate_limiter import make_rate_limiter
        # Replace _check_rate_limit with a new instance that has limit=2
        monkeypatch.setattr(qmod, "_check_rate_limit", make_rate_limiter(limit=2, window=60))
        from main import app
        return TestClient(app)

    def _make_structured_query(self):
        from models.schemas import StructuredQuery, QueryType
        return StructuredQuery(
            query_type=QueryType.health_index,
            metric="power_total",
            device_ids=[],
            time_range="last_24h",
        )

    def test_third_request_returns_429(self, client_with_low_limit):
        """With RATE_LIMIT=2, the 3rd request to /api/query must return 429."""
        sq = self._make_structured_query()

        with patch("routes.query.translate_query", new=AsyncMock(return_value=(sq, None))):
            r1 = client_with_low_limit.post(
                "/api/query",
                json={"user_query": "show level 1 health"},
                headers=AUTH,
            )
            r2 = client_with_low_limit.post(
                "/api/query",
                json={"user_query": "show level 1 health"},
                headers=AUTH,
            )
            r3 = client_with_low_limit.post(
                "/api/query",
                json={"user_query": "show level 1 health"},
                headers=AUTH,
            )

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        assert "Too many requests" in str(r3.json())
