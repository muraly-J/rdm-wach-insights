import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from llm.circuit_breaker import CircuitBreaker, LLMUnavailableError


@pytest.fixture
def breaker():
    """Breaker with low thresholds for fast testing."""
    return CircuitBreaker(failure_threshold=2, cooldown_seconds=1)


def test_starts_closed(breaker):
    """Breaker starts in CLOSED state."""
    assert breaker.state == "closed"


def test_success_keeps_closed(breaker):
    """Successful call keeps breaker closed."""
    breaker.record_success()
    assert breaker.state == "closed"


def test_failures_trip_to_open(breaker):
    """After failure_threshold consecutive failures, state becomes OPEN."""
    breaker.record_failure()
    assert breaker.state == "closed"
    breaker.record_failure()
    assert breaker.state == "open"


def test_open_state_raises(breaker):
    """check_state raises LLMUnavailableError when OPEN."""
    breaker.record_failure()
    breaker.record_failure()
    with pytest.raises(LLMUnavailableError):
        breaker.check_state()


def test_success_resets_failure_count(breaker):
    """A success resets the consecutive failure counter."""
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert breaker.state == "closed"  # only 1 consecutive failure


def test_open_transitions_to_half_open_after_cooldown(breaker):
    """After cooldown expires, state becomes HALF_OPEN."""
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == "open"
    time.sleep(1.1)  # cooldown is 1 second
    assert breaker.state == "half_open"


def test_half_open_success_closes(breaker):
    """Success in HALF_OPEN transitions to CLOSED."""
    breaker.record_failure()
    breaker.record_failure()
    time.sleep(1.1)
    assert breaker.state == "half_open"

    breaker.record_success()
    assert breaker.state == "closed"


def test_half_open_failure_reopens(breaker):
    """Failure in HALF_OPEN transitions back to OPEN."""
    breaker.record_failure()
    breaker.record_failure()
    time.sleep(1.1)
    assert breaker.state == "half_open"

    breaker.record_failure()
    assert breaker.state == "open"
