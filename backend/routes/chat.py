"""
routes/chat.py
──────────────
AI-powered chat endpoint — V2 (agentic tool-use).

POST /api/chat
  Request:  { message: str, history?: list, context?: dict, persona?: str }
  Response: { reply: str, navigate: dict|null, thinking_mode: str }

Architecture:
  1. detect_persona() → "general" | "technical" | "technician" | "financial"
  2. classify_query_complexity() → "think" or "fast"
  3. Prepend /think or /no_think to message
  4. Lean system prompt + 5 tool definitions → QwenClient.generate_with_tools()
  5. Model calls tools on demand (HealthDB, InfluxDB, RAG, financial)
  6. Return final reply + thinking_mode indicator
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from llm.client_factory import get_chat_client
from llm.persona_detector import detect_persona
from llm.prompts import build_system_prompt
from models.schemas import ChatHistoryItem
from core.query_classifier import classify_query_complexity
from tools.tool_registry import TOOLS, dispatch_tool

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatHistoryItem]] = None
    context: Optional[dict] = None
    persona: Optional[str] = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        if len(v) > 1000:
            raise ValueError("message must be 1000 characters or fewer")
        return v


# ── History conversion ─────────────────────────────────────────────────────────

def _to_openai_messages(history: list[ChatHistoryItem]) -> list[dict]:
    """Convert ChatHistoryItem list to OpenAI-format messages."""
    messages = []
    for item in history:
        role = "assistant" if item.role in ("model", "assistant") else "user"
        messages.append({"role": role, "content": item.content})
    return messages


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(body: ChatRequest):
    history = body.history or []
    history_messages = _to_openai_messages(history)

    # 1. Detect persona from message + history + explicit field
    history_dicts = [{"role": m["role"], "content": m["content"]} for m in history_messages]
    persona = detect_persona(body.message, history=history_dicts, stated_persona=body.persona)

    # 2. Classify complexity → choose thinking mode
    thinking_mode = classify_query_complexity(body.message, history_messages)
    prefix = "/think " if thinking_mode == "think" else "/no_think "
    user_content = prefix + body.message

    # 3. Build messages list for tool loop
    messages = history_messages + [{"role": "user", "content": user_content}]

    # 4. Generate response using tool-augmented generation
    try:
        client = get_chat_client()
        reply = await client.generate_with_tools(
            system_prompt=build_system_prompt(persona),
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
