"""
Integration test fixtures.

Provides a TestClient for the FastAPI app and a mock_translate fixture
that prevents tests from hitting the real Qwen LLM.
"""
import pytest
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer test-key"}


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient — starts the app once per module."""
    from main import app
    return TestClient(app)


@pytest.fixture
def auth():
    """Auth header dict for authenticated requests."""
    return AUTH
