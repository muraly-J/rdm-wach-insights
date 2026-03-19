"""
llm/client_factory.py
─────────────────────
Returns the active LLM chat client.

  LLM_BACKEND=qwen    → QwenClient   (default — local Qwen via LM Studio)
  LLM_BACKEND=gemini  → GeminiClient (fallback — requires GEMINI_API_KEY)
"""

import os
import logging

logger = logging.getLogger(__name__)


def get_chat_client():
    """Return the configured LLM client instance."""
    backend = os.getenv("LLM_BACKEND", "qwen").lower()
    logger.info(f"LLM backend: {backend}")
    if backend == "gemini":
        from llm.gemini_client import GeminiClient
        return GeminiClient()
    from llm.qwen_client import QwenClient
    return QwenClient()
