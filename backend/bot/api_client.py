from __future__ import annotations

"""
bot/api_client.py
─────────────────
Async httpx wrapper around the WACH REST API.
All methods raise WACHAPIError on non-2xx responses.
"""

from typing import Any

import httpx

from bot.config import API_BASE_URL


class WACHAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"WACH API {status_code}: {detail}")


async def _get(path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.get(path, params=params)
    if not resp.is_success:
        raise WACHAPIError(resp.status_code, resp.text[:200])
    return resp.json()


async def _post(path: str, json: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.post(path, json=json or {})
    if not resp.is_success:
        raise WACHAPIError(resp.status_code, resp.text[:200])
    return resp.json()


async def _patch(path: str, json: dict) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.patch(path, json=json)
    if not resp.is_success:
        raise WACHAPIError(resp.status_code, resp.text[:200])
    return resp.json()


# ── Work order helpers ─────────────────────────────────────────────────────────

async def list_work_orders(
    status: str | None = None,
    assigned_to: str | None = None,
) -> list[dict]:
    params: dict = {}
    if status:
        params["status"] = status
    if assigned_to is not None:
        params["assigned_to"] = assigned_to
    data = await _get("/api/work-orders", params=params)
    return data["work_orders"]


async def get_work_order(wo_id: int) -> dict:
    return await _get(f"/api/work-orders/{wo_id}")


async def approve_work_order(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/approve")


async def dismiss_work_order(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/dismiss")


async def push_to_engineers(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/push-to-engineers")


async def start_work_order(wo_id: int) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/start")


async def resolve_work_order(wo_id: int, notes: str | None = None) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/resolve", json={"notes": notes})


async def assign_work_order(wo_id: int, assigned_to: str) -> dict:
    return await _post(f"/api/work-orders/{wo_id}/assign", json={"assigned_to": assigned_to})


async def edit_work_order(wo_id: int, title: str | None = None, description: str | None = None) -> dict:
    payload: dict = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    return await _patch(f"/api/work-orders/{wo_id}", json=payload)


async def get_health_scores() -> dict:
    return await _get("/api/health-scores")


async def get_ahu_status(ahu_id: str) -> dict:
    return await _get(f"/api/measurements/{ahu_id}")
