#!/usr/bin/env python3
"""
scripts/escalation_checker.py
Detect stale work order tickets and send Telegram escalation alerts.

Usage:
    python scripts/escalation_checker.py [--dry-run]
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from core.agentdb import AgentDB
from core.logger import get_logger

logger = get_logger(__name__)

THRESHOLD_LABELS = {
    "Critical": "2 hours",
    "High": "2 hours",
    "Medium": "8 hours",
    "Low": "24 hours",
}


async def send_escalation(
    ticket_no: str,
    ahu_id: str,
    priority: str,
    title: str,
    dry_run: bool = False,
) -> None:
    threshold = THRESHOLD_LABELS.get(priority, "24 hours")
    message = (
        f"⚠️ *Escalation Alert*\n"
        f"Ticket `{ticket_no}` ({priority} priority) unclaimed after {threshold}!\n\n"
        f"AHU: `{ahu_id}`\n"
        f"Issue: {title}\n\n"
        f"Assign immediately or escalate to supervisor."
    )
    if dry_run:
        print(f"[DRY RUN] {message}\n")
        return

    try:
        from bot.config import BOT_TOKEN, ADMIN_CHAT_ID
        from telegram import Bot

        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID, text=message, parse_mode="Markdown"
        )
        logger.info(f"Escalation sent for {ticket_no}")
    except Exception as e:
        logger.warning(f"Failed to send escalation for {ticket_no}: {e}")


async def run(dry_run: bool = False) -> None:
    db = AgentDB()
    stale = db.list_stale_tickets()
    if not stale:
        logger.info("No stale tickets found.")
        return
    logger.info(f"Found {len(stale)} stale ticket(s).")
    for ticket in stale:
        await send_escalation(
            ticket_no=ticket["ticket_no"],
            ahu_id=ticket["ahu_id"],
            priority=ticket.get("priority", "Low"),
            title=ticket["title"],
            dry_run=dry_run,
        )


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run(dry_run=dry_run))
