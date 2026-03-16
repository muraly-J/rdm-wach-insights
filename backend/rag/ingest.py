"""
rag/ingest.py
─────────────
CLI script: chunk PDF/TXT documents → embed → store in ChromaDB.

Usage:
    python -m rag.ingest --file path/to/manual.pdf --collection wach_docs
    python -m rag.ingest --file path/to/notes.txt
"""

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def _extract_text(file_path: Path) -> str:
    """Extract text from PDF or TXT file."""
    if file_path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif file_path.suffix.lower() in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")


async def ingest(
    file_path: str,
    collection: str = "wach_docs",
    persist_dir: str = "data/chroma",
    chunk_size: int = 800,
    overlap: int = 100,
) -> int:
    """Ingest a document into the vector store. Returns number of chunks ingested."""
    os.makedirs(persist_dir, exist_ok=True)

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    print(f"[ingest] Extracting text from {path.name}...")
    raw_text = _extract_text(path)
    chunks = _chunk_text(raw_text, chunk_size, overlap)
    print(f"[ingest] Split into {len(chunks)} chunks.")

    from rag.embedder import Embedder
    from rag.vector_store import VectorStore

    embedder = Embedder()
    store = VectorStore(persist_dir=persist_dir, collection_name=collection)

    ids = []
    embeddings = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{path.name}:{i}:{chunk[:50]}".encode()).hexdigest()
        print(f"[ingest] Embedding chunk {i+1}/{len(chunks)}...")
        vec = await embedder.embed_document(chunk)
        ids.append(chunk_id)
        embeddings.append(vec)
        metadatas.append({"source": path.name, "chunk_index": i})

    store.add_documents(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
    print(f"[ingest] Stored {len(chunks)} chunks in collection '{collection}'.")
    return len(chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into WACH RAG store")
    parser.add_argument("--file", required=True, help="Path to PDF or TXT file")
    parser.add_argument("--collection", default="wach_docs")
    parser.add_argument("--persist-dir", default="data/chroma")
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args()

    count = asyncio.run(ingest(
        file_path=args.file,
        collection=args.collection,
        persist_dir=args.persist_dir,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    ))
    sys.exit(0 if count > 0 else 1)
