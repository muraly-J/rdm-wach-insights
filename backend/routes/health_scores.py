"""
health_scores.py
──────────────
API endpoints for UI Revamp:

    GET /api/levels                              - List available building levels
    GET /api/level/{id}/scores                   - Five-score breakdown per device (FAIR names)
    GET /api/level/{id}/health-index             - Health index time series per device
    GET /api/device/{id}/raw-score-relationship  - Raw data ↔ Score mapping

These endpoints serve real data from health_all_levels.csv via csv_reader.
"""

import asyncio
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel

from models.schemas import AHU_LEVEL_CONFIG
from core.csv_reader import (
    get_score_breakdown,
    get_health_index_series,
    get_raw_score_relationship as csv_raw_score,
)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/levels — List available building levels
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/levels")
async def get_levels():
    """
    Get list of available building levels (1-11).

    Returns:
        {"levels": [1, 2, 3, ..., 11]}
    """
    return {
        "levels": list(AHU_LEVEL_CONFIG.keys())
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/level/{id}/scores — Five FAIR-score breakdown
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/level/{level_id}/scores")
async def get_level_scores(
    level_id: int,
    time_range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
):
    """
    Get five FAIR-score breakdown for all AHUs on a specific level.
    Data is read from health_all_levels.csv.

    Parameters:
        level_id: Building level (1-11)
        time_range: Time range - 24h, 7d, or 30d
    """
    valid_ranges = ["24h", "7d", "30d"]
    if time_range not in valid_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"Time range must be one of: {', '.join(valid_ranges)}"
        )
    if level_id not in AHU_LEVEL_CONFIG:
        raise HTTPException(
            status_code=404,
            detail=f"Level {level_id} is invalid. Valid levels: 1-11"
        )

    devices = await asyncio.to_thread(get_score_breakdown, level_id, time_range)
    return {
        "level": level_id,
        "time_range": time_range,
        "devices": devices,
        "generated_at": datetime.now().isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/level/{id}/health-index — Health index time series
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/level/{level_id}/health-index")
async def get_level_health_index(
    level_id: int,
    device_id: str = Query(default=None, description="Filter to single device"),
    time_range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
):
    """
    Get health index time series for all AHUs on a level (or a single device).
    Data is read from health_all_levels.csv.

    Parameters:
        level_id: Building level (1-11)
        device_id: Optional device filter (e.g., e0101)
        time_range: Time range - 24h, 7d, or 30d
    """
    valid_ranges = ["24h", "7d", "30d"]
    if time_range not in valid_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"Time range must be one of: {', '.join(valid_ranges)}"
        )
    if level_id not in AHU_LEVEL_CONFIG:
        raise HTTPException(
            status_code=404,
            detail=f"Level {level_id} is invalid. Valid levels: 1-11"
        )

    series = await asyncio.to_thread(get_health_index_series, level_id, device_id, time_range)
    return {
        "level": level_id,
        "time_range": time_range,
        "devices": series,
        "generated_at": datetime.now().isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/device/{id}/raw-score-relationship — Raw data ↔ Score mapping
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/device/{device_id}/raw-score-relationship")
async def get_raw_score_relationship(
    device_id: str,
    range: str = Query(default="7d", description="Time range: 24h, 7d, or 30d")
):
    """
    Get raw sensor data ↔ computed FAIR score relationship for a single device.
    Data is read from health_all_levels.csv.

    Parameters:
        device_id: Device ID (e.g., e0101)
        range: Time range - 24h, 7d, or 30d
    """
    valid_ranges = ["24h", "7d", "30d"]
    if range not in valid_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"Range must be one of: {', '.join(valid_ranges)}"
        )

    if not re.match(r'^e\d{4}$', device_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid device_id format: {device_id}"
        )

    from models.schemas import ALLOWED_DEVICES
    if device_id not in ALLOWED_DEVICES:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found"
        )

    scores = await asyncio.to_thread(csv_raw_score, device_id, range)
    return {
        "device_id": device_id,
        "range": range,
        "scores": scores,
        "generated_at": datetime.now().isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/chat — Chat endpoint
# ──────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    """
    Chat widget messaging endpoint.

    Parameters:
        message: User's query
        context: Optional {level, device} for contextual responses
    """
    message = body.message.lower()
    context = body.context or {}

    level = context.get("level")
    device = context.get("device")

    if "health" in message or "score" in message:
        reply = (
            f"I can see you're viewing {'Level ' + str(level) if level else ''} "
            f"{'device ' + device if device else ''}. "
            "Health scores range from 0-100, with 80+ being Healthy. "
            "Would you like to see the breakdown by component?"
        )
    elif "energy" in message:
        reply = (
            "Energy anomaly shows deviation from expected consumption. "
            "High values indicate either increased usage or measurement issues."
        )
    elif "levels" in message or "compare" in message:
        reply = (
            f"Level 1 has {len(AHU_LEVEL_CONFIG[1]['device_ids'])} AHUs, "
            f"Level 2 has {len(AHU_LEVEL_CONFIG[2]['device_ids'])}, "
            f"and Level 3 has {len(AHU_LEVEL_CONFIG[3]['device_ids'])}."
        )
    else:
        reply = (
            "I'm WACH AI, your AHU health assistant. "
            "Ask me about health scores, energy usage, or device performance."
        )

    return {"reply": reply}
