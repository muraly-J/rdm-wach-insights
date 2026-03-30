"""
routes/chat.py
──────────────
AI-powered chat endpoint — V2 (agentic tool-use).

POST /api/chat
  Request:  { message: str, history?: list, context?: dict }
  Response: { reply: str, navigate: dict|null, thinking_mode: str }

Architecture:
  1. classify_query_complexity() → "think" or "fast"
  2. Prepend /think or /no_think to message
  3. Lean system prompt + 5 tool definitions → QwenClient.generate_with_tools()
  4. Model calls tools on demand (HealthDB, InfluxDB, RAG, financial)
  5. Return final reply + thinking_mode indicator
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from llm.client_factory import get_chat_client
from models.schemas import ChatHistoryItem
from config import get_building_name, get_department
from core.query_classifier import classify_query_complexity
from tools.tool_registry import TOOLS, dispatch_tool

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatHistoryItem]] = None
    context: Optional[dict] = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        if len(v) > 1000:
            raise ValueError("message must be 1000 characters or fewer")
        return v


# ── System prompt ──────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    building = get_building_name()
    department = get_department()
    return f"""You are WACH AI, an AHU health assistant for {building} ({department}).

You monitor Air Handling Units (AHUs) across 11 building levels (Level 1–Level 11), totalling 121 AHUs.
Device IDs follow the format e[LEVEL][NN], e.g. e0101 (Level 1, unit 01) through e1108 (Level 11, unit 08).

## Health Scoring (FAIR)
Health Index: 0–100 scale.
- Healthy (80–100): Normal operation
- Monitor (60–79): Watch closely
- Maintenance (40–59): Schedule maintenance
- Critical (0–39): Immediate intervention required

FAIR component penalty weights:
- Energy Anomaly (15%): Unusual energy consumption
- Power Factor Degradation (25%): Poor reactive power management
- Phase Imbalance (25%): Unequal current across phases
- THD Drift (15%): Total Harmonic Distortion increase
- Overload (20%): Power demand exceeding rated capacity

Power quality targets: power factor >0.85, voltage THD <5% (IEEE 519), current unbalance <2% (NEMA MG-1).

Financial impact categories:
- Excess Energy Cost: kWh above baseline × TNB tariff
- Power Factor Penalty: TNB surcharge of 1.5% per 0.01 below PF 0.85
- Maintenance Risk: emergency repair premium for AHUs with health index < 60

## Instructions
- Use the provided tools to retrieve data. Never guess device readings or fabricate values.
- Cite which devices and time ranges your data covers.
- If a tool returns no data, say so explicitly — do not invent numbers.
- Use markdown formatting. No emojis.
- Be concise and actionable. Use tables for comparisons.
"""


# ── History conversion ─────────────────────────────────────────────────────────

def _to_openai_messages(history: list[ChatHistoryItem]) -> list[dict]:
    """Convert ChatHistoryItem list to OpenAI-format messages."""
    messages = []
    for item in history:
        role = "assistant" if item.role in ("model", "assistant") else "user"
        messages.append({"role": role, "content": item.content})
    return messages


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@router.post("")
async def chat(body: ChatRequest):
    history = body.history or []
    history_messages = _to_openai_messages(history)

    # 1. Classify complexity → choose thinking mode
    thinking_mode = classify_query_complexity(body.message, history_messages)
    prefix = "/think " if thinking_mode == "think" else "/no_think "
    user_content = prefix + body.message

    # 2. Build messages list for tool loop
    messages = history_messages + [{"role": "user", "content": user_content}]

    # 3. Generate response using tool-augmented generation
    try:
        client = get_chat_client()
        reply = await client.generate_with_tools(
            system_prompt=_build_system_prompt(),
            messages=messages,
            tools=TOOLS,
            tool_dispatcher=dispatch_tool,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    return {
        "reply": reply,
        "navigate": None,
        "thinking_mode": thinking_mode,
    }
