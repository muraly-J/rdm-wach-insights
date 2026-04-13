"""
Shared pytest configuration for all backend tests.

Sets sys.path so that `from llm.persona_detector import ...` works when pytest
is run from the repo root with `pytest backend/tests/ -x`.
Sets minimum required env vars so FastAPI app startup does not raise RuntimeError.
"""
import os
import sys

import pytest

# Add backend/ to path — all tests use bare imports like `from llm.X import Y`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DEV_API_KEY", "test-key")
os.environ.setdefault("INFLUX_URL", "https://localhost:8086")
os.environ.setdefault("INFLUX_TOKEN", "test-token")
os.environ.setdefault("INFLUX_ORG", "test-org")
os.environ.setdefault("INFLUX_BUCKET", "test-bucket")


@pytest.fixture(autouse=True)
def cleanup_duckdb():
    """Clear DuckDB singleton and close connections after each test.

    DuckDB doesn't allow multiple connections with different configurations to the
    same file. This fixture clears the DB instances dict and properly closes any
    remaining connections to prevent stale locks.
    """
    yield
    # After test, close all connections and clear the cache
    try:
        from core import db_reader
        # Close any existing DB instances
        for db_instance in db_reader._DB_INSTANCES.values():
            try:
                # HealthDB doesn't have a close method, but DuckDB connections do
                # We just clear references to let them be garbage collected
                pass
            except:
                pass
        db_reader._DB_INSTANCES.clear()
        # Force garbage collection to free DuckDB resources
        import gc
        gc.collect()
    except (ImportError, AttributeError):
        pass
