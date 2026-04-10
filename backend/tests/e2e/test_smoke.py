"""
E2E smoke tests — run against the full FastAPI app via TestClient.

Tests:
1. GET /health — always passes if the app boots
2. GET /api/level/1/health-index — reads from DuckDB; must not 500
3. POST /api/chat — skipped unless QWEN_API_BASE is set (needs a live LLM)

These are boot-level canaries, not comprehensive coverage.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient


AUTH = {"Authorization": "Bearer test-key"}


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def test_health_endpoint_returns_200(client):
    """App is alive — no external dependencies required."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"


@pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") == "true",
    reason="Skipped in CI due to DuckDB connection isolation issues across test modules",
)
def test_health_index_endpoint_does_not_500(client):
    """
    /api/level/1/health-index reads from DuckDB.
    May return 200 or 404 depending on data state — must not crash (5xx).
    Skipped in CI where test isolation can cause DuckDB connection conflicts.
    """
    resp = client.get(
        "/api/level/1/health-index",
        params={"time_range": "24h"},
        headers=AUTH,
    )
    assert resp.status_code < 500, (
        f"health-index returned {resp.status_code}: {resp.text}"
    )


@pytest.mark.skipif(
    not os.getenv("QWEN_API_BASE"),
    reason="QWEN_API_BASE not set — skip LLM-dependent smoke test in CI",
)
def test_chat_returns_reply(client):
    """Full chat round-trip — only runs when a live LLM is configured."""
    resp = client.post(
        "/api/chat",
        json={"message": "What is the health of level 1?"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "reply" in body
    assert isinstance(body["reply"], str)
    assert len(body["reply"]) > 0
