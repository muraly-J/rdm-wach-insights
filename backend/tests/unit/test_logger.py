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
