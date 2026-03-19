"""
rag/embedder.py
───────────────
Wraps GeminiClient.embed_text for RAG document and query embedding.
"""

from llm.gemini_client import GeminiClient


class Embedder:
    """Generates embeddings using the configured Gemini embedding model."""

    def __init__(self):
        self._client = GeminiClient()

    async def embed_document(self, text: str) -> list[float]:
        """Embed a document chunk for storage."""
        return await self._client.embed_text(text, task_type="retrieval_document")

    async def embed_query(self, text: str) -> list[float]:
        """Embed a user query for similarity search."""
        return await self._client.embed_text(text, task_type="retrieval_query")
