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
