"""
rag/qwen_embedder.py
────────────────────
Local text embedding using Qwen3-Embedding-0.6B via sentence-transformers.

Model downloads ~300MB to ~/.cache/huggingface/ on first use.
"""

import asyncio

from core.logger import get_logger

logger = get_logger(__name__)

_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
_model = None

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    logger.warning("sentence-transformers not installed — local embeddings unavailable")


def _get_model():
    global _model
    if not _ST_AVAILABLE:
        raise RuntimeError("sentence-transformers is not installed in this environment")
    if _model is None:
        logger.info(f"Loading embedding model {_MODEL_NAME}...")
        _model = SentenceTransformer(_MODEL_NAME, trust_remote_code=True)
        logger.info("Embedding model loaded.")
    return _model


class QwenEmbedder:
    """Generates embeddings using Qwen3-Embedding-0.6B locally."""

    def _embed(self, text: str) -> list[float]:
        vector = _get_model().encode(text, normalize_embeddings=True)
        return vector.tolist()

    async def embed_document(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._embed, text)

    async def embed_query(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._embed, text)
