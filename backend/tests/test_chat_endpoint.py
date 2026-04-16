"""Tests for the AI-powered POST /api/chat endpoint."""
import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Load env files in priority order (backend-local first, then repo root)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Resolve the actual API key the server will use (mirrors main.py get_api_key())
_API_KEY = os.getenv("API_KEY") or os.getenv("DEV_API_KEY", "dev-key-change-in-production")
_AUTH_HEADERS = {"Authorization": f"Bearer {_API_KEY}"}


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_llm_client():
    """Patch the analysis agent's LLM client to return a canned reply without hitting LM Studio."""
    mock = AsyncMock()
    mock.generate_with_tools = AsyncMock(return_value="Mocked LLM reply.")
    with patch("agents.analysis_agent.get_chat_client", return_value=mock):
        yield mock


def test_chat_returns_reply_field(client, mock_llm_client):
    """Chat endpoint must return JSON with a 'reply' key."""
    resp = client.post(
        "/api/chat",
        json={"message": "hello"},
        headers=_AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert "reply" in resp.json()
    assert isinstance(resp.json()["reply"], str)
    assert len(resp.json()["reply"]) > 0


def test_chat_accepts_history(client, mock_llm_client):
    """Chat endpoint must accept a history array without errors."""
    payload = {
        "message": "What does that mean?",
        "history": [
            {"role": "user", "content": "What is power factor?"},
            {"role": "model", "content": "Power factor measures efficiency."},
        ],
    }
    resp = client.post(
        "/api/chat",
        json=payload,
        headers=_AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert "reply" in resp.json()


def test_chat_empty_message_rejected(client):
    """Chat endpoint must reject blank messages."""
    resp = client.post(
        "/api/chat",
        json={"message": ""},
        headers=_AUTH_HEADERS,
    )
    assert resp.status_code == 422


def test_chat_accepts_context(client, mock_llm_client):
    """Chat endpoint must accept optional context without errors."""
    payload = {"message": "How is this level doing?", "context": {"level": 3}}
    resp = client.post(
        "/api/chat",
        json=payload,
        headers=_AUTH_HEADERS,
    )
    assert resp.status_code == 200


def test_chat_llm_unavailable_returns_503(client):
    """Chat endpoint must return 503 when the agent raises an exception."""
    from llm.circuit_breaker import LLMUnavailableError

    with patch("agents.analysis_agent.run", new=AsyncMock(side_effect=LLMUnavailableError("breaker open"))):
        resp = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers=_AUTH_HEADERS,
        )
    assert resp.status_code == 503
    assert "AI service unavailable" in resp.json()["detail"]
