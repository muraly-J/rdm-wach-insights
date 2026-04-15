"""
llm/circuit_breaker.py
──────────────────────
Lightweight circuit breaker for LLM calls.

States: CLOSED → OPEN → HALF_OPEN → CLOSED (or back to OPEN).
Prevents repeated 60-second timeouts when LM Studio is down.
"""

import os
import time
import threading


class LLMUnavailableError(Exception):
    """Raised when the circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    In-memory circuit breaker with three states.

    Args:
        failure_threshold: Consecutive failures to trip the breaker.
        cooldown_seconds: How long OPEN state lasts before probing.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        cooldown_seconds: float | None = None,
    ):
        self._failure_threshold = (
            failure_threshold if failure_threshold is not None
            else int(os.getenv("LLM_FAILURE_THRESHOLD", "3"))
        )
        self._cooldown_seconds = (
            cooldown_seconds if cooldown_seconds is not None
            else float(os.getenv("LLM_COOLDOWN_SECONDS", "300"))
        )
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._consecutive_failures < self._failure_threshold:
                return "closed"
            # Breaker has been tripped
            if self._opened_at is None:
                return "open"
            elapsed = time.time() - self._opened_at
            if elapsed >= self._cooldown_seconds:
                return "half_open"
            return "open"

    def check_state(self) -> None:
        """Raise LLMUnavailableError if the breaker is OPEN."""
        s = self.state
        if s == "open":
            raise LLMUnavailableError(
                "AI is temporarily unavailable, please try again in a few minutes."
            )
        # half_open and closed: allow the call through

    def record_success(self) -> None:
        """Record a successful call. Resets failure counter."""
        with self._lock:
            self._consecutive_failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        """Record a failed call. May trip the breaker."""
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._opened_at = time.time()
