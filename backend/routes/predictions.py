from __future__ import annotations

"""
GET /api/predictions/{device_id}
  ?horizons=1h,12h,24h,168h   (default: all four)

Returns math-predicted measurements, FAIR scores, and health index
for the requested AHU at each horizon.
"""


from core.prediction_engine import compute_predictions_async
from fastapi import APIRouter, HTTPException, Query
from models.schemas import DEVICE_TO_LEVEL

router = APIRouter()


@router.get("/predictions/{device_id}")
async def get_predictions(
    device_id: str,
    horizons: str | None = Query(default="1h,12h,24h,168h"),
):
    device_id = device_id.lower()
    if device_id not in DEVICE_TO_LEVEL:
        raise HTTPException(status_code=404, detail=f"Unknown device: {device_id}")

    horizon_list = [h.strip() for h in horizons.split(",") if h.strip()]
    valid = {"1h", "12h", "24h", "168h"}
    invalid = set(horizon_list) - valid
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid horizons: {invalid}. Use: {valid}")

    result = await compute_predictions_async(device_id, horizons=horizon_list)
    if result is None:
        raise HTTPException(
            status_code=503,
            detail=f"Insufficient historical data for {device_id}. Minimum 24h required.",
        )
    return result
