from __future__ import annotations

import httpx

from bot.config import API_BASE_URL


async def ask(question: str, user_id: str, role: str, read_only: bool = True) -> str:
    """Send question to /api/chat, return text response."""
    payload = {
        "message": question,
        "session_id": f"tg:{user_id}",
        "context": {"source": "telegram", "role": role, "read_only": read_only},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{API_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response") or data.get("message") or str(data)
