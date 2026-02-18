"""
routes/query.py
───────────────
The single POST /api/query endpoint that orchestrates:
  LLM translation → middleware validation → InfluxDB → chart builder → summarizer
"""

import uuid
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from llm.translator import translate_query
from influx_client import fetch_time_series, fetch_ranking
from charts import build_line_chart, build_bar_chart
from summarizer import generate_summary
from middleware.query_logger import log_query
from models.schemas import QueryType

router = APIRouter()


class QueryRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = None


@router.post("/query")
async def handle_query(request: QueryRequest):
    session_id = request.session_id or str(uuid.uuid4())
    user_query = request.user_query.strip()

    if not user_query:
        return JSONResponse(status_code=400, content={"error": "Query cannot be empty."})

    # ── Step 1: LLM translation + validation ──────────────────────────────────
    structured_query, error = translate_query(user_query)

    if error or structured_query is None:
        log_query(
            session_id=session_id,
            user_query=user_query,
            structured_query=None,
            execution_status="parse_error",
            error_detail=error,
        )
        return JSONResponse(status_code=422, content={
            "error": error or "Could not interpret your query.",
            "suggestion": "Try asking about a specific device (e.g. 'Show e0101 power for last 7 days') or ranking devices (e.g. 'Top 10 devices by energy this month')."
        })

    query_dict = structured_query.model_dump()

    # ── Step 2: Fetch from InfluxDB ───────────────────────────────────────────
    try:
        if structured_query.query_type == QueryType.time_series:
            df = fetch_time_series(
                device_ids=structured_query.device_ids,
                metric=structured_query.metric,
                time_range=structured_query.time_range,
            )
            chart_payload = build_line_chart(
                df,
                metric=structured_query.metric,
                time_range=structured_query.time_range,
            )
        else:
            df = fetch_ranking(
                metric=structured_query.metric,
                time_range=structured_query.time_range,
                device_ids=structured_query.device_ids,
                top_n=structured_query.top_n or 10,
            )
            chart_payload = build_bar_chart(
                df,
                metric=structured_query.metric,
                time_range=structured_query.time_range,
                top_n=structured_query.top_n or 10,
            )

    except Exception as e:
        log_query(
            session_id=session_id,
            user_query=user_query,
            structured_query=query_dict,
            execution_status="influx_error",
            error_detail=str(e),
        )
        return JSONResponse(status_code=500, content={
            "error": "Failed to retrieve data from the database. Please try again."
        })

    # ── Step 3: Generate summary ──────────────────────────────────────────────
    summary = generate_summary(
        chart_payload=chart_payload,
        query_type=structured_query.query_type.value,
        device_ids=structured_query.device_ids,
        metric=structured_query.metric,
        time_range=structured_query.time_range,
    )

    # ── Step 4: Log success ───────────────────────────────────────────────────
    log_query(
        session_id=session_id,
        user_query=user_query,
        structured_query=query_dict,
        execution_status="success",
    )

    # ── Step 5: Return response ───────────────────────────────────────────────
    return {
        "session_id":       session_id,
        "query_type":       structured_query.query_type.value,
        "metric":           structured_query.metric,
        "time_range":       structured_query.time_range,
        "device_ids":       structured_query.device_ids,
        "structured_query": query_dict,
        "chart":            chart_payload,
        "summary":          summary,
        "csv_available":    bool(chart_payload.get("csv")),
    }