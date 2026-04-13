"""
on_off_periods.py
─────────────────
GET /api/on-off-periods/{ahu_id}?range=24h|7d|30d

Returns contiguous time intervals when the AHU was powered off,
derived from the is_on flag in the health database.
"""

from core import db_reader
from fastapi import APIRouter, HTTPException, Query
from models.schemas import ALLOWED_DEVICES

router = APIRouter()

_VALID_RANGES = {"24h", "7d", "30d"}


@router.get("/on-off-periods/{ahu_id}")
async def get_on_off_periods(
    ahu_id: str,
    time_range: str = Query(default="7d", alias="range", description="24h | 7d | 30d"),
):
    if ahu_id not in ALLOWED_DEVICES:
        raise HTTPException(status_code=404, detail=f"Unknown device: {ahu_id}")
    if time_range not in _VALID_RANGES:
        raise HTTPException(status_code=400, detail=f"range must be one of: {sorted(_VALID_RANGES)}")

    off_periods = db_reader.get_off_periods(ahu_id, time_range)
    return {"ahu_id": ahu_id, "range": time_range, "off_periods": off_periods}
