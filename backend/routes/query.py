"""
POST /api/query — main endpoint with security hardening:
- Input length cap
- Prompt injection pattern detection
- Per-IP rate limiting (in-memory, 20 req/min)
- Session ID validation
- LLM output allowlist validation (prevents injection via structured output)
"""
import logging
import re
import time
import uuid
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, validator

from llm.translator import translate_query
from middleware.validator import validate_structured_query
from middleware.query_logger import log_query
from core.influx_client import fetch_time_series, fetch_ranking
from core.charts import build_chart
from core.summarizer import summarize
from models.schemas import ALLOWED_METRICS, ALLOWED_DEVICES, QueryType

router = APIRouter()

# ── Rate limiter (in-memory, per IP) ────────────────────────────────────────
_rate_store: dict = defaultdict(list)
RATE_LIMIT        = 20   # requests
RATE_WINDOW       = 60   # seconds

def _check_rate_limit(ip: str) -> None:
    now  = time.time()
    hits = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    hits.append(now)
    _rate_store[ip] = hits
    if len(hits) > RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={"error": "Too many requests. Please wait a moment before trying again."}
        )

# ── Injection & abuse patterns ───────────────────────────────────────────────
_INJECTION_PATTERNS = [
    # Prompt injection classics
    r"ignore\s+(all\s+)?(previous|prior|above)",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(previous|prior|above)",
    r"new\s+(role|persona|instruction|task|system)",
    r"you\s+are\s+now",
    r"act\s+as\s+(?!an?\s+ahu)",   # allow "act as an AHU monitor" but not "act as DAN"
    r"pretend\s+to\s+be",
    r"(system|assistant|user)\s*:",  # role injection
    r"<\s*/?(?:system|prompt|instruction)",
    r"\[\s*INST\s*\]",
    r"###\s*(instruction|system|prompt)",
    # SQL/NoSQL injection
    r";\s*(drop|delete|insert|update|truncate|alter)\s",
    r"union\s+select",
    r"--\s+",
    # Script injection
    r"<script",
    r"javascript:",
    r"on\w+\s*=",
]
_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE | re.DOTALL,
)

def _check_injection(text: str) -> None:
    if _INJECTION_RE.search(text):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Your query contains patterns that aren't allowed. "
                         "Please ask a plain question about AHU performance.",
                "suggestion": "Try: 'Show e0101 power last 7 days' or "
                              "'Rank top 10 devices by energy this month'."
            }
        )

# ── LLM output allowlists ─────────────────────────────────────────────────────
# Derived from schemas.py — single source of truth.
# If the LLM is manipulated into returning anything outside these sets,
# the request is rejected before it ever reaches InfluxDB.

_ALLOWED_QUERY_TYPES = {qt.value for qt in QueryType}  # {"time_series", "ranking"}

_ALLOWED_TIME_RANGES = {"last_24h", "last_7d", "last_30d", "all_time"}

# Device IDs are e0101 → e1108 — enforce the pattern strictly
_DEVICE_ID_RE = re.compile(r'^e\d{4}$')


def _validate_llm_output(structured) -> None:
    """
    Allowlist-validate every field the LLM returns before it touches InfluxDB.
    Raises HTTPException(400) on any violation.

    Note: metric and device_ids are also validated by Pydantic field_validators
    on StructuredQuery, but we check here too as defence-in-depth in case the
    object was constructed in an unexpected way.
    """
    errors = []

    # query_type
    if structured.query_type not in _ALLOWED_QUERY_TYPES:
        errors.append(f"Invalid query_type: '{structured.query_type}'")

    # metric — ALLOWED_METRICS imported from schemas.py
    if structured.metric not in ALLOWED_METRICS:
        errors.append(f"Invalid metric: '{structured.metric}'")

    # time_range
    if structured.time_range not in _ALLOWED_TIME_RANGES:
        errors.append(f"Invalid time_range: '{structured.time_range}'")

    # device_ids — pattern check + membership check against ALLOWED_DEVICES
    for did in structured.device_ids:
        did_str = str(did)
        if not _DEVICE_ID_RE.match(did_str):
            errors.append(f"Invalid device_id format: '{did_str}'")
        elif did_str not in ALLOWED_DEVICES:
            errors.append(f"Unrecognised device: '{did_str}'")

    if len(structured.device_ids) > 100:
        errors.append("Too many device_ids requested (max 100).")

    # top_n — only relevant for ranking queries, must be a small positive int
    if structured.top_n is not None:
        if not isinstance(structured.top_n, int) or not (1 <= structured.top_n <= 100):
            errors.append(f"Invalid top_n: '{structured.top_n}' (must be integer 1–100)")

    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "The query could not be processed safely.",
                "detail": errors,
            }
        )


# ── Request schema ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = None

    @validator('user_query')
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Query cannot be empty.')
        if len(v) > 400:
            raise ValueError('Query is too long. Please keep it under 400 characters.')
        # Strip null bytes and control characters (except newlines/tabs)
        v = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', v)
        return v

    @validator('session_id')
    def validate_session(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return str(uuid.uuid4())
        try:
            uuid.UUID(str(v))
        except ValueError:
            return str(uuid.uuid4())
        return v


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post('/query')
async def handle_query(request: Request, body: QueryRequest):
    client_ip = request.client.host or 'unknown'

    # 1. Rate limit
    _check_rate_limit(client_ip)

    # 2. Input injection detection
    _check_injection(body.user_query)

    session_id = body.session_id or str(uuid.uuid4())

    # 3. LLM translation
    structured, error = await translate_query(body.user_query)

    if structured is None:
        log_query(
            session_id=session_id,
            user_query=body.user_query,
            structured_query=None,
            execution_status='parse_error',
            error_detail=error
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": error or "I couldn't understand that query.",
                "suggestion": "Try: 'Show e0101 power last 7 days' or "
                              "'Rank top 5 by energy this month'."
            }
        )

    # 4. Allowlist validation on LLM output (before anything touches InfluxDB)
    _validate_llm_output(structured)

    # 5. Middleware schema validation
    validation_error = validate_structured_query(structured)
    if validation_error:
        log_query(
            session_id=session_id,
            user_query=body.user_query,
            structured_query=structured.model_dump(),
            execution_status='validation_error',
            error_detail=validation_error
        )
        raise HTTPException(status_code=422, detail={"error": validation_error})

    # 6. Fetch data from InfluxDB
    try:
        if structured.query_type == 'time_series':
            df = fetch_time_series(
                device_ids=structured.device_ids,
                metric=structured.metric,
                time_range=structured.time_range,
            )
        else:
            df = fetch_ranking(
                metric=structured.metric,
                time_range=structured.time_range,
                device_ids=structured.device_ids,
                top_n=structured.top_n,  # Pass through None for all devices
            )
    except Exception as e:
        logging.getLogger(__name__).error("Query processing error: %s", e, exc_info=True)
        log_query(
            session_id=session_id,
            user_query=body.user_query,
            structured_query=structured.model_dump(),
            execution_status='influx_error',
            error_detail="An error occurred processing your query."
        )
        raise HTTPException(
            status_code=502,
            detail={"error": "Could not retrieve data. Please try again in a moment."}
        )

    # 7. Build chart + summary
    chart   = build_chart(df, structured)
    summary = await summarize(df, structured)

    log_query(
        session_id=session_id,
        user_query=body.user_query,
        structured_query=structured.model_dump(),
        execution_status='success'
    )

    return {
        **structured.model_dump(),
        'chart':         chart,
        'summary':       summary,
        'csv_available': bool(chart.get('csv')),
    }
