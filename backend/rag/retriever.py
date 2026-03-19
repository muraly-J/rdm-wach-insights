"""
rag/retriever.py
────────────────
Combines Embedder + VectorStore for end-to-end similarity retrieval.
"""

from rag.embedder import Embedder
from rag.vector_store import VectorStore


class Retriever:
    """Retrieves relevant document snippets for a user query."""

    def __init__(self, vector_store: VectorStore):
        self._store = vector_store
        self._embedder = Embedder()

    async def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """Embed query and return top-k matching document snippets."""
        if self._store.count == 0:
            return []
        query_vec = await self._embedder.embed_query(query)
        return self._store.query_by_embedding(query_vec, top_k=top_k)
