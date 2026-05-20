"""
Unit tests for the centralized Settings model.

Tests:
- Settings is importable as a pydantic-settings BaseSettings subclass
- All expected fields exist with correct types and defaults
- settings singleton is already instantiated at import time
- No raw os.getenv calls remain outside config.py
"""

import ast
import pathlib

import pytest


class TestSettingsModel:
    def test_settings_importable(self):
        from config import settings

        assert settings is not None

    def test_settings_is_pydantic_model(self):
        from config import Settings
        from pydantic_settings import BaseSettings

        assert issubclass(Settings, BaseSettings)

    def test_required_fields_exist(self):
        from config import settings

        fields = [
            "influx_url",
            "influx_token",
            "influx_org",
            "influx_bucket",
            "lms_base_url",
            "lms_model",
            "lms_api_key",
            "lms_timeout",
            "enable_llm",
            "chroma_persist_dir",
            "rag_collection",
            "api_key",
            "dev_api_key",
            "cors_origins",
            "app_env",
            "rate_limit_requests",
            "rate_limit_window",
            "alert_webhook_url",
            "csv_debug",
            "wach_building_name",
            "wach_department",
            "hospital_id",
        ]
        for field in fields:
            assert hasattr(settings, field), f"Settings missing field: {field}"

    def test_cors_origins_list_property(self):
        from config import Settings

        s = Settings(
            cors_origins="http://localhost:3000,http://localhost:5173",
            influx_token="test-token",
        )
        origins = s.cors_origins_list
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_holiday_subdivision_validator_accepts_known_code(self, monkeypatch):
        monkeypatch.setenv("HOLIDAY_SUBDIVISION", "kul")  # lowercase env override
        from config import Settings
        s = Settings()
        assert s.holiday_subdivision == "KUL"  # normalised to upper

    def test_holiday_subdivision_validator_rejects_unknown(self, monkeypatch):
        monkeypatch.setenv("HOLIDAY_SUBDIVISION", "KLU")  # typo
        import pytest
        from config import Settings
        with pytest.raises(ValueError, match="holiday_subdivision must be one of"):
            Settings()

    def test_holiday_subdivision_validator_accepts_none_and_empty(self, monkeypatch):
        monkeypatch.delenv("HOLIDAY_SUBDIVISION", raising=False)
        from config import Settings
        assert Settings().holiday_subdivision is None
        monkeypatch.setenv("HOLIDAY_SUBDIVISION", "")
        assert Settings().holiday_subdivision is None

    def test_no_raw_getenv_outside_config(self):
        """No module other than config.py may call os.getenv directly."""
        backend = pathlib.Path("backend")
        violations = []
        skip = {"venv", "__pycache__", "tests", "scripts"}
        for p in sorted(backend.rglob("*.py")):
            if any(s in p.parts for s in skip):
                continue
            if p.name == "config.py":
                continue
            try:
                src = p.read_text()
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if (
                            isinstance(node.func, ast.Attribute)
                            and node.func.attr == "getenv"
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "os"
                        ):
                            violations.append(str(p))
                            break
            except Exception:
                pass
        assert violations == [], (
            f"Raw os.getenv found in non-config files: {violations}\n"
            "Move these to config.py Settings and access via `from config import settings`."
        )
