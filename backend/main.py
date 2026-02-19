"""
FastAPI app entry point.
- CORS configured for Vercel frontend + local dev
- Security headers on every response
- Static file serving for production build
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.routes.query import router

# ── Security headers middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers['X-Content-Type-Options']    = 'nosniff'
        response.headers['X-Frame-Options']           = 'DENY'
        response.headers['X-XSS-Protection']          = '1; mode=block'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']        = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "      # Vite needs this
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        )
        return response

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title='WACH Insight API',
    docs_url=None,     # disable Swagger UI in production
    redoc_url=None,    # disable ReDoc in production
    openapi_url=None,  # disable OpenAPI schema in production
)

app.add_middleware(SecurityHeadersMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Add your Vercel URL to CORS_ORIGINS in .env when deploying.
# Multiple origins separated by commas:
# CORS_ORIGINS=https://wach-insight.vercel.app,http://localhost:5173

_raw_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173')
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(',') if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=['POST', 'GET'],
    allow_headers=['Content-Type', 'X-Requested-With'],
)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(router)

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