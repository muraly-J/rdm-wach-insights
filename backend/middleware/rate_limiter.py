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
from collections.abc import Callable
from typing import Protocol

from config import settings
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiter(Protocol):
    """Protocol for rate limiters — allows swapping to Redis later."""

    def check(self, key: str) -> None:
        """Raise HTTPException(429) if rate limit exceeded."""
        ...


class InMemoryRateLimiter:
    """Sliding-window rate limiter using in-memory storage."""

    def __init__(self, max_requests: int, window_seconds: int):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.time()
        hits = [t for t in self._store[key] if now - t < self._window_seconds]
        hits.append(now)
        self._store[key] = hits
        if len(hits) > self._max_requests:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests. Please wait a moment before trying again."
                },
            )


def get_rate_limiter() -> RateLimiter:
    """Factory — returns configured InMemoryRateLimiter."""
    return InMemoryRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window,
    )


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
