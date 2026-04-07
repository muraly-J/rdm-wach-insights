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
import sys
import time
import logging
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from routes.forecast import router as forecast_router
from routes.dashboard import router as dashboard_router
from routes.health_scores import router as health_scores_router
from routes.predictions import router as predictions_router
from routes.measurements import router as measurements_router
from routes.delta_forecast import router as delta_forecast_router
from routes.financial_impact import router as financial_impact_router
from routes.site_summary import router as site_summary_router

from dotenv import load_dotenv
from middleware.query_logger import init_db, log_query
from routes.query import router as query_router


# ── Rate Limiter (in-memory, per IP) ───────────────────────────────────────
_rate_store: dict = defaultdict(list)
RATE_LIMIT        = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_WINDOW       = int(os.getenv("RATE_LIMIT_WINDOW", "60"))


def _check_rate_limit(ip: str) -> bool:
    """Returns True if the request should be rate-limited."""
    now  = time.time()
    hits = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    hits.append(now)
    _rate_store[ip] = hits
    return len(hits) > RATE_LIMIT


# ── API Key Authentication Middleware ────────────────────────────────────────
def get_api_key() -> str:
    """Get the API key from environment. Raises RuntimeError if unset."""
    api_key = os.getenv("API_KEY") or os.getenv("DEV_API_KEY")
    if not api_key:
        raise RuntimeError(
            "API_KEY environment variable is required. "
            "Set it in your .env file before starting the server."
        )
    return api_key


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API Key Authentication Middleware."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check and Swagger UI endpoints
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
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


# ── Rate Limiting Middleware ─────────────────────────────────────────────────
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate Limiting Middleware - applied to forecast endpoints."""

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host or "unknown"

        # Check rate limit for /api endpoints
        # NOTE: Must return JSONResponse directly — raising HTTPException inside
        # BaseHTTPMiddleware is swallowed by Starlette and surfaces as 500.
        if request.url.path.startswith("/api/"):
            if _check_rate_limit(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": {"error": "Too many requests. Please wait a moment before trying again."}}
                )

        return await call_next(request)


# ── Security headers middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: callable) -> Response:
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


# ── App setup ─────────────────────────────────────────────────────────────────

def get_cors_origins():
    """Get CORS origins from env or use defaults."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins


def create_app():
    """Create and configure the FastAPI app."""
    app = FastAPI(
        title="WACH Insight API",
        description="Conversational AHU energy analytics for the WACH ward.",
        version="1.0.0",
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

    @app.get('/health')
    async def health():
        return {'status': 'ok'}

    # Static files for local development
    DIST_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
    
    if os.path.isdir(DIST_DIR):
        app.mount('/assets', StaticFiles(directory=os.path.join(DIST_DIR, 'assets')), name='assets')

    return app

# ── Create the app instance ───────────────────────────────────────────────────

app = create_app()


# ── Initialize database on startup ───────────────────────────────────────────

try:
    init_db()
    logger.info("[Startup] Query logging initialized")
except Exception as e:
    logger.warning(f"[Startup] Warning: Could not initialize query logger: {e}")


# ── Background ETL backfill (runs once on cold start when DB is empty) ────────

def _run_etl_backfill():
    """
    Run health ETL in the background if the DuckDB is empty.
    Called once at startup — safe to skip if InfluxDB is unreachable.
    """
    import threading
    import subprocess

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
