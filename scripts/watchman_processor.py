#!/usr/bin/env python3
"""
scripts/watchman_processor.py
──────────────────────────────
Dequeues flagged AHUs from watchman_queue and runs the Resolution Agent
on each one to create work orders and send notifications.

Run from the backend/ directory:
  cd backend && python ../scripts/watchman_processor.py
"""

import asyncio
import os
import sys

# Run from backend/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")


async def process_queue():
    from core.agentdb import AgentDB
    from core.logger import get_logger

    logger = get_logger("watchman_processor")
    db = AgentDB()

    alerts = db.dequeue_watchman_alerts()
    if not alerts:
        logger.info("watchman_processor: no alerts in queue")
        return

    logger.info(f"watchman_processor: processing {len(alerts)} alert(s)")

    from agents import resolution_agent

    for alert in alerts:
        ahu_id = alert["ahu_id"]
        level = alert["level"]
        score = alert["fair_score"]
        severity = alert["severity"]

        logger.info(f"watchman_processor: analysing {ahu_id} (score={score:.1f} severity={severity})")

        # Build a synthetic user message for the Resolution Agent
        prompt = (
            f"AHU {ahu_id} on Level {level} has a FAIR health score of {score:.1f} "
            f"(severity: {severity}). "
            "Query its current health scores and financial impact, then take appropriate action: "
            "create a work order and notify if critical."
        )

        messages = [{"role": "user", "content": f"/no_think {prompt}"}]

        try:
            reply, drafts = await resolution_agent.run(messages)
            logger.info(
                f"watchman_processor: {ahu_id} processed — "
                f"reply_len={len(reply)} drafts={len(drafts)}"
            )
        except Exception as e:
            logger.error(f"watchman_processor: failed for {ahu_id} — {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(process_queue())
