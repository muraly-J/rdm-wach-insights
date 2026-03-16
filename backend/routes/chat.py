"""
routes/chat.py
──────────────
AI-powered conversational chat endpoint for WACH Insight.

POST /api/chat
  Request:  { message, history?, context? }
  Response: { reply: str }

Uses Gemini 2.0 Flash with the WACH AI system persona.
Conversation history is passed by the client (stateless server).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

from llm.gemini_client import GeminiClient
from models.schemas import ChatHistoryItem

router = APIRouter()

# ── System persona ─────────────────────────────────────────────────────────────
_WACH_SYSTEM_PROMPT = """You are WACH AI, an expert assistant for the WACH building energy
monitoring platform. You help building managers and engineers understand AHU (Air Handling Unit)
health scores, power quality, energy consumption, and anomalies.

Your responses should be:
- Concise and actionable (2-4 sentences unless more detail is clearly needed)
- Grounded in the data context provided
- Written for a non-expert building manager, not a data scientist
- Formatted in Markdown when structure helps clarity

You have knowledge of:
- AHU electrical health scoring (0-100 scale, tiers: Critical <50, Poor 50-65, Fair 65-80, Healthy 80+)
- Power quality metrics: power factor (target >0.85), voltage THD (IEEE 519: <5%), current unbalance (NEMA MG-1: <2%)
- Energy anomaly detection and diagnosis
- HVAC operational best practices

If asked something outside your domain, politely redirect to AHU/energy topics."""

_MAX_HISTORY = 10  # Keep last N turns to stay within token limits


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] = []
    context: Optional[dict] = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("message must not be empty")
        return v.strip()[:1000]  # Truncate to avoid abuse


def _build_gemini_history(history: list[ChatHistoryItem]) -> list[dict]:
    """Convert our ChatHistoryItem list to Gemini's {role, parts} format."""
    return [
        {"role": item.role, "parts": [item.content]}
        for item in history[-_MAX_HISTORY:]
    ]


def _build_system_prompt(context: Optional[dict]) -> str:
    """Inject optional dashboard context (level, device) into the system prompt."""
    prompt = _WACH_SYSTEM_PROMPT
    if context:
        level = context.get("level")
        device = context.get("device")
        if level or device:
            prompt += f"\n\nCurrent dashboard context: "
            if level:
                prompt += f"viewing Level {level}. "
            if device:
                prompt += f"focused on device {device}."
    return prompt


@router.post("/chat")
async def chat(body: ChatRequest):
    """
    AI-powered chat endpoint.

    Accepts the full conversation history from the client (stateless).
    Injects dashboard context into the system prompt when provided.
    """
    gemini_history = _build_gemini_history(body.history)
    system_prompt = _build_system_prompt(body.context)

    # Append current user message to history for the Gemini call
    full_messages = gemini_history + [
        {"role": "user", "parts": [body.message]}
    ]

    try:
        client = GeminiClient()
        reply = await client.generate_chat_response(
            messages=full_messages,
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=512,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI service unavailable: {e}",
        )

    return {"reply": reply}
