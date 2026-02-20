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
        response.headers['X-Content-Type-Options']    = 'nosniff'
        response.headers['X-Frame-Options']           = 'DENY'
        response.headers['X-XSS-Protection']          = '1; mode=block'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']        = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        )
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

# CORS — allow both localhost and network access
_cors_origins = [
    os.getenv("CORS_ORIGIN", "http://localhost:5173"),
    "http://127.0.0.1:5173",
    "http://10.1.128.106:5173",
]

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
