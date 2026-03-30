"""
tools/health_tools.py
─────────────────────
Handler implementations for the five chat tools.

Each handler is called by dispatch_tool() in tool_registry.py.
Handlers receive keyword arguments matching the tool's parameter schema.
Each returns a plain Python dict serialisable to JSON.
"""
import logging
from typing import Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


# ── Lazy singletons ────────────────────────────────────────────────────────────

_db_instance = None
_retriever_instance = None


def _get_db():
    """Return the shared HealthDB instance (read-only for API process)."""
    global _db_instance
    if _db_instance is None:
        from core.healthdb import HealthDB
        _db_instance = HealthDB()
    return _db_instance


def _get_retriever():
    """Return the RAG retriever, or None if ChromaDB not configured."""
    global _retriever_instance
    if _retriever_instance is None:
        try:
            import os
            from rag.vector_store import VectorStore
            from rag.retriever import Retriever
            chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
            collection = os.getenv("RAG_COLLECTION", "wach_docs")
            store = VectorStore(persist_dir=chroma_dir, collection_name=collection)
            if store.count == 0:
                return None
            _retriever_instance = Retriever(vector_store=store)
        except Exception:
            return None
    return _retriever_instance


# ── Helpers ────────────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to JSON-serialisable list of dicts."""
    return df.where(pd.notna(df), None).to_dict(orient="records")


# ── Handlers ───────────────────────────────────────────────────────────────────

async def handle_query_health_scores(
    ahu_ids: Optional[list] = None,
    level: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    metrics: Optional[list] = None,
) -> dict:
    """
    Query FAIR health scores from DuckDB.
    Returns latest snapshot when no time range given; time-series otherwise.
    """
    db = _get_db()
    if start or end:
        df = db.get_time_range(ahu_ids=ahu_ids, level=level, start=start, end=end, metrics=metrics)
        query_type = "time_range"
    else:
        df = db.get_latest_snapshot(ahu_ids=ahu_ids, level=level)
        query_type = "latest_snapshot"

    if df.empty:
        return {"rows": [], "note": "No health data found for the given filters."}

    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].astype(str)

    return {
        "query_type": query_type,
        "row_count": len(df),
        "rows": _df_to_records(df),
    }


async def handle_query_live_readings(
    ahu_ids: Optional[list] = None,
    level: Optional[int] = None,
) -> dict:
    """
    Fetch latest sensor readings from InfluxDB.
    """
    try:
        from core.influx_client import fetch_latest_hourly_data
        from models.schemas import AHU_LEVEL_CONFIG

        if ahu_ids:
            devices_filter = ahu_ids
        elif level is not None:
            level_key = f"level_{level}"
            devices_filter = AHU_LEVEL_CONFIG.get(level_key, {}).get("devices", [])
        else:
            devices_filter = None

        df = await fetch_latest_hourly_data(devices_filter=devices_filter)
        if df is None or (hasattr(df, 'empty') and df.empty):
            return {"readings": [], "note": "No live readings available."}

        if hasattr(df, 'to_dict'):
            if "timestamp" in df.columns:
                df["timestamp"] = df["timestamp"].astype(str)
            return {"reading_count": len(df), "readings": _df_to_records(df)}

        return {"readings": [], "note": "Unexpected data format from InfluxDB."}
    except Exception as e:
        logger.warning(f"handle_query_live_readings failed: {e}")
        return {"readings": [], "error": str(e)}


async def handle_query_ranking(
    level: int,
    metric: str,
    n: int = 5,
    order: str = "asc",
) -> dict:
    """
    Rank AHUs by metric within a level.
    """
    db = _get_db()
    df = db.get_ranking(level=level, metric=metric, n=n, order=order)

    if df.empty:
        return {"ranking": [], "note": f"No data for level {level}."}

    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].astype(str)

    return {
        "level": level,
        "metric": metric,
        "order": order,
        "ranking": _df_to_records(df),
    }


async def handle_query_financial_impact(
    level: int,
    time_range: str = "7d",
) -> dict:
    """
    Compute financial impact for a level using the existing risk engine.
    """
    try:
        from routes.financial_impact import _compute_impact
        result = await _compute_impact(level=level, time_range=time_range)
        return result if isinstance(result, dict) else {"data": result}
    except Exception as e:
        logger.warning(f"handle_query_financial_impact failed: {e}")
        return {"error": str(e), "note": "Financial impact data unavailable."}


async def handle_search_docs(
    query: str,
    k: int = 3,
) -> dict:
    """
    Search RAG knowledge base for relevant document chunks.
    """
    retriever = _get_retriever()
    if retriever is None:
        return {"documents": [], "note": "No documents indexed in RAG."}

    try:
        k = min(k, 8)  # cap at 8
        snippets = await retriever.retrieve(query, top_k=k)
        return {"query": query, "documents": snippets or []}
    except Exception as e:
        logger.warning(f"handle_search_docs failed: {e}")
        return {"documents": [], "error": str(e)}
