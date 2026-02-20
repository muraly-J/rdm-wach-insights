"""
backend/config.py
─────────────────
Centralized configuration management for WACH Insight.

This module handles:
- Loading environment variables from .env files
- Providing default values for optional settings
- Validating required configuration
"""

import os
from pathlib import Path


# ── Base paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent


# ── Helper to load .env files ───────────────────────────────────────────────
def load_env_files():
    """Load .env files in order of precedence (later overrides earlier)."""
    from dotenv import load_dotenv

    # Try multiple locations for .env files
    env_locations = [
        BASE_DIR / ".env",              # Root of backend
        BASE_DIR.parent / ".env",       # Project root (for deployment)
    ]

    for env_path in env_locations:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[config] Loaded environment from {env_path}")


# ── InfluxDB Configuration ────────────────────────────────────────────────────
def get_influx_url() -> str:
    """Get InfluxDB URL."""
    return os.getenv("INFLUX_URL", "http://localhost:8086")


def get_influx_token() -> str:
    """Get InfluxDB API token."""
    token = os.getenv("INFLUX_TOKEN")
    if not token:
        raise ValueError(
            "INFLUX_TOKEN is required. Set it in your .env file or environment."
        )
    return token


def get_influx_org() -> str:
    """Get InfluxDB organization name."""
    return os.getenv("INFLUX_ORG", "wach")


def get_influx_bucket() -> str:
    """Get InfluxDB bucket name."""
    return os.getenv("INFLUX_BUCKET", "wach_bucket_3")


# ── LM Studio (LLM) Configuration ─────────────────────────────────────────────
def get_lms_base_url() -> str:
    """Get LM Studio base URL."""
    return os.getenv("LMS_BASE_URL", "http://localhost:1234/v1")


def get_lms_model() -> str:
    """Get LM Studio model name."""
    return os.getenv("LMS_MODEL", "qwen/qwen3-coder-next")


def get_lms_api_key() -> str:
    """Get LM Studio API key (placeholder for lm-studio)."""
    return os.getenv("LMS_API_KEY", "lm-studio")


# ── Application Configuration ───────────────────────────────────────────────
def get_app_env() -> str:
    """Get application environment (development/production)."""
    return os.getenv("APP_ENV", "development")


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins as a list."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


# ── Security Configuration ───────────────────────────────────────────────────
def get_debug_mode() -> bool:
    """Get debug mode setting."""
    return os.getenv("DEBUG", "false").lower() == "true"


def get_rate_limit_requests() -> int:
    """Get maximum requests per window."""
    return int(os.getenv("RATE_LIMIT_REQUESTS", "20"))


def get_rate_limit_window() -> int:
    """Get rate limit window in seconds."""
    return int(os.getenv("RATE_LIMIT_WINDOW", "60"))


# ── Data/Output paths ───────────────────────────────────────────────────────
def get_data_dir() -> Path:
    """Get path to data directory."""
    return BASE_DIR / "data"


def get_exports_dir() -> Path:
    """Get path to exports directory."""
    return BASE_DIR / "exports"


# ── Initialization ───────────────────────────────────────────────────────────
def init_config():
    """Initialize configuration and validate requirements."""
    load_env_files()
    
    # Validate required settings
    try:
        get_influx_token()
    except ValueError as e:
        if get_app_env() == "production":
            raise
        print(f"[config] Warning: {e}")
    
    # Ensure directories exist
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_exports_dir().mkdir(parents=True, exist_ok=True)


# Call init on module import
init_config()
