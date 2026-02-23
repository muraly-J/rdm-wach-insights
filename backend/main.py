"""
FastAPI app entry point.
- CORS configured for Vercel frontend + local dev
- Security headers on every response
- Static file serving for production build
"""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.forecast import router as forecast_router
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from dotenv import load_dotenv
from middleware.query_logger import init_db
from routes.query import router as query_router

load_dotenv()


# ── Security headers middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: callable) -> Response:
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
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

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(
    title="WACH Insight API",
    description="Conversational AHU energy analytics for the WACH ward.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)

# CORS — restrict to production and localhost only (security best practice)
# Production domain: rdm-wach-insights.vercel.app
# Local development: http://localhost:5173 (Vite default)
_cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,https://rdm-wach-insights.vercel.app")
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast_router)

app.include_router(query_router, prefix="/api")

@app.get('/health')
async def health():
    return {'status': 'ok'}

# ── Static files (production: serves built React frontend) ───────────────────

DIST_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')

if os.path.isdir(DIST_DIR):
    app.mount('/assets', StaticFiles(directory=os.path.join(DIST_DIR, 'assets')), name='assets')

    @app.get('/{full_path:path}')
    async def serve_spa(full_path: str):
        index = os.path.join(DIST_DIR, 'index.html')
        return FileResponse(index)
