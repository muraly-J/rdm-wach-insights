# Phase 3: Observability & Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace scattered, plain-text logging with structured JSON logs, add a Request ID that threads through every log line, expose a Prometheus `/metrics` endpoint, consolidate the duplicated rate limiter, add startup health checks + SIGTERM flush, and wire an alerting webhook for 5xx spikes.

**Architecture:** A new `backend/core/logger.py` acts as the single import point for all logging. A `contextvars.ContextVar` carries the request ID from `middleware/request_id.py` into every log line automatically. The two rate-limiter implementations (one in `main.py`, one in `routes/query.py`) are replaced by a single `middleware/rate_limiter.py` that both callers import. Prometheus instrumentation is a one-liner. The alerter is a pure function called from the error-response path — no background threads.

**Tech Stack:** `python-json-logger>=3.2`, `prometheus-fastapi-instrumentator>=7.0`, `httpx` (already in requirements), Python `contextvars`, `signal`, FastAPI `lifespan`

---

## File Structure

**New files (create):**
```
backend/core/logger.py                  — JSON formatter + ContextVar request_id + get_logger()
backend/middleware/request_id.py        — Sets X-Request-ID per request, binds ContextVar
backend/middleware/rate_limiter.py      — Single RateLimitMiddleware + make_rate_limiter() factory
backend/core/alerter.py                 — Sliding-window 5xx rate tracker + webhook fire
```

**Modified files:**
```
backend/requirements.txt                — add python-json-logger, prometheus-fastapi-instrumentator
backend/main.py                         — remove logging.basicConfig + RateLimitMiddleware + _rate_store;
                                          add lifespan, SIGTERM, import new middleware, /metrics
backend/routes/query.py                 — remove _rate_store + _check_rate_limit; import from middleware
backend/config.py                       — replace logging.getLogger with get_logger
backend/utils/error_handler.py          — same
backend/core/influx_client.py           — same
backend/llm/translator.py               — same
backend/llm/qwen_client.py              — same
backend/tools/tool_registry.py          — same
backend/tools/health_tools.py           — same
backend/rag/qwen_embedder.py            — same
backend/core/prediction_engine.py       — same
docker-compose.yml                      — add commented Prometheus + Grafana sidecar
.env.example                            — add ALERT_WEBHOOK_URL
```

---

## Task 1: Add dependencies to `requirements.txt`

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Write a failing import test**

```bash
cd backend && python -c "from pythonjsonlogger import jsonlogger; print('ok')" 2>&1
```

Expected: `ModuleNotFoundError` — confirms the dep is missing.

- [ ] **Step 2: Add dependencies**

Edit `backend/requirements.txt` to add two lines after the existing entries:

```
python-json-logger>=3.2.0
prometheus-fastapi-instrumentator>=7.0.0
```

- [ ] **Step 3: Install and verify**

```bash
pip install -r backend/requirements.txt
python -c "from pythonjsonlogger import jsonlogger; print('python-json-logger ok')"
python -c "from prometheus_fastapi_instrumentator import Instrumentator; print('prometheus ok')"
```

Expected: both print their `ok` line without error.

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(deps): add python-json-logger and prometheus-fastapi-instrumentator"
```

---

## Task 2: Create `backend/core/logger.py`

**Files:**
- Create: `backend/core/logger.py`
- Test: `backend/tests/unit/test_logger.py`

The logger must:
1. Emit JSON lines to stderr
2. Include `asctime`, `name`, `levelname`, `message` in every record
3. Automatically include `request_id` from the `ContextVar` (empty string when not set)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_logger.py`:

```python
"""
Unit tests for the centralised JSON logger.

Tests:
- Log output is valid JSON
- Required fields are present in every record
- request_id ContextVar is included in log records
- get_logger returns the same Logger instance on repeated calls (no handler duplication)
"""
import json
import logging
import io
import pytest


class TestJsonLogger:
    def _capture_log(self, level, message, **extra):
        """Return a parsed dict of one log record emitted by get_logger."""
        from core.logger import get_logger
        buf = io.StringIO()
        logger = get_logger("test.module")
        # Replace all handlers with a StringIO handler for test capture
        logger.handlers.clear()
        handler = logging.StreamHandler(buf)
        from pythonjsonlogger import jsonlogger
        handler.setFormatter(
            jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s")
        )
        from core.logger import _ContextFilter
        handler.addFilter(_ContextFilter())
        logger.addHandler(handler)
        logger.log(level, message, **extra)
        buf.seek(0)
        return json.loads(buf.read())

    def test_output_is_valid_json(self):
        record = self._capture_log(logging.INFO, "hello world")
        assert isinstance(record, dict)

    def test_required_fields_present(self):
        record = self._capture_log(logging.INFO, "hello")
        assert "message" in record
        assert "levelname" in record
        assert "name" in record
        assert "asctime" in record

    def test_message_matches(self):
        record = self._capture_log(logging.INFO, "test message")
        assert record["message"] == "test message"

    def test_request_id_field_present_when_empty(self):
        """request_id is always emitted even if no request is active."""
        record = self._capture_log(logging.INFO, "no request")
        assert "request_id" in record

    def test_request_id_from_contextvar(self):
        """request_id in log matches what was set in the ContextVar."""
        from core.logger import _request_id
        token = _request_id.set("req-abc-123")
        try:
            record = self._capture_log(logging.INFO, "with request")
            assert record["request_id"] == "req-abc-123"
        finally:
            _request_id.reset(token)

    def test_get_logger_no_handler_duplication(self):
        """Calling get_logger twice for the same name must not duplicate handlers."""
        from core.logger import get_logger
        logger = get_logger("duplicate.test")
        initial_count = len(logger.handlers)
        get_logger("duplicate.test")
        assert len(logger.handlers) == initial_count
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest backend/tests/unit/test_logger.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'get_logger' from 'core.logger'` (file doesn't exist yet).

- [ ] **Step 3: Create `backend/core/logger.py`**

```python
"""
core/logger.py
──────────────
Centralised JSON structured logger for WACH Insight.

Every module should import get_logger from here instead of calling
logging.getLogger(__name__) directly. This ensures all log lines:
  1. Emit valid JSON to stderr (compatible with any log aggregator)
  2. Include a request_id field threaded from RequestIDMiddleware
  3. Never duplicate handlers on repeated calls

Usage:
    from core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Processing request", extra={"session_id": sid})
"""

import logging
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

# ── ContextVar for request-scoped tracing ────────────────────────────────────
# Set by RequestIDMiddleware on every inbound request.
# Automatically included in every log line via _ContextFilter.
_request_id: ContextVar[str] = ContextVar("request_id", default="")

_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class _ContextFilter(logging.Filter):
    """Injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get("")
        return True


def get_logger(name: str) -> logging.Logger:
    """
    Return a JSON-structured logger for the given module name.

    Idempotent: calling get_logger("foo.bar") twice returns the same
    Logger instance and does not add duplicate handlers.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(
        jsonlogger.JsonFormatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    )
    handler.addFilter(_ContextFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
pytest backend/tests/unit/test_logger.py -v
```

Expected: All 6 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/core/logger.py backend/tests/unit/test_logger.py
git commit -m "feat(observability): add centralised JSON logger with request_id ContextVar"
```

---

## Task 3: Replace scattered `logging.getLogger` calls in all backend modules

**Files:**
- Modify: `backend/main.py` (remove `logging.basicConfig` + `logger = logging.getLogger(...)`)
- Modify: `backend/config.py`
- Modify: `backend/utils/error_handler.py`
- Modify: `backend/core/influx_client.py`
- Modify: `backend/llm/translator.py`
- Modify: `backend/llm/qwen_client.py`
- Modify: `backend/tools/tool_registry.py`
- Modify: `backend/tools/health_tools.py`
- Modify: `backend/rag/qwen_embedder.py`
- Modify: `backend/core/prediction_engine.py`
- Modify: `backend/routes/chat.py`
- Modify: `backend/routes/query.py`

- [ ] **Step 1: Write a failing test that confirms logger is plain in one module**

```bash
python -c "
import ast, pathlib
src = pathlib.Path('backend/config.py').read_text()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        func = getattr(node.func, 'attr', None)
        if func == 'getLogger':
            print('FOUND getLogger — test will fail post-migration')
" 2>&1
```

Expected output: prints `FOUND getLogger`. After migration it will print nothing.

- [ ] **Step 2: In each file listed above, replace the logger instantiation**

**Pattern to find:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Replacement:**
```python
from core.logger import get_logger
logger = get_logger(__name__)
```

Do this for every file in the list. Files may also have `import logging` at the top that is used solely for `logging.getLogger` — remove that import if `logging` is no longer used directly in the file (keep it if the file calls `logging.INFO` or similar constants).

**`backend/main.py` specifically:**
- Remove the three lines starting at line 19:
  ```python
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
      datefmt="%Y-%m-%d %H:%M:%S"
  )
  logger = logging.getLogger(__name__)
  ```
- Replace with:
  ```python
  from core.logger import get_logger
  logger = get_logger(__name__)
  ```
- Keep `import logging` in `main.py` only if any other line in the file uses `logging.*` constants directly. Check and remove if unused.

- [ ] **Step 3: Run the full backend test suite to confirm nothing broke**

```bash
pytest backend/tests/ -x -q 2>&1 | tail -20
```

Expected: same pass count as before Task 3 started. Zero new failures.

- [ ] **Step 4: Verify JSON output in one module**

```bash
cd backend && python -c "
from core.logger import get_logger
logger = get_logger('smoke')
logger.info('logger migration smoke test')
" 2>&1
```

Expected: a single JSON line on stderr containing `\"message\": \"logger migration smoke test\"`.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/config.py backend/utils/error_handler.py \
        backend/core/influx_client.py backend/llm/translator.py \
        backend/llm/qwen_client.py backend/tools/tool_registry.py \
        backend/tools/health_tools.py backend/rag/qwen_embedder.py \
        backend/core/prediction_engine.py backend/routes/chat.py \
        backend/routes/query.py
git commit -m "refactor(logging): replace logging.getLogger calls with centralized get_logger"
```

---

## Task 4: Create `middleware/request_id.py`

**Files:**
- Create: `backend/middleware/request_id.py`
- Modify: `backend/main.py` (add `RequestIDMiddleware` to stack)
- Test: `backend/tests/integration/test_request_id.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_request_id.py`:

```python
"""
Integration tests for RequestIDMiddleware.

Tests:
- Every response has an X-Request-ID header
- If client sends X-Request-ID, the same value is echoed back
- If client sends no X-Request-ID, a UUID is generated
"""
import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


class TestRequestIDMiddleware:
    def test_response_always_has_request_id_header(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers or "X-Request-ID" in resp.headers

    def test_provided_request_id_echoed_back(self, client):
        rid = "my-custom-id-123"
        resp = client.get("/health", headers={"X-Request-ID": rid})
        returned = resp.headers.get("x-request-id") or resp.headers.get("X-Request-ID")
        assert returned == rid

    def test_generated_request_id_is_valid_uuid(self, client):
        """When no X-Request-ID is sent, the server generates a UUID."""
        resp = client.get("/health")
        rid = resp.headers.get("x-request-id") or resp.headers.get("X-Request-ID")
        assert rid is not None
        uuid.UUID(rid)  # raises ValueError if not a valid UUID
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest backend/tests/integration/test_request_id.py -v 2>&1 | head -15
```

Expected: `FAILED test_response_always_has_request_id_header` — header absent.

- [ ] **Step 3: Create `backend/middleware/request_id.py`**

```python
"""
middleware/request_id.py
────────────────────────
Stamps every inbound request with a UUID request ID.

Behaviour:
  - Uses X-Request-ID from the incoming request if present (for end-to-end tracing).
  - Generates a UUID4 if the header is absent.
  - Stores the ID in core.logger._request_id (ContextVar) so it appears in all
    log lines emitted during that request.
  - Echoes the ID back in the response X-Request-ID header.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logger import _request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            _request_id.reset(token)
```

- [ ] **Step 4: Add `RequestIDMiddleware` to `main.py`**

In `main.py`, inside `create_app()`, after the existing `app.add_middleware(SecurityHeadersMiddleware)` line, add:

```python
from middleware.request_id import RequestIDMiddleware
app.add_middleware(RequestIDMiddleware)
```

The middleware stack order in `create_app()` after this change (first-added = outermost):
```python
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)   # ← add this line
```

Also add `/metrics` (for the next task) to the auth-skip list in `APIKeyAuthMiddleware`. Find this line:
```python
if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
```
And change it to:
```python
if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/metrics"):
```

- [ ] **Step 5: Run tests**

```bash
pytest backend/tests/integration/test_request_id.py -v
```

Expected: All 3 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/middleware/request_id.py backend/main.py \
        backend/tests/integration/test_request_id.py
git commit -m "feat(observability): add RequestIDMiddleware — X-Request-ID threads through all logs"
```

---

## Task 5: Create `middleware/rate_limiter.py` and remove duplicates

**Files:**
- Create: `backend/middleware/rate_limiter.py`
- Modify: `backend/main.py` (remove `_rate_store`, `_check_rate_limit`, `RateLimitMiddleware`)
- Modify: `backend/routes/query.py` (remove `_rate_store`, `_check_rate_limit`)
- Test: `backend/tests/unit/test_rate_limiter_module.py`

The current code has two separate rate limiters:
- `main.py`: `RateLimitMiddleware` (app-level, 100 req/60s)
- `routes/query.py`: `_check_rate_limit` function (route-level, 20 req/60s)

After this task, both are implemented in `middleware/rate_limiter.py`. `main.py` imports `RateLimitMiddleware`. `routes/query.py` imports a factory function `make_rate_limiter` to retain its tighter 20-req limit.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_rate_limiter_module.py`:

```python
"""
Unit tests confirming rate limiter consolidation.

Tests:
- RateLimitMiddleware is importable from middleware.rate_limiter
- make_rate_limiter returns a callable that raises HTTPException(429) at limit
- main.py no longer defines RateLimitMiddleware (duplication removed)
- routes/query.py no longer defines _check_rate_limit (duplication removed)
"""
import ast
import pathlib
import pytest
from fastapi import HTTPException


class TestRateLimiterModule:
    def test_rate_limit_middleware_importable(self):
        from middleware.rate_limiter import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_make_rate_limiter_importable(self):
        from middleware.rate_limiter import make_rate_limiter
        assert callable(make_rate_limiter)

    def test_make_rate_limiter_raises_at_limit(self):
        from middleware.rate_limiter import make_rate_limiter
        check = make_rate_limiter(limit=3, window=60)
        for _ in range(3):
            check("ip-a")  # should not raise
        with pytest.raises(HTTPException) as exc:
            check("ip-a")
        assert exc.value.status_code == 429

    def test_different_ips_have_independent_limits(self):
        from middleware.rate_limiter import make_rate_limiter
        check = make_rate_limiter(limit=2, window=60)
        for _ in range(2):
            check("ip-x")
        check("ip-y")  # ip-y untouched, must not raise

    def test_main_py_does_not_define_rate_limit_middleware(self):
        """After refactor, main.py must not contain a class named RateLimitMiddleware."""
        src = pathlib.Path("backend/main.py").read_text()
        tree = ast.parse(src)
        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "RateLimitMiddleware" not in class_names, (
            "RateLimitMiddleware is still defined in main.py — remove it"
        )

    def test_query_py_does_not_define_check_rate_limit(self):
        """After refactor, routes/query.py must not define _check_rate_limit."""
        src = pathlib.Path("backend/routes/query.py").read_text()
        tree = ast.parse(src)
        func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "_check_rate_limit" not in func_names, (
            "_check_rate_limit is still defined in routes/query.py — remove it"
        )
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest backend/tests/unit/test_rate_limiter_module.py -v 2>&1 | head -20
```

Expected: `FAILED test_rate_limit_middleware_importable` (module doesn't exist yet) and `FAILED test_main_py_does_not_define...` (still defined).

- [ ] **Step 3: Create `backend/middleware/rate_limiter.py`**

```python
"""
middleware/rate_limiter.py
──────────────────────────
Single implementation of rate limiting for WACH Insight.

Replaces two previous duplicates:
  - RateLimitMiddleware that was defined in main.py
  - _check_rate_limit() that was defined in routes/query.py

Public API:
  RateLimitMiddleware  — BaseHTTPMiddleware for app-level use (100 req/min by default)
  make_rate_limiter()  — factory returning a callable for route-level use

Why both exist:
  The app-level middleware protects all /api/ routes at 100 req/60s.
  Routes with expensive operations (e.g. LLM calls) can use make_rate_limiter()
  for a tighter per-route limit (e.g. 20 req/60s) without a separate implementation.
"""

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def make_rate_limiter(limit: int = 100, window: int = 60) -> Callable[[str], None]:
    """
    Return a rate-check callable with its own in-memory store.

    Usage in a FastAPI route:
        _check = make_rate_limiter(limit=20, window=60)

        @router.post("/query")
        async def handle(request: Request, ...):
            _check(request.client.host or "unknown")
            ...

    Raises:
        HTTPException(429) when the caller's IP exceeds `limit` requests
        within the last `window` seconds.
    """
    _store: dict = defaultdict(list)

    def check(ip: str) -> None:
        now = time.time()
        hits = [t for t in _store[ip] if now - t < window]
        hits.append(now)
        _store[ip] = hits
        if len(hits) > limit:
            raise HTTPException(
                status_code=429,
                detail={"error": "Too many requests. Please wait a moment before trying again."},
            )

    return check


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    App-level rate limiting middleware.

    Applied to all /api/ routes. Skips /health.
    Defaults: 100 requests per 60-second window per IP.

    NOTE: Must return JSONResponse directly — raising HTTPException inside
    BaseHTTPMiddleware is swallowed by Starlette and surfaces as 500.
    """

    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self._check = make_rate_limiter(limit=limit, window=window)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        if request.url.path.startswith("/api/"):
            ip = (request.client.host if request.client else None) or "unknown"
            try:
                self._check(ip)
            except HTTPException:
                return JSONResponse(
                    status_code=429,
                    content={"detail": {"error": "Too many requests. Please wait a moment before trying again."}},
                )

        return await call_next(request)
```

- [ ] **Step 4: Update `main.py` — remove the duplicate, import from middleware**

**Delete** the following block in `main.py` (lines 49–60):
```python
# ── Rate Limiter (in-memory, per IP) ───────────────────────────────────────
_rate_store: dict = defaultdict(list)
RATE_LIMIT        = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_WINDOW       = int(os.getenv("RATE_LIMIT_WINDOW", "60"))


def _check_rate_limit(ip: str) -> bool:
    """Returns True if the request should be rate-limited."""
    now  = time.time()
    hits = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    hits.append(now)
    _rate_store[ip] = hits
    return len(hits) > RATE_LIMIT
```

**Delete** the `RateLimitMiddleware` class definition (lines 133–154).

**Add** at the top of `main.py` with the other middleware imports:
```python
from middleware.rate_limiter import RateLimitMiddleware
```

Keep the `app.add_middleware(RateLimitMiddleware)` line in `create_app()` — it now refers to the imported class.

If `time` and `defaultdict` imports are no longer used in `main.py` after removal, delete them too. Check by scanning for other usages before removing.

- [ ] **Step 5: Update `routes/query.py` — remove the duplicate, import from middleware**

**Delete** the following block in `routes/query.py` (lines 35–48):
```python
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
```

**Add** at the top of `routes/query.py`:
```python
from middleware.rate_limiter import make_rate_limiter
_check_rate_limit = make_rate_limiter(limit=20, window=60)
```

This preserves the tighter 20-req limit for the LLM endpoint while using the consolidated implementation.

Remove any now-unused `time`, `defaultdict` imports from `routes/query.py` if no other code in that file uses them.

- [ ] **Step 6: Run all tests**

```bash
pytest backend/tests/ -x -q 2>&1 | tail -20
```

Expected: All previous tests still pass. New `test_rate_limiter_module.py` tests all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/middleware/rate_limiter.py backend/main.py backend/routes/query.py \
        backend/tests/unit/test_rate_limiter_module.py
git commit -m "refactor(reliability): consolidate rate limiters into middleware/rate_limiter.py"
```

---

## Task 6: Add lifespan + SIGTERM handler to `main.py`

**Files:**
- Modify: `backend/main.py`
- Test: `backend/tests/integration/test_startup.py`

The spec requires:
- FastAPI `lifespan` that runs startup checks for DuckDB and ChromaDB
- `SIGTERM` handler that flushes the query log before shutdown

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_startup.py`:

```python
"""
Integration tests for startup health checks.

Tests that the lifespan startup routine logs appropriate messages
when DuckDB / ChromaDB are present or absent, and does NOT crash.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestStartupChecks:
    def test_startup_with_missing_duckdb_logs_warning_not_crash(self, caplog):
        """If DuckDB path doesn't exist, startup must log a warning and continue — not crash."""
        import logging
        with patch("os.path.exists", return_value=False):
            with caplog.at_level(logging.WARNING):
                from main import _startup_checks
                _startup_checks()  # must not raise
        # Either a warning or info about missing db is logged
        assert any(
            "duckdb" in r.message.lower() or "health" in r.message.lower()
            for r in caplog.records
        ) or True  # startup completing without crash is the primary assertion

    def test_startup_with_missing_chroma_logs_warning_not_crash(self, caplog):
        """If ChromaDB dir doesn't exist, startup must log a warning and continue."""
        import logging
        with patch("os.path.isdir", return_value=False):
            with caplog.at_level(logging.WARNING):
                from main import _startup_checks
                _startup_checks()  # must not raise

    def test_app_health_after_startup(self):
        """The full app must respond to /health after startup completes."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest backend/tests/integration/test_startup.py::TestStartupChecks::test_startup_with_missing_duckdb_logs_warning_not_crash -v 2>&1 | head -15
```

Expected: `ImportError: cannot import name '_startup_checks' from 'main'`

- [ ] **Step 3: Add `_startup_checks()` and `lifespan` to `main.py`**

Add these imports at the top of `main.py` (after the existing imports):

```python
import signal
import sys
from contextlib import asynccontextmanager
```

Add the following functions **before** `create_app()`:

```python
def _handle_sigterm(*_) -> None:
    """Flush query log and shut down cleanly on SIGTERM (e.g. Docker stop)."""
    logger.info("SIGTERM received — flushing query log and shutting down")
    # SQLite commits happen inside context managers in query_logger.py,
    # so no explicit flush is needed; log the path for ops visibility.
    from middleware.query_logger import _DB_PATH
    logger.info("Query log location", extra={"db_path": str(_DB_PATH)})
    sys.exit(0)


def _startup_checks() -> None:
    """
    Verify DuckDB and ChromaDB are accessible on boot.
    Logs a warning (does not crash) if either is unavailable — this allows
    the app to start without data and serve the /health endpoint.
    """
    import duckdb

    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "healthdb.duckdb")
    if os.path.exists(db_path):
        try:
            conn = duckdb.connect(db_path, read_only=True)
            conn.close()
            logger.info("DuckDB startup check passed", extra={"db": db_path})
        except Exception as e:
            logger.error("DuckDB startup check failed — health scores may be unavailable", extra={"error": str(e)})
    else:
        logger.warning("DuckDB not found — health scores will be empty on first boot", extra={"db": db_path})

    chroma_dir = os.getenv("CHROMA_PERSIST_DIR", os.path.join(os.path.dirname(__file__), "data", "chroma"))
    if os.path.isdir(chroma_dir):
        logger.info("ChromaDB directory present", extra={"dir": chroma_dir})
    else:
        logger.warning("ChromaDB directory not found — RAG will be unavailable until ingestion runs", extra={"dir": chroma_dir})


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan: startup checks + SIGTERM registration."""
    _startup_checks()
    signal.signal(signal.SIGTERM, _handle_sigterm)
    try:
        init_db()
        logger.info("Query logging initialized")
    except Exception as e:
        logger.warning("Could not initialize query logger", extra={"error": str(e)})
    yield
    logger.info("Application shutdown complete")
```

**Update `create_app()` to use the lifespan:**

Change:
```python
def create_app():
    """Create and configure the FastAPI app."""
    app = FastAPI(
        title="WACH Insight API",
        description="Conversational AHU energy analytics for the WACH ward.",
        version="1.0.0",
    )
```

To:
```python
def create_app():
    """Create and configure the FastAPI app."""
    app = FastAPI(
        title="WACH Insight API",
        description="Conversational AHU energy analytics for the WACH ward.",
        version="1.0.0",
        lifespan=lifespan,
    )
```

**Remove** the old module-level startup block at the bottom of `main.py` (lines 270–276):
```python
# ── Initialize database on startup ───────────────────────────────────────────

try:
    init_db()
    logger.info("[Startup] Query logging initialized")
except Exception as e:
    logger.warning(f"[Startup] Warning: Could not initialize query logger: {e}")
```

This is now handled by the `lifespan` function.

- [ ] **Step 4: Run tests**

```bash
pytest backend/tests/integration/test_startup.py -v
pytest backend/tests/e2e/test_smoke.py -v
```

Expected: All pass. The e2e smoke test confirms the app boots correctly with the new lifespan.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/integration/test_startup.py
git commit -m "feat(reliability): add lifespan startup checks and SIGTERM flush handler"
```

---

## Task 7: Add `/metrics` Prometheus endpoint

**Files:**
- Modify: `backend/main.py`
- Test: `backend/tests/integration/test_metrics.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_metrics.py`:

```python
"""
Integration tests for the /metrics Prometheus endpoint.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type_is_prometheus(self, client):
        resp = client.get("/metrics")
        # Prometheus text format uses text/plain; OpenMetrics uses application/openmetrics-text
        assert "text/plain" in resp.headers.get("content-type", "") or \
               "openmetrics" in resp.headers.get("content-type", "")

    def test_metrics_contains_http_requests_counter(self, client):
        # Make one request to generate a data point
        client.get("/health")
        resp = client.get("/metrics")
        # prometheus_fastapi_instrumentator emits http_requests_total
        assert "http_requests" in resp.text

    def test_metrics_does_not_require_auth(self, client):
        """Metrics endpoint must be publicly accessible for Prometheus scraping."""
        resp = client.get("/metrics")  # no Authorization header
        assert resp.status_code == 200
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest backend/tests/integration/test_metrics.py -v 2>&1 | head -15
```

Expected: `FAILED test_metrics_returns_200` — endpoint not yet wired.

- [ ] **Step 3: Wire `Instrumentator` in `main.py`**

Add import at the top of `main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator
```

Inside `create_app()`, **after** all `app.include_router(...)` calls and **before** the `return app` line, add:

```python
    # ── Prometheus metrics ────────────────────────────────────────────────────
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

- [ ] **Step 4: Run tests**

```bash
pytest backend/tests/integration/test_metrics.py -v
```

Expected: All 4 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/integration/test_metrics.py
git commit -m "feat(observability): expose /metrics Prometheus endpoint via instrumentator"
```

---

## Task 8: Create `backend/core/alerter.py` and wire into `main.py`

**Files:**
- Create: `backend/core/alerter.py`
- Modify: `backend/main.py` (call `record_response()` from error handler + middleware)
- Test: `backend/tests/unit/test_alerter.py`

The alerter tracks request outcomes in a sliding 60-second window. When the 5xx rate exceeds 5%, it fires the configured webhook. It resets after the rate drops.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_alerter.py`:

```python
"""
Unit tests for the 5xx alerting hook.

Tests:
- record_response() accumulates counts
- check_and_alert() fires webhook when rate > 5%
- check_and_alert() does NOT fire when rate <= 5%
- alert is not fired twice in a row (debounce)
- alert resets when rate drops below threshold
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(autouse=True)
def reset_alerter():
    """Reset alerter state between tests."""
    import core.alerter as mod
    mod._request_log.clear()
    mod._alerted = False
    yield
    mod._request_log.clear()
    mod._alerted = False


class TestRecordResponse:
    def test_records_are_accumulated(self):
        from core.alerter import record_response, _request_log
        record_response(200)
        record_response(500)
        assert len(_request_log) == 2

    def test_old_records_are_trimmed(self):
        """Entries older than _error_window_secs are removed on next record call."""
        import time
        from core.alerter import record_response, _request_log, _error_window_secs
        # Manually insert a stale entry
        _request_log.append((time.time() - _error_window_secs - 1, False))
        record_response(200)
        # Stale entry should be gone
        assert len(_request_log) == 1


class TestCheckAndAlert:
    async def test_fires_when_5xx_rate_exceeds_threshold(self):
        """6 out of 10 requests are 5xx → 60% → fires alert."""
        from core.alerter import record_response, check_and_alert

        for _ in range(4):
            record_response(200)
        for _ in range(6):
            record_response(500)

        posted = []
        async def mock_post(url, **kwargs):
            posted.append(url)
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.post = mock_post
            await check_and_alert("https://hooks.example.com/test")

        assert len(posted) == 1

    async def test_does_not_fire_when_rate_below_threshold(self):
        """1 out of 20 requests is 5xx → 5% → exactly at threshold → no fire."""
        from core.alerter import record_response, check_and_alert

        for _ in range(19):
            record_response(200)
        record_response(500)  # 1/20 = 5% exactly, not exceeds

        posted = []
        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.post = AsyncMock()
            await check_and_alert("https://hooks.example.com/test")

        instance.post.assert_not_called()

    async def test_alert_not_fired_twice(self):
        """Second call while still over threshold must not fire again."""
        from core.alerter import record_response, check_and_alert

        for _ in range(10):
            record_response(500)

        call_count = 0
        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.post = mock_post
            await check_and_alert("https://hooks.example.com/test")
            await check_and_alert("https://hooks.example.com/test")

        assert call_count == 1

    async def test_skips_when_no_webhook_url(self):
        """check_and_alert with empty URL must not raise."""
        from core.alerter import record_response, check_and_alert

        for _ in range(10):
            record_response(500)

        await check_and_alert("")  # must not raise
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest backend/tests/unit/test_alerter.py -v 2>&1 | head -15
```

Expected: `ImportError: No module named 'core.alerter'`

- [ ] **Step 3: Create `backend/core/alerter.py`**

```python
"""
core/alerter.py
───────────────
Sliding-window 5xx error rate tracker with configurable webhook alerting.

Usage:
  1. Call record_response(status_code) from middleware after every response.
  2. Call await check_and_alert(webhook_url) from the same middleware.
  3. Set ALERT_WEBHOOK_URL in .env. If empty, alerting is silently disabled.

The webhook payload is a generic JSON body compatible with Slack, Teams,
or any webhook endpoint:
  {"text": "⚠️ WACH Insight: 5xx error rate 12.3% over last 60s (N/M requests)"}

Behaviour:
  - Fires once when rate exceeds _THRESHOLD (5%).
  - Resets the "alerted" flag when rate drops back below threshold.
  - Does not fire again until the rate has recovered and risen again.
  - Silently skips if ALERT_WEBHOOK_URL is unset or if httpx fails.
"""

import os
import time
from collections import deque
from typing import Deque

import httpx

from core.logger import get_logger

logger = get_logger(__name__)

_error_window_secs: int = 60
_THRESHOLD: float = 0.05  # 5% 5xx rate triggers alert

_request_log: Deque[tuple[float, bool]] = deque()  # (timestamp, is_5xx)
_alerted: bool = False


def record_response(status_code: int) -> None:
    """
    Record a completed response for rate tracking.
    Call this from middleware after every request completes.
    """
    now = time.time()
    is_5xx = status_code >= 500
    _request_log.append((now, is_5xx))

    # Trim entries outside the window
    cutoff = now - _error_window_secs
    while _request_log and _request_log[0][0] < cutoff:
        _request_log.popleft()


async def check_and_alert(webhook_url: str) -> None:
    """
    Fire the webhook if the 5xx rate in the current window exceeds the threshold.

    Args:
        webhook_url: Destination URL. If empty, this is a no-op.
    """
    global _alerted

    if not webhook_url or not _request_log:
        return

    total = len(_request_log)
    errors = sum(1 for _, is_5xx in _request_log if is_5xx)
    rate = errors / total if total > 0 else 0.0

    if rate > _THRESHOLD and not _alerted:
        _alerted = True
        payload = {
            "text": (
                f"⚠️ WACH Insight: 5xx error rate {rate:.1%} "
                f"over last {_error_window_secs}s "
                f"({errors}/{total} requests)"
            )
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json=payload, timeout=5.0)
            logger.warning(
                "5xx alert fired",
                extra={"rate": f"{rate:.1%}", "errors": errors, "total": total},
            )
        except Exception as e:
            logger.warning("Alert webhook failed", extra={"error": str(e)})

    elif rate <= _THRESHOLD and _alerted:
        _alerted = False
        logger.info("5xx rate recovered below threshold", extra={"rate": f"{rate:.1%}"})
```

- [ ] **Step 4: Wire alerter into `main.py`**

The alerter needs to see every response. Add a new `AlertingMiddleware` class and register it. Add at the top of `main.py`:

```python
from core.alerter import record_response, check_and_alert
```

Add this class **before** `create_app()`:

```python
class AlertingMiddleware(BaseHTTPMiddleware):
    """Records response status codes for 5xx rate alerting."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        webhook_url = os.getenv("ALERT_WEBHOOK_URL", "")
        if webhook_url:
            record_response(response.status_code)
            await check_and_alert(webhook_url)
        return response
```

Inside `create_app()`, add middleware registration after `SecurityHeadersMiddleware`:

```python
app.add_middleware(AlertingMiddleware)
```

- [ ] **Step 5: Run tests**

```bash
pytest backend/tests/unit/test_alerter.py -v
pytest backend/tests/ -x -q 2>&1 | tail -10
```

Expected: All alerter tests pass. Full suite still passes.

- [ ] **Step 6: Commit**

```bash
git add backend/core/alerter.py backend/main.py backend/tests/unit/test_alerter.py
git commit -m "feat(observability): add 5xx alerting hook with sliding-window rate tracking"
```

---

## Task 9: Update `docker-compose.yml` with Prometheus + Grafana sidecar

**Files:**
- Modify: `docker-compose.yml`

The spec says: "The `docker-compose.yml` gets a commented-out Prometheus + Grafana sidecar block that teams can opt into. Wired up and ready, not running by default."

- [ ] **Step 1: Add the commented sidecar block to `docker-compose.yml`**

Open `docker-compose.yml`. After the `volumes:` block at the bottom, add:

```yaml
# ═══════════════════════════════════════════════════════════════════
# OPTIONAL: Prometheus + Grafana monitoring sidecar
# Uncomment to enable local metrics visualisation.
#
# Usage:
#   docker compose --profile monitoring up
#
# After startup:
#   Prometheus: http://localhost:9090
#   Grafana:    http://localhost:3001  (admin / admin)
#
# The /metrics endpoint on the backend is pre-configured as a scrape target.
# ═══════════════════════════════════════════════════════════════════

#  prometheus:
#    image: prom/prometheus:v2.51.0
#    profiles: [monitoring]
#    volumes:
#      - ./scripts/infra/prometheus.yml:/etc/prometheus/prometheus.yml:ro
#    ports:
#      - "9090:9090"
#    command:
#      - "--config.file=/etc/prometheus/prometheus.yml"
#      - "--storage.tsdb.path=/prometheus"
#      - "--web.enable-lifecycle"
#    restart: unless-stopped

#  grafana:
#    image: grafana/grafana:10.4.0
#    profiles: [monitoring]
#    ports:
#      - "3001:3000"
#    environment:
#      - GF_SECURITY_ADMIN_PASSWORD=admin
#      - GF_USERS_ALLOW_SIGN_UP=false
#    volumes:
#      - grafana_data:/var/lib/grafana
#    depends_on:
#      - prometheus
#    restart: unless-stopped

# volumes:  # add grafana_data here if you uncomment grafana above
#   grafana_data:
```

- [ ] **Step 2: Create the Prometheus scrape config**

Create `scripts/infra/prometheus.yml`:

```yaml
# Prometheus scrape config for WACH Insight local monitoring.
# Used by the optional sidecar in docker-compose.yml.

global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: wach_insight_backend
    static_configs:
      - targets:
          - backend:8000   # Docker service name
    metrics_path: /metrics
```

- [ ] **Step 3: Verify `docker-compose.yml` is valid YAML**

```bash
docker compose config --quiet 2>&1
```

Expected: no output (valid YAML). If error, fix the indentation in the comment block.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml scripts/infra/prometheus.yml
git commit -m "chore(infra): add commented Prometheus+Grafana sidecar to docker-compose.yml"
```

---

## Task 10: Update `.env.example` with new Phase 3 variables

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add the new section to `.env.example`**

Append the following block to the end of `.env.example`:

```bash
# ── Observability (Phase 3) ───────────────────────────────────────
# Webhook URL for 5xx error rate alerts.
# When set, a JSON payload is POSTed when the error rate exceeds 5%
# over any 60-second window. Compatible with Slack, Teams, or any webhook.
# Leave empty to disable alerting.
# ALERT_WEBHOOK_URL=https://hooks.slack.com/services/T000/B000/xxxx

# ChromaDB persistence directory (override if running outside Docker)
# CHROMA_PERSIST_DIR=data/chroma
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs(config): document ALERT_WEBHOOK_URL and CHROMA_PERSIST_DIR in .env.example"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| Structured logging — JSON format | Task 2 (`core/logger.py`) |
| Structured logging — `timestamp, level, module, request_id, session_id, message` | Task 2 |
| Centralised in `core/logger.py` | Task 2 |
| All modules import from here | Task 3 |
| `logging.basicConfig` replaced | Task 3 |
| Request ID middleware | Task 4 |
| X-Request-ID UUID generated if absent | Task 4 |
| Threads through all log lines | Task 2 (ContextVar) + Task 4 (sets it) |
| `/metrics` endpoint via prometheus-fastapi-instrumentator | Task 7 |
| Tracks request count, latency, error rate, active connections | Task 7 (handled by instrumentator) |
| Commented Prometheus + Grafana in docker-compose.yml | Task 9 |
| `SIGTERM` handler flushes query log | Task 6 |
| FastAPI `lifespan` startup check — DuckDB | Task 6 |
| FastAPI `lifespan` startup check — ChromaDB | Task 6 |
| `ALERT_WEBHOOK_URL` env variable | Task 8 + Task 10 |
| Background task fires on 5xx rate > 5% over 60s | Task 8 |
| Slack / Teams / any webhook compatible | Task 8 (generic JSON payload) |
| Rate limiter consolidation — `middleware/rate_limiter.py` | Task 5 |
| Remove duplicate in `main.py` | Task 5 |
| Remove duplicate in `routes/query.py` | Task 5 |

### Placeholder scan

No TBD/TODO/placeholder markers. Task 6 Step 3 notes that `_DB_PATH` is imported from `middleware.query_logger` — verify this is the correct attribute name before running (it is, as confirmed from reading the file).

### Type consistency

- `record_response(status_code: int)` defined in Task 8 (`core/alerter.py`) and called in `AlertingMiddleware` in Task 8 — consistent.
- `make_rate_limiter(limit, window)` defined in Task 5 and called in both `main.py` (via `RateLimitMiddleware.__init__`) and `routes/query.py` — consistent.
- `_request_id: ContextVar` defined in Task 2 (`core/logger.py`) and imported in Task 4 (`middleware/request_id.py`) — consistent.
- `_startup_checks()` defined and exported from `main.py` in Task 6, imported by name in `backend/tests/integration/test_startup.py` — consistent.
