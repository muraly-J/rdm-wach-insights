"""
Tests for backend/llm/gemini_client.py

Requires GEMINI_API_KEY env var. Set it in your .env before running.
"""
import os
import pytest

# Load .env so GEMINI_API_KEY is available
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def test_gemini_client_imports():
    """Client module must import without error."""
    from llm.gemini_client import GeminiClient  # noqa: F401
    assert GeminiClient is not None


def test_gemini_client_raises_without_key(monkeypatch):
    """Client must raise ValueError if GEMINI_API_KEY is missing."""
    import importlib, config as cfg
    # Reload config, then remove the key (reload re-reads .env, so remove after)
    importlib.reload(cfg)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        cfg.get_gemini_api_key()


@pytest.mark.asyncio
async def test_generate_text_returns_string():
    """generate_text must return a non-empty string for a trivial prompt."""
    from llm.gemini_client import GeminiClient
    client = GeminiClient()
    result = await client.generate_text("Reply with exactly: OK")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_embed_text_returns_vector():
    """embed_text must return a list of floats."""
    from llm.gemini_client import GeminiClient
    client = GeminiClient()
    vector = await client.embed_text("AHU power factor test")
    assert isinstance(vector, list)
    assert len(vector) > 0
    assert isinstance(vector[0], float)
