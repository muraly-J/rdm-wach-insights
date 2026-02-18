"""
main.py
───────
FastAPI application entry point for WACH Insight.
Run with: uvicorn backend.main:app --reload (from project root)
"""

import os
import sys
from contextlib import asynccontextmanager
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from middleware.query_logger import init_db
from routes.query import router as query_router

load_dotenv()

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

app.include_router(query_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "WACH Insight API"}