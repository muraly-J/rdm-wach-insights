"""
Unit tests for the 5xx alerting hook.

Tests:
- record_response() accumulates counts
- check_and_alert() fires webhook when rate > 5%
- check_and_alert() does NOT fire when rate <= 5%
- alert is not fired twice in a row (debounce)
- alert resets when rate drops below threshold
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
        from core.alerter import _request_log, record_response
        record_response(200)
        record_response(500)
        assert len(_request_log) == 2

    def test_old_records_are_trimmed(self):
        """Entries older than _error_window_secs are removed on next record call."""
        import time

        from core.alerter import _error_window_secs, _request_log, record_response
        # Manually insert a stale entry
        _request_log.append((time.time() - _error_window_secs - 1, False))
        record_response(200)
        # Stale entry should be gone
        assert len(_request_log) == 1


class TestCheckAndAlert:
    async def test_fires_when_5xx_rate_exceeds_threshold(self):
        """6 out of 10 requests are 5xx → 60% → fires alert."""
        from core.alerter import check_and_alert, record_response

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
        from core.alerter import check_and_alert, record_response

        for _ in range(19):
            record_response(200)
        record_response(500)  # 1/20 = 5% exactly, not exceeds

        with patch("httpx.AsyncClient") as MockClient:
            instance = MockClient.return_value.__aenter__.return_value
            instance.post = AsyncMock()
            await check_and_alert("https://hooks.example.com/test")

        instance.post.assert_not_called()

    async def test_alert_not_fired_twice(self):
        """Second call while still over threshold must not fire again."""
        from core.alerter import check_and_alert, record_response

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
        from core.alerter import check_and_alert, record_response

        for _ in range(10):
            record_response(500)

        await check_and_alert("")  # must not raise
