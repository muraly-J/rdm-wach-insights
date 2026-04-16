from __future__ import annotations

"""
tools/action_tools.py
─────────────────────
Handler implementations for the three action tools:
  create_work_order, send_notification, update_work_order

These are called by dispatch_tool() in tool_registry.py.
Pure functions: create_work_order does NOT call send_notification internally.
The Resolution Agent calls each tool explicitly in sequence.
"""

from core.logger import get_logger

logger = get_logger(__name__)

# ── Lazy singleton ─────────────────────────────────────────────────────────────

_db_instance = None


def _get_db():
    import core.agentdb as agentdb_module
    if agentdb_module._db_instance is None:
        from core.agentdb import AgentDB
        agentdb_module._db_instance = AgentDB()
    return agentdb_module._db_instance


def _level_from_ahu_id(ahu_id: str) -> int:
    """Extract building level from AHU ID format e{level:02d}{nn:02d}.
    e.g. e0507 → level 5, e1108 → level 11. Returns 0 if parse fails.
    """
    try:
        if len(ahu_id) == 5 and ahu_id[0] == 'e':
            level = int(ahu_id[1:3])
            if 1 <= level <= 11:
                return level
        return 0
    except (ValueError, IndexError):
        return 0


# ── create_work_order ──────────────────────────────────────────────────────────

async def handle_create_work_order(
    ahu_id: str,
    title: str,
    description: str | None = None,
    severity: str = "warning",
    fair_snapshot: dict | None = None,
    trigger_source: str = "chat",
) -> dict:
    """
    Create a work order for an AHU.

    Status is set based on severity:
      - "critical" → "approved"  (auto-approved, agent should call send_notification next)
      - "warning"  → "draft"     (needs human approval via HITL)
      - "info"     → "draft"     (logged only)

    Returns the created work order dict with id and status.
    """
    db = _get_db()
    level = _level_from_ahu_id(ahu_id)

    # Severity-based initial status
    status = "approved" if severity == "critical" else "draft"

    wo_id = db.create_work_order(
        ahu_id=ahu_id,
        level=level,
        title=title,
        description=description,
        severity=severity,
        trigger_source=trigger_source,
        fair_snapshot=fair_snapshot,
        status=status,
    )

    wo = db.get_work_order(wo_id)
    logger.info(f"create_work_order: id={wo_id} ahu={ahu_id} severity={severity} status={status}")

    # Convert any non-serialisable values to strings
    return {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in wo.items()}
