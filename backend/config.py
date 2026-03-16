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
def get_influx_skip_tls() -> bool:
    """Return True if INFLUX_SKIP_TLS=true, meaning HTTP is allowed for non-localhost hosts.

    Use this when InfluxDB is running without TLS (plain HTTP) on a remote server.
    Only set this if the connection is on a trusted private network.
    """
    return os.getenv("INFLUX_SKIP_TLS", "false").lower() == "true"


def get_influx_url() -> str:
    """Get InfluxDB URL.

    HTTP is allowed for localhost and when INFLUX_SKIP_TLS=true.
    Otherwise HTTPS is required for non-localhost hosts.

    Allowed formats:
    - Local development: http://localhost:8086 or http://127.0.0.1:8086
    - Remote (no TLS):   http://178.128.53.199:8086  (requires INFLUX_SKIP_TLS=true)
    - Remote (TLS):      https://178.128.53.199:8086
    """
    url = os.getenv("INFLUX_URL")
    if not url:
        raise ValueError(
            "INFLUX_URL environment variable is required. "
            "Set to your InfluxDB URL (e.g., http://localhost:8086 or https://cloud.influxdata.com)."
        )

    # Always allow HTTP for localhost
    if url.startswith("http://localhost") or url.startswith("http://127.0.0.1"):
        return url

    # Allow HTTP for remote hosts only when explicitly opted in
    if url.startswith("http://") and get_influx_skip_tls():
        return url

    # For other hosts, require HTTPS
    if not url.startswith("https://"):
        raise ValueError(
            "INFLUX_URL must use HTTPS for secure communication. "
            f"Received: {url}\n\n"
            "For local development, use: http://localhost:8086 or http://127.0.0.1:8086\n"
            "If your InfluxDB server runs plain HTTP (no TLS), set INFLUX_SKIP_TLS=true in .env\n"
            "For production with TLS, use: https://178.128.53.199:8086"
        )
    return url


def get_influx_token() -> str:
    """Get InfluxDB API token."""
    token = os.getenv("INFLUX_TOKEN")
    if not token:
        raise ValueError(
            "INFLUX_TOKEN environment variable is required. "
            "Set to a valid InfluxDB API token with read access."
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
    api_key = os.getenv("LMS_API_KEY")
    if not api_key:
        # Return default placeholder for local development without LLM
        return "lm-studio-placeholder"
    # Allow lm-studio placeholder for local development without valid API
    if api_key == "lm-studio":
        return "lm-studio-placeholder"
    return api_key


# ── Gemini Configuration ──────────────────────────────────────────────────────
def get_gemini_api_key() -> str:
    """Get Google AI Studio API key."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is required. "
            "Get a key from https://aistudio.google.com/app/apikey"
        )
    return key


def get_gemini_model() -> str:
    """Get Gemini generative model name."""
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def get_gemini_embed_model() -> str:
    """Get Gemini embedding model name."""
    return os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")


# ── Building Identity ─────────────────────────────────────────────────────────
def get_building_name() -> str:
    return os.getenv("WACH_BUILDING_NAME", "Hospital Kuala Lumpur")


def get_department() -> str:
    return os.getenv("WACH_DEPARTMENT", "Women and Children Hospital")


# ── Application Configuration ───────────────────────────────────────────────
def get_app_env() -> str:
    """Get application environment (development/production)."""
    return os.getenv("APP_ENV", "development")


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins as a list."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
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

    # Ensure directories exist
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_exports_dir().mkdir(parents=True, exist_ok=True)


# Call init on module import
init_config()
