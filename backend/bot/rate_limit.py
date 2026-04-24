from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """Per-user token bucket rate limiter."""

    def __init__(self, max_calls: int, period_seconds: int):
        """max_calls per period_seconds window (sliding)."""
        self._max = max_calls
        self._period = period_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, user_id: str) -> bool:
        """Returns True if the request is within the rate limit."""
        now = time.time()
        with self._lock:
            calls = self._buckets[user_id]
            # Remove calls outside the window
            calls[:] = [t for t in calls if now - t < self._period]
            if len(calls) >= self._max:
                return False
            calls.append(now)
            return True


def _make_default_limiter() -> RateLimiter:
    from bot.config import BOT_RATE_LIMIT_DEFAULT
    return RateLimiter(BOT_RATE_LIMIT_DEFAULT, 60)


def _make_ask_limiter() -> RateLimiter:
    from bot.config import BOT_RATE_LIMIT_ASK
    return RateLimiter(BOT_RATE_LIMIT_ASK, 300)  # 5 per 5 min


# Singletons initialised at import time — no lazy-init race condition.
_default_limiter: RateLimiter = _make_default_limiter()
_ask_limiter: RateLimiter = _make_ask_limiter()


def get_default_limiter() -> RateLimiter:
    return _default_limiter


def get_ask_limiter() -> RateLimiter:
    return _ask_limiter
