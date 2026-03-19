"""Tests for RAG infrastructure: embedder, vector store, retriever."""
import os
import pytest
import tempfile
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def test_embedder_imports():
    from rag.embedder import Embedder
    assert Embedder is not None


@pytest.mark.asyncio
async def test_embedder_returns_vector():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    from rag.embedder import Embedder
    embedder = Embedder()
    vec = await embedder.embed_document("power factor optimal range 0.95")
    assert isinstance(vec, list)
    assert len(vec) > 100  # gemini-embedding-001 produces 3072-dim vectors


def test_vector_store_add_and_query():
    """VectorStore must persist and retrieve documents by similarity."""
    from rag.vector_store import VectorStore
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(persist_dir=tmpdir, collection_name="test")
        store.add_documents(
            ids=["doc1", "doc2", "doc3"],
            documents=["power factor measures efficiency", "energy import is daily kWh", "voltage unbalance causes motor damage"],
            embeddings=[[0.1]*3072, [0.2]*3072, [0.3]*3072],
        )
        results = store.query_by_embedding(embedding=[0.1]*3072, top_k=1)
        assert len(results) == 1
        assert "power factor" in results[0]


@pytest.mark.asyncio
async def test_retriever_returns_snippets():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    from rag.vector_store import VectorStore
    from rag.retriever import Retriever
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(persist_dir=tmpdir, collection_name="test_retriever")
        store.add_documents(
            ids=["p1"],
            documents=["A power factor below 0.85 indicates reactive power losses."],
            embeddings=[[0.5]*3072],
        )
        retriever = Retriever(vector_store=store)
        snippets = await retriever.retrieve("what is a good power factor", top_k=1)
        assert isinstance(snippets, list)
        assert len(snippets) >= 1
