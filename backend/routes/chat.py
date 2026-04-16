from __future__ import annotations

"""
routes/chat.py
──────────────
AI-powered chat endpoint — V3 (multi-agent with HITL).

POST /api/chat
  Request:  { message: str, history?: list, context?: dict, persona?: str }
  Response: { reply: str, navigate: dict|null, thinking_mode: str,
              actions: list[ActionItem], pending_drafts_count: int }

Architecture:
  1. Check pending draft work orders (surfaced if no history = first message)
  2. detect_persona() → "general" | "technical" | "technician" | "financial"
  3. classify_query_complexity() → "think" or "fast"
  4. classify_intent() → "analysis" or "resolution"
  5. Route to Analysis Agent (query tools) or Resolution Agent (action tools)
  6. Build actions list from any draft work orders created this turn
  7. Return reply + navigate + thinking_mode + actions + pending_drafts_count
"""

import re

from agents.router import classify_intent
from core.logger import get_logger
from core.query_classifier import classify_query_complexity
from fastapi import APIRouter, HTTPException
from llm.client_factory import get_chat_client
from llm.persona_detector import detect_persona
from llm.prompts import build_system_prompt
from models.schemas import ChatHistoryItem
from pydantic import BaseModel, field_validator

logger = get_logger(__name__)
router = APIRouter()

# Patterns to strip from LLM replies before returning to the user
_TOOL_CALL_XML_RE = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL)
_TOOL_RESPONSE_XML_RE = re.compile(r"<tool_response>.*?</tool_response>", re.DOTALL)
_FUNCTION_CALL_JSON_RE = re.compile(
    r"```(?:json)?\s*\{[^`]*[\"'](?:name|function)[\"']\s*:[^`]*\}[^`]*```",
    re.DOTALL,
)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _sanitize_reply(text: str) -> str:
    """Strip tool-call artifacts and code blocks from LLM reply text."""
    text = _THINK_RE.sub("", text)
    text = _TOOL_CALL_XML_RE.sub("", text)
    text = _TOOL_RESPONSE_XML_RE.sub("", text)
    text = _FUNCTION_CALL_JSON_RE.sub("", text)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^(Calling|Executing|Invoking|Running)\s+\w+", stripped, re.IGNORECASE):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _build_actions(draft_work_orders: list[dict]) -> list[dict]:
    """Convert draft work order dicts into frontend action button descriptors."""
    actions = []
    for wo in draft_work_orders:
        wo_id = wo.get("id")
        ahu_id = wo.get("ahu_id", "unknown")
        title = wo.get("title", "Work order")
        actions.extend([
            {
                "type": "approve_work_order",
                "work_order_id": wo_id,
                "label": "Submit Ticket",
                "description": f"Create work order for {ahu_id}: {title}. Notifies technician via Telegram.",
            },
            {
                "type": "edit_draft",
                "work_order_id": wo_id,
                "label": "Edit Draft",
                "description": "Edit the work order description before submitting.",
            },
            {
                "type": "dismiss",
                "work_order_id": wo_id,
                "label": "Dismiss",
                "description": "Dismiss this work order draft.",
            },
        ])
    return actions


def _get_pending_drafts_count() -> int:
    """Return count of unresolved draft work orders."""
    try:
        from core.agentdb import AgentDB
        db = AgentDB()
        return len(db.list_work_orders(status="draft"))
    except Exception:
        return 0


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] | None = None
    context: dict | None = None
    persona: str | None = None

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
    messages = []
    for item in history:
        role = "assistant" if item.role in ("model", "assistant") else "user"
        messages.append({"role": role, "content": item.content})
    return messages


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(body: ChatRequest) -> dict:
    history = body.history or []
    history_messages = _to_openai_messages(history)

    # Check pending drafts on first message of a session
    pending_drafts_count = 0
    if not history:
        pending_drafts_count = _get_pending_drafts_count()

    # 1. Detect persona
    history_dicts = [{"role": m["role"], "content": m["content"]} for m in history_messages]
    persona = detect_persona(body.message, history=history_dicts, stated_persona=body.persona)

    # 2. Classify complexity → choose thinking mode
    thinking_mode = classify_query_complexity(body.message, history_messages)
    prefix = "/think " if thinking_mode == "think" else "/no_think "
    user_content = prefix + body.message

    # 3. Build messages list
    messages = history_messages + [{"role": "user", "content": user_content}]

    # 4. Route to appropriate agent
    agent_type = classify_intent(body.message, history=history_dicts)
    logger.info(f"chat: persona={persona} thinking={thinking_mode} agent={agent_type}")

    try:
        draft_work_orders: list[dict] = []

        if agent_type == "resolution":
            from agents import resolution_agent
            reply, draft_work_orders = await resolution_agent.run(messages)
        else:
            from agents import analysis_agent
            reply = await analysis_agent.run(messages, persona=persona)

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    actions = _build_actions(draft_work_orders)

    return {
        "reply": _sanitize_reply(reply),
        "navigate": None,
        "thinking_mode": thinking_mode,
        "actions": actions,
        "pending_drafts_count": pending_drafts_count,
    }
