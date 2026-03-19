"""
rag/embedder.py
───────────────
Returns the configured text embedder.

  EMBED_BACKEND=qwen    → QwenEmbedder (default — local Qwen3-Embedding-0.6B)
  EMBED_BACKEND=gemini  → GeminiClient embeddings (requires GEMINI_API_KEY)
"""

import os
import logging

logger = logging.getLogger(__name__)


class Embedder:
    """Generates embeddings using the configured backend."""

    def __init__(self):
        backend = os.getenv("EMBED_BACKEND", "qwen").lower()
        logger.info(f"Embedding backend: {backend}")
        if backend == "gemini":
            from llm.gemini_client import GeminiClient
            self._impl = _GeminiEmbedder(GeminiClient())
        else:
            from rag.qwen_embedder import QwenEmbedder
            self._impl = QwenEmbedder()

    async def embed_document(self, text: str) -> list[float]:
        return await self._impl.embed_document(text)

    async def embed_query(self, text: str) -> list[float]:
        return await self._impl.embed_query(text)


class _GeminiEmbedder:
    def __init__(self, client):
        self._client = client

    async def embed_document(self, text: str) -> list[float]:
        return await self._client.embed_text(text, task_type="retrieval_document")

    async def embed_query(self, text: str) -> list[float]:
        return await self._client.embed_text(text, task_type="retrieval_query")
