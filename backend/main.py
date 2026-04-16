"""
FastAPI app entry point.
- CORS configured for localhost frontend
- Security headers on every response
- Static file serving for production build

For local development:
  - Run backend: ./start.sh (port 8081)
  - Run frontend: cd frontend && npm run dev (port 3000)

Backend and frontend communicate via /api endpoints.
"""
import os
import signal
import sys
from collections.abc import Callable
from contextlib import asynccontextmanager

from config import settings
from core.alerter import check_and_alert, record_response
from core.logger import get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from middleware.query_logger import init_db
from middleware.rate_limiter import RateLimitMiddleware
from middleware.request_id import RequestIDMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from routes.dashboard import router as dashboard_router
from routes.delta_forecast import router as delta_forecast_router
from routes.financial_impact import router as financial_impact_router
from routes.forecast import router as forecast_router
from routes.health_scores import router as health_scores_router
from routes.measurements import router as measurements_router
from routes.on_off_periods import router as on_off_periods_router
from routes.work_orders import router as work_orders_router
from routes.predictions import router as predictions_router
from routes.query import router as query_router
from routes.site_summary import router as site_summary_router
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = get_logger(__name__)


# ── API Key Authentication Middleware ────────────────────────────────────────
def get_api_key() -> str:
    """Get the API key from environment. Raises RuntimeError if unset."""
    return settings.effective_api_key


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API Key Authentication Middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for health check and Swagger UI endpoints
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/metrics"):
            return await call_next(request)

        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get API key from Authorization header
        auth_header = request.headers.get("Authorization", "")

        # Also allow API key as query parameter (for browsers)
        api_key_param = request.query_params.get("api_key")

        if not auth_header and not api_key_param:
            response = JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "error": "Missing API key",
                        "suggestion": "Include 'Authorization: Bearer <api_key>' header or '?api_key=<key>' query parameter"
                    }
                }
            )
            return response

        # Extract API key from "Bearer <token>" format
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        else:
            api_key = auth_header

        # Check query param if header not present
        if not api_key and api_key_param:
            api_key = api_key_param

        # Validate API key
        expected_api_key = get_api_key()
        if api_key != expected_api_key:
            response = JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "error": "Invalid API key",
                        "suggestion": "Please provide a valid API key"
                    }
                }
            )
            return response

        return await call_next(request)


# ── Security headers middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers['X-Content-Type-Options']    = 'nosniff'
        response.headers['X-Frame-Options']           = 'DENY'
        response.headers['X-XSS-Protection']          = '1; mode=block'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']        = 'camera=(), microphone=(), geolocation=()'

        # --- CSP: Allow same-origin + Vercel/Cloudflare for production ---
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://*.vercel.app https://*.railway.app; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp
        return response


# ── Alerting middleware ───────────────────────────────────────────────────────

class AlertingMiddleware(BaseHTTPMiddleware):
    """Records response status codes for 5xx rate alerting."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        webhook_url = settings.alert_webhook_url
        if webhook_url:
            record_response(response.status_code)
            await check_and_alert(webhook_url)
        return response


# ── Startup checks and SIGTERM handler ────────────────────────────────────────

def _handle_sigterm(*_) -> None:
    """Flush query log and shut down cleanly on SIGTERM (e.g. Docker stop)."""
    logger.info("SIGTERM received — flushing query log and shutting down")
    # SQLite commits happen inside context managers in query_logger.py,
    # so no explicit flush is needed; log the path for ops visibility.
    from middleware.query_logger import _DB_PATH
    logger.info("Query log location", extra={"db_path": str(_DB_PATH)})
    sys.exit(0)


def _startup_checks() -> None:
    """
    Verify DuckDB and ChromaDB are accessible on boot.
    Logs a warning (does not crash) if either is unavailable — this allows
    the app to start without data and serve the /health endpoint.
    """
    import duckdb

    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "healthdb.duckdb")
    if os.path.exists(db_path):
        try:
            conn = duckdb.connect(db_path, read_only=True)
            conn.close()
            logger.info("DuckDB startup check passed", extra={"db": db_path})
        except Exception as e:
            logger.error("DuckDB startup check failed — health scores may be unavailable", extra={"error": str(e)})
    else:
        logger.warning("DuckDB not found — health scores will be empty on first boot", extra={"db": db_path})

    chroma_dir = str(settings.chroma_persist_dir)
    if os.path.isdir(chroma_dir):
        logger.info("ChromaDB directory present", extra={"dir": chroma_dir})
    else:
        logger.warning("ChromaDB directory not found — RAG will be unavailable until ingestion runs", extra={"dir": chroma_dir})


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan: startup checks + SIGTERM registration."""
    _startup_checks()
    signal.signal(signal.SIGTERM, _handle_sigterm)
    try:
        init_db()
        logger.info("Query logging initialized")
    except Exception as e:
        logger.warning("Could not initialize query logger", extra={"error": str(e)})
    yield
    logger.info("Application shutdown complete")


# ── App setup ─────────────────────────────────────────────────────────────────

def get_cors_origins() -> list[str]:
    """Get CORS origins from env or use defaults."""
    return settings.cors_origins_list


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(
        title="WACH Insight API",
        description="Conversational AHU energy analytics for the WACH ward.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Declare Bearer auth scheme so Swagger UI shows the Authorize button
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema.setdefault("components", {})["securitySchemes"] = {
            "BearerAuth": {"type": "http", "scheme": "bearer"}
        }
        schema["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    # Add security middleware in order of execution (first to last)
    app.add_middleware(APIKeyAuthMiddleware)  # Authentication
    app.add_middleware(RateLimitMiddleware)   # Rate limiting
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AlertingMiddleware)    # 5xx error rate alerting
    app.add_middleware(RequestIDMiddleware)   # Request ID tracing

    # CORS — restrict to specific origins (not all methods/headers)
    _cors_origins = get_cors_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],  # Restricted methods
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID"
        ],  # Restricted headers
    )

    # Include all routers with /api prefix for consistent routing
    app.include_router(forecast_router, prefix="/api")
    app.include_router(query_router, prefix="/api")
    app.include_router(dashboard_router)
    app.include_router(health_scores_router, prefix="/api")

    from routes.chat import router as chat_router
    app.include_router(chat_router, prefix="/api")
    app.include_router(predictions_router, prefix="/api")
    app.include_router(measurements_router, prefix="/api")
    app.include_router(delta_forecast_router, prefix="/api")
    app.include_router(financial_impact_router, prefix="/api")
    app.include_router(site_summary_router, prefix="/api")
    app.include_router(on_off_periods_router, prefix="/api")
    app.include_router(work_orders_router, prefix="/api")

    @app.get('/health')
    async def health() -> dict:
        return {'status': 'ok'}

    # Static files for local development
    DIST_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')

    if os.path.isdir(DIST_DIR):
        app.mount('/assets', StaticFiles(directory=os.path.join(DIST_DIR, 'assets')), name='assets')

    # ── Prometheus metrics ────────────────────────────────────────────────────
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    return app

# ── Create the app instance ───────────────────────────────────────────────────

app = create_app()


# ── Background ETL backfill (runs once on cold start when DB is empty) ────────

def _run_etl_backfill():
    """
    Run health ETL in the background if the DuckDB is empty.
    Called once at startup — safe to skip if InfluxDB is unreachable.
    """
    import subprocess
    import threading

    def _backfill():
        try:
            from core.healthdb import HealthDB
            db = HealthDB()
            latest = db.get_latest_timestamp()
            if latest is not None:
                logger.info("[ETL] DB already has data (latest: %s) — skipping backfill", latest)
                return
            logger.info("[ETL] DB is empty — running health ETL backfill...")
            script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'etl', 'run_health_etl.py')
            result = subprocess.run(
                [sys.executable, script, '--level', 'all'],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                logger.info("[ETL] Backfill completed successfully")
            else:
                logger.warning("[ETL] Backfill exited with code %d: %s", result.returncode, result.stderr[:500])
        except Exception as exc:
            logger.warning("[ETL] Backfill skipped: %s", exc)

    t = threading.Thread(target=_backfill, daemon=True, name="etl-backfill")
    t.start()


_run_etl_backfill()
