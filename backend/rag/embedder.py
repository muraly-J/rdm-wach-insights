"""
rag/embedder.py
───────────────
Text embedder using local Qwen3-Embedding-0.6B via sentence-transformers.
"""

from rag.qwen_embedder import QwenEmbedder


class Embedder:
    """Generates embeddings using QwenEmbedder."""

    def __init__(self):
        self._impl = QwenEmbedder()

    async def embed_document(self, text: str) -> list[float]:
        return await self._impl.embed_document(text)

    async def embed_query(self, text: str) -> list[float]:
        return await self._impl.embed_query(text)
