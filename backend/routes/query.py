"""
POST /api/query — main endpoint with security hardening:
- Input length cap
- Prompt injection pattern detection
- Per-IP rate limiting (in-memory, 20 req/min)
- Session ID validation
- LLM output allowlist validation (prevents injection via structured output)
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
                "suggestion": "Try: 'Show e0101 power last 7 days' or 'Rank top 10 devices by energy this month'."
            }
        )

# ── LLM output allowlists ─────────────────────────────────────────────────────
# These are the ONLY values the LLM is permitted to produce.
# If the model is manipulated into returning anything else, the request is
# rejected here — before it ever reaches InfluxDB.

ALLOWED_QUERY_TYPES = {"time_series", "ranking"}

ALLOWED_METRICS = {
    "power",
    "energy",
    "current",
    "voltage",
    "power_factor",
    "frequency",
}

ALLOWED_AGGREGATIONS = {
    "mean",
    "max",
    "min",
    "sum",
    "count",
    "last",
}

# Device IDs must match your naming convention — adjust the pattern if needed.
# e.g. e0101, e0202, ahu-01, etc.
_DEVICE_ID_RE = re.compile(r'^[a-zA-Z0-9_\-]{1,32}$')

# Time range strings — allow relative ranges like "7d", "30d", "1h", "24h",
# or absolute ISO pairs. Adjust if your schema uses a different format.
_TIME_RANGE_RE = re.compile(r'^\d+[smhdwMy]$|^\d{4}-\d{2}-\d{2}')


def _validate_llm_output(structured) -> None:
    """
    Allowlist-validate every field the LLM returns before it touches InfluxDB.
    Raises HTTPException(400) on any violation.
    This is the primary defence against prompt injection via structured output.
    """
    errors = []

    # query_type
    if structured.query_type not in ALLOWED_QUERY_TYPES:
        errors.append(f"Invalid query_type: '{structured.query_type}'")

    # metric
    if structured.metric not in ALLOWED_METRICS:
        errors.append(f"Invalid metric: '{structured.metric}'")

    # aggregation (may be None for some query types)
    if structured.aggregation is not None:
        if structured.aggregation not in ALLOWED_AGGREGATIONS:
            errors.append(f"Invalid aggregation: '{structured.aggregation}'")

    # device_ids — each must be a safe alphanumeric identifier
    if structured.device_ids:
        for did in structured.device_ids:
            if not _DEVICE_ID_RE.match(str(did)):
                errors.append(f"Invalid device_id: '{did}'")
        if len(structured.device_ids) > 50:
            errors.append("Too many device_ids requested (max 50).")

    # top_n — must be a small positive integer
    if structured.top_n is not None:
        if not isinstance(structured.top_n, int) or not (1 <= structured.top_n <= 100):
            errors.append(f"Invalid top_n: '{structured.top_n}' (must be 1–100)")

    # time_range — basic sanity check
    if structured.time_range is not None:
        tr = str(structured.time_range)
        if not _TIME_RANGE_RE.match(tr):
            errors.append(f"Invalid time_range format: '{tr}'")

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

@router.post('/api/query')
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
                "suggestion": "Try: 'Show e0101 power last 7 days' or 'Rank top 5 by energy this month'."
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
                top_n=structured.top_n or 10,
            )
    except Exception as e:
        log_query(
            session_id=session_id,
            user_query=body.user_query,
            structured_query=structured.model_dump(),
            execution_status='influx_error',
            error_detail=str(e)
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