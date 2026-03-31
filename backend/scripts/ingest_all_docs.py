"""
scripts/ingest_all_docs.py
──────────────────────────
Batch-ingest all markdown files in data/rag_docs/ into ChromaDB.
Safe to re-run — hash-based dedup in rag/ingest.py skips already-indexed chunks.

Usage (from backend/):
    python -m scripts.ingest_all_docs
    python -m scripts.ingest_all_docs --persist-dir data/chroma --collection wach_docs
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def ingest_all(persist_dir: str, collection: str) -> None:
    from rag.ingest import ingest

    docs_dir = Path(__file__).parent.parent / "data" / "rag_docs"
    files = sorted(docs_dir.glob("*.md"))
    if not files:
        print(f"[ingest_all] No .md files found in {docs_dir}")
        sys.exit(1)

    total = 0
    for f in files:
        print(f"\n[ingest_all] Processing {f.name}...")
        try:
            count = await ingest(str(f), collection=collection, persist_dir=persist_dir)
            total += count
            print(f"[ingest_all] {f.name}: {count} chunks")
        except Exception as e:
            print(f"[ingest_all] ERROR on {f.name}: {e}")

    print(f"\n[ingest_all] Done. Total chunks ingested: {total}")
    if total < 50:
        print("[ingest_all] WARNING: fewer than 50 chunks — check documents exist and are non-empty")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest all RAG docs into ChromaDB")
    parser.add_argument("--persist-dir", default="data/chroma")
    parser.add_argument("--collection", default="wach_docs")
    args = parser.parse_args()
    asyncio.run(ingest_all(args.persist_dir, args.collection))
