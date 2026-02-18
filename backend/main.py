"""
main.py
───────
FastAPI application entry point for WACH Insight.
Run with: uvicorn backend.main:app --reload (from project root)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from middleware.query_logger import init_db
from routes.query import router as query_router

load_dotenv()

app = FastAPI(
    title="WACH Insight API",
    description="Conversational AHU energy analytics for the WACH ward.",
    version="1.0.0",
)

# CORS — allow the Vite dev server to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise SQLite log DB on startup
@app.on_event("startup")
async def startup():
    init_db()

# Mount routes
app.include_router(query_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "WACH Insight API"}