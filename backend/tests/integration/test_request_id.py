"""
Integration tests for RequestIDMiddleware.

Tests:
- Every response has an X-Request-ID header
- If client sends X-Request-ID, the same value is echoed back
- If client sends no X-Request-ID, a UUID is generated
"""
import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


class TestRequestIDMiddleware:
    def test_response_always_has_request_id_header(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers or "X-Request-ID" in resp.headers

    def test_provided_request_id_echoed_back(self, client):
        rid = "my-custom-id-123"
        resp = client.get("/health", headers={"X-Request-ID": rid})
        returned = resp.headers.get("x-request-id") or resp.headers.get("X-Request-ID")
        assert returned == rid

    def test_generated_request_id_is_valid_uuid(self, client):
        """When no X-Request-ID is sent, the server generates a UUID."""
        resp = client.get("/health")
        rid = resp.headers.get("x-request-id") or resp.headers.get("X-Request-ID")
        assert rid is not None
        uuid.UUID(rid)  # raises ValueError if not a valid UUID
