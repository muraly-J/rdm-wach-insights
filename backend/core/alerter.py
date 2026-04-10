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
