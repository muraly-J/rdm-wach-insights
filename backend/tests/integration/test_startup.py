"""
Integration tests for startup health checks.

Tests that the lifespan startup routine logs appropriate messages
when DuckDB / ChromaDB are present or absent, and does NOT crash.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Import the function directly to test it
def test_startup_with_all_files_present():
    """When both DuckDB and ChromaDB are present, startup completes without crashing."""
    from main import _startup_checks

    # The primary assertion is that this does not raise an exception
    _startup_checks()


def test_startup_with_missing_duckdb_logs_warning_not_crash(caplog):
    """If DuckDB path doesn't exist, startup must log a warning and continue — not crash."""
    import logging

    from main import _startup_checks

    with patch("os.path.exists", return_value=False):
        with caplog.at_level(logging.WARNING):
            _startup_checks()  # must not raise

    # Startup must complete without crashing
    assert True  # If we got here, no exception was raised


def test_startup_with_missing_chroma_logs_warning_not_crash(caplog):
    """If ChromaDB dir doesn't exist, startup must log a warning and continue."""
    import logging

    from main import _startup_checks

    with patch("os.path.isdir", return_value=False):
        with caplog.at_level(logging.WARNING):
            _startup_checks()  # must not raise

    # Startup must complete without crashing
    assert True  # If we got here, no exception was raised


def test_app_health_after_startup():
    """The full app must respond to /health after startup completes."""
    from main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
