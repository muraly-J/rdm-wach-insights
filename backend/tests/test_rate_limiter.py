import os
import sys
import time
import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from middleware.rate_limiter import InMemoryRateLimiter


def test_allows_under_limit():
    """Requests under the limit should pass without error."""
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.1")
    # 3 requests = at the limit, should still pass


def test_blocks_over_limit():
    """Requests over the limit should raise HTTPException 429."""
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.1")
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("192.168.1.1")
    assert exc_info.value.status_code == 429


def test_different_keys_independent():
    """Different IPs should have independent limits."""
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    limiter.check("192.168.1.1")
    limiter.check("192.168.1.2")  # different IP, should pass


def test_window_resets():
    """After the window expires, the limit resets."""
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=1)
    limiter.check("192.168.1.1")
    with pytest.raises(HTTPException):
        limiter.check("192.168.1.1")

    time.sleep(1.1)  # wait for window to expire
    limiter.check("192.168.1.1")  # should pass now
