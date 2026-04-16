from __future__ import annotations

"""
core/watchman.py
────────────────
Proactive background health monitor — "The Watchman".

Two components:
  1. run_pulse():   lightweight async function, called every 30 minutes
                    from FastAPI lifespan. Pure threshold math — no LLM.
  2. start_pulse(): starts the asyncio background loop. Called in main.py lifespan.

The pulse writes flagged AHUs to watchman_queue. The external scheduler
reads the queue and runs the Resolution Agent for heavy LLM analysis.
"""

import asyncio

from core.logger import get_logger

logger = get_logger(__name__)

# ── Lazy singletons ────────────────────────────────────────────────────────────

_health_db_instance = None
_agent_db_instance = None


def _get_health_db():
    global _health_db_instance
    if _health_db_instance is None:
        from core.healthdb import HealthDB
        _health_db_instance = HealthDB()
    return _health_db_instance


def _get_agent_db():
    global _agent_db_instance
    if _agent_db_instance is None:
        from core.agentdb import AgentDB
        _agent_db_instance = AgentDB()
    return _agent_db_instance


# ── Threshold logic ────────────────────────────────────────────────────────────

def classify_score(health_index: float) -> str | None:
    """
    Return "critical", "warning", or None based on health_index.

    critical: FAIR < 40
    warning:  40 <= FAIR < 60
    healthy:  FAIR >= 60 → None
    """
    from config import settings
    if health_index < settings.watchman_critical_threshold:
        return "critical"
    if health_index < settings.watchman_warning_threshold:
        return "warning"
    return None


def is_in_cooldown(agent_db, ahu_id: str, severity: str) -> bool:
    """
    Return True if this AHU has been alerted recently (within cooldown window).
    Cooldown is stored as expires_at in agent_state. get_agent_state() returns
    None if expired or missing, so a non-None result means still in cooldown.
    """
    state = agent_db.get_agent_state(f"last_alert:{ahu_id}")
    return state is not None


# ── Pulse ──────────────────────────────────────────────────────────────────────

async def run_pulse() -> None:
    """
    Single pulse iteration:
    1. Fetch latest FAIR scores for all AHUs from HealthDB
    2. Classify each score
    3. Skip AHUs in cooldown
    4. Enqueue flagged AHUs to watchman_queue
    """
    from config import settings
    if not settings.watchman_enabled:
        return

    health_db = _get_health_db()
    agent_db = _get_agent_db()

    try:
        df = health_db.get_latest_snapshot()
    except Exception as e:
        logger.error(f"watchman: failed to fetch health snapshot — {e}")
        return

    if df is None or df.empty:
        logger.debug("watchman: no health data available")
        return

    flagged = 0
    for _, row in df.iterrows():
        ahu_id = row.get("ahu_id")
        level = int(row.get("level", 0))
        health_index = float(row.get("health_index", 100.0))

        severity = classify_score(health_index)
        if severity is None:
            continue

        if is_in_cooldown(agent_db, ahu_id, severity):
            logger.debug(f"watchman: {ahu_id} in cooldown, skipping")
            continue

        agent_db.enqueue_watchman_alert(
            ahu_id=ahu_id,
            level=level,
            fair_score=health_index,
            severity=severity,
        )
        flagged += 1
        logger.info(f"watchman: flagged {ahu_id} level={level} score={health_index:.1f} severity={severity}")

    if flagged:
        logger.info(f"watchman: pulse complete — {flagged} AHU(s) queued for analysis")
    else:
        logger.debug("watchman: pulse complete — no issues detected")


# ── Background loop ────────────────────────────────────────────────────────────

async def start_pulse() -> None:
    """
    Asyncio background loop. Run via asyncio.create_task() in FastAPI lifespan.
    Runs run_pulse() every WATCHMAN_INTERVAL_SECONDS seconds.
    """
    from config import settings
    interval = settings.watchman_interval_seconds
    logger.info(f"watchman: background pulse started (interval={interval}s)")

    while True:
        try:
            await run_pulse()
        except Exception as e:
            logger.error(f"watchman: pulse error — {e}", exc_info=True)
        await asyncio.sleep(interval)
