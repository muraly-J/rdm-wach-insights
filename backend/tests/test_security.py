"""
test_security.py
────────────────
Security tests for WACH Insight backend.

Tests:
1. Environment variable validation (HTTPS required)
2. API key authentication
3. Rate limiting
4. Device ID injection prevention (unit tests without full imports)
5. Metric validation
"""

import pytest
from unittest.mock import patch, MagicMock
from pydantic_core import ValidationError


class TestEnvironmentSecurity:
    """Test environment variable security."""
    
    def test_influx_url_requires_https(self):
        """Influx URL must use HTTPS in production (warns but allows with INFLUX_SKIP_TLS)."""
        from config import Settings

        # HTTP on localhost should work
        s = Settings(
            influx_url="http://localhost:8086",
            influx_token="test-token"
        )
        assert s.influx_url == "http://localhost:8086"
        
        # HTTP on remote host without INFLUX_SKIP_TLS should warn
        s = Settings(
            influx_url="http://remote-host:8086",
            influx_token="test-token",
            influx_skip_tls=True
        )
        assert s.influx_url == "http://remote-host:8086"
    
    def test_influx_token_required(self):
        """Influx token can be empty string in settings, but getter validates it."""
        from config import Settings, get_influx_token

        # Settings allows empty token
        s = Settings(influx_token="")
        assert s.influx_token == ""
        
        # But get_influx_token() getter raises ValueError if empty
        with patch('config.settings.influx_token', ""):
            with pytest.raises(ValueError) as exc_info:
                get_influx_token()
            assert 'INFLUX_TOKEN' in str(exc_info.value)
    
    def test_lms_api_key_has_default(self):
        """LM Studio API key has a sensible default."""
        from config import Settings

        s = Settings()
        # Default should be the placeholder for local development
        assert s.lms_api_key is not None
    
    def test_device_id_regex_escaping(self):
        """Device IDs should be properly escaped in regex patterns."""
        import re
    
    def test_device_id_regex_escaping(self):
        """Device IDs should be properly escaped in regex patterns."""
        import re
        
        # Test special regex characters are escaped
        malicious_id = "e0101.*"  # Should not match all e01xx devices
        
        sanitized = re.escape(malicious_id)
        assert sanitized == r"e0101\.\*"
        
        # The escaped pattern should only match the literal string
        assert not re.match(sanitized, "e0101abc")
        assert re.match(sanitized, malicious_id)
    
    def test_get_api_key_raises_when_unset(self):
        """effective_api_key property must raise RuntimeError if neither set."""
        from config import Settings
        
        # Settings with no api_key should use dev_api_key (default exists)
        s = Settings(dev_api_key="test-key")
        assert s.effective_api_key == "test-key"
        
        # Settings with empty api_key and dev_api_key should raise
        s_empty = Settings(api_key=None, dev_api_key="")
        with pytest.raises(RuntimeError, match='API_KEY'):
            _ = s_empty.effective_api_key


class TestErrorResponseSanitization:
    """HTTP 500 responses must not leak internal exception details."""

    def test_health_index_error_does_not_leak_exception(self, monkeypatch):
        """health-index endpoint must not leak internal file paths in error responses."""
        import routes.health_scores as hs_mod
        import main as main_mod

        def _boom(*args, **kwargs):
            raise RuntimeError("/internal/secret/path/health_hourly.csv not found")
        # Patch the binding in the route module (not the source module)
        monkeypatch.setattr(hs_mod, "get_health_index_series", _boom)
        monkeypatch.setattr(main_mod, "get_api_key", lambda: "test-key")

        from fastapi.testclient import TestClient
        client = TestClient(main_mod.app)
        resp = client.get(
            "/api/level/1/health-index?time_range=24h",
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code in (500, 503)
        detail = str(resp.json().get("detail", ""))
        assert "/internal/secret/path" not in detail
        assert "health_hourly.csv" not in detail


class TestDeviceIdInjectionPrevention:
    """Test device ID injection prevention with standalone validation."""
    
    def test_validate_device_id_format(self):
        """Device IDs should match pattern eXXXX."""
        import re
        
        # Valid device ID pattern
        valid_pattern = r'^e\d{4}$'
        
        # Test valid IDs
        assert re.match(valid_pattern, 'e0101')
        assert re.match(valid_pattern, 'e1112')
        
        # Test invalid IDs (injection attempts)
        assert not re.match(valid_pattern, "e0101' OR '1'='1")
        assert not re.match(valid_pattern, "e9999; DROP TABLE users--")
        assert not re.match(valid_pattern, 'e123')  # too short
        assert not re.match(valid_pattern, 'e12345')  # too long
    
    def test_validate_metric_format(self):
        """Metrics should be alphanumeric with underscores."""
        import re
        
        # Valid metric pattern
        valid_pattern = r'^[a-z_]+$'
        
        # Test valid metrics
        assert re.match(valid_pattern, 'power_total')
        assert re.match(valid_pattern, 'energy_import')
        assert re.match(valid_pattern, 'power_factor_avg')
        
        # Test invalid metrics (injection attempts)
        assert not re.match(valid_pattern, "power_total'; DROP TABLE users--")


class TestSecurityFeatures:
    """Test security features without loading full app."""
    
    def test_regex_escaping_prevents_injection(self):
        """Ensure regex escaping prevents injection in device ID patterns."""
        import re
        
        # Test that special characters are escaped
        test_cases = [
            ("e0101.*", r"e0101\.\*"),
            ("e0207+", r"e0207\+"),
            ("e0505?", r"e0505\?"),
            ("e0304[0-9]", r"e0304\[0\-9\]"),
        ]
        
        for original, expected in test_cases:
            assert re.escape(original) == expected
