"""
delta_forecast.py — GET /api/device/{device_id}/delta-forecast
Returns 23 predicted hourly delta kWh values (T+1h … T+23h).

Formula: predicted_delta(T+N) = mean of [delta(t-24+N), delta(t-168+N), delta(t-336+N)]
where delta(X) = energy_import(X) - energy_import(X-1h)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from core.influx_client import fetch_exact_slots
from models.schemas import ALLOWED_DEVICES

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/device/{device_id}/delta-forecast")
async def get_delta_forecast(device_id: str):
    if device_id not in ALLOWED_DEVICES:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    try:
        result = await asyncio.to_thread(_compute_forecast, device_id)
    except Exception as exc:
        log.error("delta-forecast %s: %s", device_id, exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Forecast temporarily unavailable")
    return result


def _compute_forecast(device_id: str) -> dict:
    t_now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    # For each N (1..23), we need energy_import at:
    # t - (24+N) hours (prev_ref_1d), t - (24+N-1) hours (ref_1d)
    # t - (168+N) hours, t - (168+N-1) hours
    # t - (336+N) hours, t - (336+N-1) hours
    # Collect all unique offsets
    offsets = set()
    for n in range(1, 24):
        for base in (24, 168, 336):
            offsets.add(base + n)       # ref point
            offsets.add(base + n - 1)   # prev point (for delta)
    offsets_list = sorted(offsets)

    # Fetch all slots in one call
    slots = fetch_exact_slots(
        device_ids=[device_id],
        metric="energy_import",
        reference_time=t_now,
        slots_hours_ago=offsets_list
    )
    lookup = slots.get(device_id, {})  # {hours_ago: value_or_None}

    forecast = []
    for n in range(1, 24):
        deltas = []
        for base in (24, 168, 336):
            ref_offset = base + n - 1   # e.g. n=1, base=24 → 24 (the ref hour)
            prev_offset = base + n      # one hour earlier
            ref_val = lookup.get(ref_offset)
            prev_val = lookup.get(prev_offset)
            if ref_val is not None and prev_val is not None:
                d = ref_val - prev_val
                if d >= 0:  # ignore negative deltas (resets/gaps)
                    deltas.append(d)

        predicted = round(sum(deltas) / len(deltas), 4) if deltas else None
        forecast.append({
            "hour": n,
            "target_time": (t_now + timedelta(hours=n)).isoformat(),
            "predicted_delta_kwh": predicted,
        })

    return {
        "device_id": device_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "t_now": t_now.isoformat(),
        "forecast": forecast,
    }
