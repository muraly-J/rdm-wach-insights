"""
Shared pytest configuration for all backend tests.

Sets sys.path so that `from llm.persona_detector import ...` works when pytest
is run from the repo root with `pytest backend/tests/ -x`.
Sets minimum required env vars so FastAPI app startup does not raise RuntimeError.
"""
import os
import sys

# Add backend/ to path — all tests use bare imports like `from llm.X import Y`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DEV_API_KEY", "test-key")
os.environ.setdefault("INFLUX_URL", "https://localhost:8086")
os.environ.setdefault("INFLUX_TOKEN", "test-token")
os.environ.setdefault("INFLUX_ORG", "test-org")
os.environ.setdefault("INFLUX_BUCKET", "test-bucket")
