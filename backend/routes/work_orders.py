from __future__ import annotations

"""
routes/work_orders.py
─────────────────────
CRUD API for work orders (HITL approval/dismiss workflow).

GET  /api/work-orders          — list all (optional ?status= filter)
GET  /api/work-orders/{id}     — get one
POST /api/work-orders/{id}/approve — transition draft → approved
POST /api/work-orders/{id}/dismiss — transition * → dismissed
PATCH /api/work-orders/{id}    — edit title/description
"""

from core.logger import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = get_logger(__name__)
router = APIRouter()


def _get_db():
    import core.agentdb as agentdb_module
    if agentdb_module._db_instance is None:
        from core.agentdb import AgentDB
        agentdb_module._db_instance = AgentDB()
    return agentdb_module._db_instance


class WorkOrderPatch(BaseModel):
    title: str | None = None
    description: str | None = None


class WorkOrderAssign(BaseModel):
    assigned_to: str  # "any" or a Telegram user_id string


class WorkOrderResolve(BaseModel):
    notes: str | None = None


@router.get("/work-orders")
async def list_work_orders(
    status: str | None = None,
    assigned_to: str | None = None,
) -> dict:
    db = _get_db()
    work_orders = db.list_work_orders(status=status, assigned_to=assigned_to)
    # Convert any non-JSON-serialisable values
    clean = []
    for wo in work_orders:
        clean.append({k: (str(v) if hasattr(v, "isoformat") else v) for k, v in wo.items()})
    return {"work_orders": clean, "count": len(clean)}


@router.get("/work-orders/{wo_id}")
async def get_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    return {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in wo.items()}


@router.post("/work-orders/{wo_id}/approve")
async def approve_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")

    success = db.update_work_order(wo_id, status="approved", approved_by="user")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve work order in status '{wo['status']}'"
        )

    logger.info(f"work_order {wo_id} approved by user")
    return {"id": wo_id, "status": "approved"}


@router.post("/work-orders/{wo_id}/dismiss")
async def dismiss_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")

    success = db.update_work_order(wo_id, status="dismissed")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot dismiss work order in status '{wo['status']}'"
        )

    logger.info(f"work_order {wo_id} dismissed by user")
    return {"id": wo_id, "status": "dismissed"}


@router.post("/work-orders/{wo_id}/push-to-engineers")
async def push_work_order_to_engineers(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="pending_engineer_review")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot push work order in status '{wo['status']}' to engineers",
        )
    logger.info(f"work_order {wo_id} pushed to engineers")
    return {"id": wo_id, "status": "pending_engineer_review"}


@router.post("/work-orders/{wo_id}/start")
async def start_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="in_progress")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start work order in status '{wo['status']}'",
        )
    logger.info(f"work_order {wo_id} started")
    return {"id": wo_id, "status": "in_progress"}


@router.post("/work-orders/{wo_id}/resolve")
async def resolve_work_order(wo_id: int, body: WorkOrderResolve) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="resolved", notes=body.notes)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resolve work order in status '{wo['status']}'",
        )
    logger.info(f"work_order {wo_id} resolved")
    return {"id": wo_id, "status": "resolved"}


@router.post("/work-orders/{wo_id}/assign")
async def assign_work_order(wo_id: int, body: WorkOrderAssign) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.assign_work_order(wo_id, assigned_to=body.assigned_to)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Can only assign approved or in_progress work orders, got '{wo['status']}'",
        )
    logger.info(f"work_order {wo_id} assigned to {body.assigned_to}")
    return {"id": wo_id, "assigned_to": body.assigned_to}


@router.post("/work-orders/{wo_id}/sendback")
async def sendback_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")
    success = db.update_work_order(wo_id, status="pending_approval")
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send back work order in status '{wo['status']}'",
        )
    logger.info(f"work_order {wo_id} sent back to manager by engineer")
    return {"id": wo_id, "status": "pending_approval"}


@router.delete("/work-orders/{wo_id}")
async def delete_work_order(wo_id: int) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")

    import duckdb
    with duckdb.connect(db._path) as conn:
        conn.execute("DELETE FROM work_orders WHERE id = ?", [wo_id])

    logger.info(f"work_order {wo_id} deleted by user")
    return {"id": wo_id, "deleted": True}


@router.patch("/work-orders/{wo_id}")
async def edit_work_order(wo_id: int, body: WorkOrderPatch) -> dict:
    db = _get_db()
    wo = db.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {wo_id} not found")

    from datetime import datetime, timezone

    import duckdb
    now = datetime.now(timezone.utc).isoformat()

    updates = ["updated_at = ?"]
    params = [now]
    if body.title:
        updates.append("title = ?")
        params.append(body.title)
    if body.description is not None:
        updates.append("description = ?")
        params.append(body.description)

    params.append(wo_id)
    with duckdb.connect(db._path) as conn:
        conn.execute(
            f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ?",
            params,
        )

    return {"id": wo_id, "updated": True}
