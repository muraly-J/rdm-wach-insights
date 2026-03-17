"""
measurements.py
──────────────
GET /api/device/{device_id}/measurements  — Fetch arbitrary metric time-series

Query params:
  metrics  comma-separated metric names (max 10), validated against ALLOWED_METRICS_WITH_UNITS
  range    "24h" | "7d" | "30d"  (default "7d")
"""

import asyncio
import re
from fastapi import APIRouter, Query, HTTPException
from models.schemas import ALLOWED_METRICS_WITH_UNITS, ALLOWED_DEVICES

router = APIRouter()

_RANGE_MAP = {
    "24h": "last_24h",
    "7d":  "last_7d",
    "30d": "last_30d",
}


@router.get("/device/{device_id}/measurements")
async def get_measurements(
    device_id: str,
    metrics: str = Query(..., description="Comma-separated metric names"),
    range: str = Query(default="7d", description="24h | 7d | 30d"),
):
    # Validate device ID
    if not re.match(r"^e\d{4}$", device_id) or device_id not in ALLOWED_DEVICES:
        raise HTTPException(status_code=404, detail=f"Unknown device: {device_id}")

    # Validate range
    if range not in _RANGE_MAP:
        raise HTTPException(status_code=400, detail=f"range must be one of: {list(_RANGE_MAP)}")

    # Parse and validate metrics
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    if not metric_list:
        raise HTTPException(status_code=400, detail="metrics param is required")
    if len(metric_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 metrics per request")

    invalid = [m for m in metric_list if m not in ALLOWED_METRICS_WITH_UNITS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown metrics: {invalid}")

    influx_range = _RANGE_MAP[range]

    # Fetch each metric — partial failures return [] for that metric
    result: dict[str, list[dict]] = {}
    for metric in metric_list:
        try:
            from core.influx_client import fetch_time_series
            df = await asyncio.to_thread(
                fetch_time_series, [device_id], metric, influx_range
            )
            if device_id in df.columns:
                series = df[device_id].dropna().reset_index()
                result[metric] = [
                    {"timestamp": str(row["time"]), "value": float(row[device_id])}
                    for _, row in series.iterrows()
                ]
            else:
                result[metric] = []
        except Exception:
            result[metric] = []

    return {
        "device_id": device_id,
        "range": range,
        "measurements": result,
    }
