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

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

from llm.gemini_client import GeminiClient
from models.schemas import ChatHistoryItem
from config import get_building_name, get_department

_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
_RAG_COLLECTION = os.getenv("RAG_COLLECTION", "wach_docs")


def _get_retriever():
    """Lazily load retriever — returns None if no documents ingested yet."""
    from rag.vector_store import VectorStore
    from rag.retriever import Retriever
    try:
        store = VectorStore(persist_dir=_CHROMA_DIR, collection_name=_RAG_COLLECTION)
        if store.count == 0:
            return None
        return Retriever(vector_store=store)
    except Exception:
        return None

router = APIRouter()

# ── System persona ─────────────────────────────────────────────────────────────
_BUILDING_NAME = get_building_name()
_DEPARTMENT = get_department()

_WACH_SYSTEM_PROMPT = f"""You are WACH AI, an expert assistant for the building energy monitoring platform
at **{_BUILDING_NAME}** ({_DEPARTMENT}).

You help building managers and engineers understand AHU (Air Handling Unit) health scores,
power quality, energy consumption, and anomalies across 11 building levels and 120 AHUs.

Your responses should be:
- Concise and actionable (2-4 sentences unless more detail is clearly needed)
- Grounded in the data context provided
- Written for a non-expert building manager, not a data scientist
- Formatted in Markdown when structure helps clarity

You have knowledge of:
- AHU electrical health scoring (0-100 scale):
  - **Healthy**: 80–100 — normal operation
  - **Monitor**: 60–79 — watch for degradation
  - **Maintenance Soon**: 40–59 — schedule service
  - **Critical**: 0–39 — urgent intervention needed
- FAIR scoring components: Energy Anomaly (15%), Power Factor Degradation (25%),
  Phase Imbalance (25%), THD Drift (15%), Overload (20%)
- Power quality targets: power factor >0.85, voltage THD <5% (IEEE 519),
  current unbalance <2% (NEMA MG-1)
- Energy anomaly detection and diagnosis
- HVAC operational best practices

The building has 11 levels (Levels 1–11) serving departments including Emergency,
O&G Clinic, ICU, Operation Theatre, Paediatric Wards, and more.

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

    # Inject RAG context if documents have been ingested
    retriever = _get_retriever()
    if retriever:
        snippets = await retriever.retrieve(body.message, top_k=3)
        if snippets:
            system_prompt += "\n\nRelevant technical documentation:\n" + "\n---\n".join(snippets)

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
            max_output_tokens=2048,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI service unavailable: {e}",
        )

    return {"reply": reply}
