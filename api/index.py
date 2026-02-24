"""
Vercel Serverless Function for WACH Insight Backend

This file is called by Vercel's Python runtime.
"""

import os
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# Set Vercel environment flag
os.environ["VERCEL"] = "1"
os.environ["APP_ENV"] = "production"

# Import the FastAPI app from backend
from backend.main import app

# Vercel Python handler - the ASGI application
handler = app
