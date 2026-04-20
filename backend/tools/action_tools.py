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
    severity: str = "Maintenance Soon",
    fair_snapshot: dict | None = None,
    trigger_source: str = "chat",
) -> dict:
    """
    Create a work order for an AHU.

    Severity uses the 4 health tiers (single source of truth: fair_health_scoring.py):
      - "Critical"         → auto-approved, agent should call send_notification next
      - "Maintenance Soon" → draft, needs human approval via HITL
      - "Monitor"          → draft, logged only

    Returns the created work order dict with id and status.
    """
    db = _get_db()
    level = _level_from_ahu_id(ahu_id)

    # Severity-based initial status
    status = "approved" if severity == "Critical" else "draft"

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


# ── send_notification ──────────────────────────────────────────────────────────

_RECIPIENT_ENV_MAP = {
    "technician": "telegram_recipient_technician",
    "manager":    "telegram_recipient_manager",
    "on_call":    "telegram_recipient_on_call",
    "engineers":  "engineers_chat_id",
}


async def handle_send_notification(
    recipient: str,
    message: str,
    work_order_id: int | None = None,
    ahu_id: str | None = None,
    channel: str = "telegram",
) -> dict:
    """
    Send a notification to a named recipient via Telegram.

    recipient: "technician" | "manager" | "on_call"
    message:   Plain text message body.
    work_order_id: Optional — updates notified_via field on work order.
    ahu_id:    Optional — used for spam prevention cooldown check.

    Spam prevention: If ahu_id is provided, checks agent_state for
    last_alert:{ahu_id}. If alerted within 4 hours, returns skipped.

    Returns {"status": "sent"|"skipped", "reason": str}
    """
    from config import settings

    db = _get_db()

    # Check spam cooldown
    if ahu_id:
        state = db.get_agent_state(f"last_alert:{ahu_id}")
        if state:
            return {
                "status": "skipped",
                "reason": f"cooldown active for {ahu_id} — already notified recently",
            }

    # Check Telegram token
    token = settings.telegram_bot_token
    if not token:
        logger.warning("send_notification: TELEGRAM_BOT_TOKEN not configured, skipping")
        return {"status": "skipped", "reason": "token not configured"}

    # Resolve chat ID
    env_field = _RECIPIENT_ENV_MAP.get(recipient)
    if not env_field:
        return {"status": "error", "reason": f"unknown recipient: {recipient}"}

    chat_id = getattr(settings, env_field, "")
    if not chat_id:
        return {"status": "skipped", "reason": f"chat_id for {recipient!r} not configured"}

    # Route to group notifier if group chat IDs are configured and work order provided
    if work_order_id:
        has_group = (
            (recipient == "manager" and settings.managers_chat_id) or
            (recipient == "engineers" and settings.engineers_chat_id) or
            (recipient == "technician" and settings.technicians_chat_id)
        )
        if has_group:
            try:
                from bot.push.notifier import notify_group
                wo = db.get_work_order(work_order_id)
                if wo:
                    clean_wo = {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in wo.items()}
                    await notify_group(recipient, clean_wo, token)
                    if ahu_id:
                        from datetime import datetime, timedelta, timezone
                        cooldown_hours = settings.watchman_cooldown_critical_hours
                        expires = (datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)).isoformat()
                        db.set_agent_state(
                            f"last_alert:{ahu_id}",
                            {"notified_at": datetime.now(timezone.utc).isoformat(), "recipient": recipient},
                            expires_at=expires,
                        )
                    return {"status": "sent", "recipient": recipient, "channel": "telegram"}
            except ImportError:
                pass  # bot module not available, fall through to plain text

    # Plain text fallback (existing code)
    try:
        from telegram import Bot
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logger.info(f"send_notification: sent to {recipient} ({chat_id})")
    except Exception as e:
        logger.error(f"send_notification: Telegram error — {e}")
        return {"status": "error", "reason": str(e)}

    # Record in agent_state with TTL = cooldown hours
    if ahu_id:
        from datetime import datetime, timedelta, timezone
        cooldown_hours = settings.watchman_cooldown_critical_hours
        expires = (datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)).isoformat()
        db.set_agent_state(
            f"last_alert:{ahu_id}",
            {"notified_at": datetime.now(timezone.utc).isoformat(), "recipient": recipient},
            expires_at=expires,
        )

    # Update work order notified_via if provided
    if work_order_id:
        wo = db.get_work_order(work_order_id)
        if wo:
            updated = db.update_work_order(work_order_id, status=wo["status"], notified_via="telegram")
            if not updated:
                logger.warning(f"send_notification: could not update notified_via for work_order_id={work_order_id} (invalid transition or not found)")

    return {"status": "sent", "recipient": recipient, "channel": "telegram"}


# ── update_work_order ──────────────────────────────────────────────────────────

async def handle_update_work_order(
    work_order_id: int,
    status: str,
    notes: str | None = None,
    approved_by: str | None = None,
) -> dict:
    """
    Transition a work order to a new status.

    Valid transitions:
      draft → pending_approval | approved | dismissed
      pending_approval → approved | dismissed
      approved → in_progress | resolved | dismissed
      in_progress → resolved

    Returns {"success": bool, "new_status": str, "reason": str}
    """
    db = _get_db()
    wo = db.get_work_order(work_order_id)
    if not wo:
        return {"success": False, "reason": f"work order {work_order_id} not found"}

    success = db.update_work_order(
        work_order_id,
        status=status,
        notes=notes,
        approved_by=approved_by,
    )

    if success:
        logger.info(f"update_work_order: id={work_order_id} → {status}")
        return {"success": True, "new_status": status, "work_order_id": work_order_id}
    else:
        return {
            "success": False,
            "reason": f"invalid transition: {wo['status']!r} → {status!r}",
            "current_status": wo["status"],
        }
