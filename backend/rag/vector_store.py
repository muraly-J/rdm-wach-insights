from __future__ import annotations

"""
rag/vector_store.py
───────────────────
ChromaDB wrapper. Stores and queries document embeddings.
"""


import chromadb
from chromadb.config import Settings


class VectorStore:
    """Persistent ChromaDB-backed vector store."""

    def __init__(self, persist_dir: str, collection_name: str = "wach_docs"):
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "l2"},
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """Add or update documents in the collection."""
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas if metadatas else None,
        )

    def query_by_embedding(
        self, embedding: list[float], top_k: int = 3
    ) -> list[str]:
        """Find the top-k most similar documents."""
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents"],
        )
        docs = results.get("documents", [[]])[0]
        return docs

    @property
    def count(self) -> int:
        return self._collection.count()
