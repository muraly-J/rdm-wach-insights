"""
POST /api/query — main endpoint with security hardening:
- Input length cap
- Prompt injection pattern detection
- Per-IP rate limiting (in-memory, 20 req/min)
- Session ID validation
"""
import re
import time
import uuid
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, validator

from backend.llm.translator import translate_query
from backend.middleware.validator import validate_structured_query
from backend.middleware.query_logger import log_query
from backend.influx_client import fetch_time_series, fetch_ranking
from backend.charts import build_chart
from backend.summarizer import summarize

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
    # SQL/NoSQL injection (belt and braces)
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
                "suggestion": "Try: 'Show e0101 power last 7 days' or 'Rank top 10 devices by energy this month'."
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
        # Must look like a UUID
        try:
            uuid.UUID(str(v))
        except ValueError:
            return str(uuid.uuid4())
        return v

# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post('/api/query')
async def handle_query(request: Request, body: QueryRequest):
    client_ip = request.client.host or 'unknown'

    # 1. Rate limit
    _check_rate_limit(client_ip)

    # 2. Injection detection
    _check_injection(body.user_query)

    session_id = body.session_id or str(uuid.uuid4())

    # 3. LLM translation
    structured = await translate_query(body.user_query)

    if structured is None:
        log_query(session_id, body.user_query, None, 'rejected_llm_parse', False)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "I couldn't understand that query.",
                "suggestion": "Try: 'Show e0101 power last 7 days' or 'Rank top 5 by energy this month'."
            }
        )

    # 4. Middleware validation
    validation_error = validate_structured_query(structured)
    if validation_error:
        log_query(session_id, body.user_query, structured, 'rejected_validation', False)
        raise HTTPException(status_code=422, detail={"error": validation_error})

    # 5. Fetch data
    try:
        if structured['query_type'] == 'time_series':
            df = fetch_time_series(
                device_ids=structured['device_ids'],
                metric=structured['metric'],
                time_range=structured['time_range'],
            )
        else:
            df = fetch_ranking(
                metric=structured['metric'],
                time_range=structured['time_range'],
            )
    except Exception as e:
        log_query(session_id, body.user_query, structured, 'error_influx', False)
        raise HTTPException(
            status_code=502,
            detail={"error": "Could not retrieve data. Please try again in a moment."}
        )

    # 6. Build chart + summary
    chart   = build_chart(df, structured)
    summary = await summarize(df, structured)

    log_query(session_id, body.user_query, structured, 'success', False)

    return {
        **structured,
        'chart':         chart,
        'summary':       summary,
        'csv_available': bool(chart.get('csv')),
    }