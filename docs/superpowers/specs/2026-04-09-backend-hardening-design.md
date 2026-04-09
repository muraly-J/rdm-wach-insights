# Backend Hardening — Design Spec

**Date**: 2026-04-09
**Status**: Approved
**Approach**: B — Hardened Foundation (root-cause fixes, minimal new dependencies)

---

## Context

An external review scored the WACH Insight backend across five dimensions. Two areas scored critically low:

| Dimension | Score | Issue |
|-----------|-------|-------|
| Observability & Reliability | 4.0/10 | No data freshness metadata — users can't tell if charts show 5-minute-old or 18-hour-old data |
| Maintainability (DX) | 5.5/10 | Hardcoded regex/keyword parser duplicates metric knowledge across files |
| Architecture (Scalability) | 6.0/10 | In-memory rate limiter and no LLM circuit breaker |

The 4 fixes are prioritized by current pain:

1. **Data Freshness Metadata** — users making decisions on potentially stale data
2. **Metric Registry** — `_parse_query_rules` is the live production path (LLM is disabled) and is 260 lines of brittle keyword matching
3. **Circuit Breaker for LLM** — no graceful degradation when LM Studio is unavailable
4. **Rate Limiter Interface** — in-memory store won't survive horizontal scaling (future-proofing)

### Current deployment context

- Single backend instance (no horizontal scaling planned near-term)
- ETL runs hourly via cron (`ETL_SCHEDULE=0 * * * *`)
- `ENABLE_LLM=false` in production — rule-based parser handles all query translation
- LM Studio (Qwen3-8b) used only for chat endpoint tool-calling loop
- Frontend is React + Vite + Zustand, proxies `/api` to backend at port 8081

---

## Phase 1: Data Freshness Metadata

### Problem

If the hourly ETL (`run_health_etl.py`) fails silently, the API continues serving stale data from DuckDB. No API response includes provenance information. Users see confident-looking charts of data that may be hours old.

### Design

#### ETL heartbeat table

Add an `etl_runs` table to `healthdb.duckdb`:

| Column | Type | Purpose |
|--------|------|---------|
| `run_id` | INTEGER (auto-increment) | Primary key |
| `started_at` | TIMESTAMP | When the ETL run began |
| `completed_at` | TIMESTAMP | When it finished (NULL if crashed mid-run) |
| `status` | VARCHAR | `running`, `success`, `partial`, `failed` |
| `rows_written` | INTEGER | How many rows upserted |
| `level` | INTEGER | Which level was processed (NULL = all) |

`run_health_etl.py` writes a row with `status='running'` at start and updates to `success`/`failed` on completion. A crashed ETL leaves `completed_at IS NULL` — detectable by the API.

#### API metadata injection

New helper in `core/healthdb.py`:

```python
def get_last_sync() -> dict:
    """
    Returns metadata about the most recent successful ETL run.
    
    Returns:
        {
            "data_as_of": "2026-04-09T14:00:00+08:00",  # ISO8601
            "sync_age_seconds": 1800
        }
    """
```

Queries `MAX(completed_at) WHERE status='success'` from `etl_runs`.

Three endpoints gain a `metadata` key in their response:

- `GET /api/dashboard/trend`
- `GET /api/dashboard/ranking`
- `GET /api/dashboard/summary`

Response shape addition (non-breaking):

```json
{
  "level": "5",
  "time_range": "last_7d",
  "metadata": {
    "data_as_of": "2026-04-09T14:00:00+08:00",
    "sync_age_seconds": 1800
  },
  "best": [...]
}
```

#### Frontend indicator

A `DataFreshnessIndicator` component that reads `metadata.data_as_of` from any dashboard API response. Renders as subtle text: "Data as of 30 min ago". No warning banners, no blocking gates — just an informational timestamp.

### Files touched

| File | Change |
|------|--------|
| `core/healthdb.py` | Add `etl_runs` table creation, `record_etl_start()`, `record_etl_complete()`, `get_last_sync()` |
| `scripts/etl/run_health_etl.py` | Call `record_etl_start()`/`record_etl_complete()` around the ETL pipeline |
| `routes/dashboard.py` | Inject `metadata` from `get_last_sync()` into trend, ranking, and summary responses |
| `frontend/src/components/DataFreshnessIndicator.tsx` | New component — renders "Data as of X ago" |
| `frontend/src/store/useAppStore.ts` | Store `metadata.data_as_of` from dashboard API responses |

---

## Phase 2: Metric Registry (Kill the Regex Monster)

### Problem

`_parse_query_rules` in `backend/llm/translator.py` (lines 120-379) is a 260-line function with a hardcoded `metric_map` dictionary, keyword sets for time ranges, query type detection heuristics, and branching logic. This duplicates metric knowledge already in `schemas.py`'s `ALLOWED_METRICS_WITH_UNITS`. Every new metric requires manual updates in multiple places.

With `ENABLE_LLM=false` in production, this parser handles all query translation — it's the live path, not a fallback.

### Design

#### Extend the registry in `schemas.py`

`ALLOWED_METRICS_WITH_UNITS` gains an `aliases` field per metric:

```python
ALLOWED_METRICS_WITH_UNITS = {
    "power_total": {
        "unit": "kW",
        "description": "Total active power across all phases",
        "aliases": ["power", "total power", "active power"],
    },
    "energy_import": {
        "unit": "kWh",
        "description": "Energy consumed from grid",
        "aliases": ["energy", "energy consumption", "energy usage", "energy import"],
    },
    "current_unbalance": {
        "unit": "%",
        "description": "Current unbalance percentage",
        "aliases": ["unbalance", "phase imbalance", "phase unbalance", "current imbalance"],
    },
    # ... all ~50 metrics
}
```

This is a structural change to the dict (tuples become dicts), so `ALLOWED_METRICS`, `get_metric_unit()`, and `get_metric_description()` need minor updates to read from the new shape.

#### New helper: `resolve_metric(text: str) -> str | None`

Added to `schemas.py`. Builds a reverse lookup dict at module load time (alias string -> metric key). Matching strategy:

1. Exact match against metric key name (e.g., `"power_total"`)
2. Longest-match-first against aliases in the query text (multi-word aliases like `"energy consumption"` match before single-word `"energy"`)

This is a flat dict lookup — no regex. Adding a new metric or alias = adding one line to the registry.

#### Simplified `_parse_query_rules`

The 260-line function shrinks to ~80 lines:

1. Extract device IDs — keep `r'\be\d{4}\b'` regex (legitimate pattern match)
2. Extract levels — keep level regex (same reason)
3. Resolve metric via `resolve_metric(query_text)` — replaces the entire `metric_map` block
4. Match time range from a 4-entry static dict (not a maintenance problem)
5. Determine query type from keyword sets (already clean enough)
6. Confidence gate and `StructuredQuery` construction

#### Consumers aligned to single source of truth

| Consumer | Currently reads from | After |
|----------|---------------------|-------|
| `_parse_query_rules` (translator.py) | Hardcoded `metric_map` dict | `resolve_metric()` from schemas.py |
| `validate_query` (validator.py) | `ALLOWED_METRICS` from schemas.py | Same (unchanged) |
| `_validate_llm_output` (query.py) | `ALLOWED_METRICS` from schemas.py | Same (unchanged) |
| LLM system prompt (prompts.py) | Can generate metric list from registry | Future opportunity, not in scope |

### Files touched

| File | Change |
|------|--------|
| `models/schemas.py` | Restructure `ALLOWED_METRICS_WITH_UNITS` from tuples to dicts with `aliases`. Add `resolve_metric()`. Update `ALLOWED_METRICS`, `get_metric_unit()`, `get_metric_description()` for new shape. |
| `llm/translator.py` | Rewrite `_parse_query_rules` to use `resolve_metric()`. Remove hardcoded `metric_map`. ~260 lines -> ~80 lines. |
| `routes/measurements.py` | Uses `ALLOWED_METRICS_WITH_UNITS` for membership check only (`in`) — no change needed |

---

## Phase 3: Circuit Breaker for LLM

### Problem

`QwenClient` connects to LM Studio at `localhost:1234` with a 60-second timeout. If LM Studio is down, every chat request independently discovers this by blocking for 60 seconds, then returning a generic error. No state tracking, no backoff.

### Design

#### State machine

Three states:

```
CLOSED  ──(N consecutive failures)──>  OPEN  ──(cooldown expires)──>  HALF_OPEN
   ^                                                                      |
   └──────────────────(probe succeeds)────────────────────────────────────┘

HALF_OPEN ──(probe fails)──> OPEN
```

- **CLOSED** (normal): All requests pass through. Consecutive failure counter increments on exception, resets on success.
- **OPEN** (tripped): Immediately raises `LLMUnavailableError` without making the HTTP call. Saves the 60s timeout per user.
- **HALF_OPEN** (probing): After cooldown expires, allows exactly one request through. Success -> CLOSED. Failure -> back to OPEN with reset cooldown.

#### Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `LLM_FAILURE_THRESHOLD` | 3 | Consecutive failures to trip the breaker |
| `LLM_COOLDOWN_SECONDS` | 300 | How long OPEN state lasts before probing |

#### Implementation

New file: `backend/llm/circuit_breaker.py`

- `CircuitBreaker` class with `call(async_fn, *args, **kwargs)` method
- In-memory state (counter + timer) — correct for per-instance LM Studio connectivity
- Raises `LLMUnavailableError` (custom exception) when open
- Thread-safe via `threading.Lock`

#### Integration

`QwenClient.__init__` creates a `CircuitBreaker` instance. The three public methods (`generate_text`, `generate_chat_response`, `generate_with_tools`) wrap their LM Studio calls through the breaker.

Route handlers catch `LLMUnavailableError`:
- `routes/chat.py` returns 503 with `"AI is temporarily unavailable, please try again in a few minutes"`
- `routes/query.py` (when `ENABLE_LLM=true`) returns 503 with same message

No fallback to rule-based mode for chat. When the breaker is open, chat is unavailable.

### Files touched

| File | Change |
|------|--------|
| `llm/circuit_breaker.py` | New file — `CircuitBreaker` class, `LLMUnavailableError` exception |
| `llm/qwen_client.py` | Wrap LM Studio calls through breaker |
| `routes/chat.py` | Catch `LLMUnavailableError`, return clean 503 |
| `routes/query.py` | Catch `LLMUnavailableError` when `LLM_ENABLED=true` |

---

## Phase 4: Rate Limiter Interface

### Problem

`_rate_store` in `query.py:35` is a `defaultdict(list)` inlined in the route file. Won't survive horizontal scaling. Currently single-instance with no near-term scaling plans, so this is a future-proofing refactor.

### Design

#### Protocol and factory

New file: `backend/middleware/rate_limiter.py`

```python
class RateLimiter(Protocol):
    def check(self, key: str) -> None:
        """Raises HTTPException(429) if rate limit exceeded."""
        ...

class InMemoryRateLimiter:
    """Same logic as today's _check_rate_limit, encapsulated."""
    def __init__(self, max_requests: int, window_seconds: int): ...
    def check(self, key: str) -> None: ...

def get_rate_limiter() -> RateLimiter:
    """Factory — returns InMemoryRateLimiter. Swap to Redis later via config."""
    return InMemoryRateLimiter(
        max_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
        window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
    )
```

#### Clean up `query.py`

Remove inline `_rate_store`, `RATE_LIMIT`, `RATE_WINDOW`, and `_check_rate_limit()`. Replace with:

```python
from middleware.rate_limiter import get_rate_limiter
limiter = get_rate_limiter()

@router.post('/query')
async def handle_query(request: Request, body: QueryRequest):
    limiter.check(request.client.host or 'unknown')
    # ...
```

Configuration reads from env vars already defined in `.env.example` (`RATE_LIMIT_REQUESTS=100`, `RATE_LIMIT_WINDOW=60`).

#### Scope boundaries

- Rate limiting stays on `/api/query` only (no chat endpoint)
- No Redis implementation shipped — just the interface that makes it a drop-in later
- No middleware-level rate limiting

### Files touched

| File | Change |
|------|--------|
| `middleware/rate_limiter.py` | New file — `RateLimiter` protocol, `InMemoryRateLimiter`, `get_rate_limiter()` factory |
| `routes/query.py` | Remove inline rate limiter code, import from `middleware/rate_limiter.py` |

---

## Testing strategy

| Phase | Tests |
|-------|-------|
| 1 — Data Freshness | Unit test `get_last_sync()` with mock DuckDB. Integration test that ETL writes heartbeat rows. API test that responses include `metadata`. |
| 2 — Metric Registry | Unit test `resolve_metric()` against all aliases. Regression test: existing `_parse_query_rules` test cases must still pass with new implementation. |
| 3 — Circuit Breaker | Unit test state transitions: CLOSED->OPEN after N failures, OPEN->HALF_OPEN after cooldown, HALF_OPEN->CLOSED on success, HALF_OPEN->OPEN on failure. |
| 4 — Rate Limiter | Unit test `InMemoryRateLimiter.check()` — passes under limit, raises 429 over limit, resets after window. |

---

## Out of scope

- Redis-backed rate limiter (future — when horizontal scaling is needed)
- ETL monitoring/alerting (Slack/email webhooks)
- Embedding-based metric search (overkill for ~50 metrics)
- Frontend warning banners for stale data (only subtle timestamp indicator)
- Fallback mode for chat when LLM is down (returns "unavailable")
- Rate limiting on `/api/chat`
- LLM system prompt generation from metric registry (future opportunity)
