"""
Integration tests for the /metrics Prometheus endpoint.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type_is_prometheus(self, client):
        resp = client.get("/metrics")
        # Prometheus text format uses text/plain; OpenMetrics uses application/openmetrics-text
        assert "text/plain" in resp.headers.get("content-type", "") or \
               "openmetrics" in resp.headers.get("content-type", "")

    def test_metrics_contains_http_requests_counter(self, client):
        # Make one request to generate a data point
        client.get("/health")
        resp = client.get("/metrics")
        # prometheus_fastapi_instrumentator emits http_requests
        assert "http_requests" in resp.text

    def test_metrics_does_not_require_auth(self, client):
        """Metrics endpoint must be publicly accessible for Prometheus scraping."""
        resp = client.get("/metrics")  # no Authorization header
        assert resp.status_code == 200
