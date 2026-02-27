"""
FastAPI app entry point.
- CORS configured for Vercel frontend + local dev
- Security headers on every response
- Static file serving for production build

For Vercel deployment, use: vercel-python with api/ directory
"""
import os
import sys

# Only run startup code when not in serverless environment (or check for vercel)
IN_VERCEL = os.getenv("VERCEL") == "1"

sys.path.insert(0, os.path.dirname(__file__))
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from routes.forecast import router as forecast_router
from routes.dashboard import router as dashboard_router

from dotenv import load_dotenv
from middleware.query_logger import init_db, log_query
from routes.query import router as query_router

# Load env but don't fail if not found (production may use Vercel env vars)
load_dotenv()


# ── Security headers middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: callable) -> Response:
        response = await call_next(request)
        response.headers['X-Content-Type-Options']    = 'nosniff'
        response.headers['X-Frame-Options']           = 'DENY'
        response.headers['X-XSS-Protection']          = '1; mode=block'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']        = 'camera=(), microphone=(), geolocation=()'

        # --- THE FIX: Updated CSP ---
        # Added your Cloudflare and Vercel domains to 'connect-src'
        # Added 'https://*.trycloudflare.com' to allow dynamic tunnel URLs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            f"connect-src 'self' https://rdm-wach-insights.vercel.app https://*.vercel.app https://*.trycloudflare.com; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp
        return response


# ── App setup ─────────────────────────────────────────────────────────────────

def get_cors_origins():
    """Get CORS origins from env or use defaults."""
    raw = os.getenv("CORS_ORIGIN", "http://localhost:3000")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    # Always add Vercel production URL
    if "https://rdm-wach-insights.vercel.app" not in origins:
        origins.append("https://rdm-wach-insights.vercel.app")
    return origins


def create_app():
    """Create and configure the FastAPI app."""
    app = FastAPI(
        title="WACH Insight API",
        description="Conversational AHU energy analytics for the WACH ward.",
        version="1.0.0",
    )

    app.add_middleware(SecurityHeadersMiddleware)

    # CORS — allow both localhost and network access
    _cors_origins = get_cors_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all routers with /api prefix for consistent routing
    app.include_router(forecast_router, prefix="/api")
    app.include_router(query_router, prefix="/api")
    app.include_router(dashboard_router)

    @app.get('/health')
    async def health():
        return {'status': 'ok'}

    # Static files for local development (not needed in Vercel)
    if not IN_VERCEL:
        DIST_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')

        if os.path.isdir(DIST_DIR):
            app.mount('/assets', StaticFiles(directory=os.path.join(DIST_DIR, 'assets')), name='assets')

    return app

# ── Create the app instance ───────────────────────────────────────────────────

app = create_app()


# ── Initialize database on startup (skip in Vercel) ───────────────────────────

if not IN_VERCEL:
    try:
        init_db()
        print("[Startup] Query logging initialized")
    except Exception as e:
        print(f"[Startup] Warning: Could not initialize query logger: {e}")
