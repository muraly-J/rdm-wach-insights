from __future__ import annotations

"""
config.py
─────────
Single source of truth for all environment-sourced configuration.

All modules should import the `settings` singleton:

    from config import settings
    url = settings.influx_url

No module other than this file may call os.getenv() directly.
Backward-compatible getter functions are provided for callers that
haven't been migrated yet — they delegate to `settings`.
"""

from pathlib import Path

from core.logger import get_logger
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent

# Known ISO 3166-2:MY subdivision codes accepted by the holidays package.
_MY_SUBDIVISIONS = frozenset({
    "JHR", "KDH", "KTN", "KUL", "LBN", "MLK", "NSN", "PHG",
    "PJY", "PLS", "PNG", "PRK", "SBH", "SGR", "SWK", "TRG",
})


class Settings(BaseSettings):
    """
    All WACH Insight configuration, sourced from environment variables
    and .env files. Field names map to uppercased env var names
    (e.g. `influx_url` → `INFLUX_URL`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── InfluxDB ──────────────────────────────────────────────────────────────
    influx_url: str = "http://localhost:8086"
    influx_token: str = ""
    influx_org: str = "wach"
    influx_bucket: str = "wach_bucket_3"
    influx_skip_tls: bool = False

    # ── LLM (LM Studio / Qwen) ───────────────────────────────────────────────
    lms_base_url: str = "http://localhost:1234/v1"
    lms_model: str = "qwen/qwen3-coder-next"
    lms_api_key: str = "lm-studio-placeholder"
    lms_timeout: float = 60.0
    enable_llm: bool = False

    # ── RAG / Vector store ────────────────────────────────────────────────────
    chroma_persist_dir: str = "data/chroma"
    rag_collection: str = "wach_docs"
    ward_config_path: str | None = None

    # ── Auth & Security ───────────────────────────────────────────────────────
    api_key: str | None = None
    dev_api_key: str = "dev-key-change-in-production"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,https://demo-wach-insight.vercel.app,https://rdm-wach-insights.vercel.app"

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # ── Observability ─────────────────────────────────────────────────────────
    alert_webhook_url: str = ""

    # ── Building identity ─────────────────────────────────────────────────────
    wach_building_name: str = "Healthcare Facility"
    wach_department: str = "Department"
    hospital_id: str = "wach"

    # ── Geographic ────────────────────────────────────────────────────────────
    hospital_lat: float = 3.139       # default: Kuala Lumpur central; override via HOSPITAL_LAT env var
    hospital_lon: float = 101.6869    # default: Kuala Lumpur central; override via HOSPITAL_LON env var
    holiday_subdivision: str | None = None  # None = federal holidays only; e.g. "KUL", "SGR" for state holidays

    @field_validator("holiday_subdivision")
    @classmethod
    def _validate_holiday_subdivision(cls, v: str | None) -> str | None:
        """Accept None/empty (→ None) or a known MY subdivision code (normalised to upper)."""
        if v is None or v == "":
            return None
        v_upper = v.upper()
        if v_upper not in _MY_SUBDIVISIONS:
            raise ValueError(
                f"holiday_subdivision must be one of {sorted(_MY_SUBDIVISIONS)} or None; got {v!r}"
            )
        return v_upper

    # ── LLM Circuit Breaker ───────────────────────────────────────────────────
    llm_failure_threshold: int = 3
    llm_cooldown_seconds: float = 300.0

    # ── Debug flags ───────────────────────────────────────────────────────────
    csv_debug: bool = False

    # ── Telegram notifications ─────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_recipient_technician: str = ""
    telegram_recipient_manager: str = ""
    telegram_recipient_on_call: str = ""

    # Group chat IDs (bot interactive mode)
    managers_chat_id: str = ""
    engineers_chat_id: str = ""
    technicians_chat_id: str = ""
    # JSON dict of technician names → telegram user IDs, e.g. '{"Alice": "123456"}'
    technicians_json: str = "{}"

    # ── Watchman (background health monitor) ──────────────────────────────────
    watchman_interval_seconds: int = 1800          # 30 minutes
    watchman_critical_threshold: float = 40.0      # FAIR < 40 → critical
    watchman_warning_threshold: float = 60.0       # FAIR < 60 → warning
    watchman_cooldown_critical_hours: int = 4
    watchman_cooldown_warning_hours: int = 24
    watchman_enabled: bool = True

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list (splits the comma-separated string)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_api_key(self) -> str:
        """Return the active API key, preferring API_KEY over DEV_API_KEY."""
        key = self.api_key or self.dev_api_key
        if not key:
            raise RuntimeError(
                "API_KEY environment variable is required. "
                "Set it in your .env file before starting the server."
            )
        return key

    @model_validator(mode="after")
    def warn_on_insecure_influx(self) -> Settings:
        """Warn (not crash) if InfluxDB uses plain HTTP on a non-localhost host."""
        url = self.influx_url
        is_local = url.startswith("http://localhost") or url.startswith("http://127.0.0.1")
        if not is_local and not self.influx_skip_tls and url.startswith("http://"):
            logger.warning(
                "INFLUX_URL uses plain HTTP on a non-localhost host. "
                "Set INFLUX_SKIP_TLS=true to suppress this warning, "
                "or switch to HTTPS for production.",
                extra={"influx_url": url},
            )
        return self

    # ── Data paths (derived from BASE_DIR) ───────────────────────────────────

    @property
    def data_dir(self) -> Path:
        """Absolute path to the backend data directory."""
        return BASE_DIR / "data"

    @property
    def exports_dir(self) -> Path:
        """Absolute path to the backend exports directory."""
        return BASE_DIR / "exports"


# ── Module-level singleton ────────────────────────────────────────────────────
# Import this in other modules: `from config import settings`
settings = Settings()

# Ensure runtime directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.exports_dir.mkdir(parents=True, exist_ok=True)


# ── Backward-compatible getters ───────────────────────────────────────────────
# These exist so callers written before this refactor still work.
# New code should use `settings.field_name` directly.


def get_influx_url() -> str:
    """Get InfluxDB URL."""
    return settings.influx_url


def get_influx_token() -> str:
    """Get InfluxDB API token."""
    token = settings.influx_token
    if not token:
        raise ValueError(
            "INFLUX_TOKEN environment variable is required. "
            "Set to a valid InfluxDB API token with read access."
        )
    return token


def get_influx_org() -> str:
    """Get InfluxDB organization name."""
    return settings.influx_org


def get_influx_bucket() -> str:
    """Get InfluxDB bucket name."""
    return settings.influx_bucket


def get_influx_skip_tls() -> bool:
    """Get InfluxDB skip TLS setting."""
    return settings.influx_skip_tls


def get_lms_base_url() -> str:
    """Get LM Studio base URL."""
    return settings.lms_base_url


def get_lms_model() -> str:
    """Get LM Studio model name."""
    return settings.lms_model


def get_lms_api_key() -> str:
    """Get LM Studio API key."""
    return settings.lms_api_key


def get_building_name() -> str:
    """Get building/facility name."""
    return settings.wach_building_name


def get_hospital_id() -> str:
    """Get hospital/facility identifier."""
    return settings.hospital_id


def get_department() -> str:
    """Get department or wing within the building."""
    return settings.wach_department


def get_app_env() -> str:
    """Get application environment."""
    return settings.app_env


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins as a list."""
    return settings.cors_origins_list


def get_debug_mode() -> bool:
    """Get debug mode setting."""
    return settings.debug


def get_rate_limit_requests() -> int:
    """Get maximum requests per window."""
    return settings.rate_limit_requests


def get_rate_limit_window() -> int:
    """Get rate limit window in seconds."""
    return settings.rate_limit_window


def get_data_dir() -> Path:
    """Get path to data directory."""
    return settings.data_dir


def get_exports_dir() -> Path:
    """Get path to exports directory."""
    return settings.exports_dir
