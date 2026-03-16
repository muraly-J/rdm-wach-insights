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

import asyncio
import os
import re
from functools import partial
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
_WACH_SYSTEM_PROMPT = f"""You are WACH AI, an expert assistant for the building energy monitoring platform
at **{get_building_name()}** ({get_department()}).

You help building managers and engineers understand AHU (Air Handling Unit) health scores,
power quality, energy consumption, and anomalies across 11 building levels and 121 AHUs.

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
            prompt += "\n\nDashboard background (supplementary context only):"
            if level:
                prompt += f" The user currently has Level {level} open on their dashboard."
            if device:
                prompt += f" They are focused on device {device}."
            prompt += (
                " Live sensor readings for this view are included above."
                " If the user's question is about a different level or device,"
                " answer that question directly — do not imply you are restricted"
                " to the current dashboard view."
            )
    return prompt


def _extract_navigate_target(message: str) -> Optional[dict]:
    """
    Extract a navigation target from the user's message.

    Returns {"level": int, "device": str} if a specific AHU is mentioned,
    {"level": int} if a level number is mentioned, or None for general questions.
    """
    from models.schemas import AHU_LEVEL_CONFIG

    # Check for explicit device ID (e.g., "e0501", "E0501")
    device_match = re.search(r'\b(e\d{4})\b', message, re.IGNORECASE)
    if device_match:
        device_id = device_match.group(1).lower()
        for level_num, config in AHU_LEVEL_CONFIG.items():
            if device_id in config["device_ids"]:
                return {"level": level_num, "device": device_id}

    # Check for level mention (e.g., "Level 5", "level5", "level 11")
    level_match = re.search(r'\blevel\s*(\d+)\b', message, re.IGNORECASE)
    if level_match:
        level_num = int(level_match.group(1))
        if 1 <= level_num <= 11:
            return {"level": level_num}

    return None


async def _get_live_context(context: Optional[dict]) -> str:
    """
    Fetch live AHU readings from InfluxDB and format as a compact text summary.

    Returns empty string if no level/device context provided, or on any error
    (graceful degradation — live context is best-effort, never blocks chat).
    """
    if not context:
        return ""

    level = context.get("level")
    device = context.get("device")

    if not level and not device:
        return ""

    try:
        from core.influx_client import fetch_latest_hourly_data

        loop = asyncio.get_running_loop()
        level_filter = int(level) if level else None
        df = await loop.run_in_executor(
            None,
            partial(
                fetch_latest_hourly_data,
                ["power_total", "power_factor_avg", "current_unbalance",
                 "current_l1_thd", "current_l3_thd"],
                level_filter,
            ),
        )

        if df is None or df.empty:
            return ""

        # If a specific device is requested, filter to that device
        if device:
            df = df[df["ahu_id"] == device]
            if df.empty:
                return ""

        lines = ["\n\n## Live AHU Readings (current snapshot)"]
        for _, row in df.iterrows():
            ahu_id = row.get("ahu_id", "?")
            pf = row.get("power_factor_avg")
            power = row.get("power_total")
            thd = row.get("composite_thd") or max(
                (v for v in [row.get("current_l1_thd"), row.get("current_l3_thd")] if v is not None),
                default=None,
            )
            unbalance = row.get("current_unbalance")

            parts = [f"**{ahu_id}**:"]
            if power is not None:
                parts.append(f"Power={power:.1f}kW")
            if pf is not None:
                parts.append(f"PF={pf:.3f}")
            if thd is not None:
                parts.append(f"THD={thd:.1f}%")
            if unbalance is not None:
                parts.append(f"Unbalance={unbalance:.1f}%")
            lines.append("- " + " ".join(parts))

        return "\n".join(lines)

    except Exception:
        return ""  # Never let live context failure crash the chat


def _read_csv_context_sync(context: dict) -> str:
    """
    Read latest health scores from ETL CSV files for the given context.
    Synchronous — called via run_in_executor.

    Returns empty string on any error (graceful degradation).
    """
    import pandas as pd

    level = context.get("level")
    device = context.get("device")

    if not level and not device:
        return ""

    project_root = Path(__file__).parent.parent.parent
    hourly_path = project_root / "data" / "health_hourly.csv"
    daily_path = project_root / "data" / "health_all_levels.csv"

    # Try hourly first, fall back to daily
    csv_path = hourly_path if hourly_path.exists() else daily_path
    if not csv_path.exists():
        return ""

    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    if df.empty:
        return ""

    # Filter to the relevant level/device
    if device:
        subset = df[df["ahu_id"] == device]
    elif level:
        level_str = f"Level {level}"
        subset = df[df["level"] == level_str]
    else:
        return ""

    if subset.empty:
        return ""

    # Take the most recent snapshot per AHU
    latest = (
        subset.sort_values("timestamp")
              .groupby("ahu_id", sort=False)
              .last()
              .reset_index()
    )

    lines = ["\n\n## Computed Health Scores (ETL — latest snapshot)"]

    if device:
        # Single device: full detail
        row = latest.iloc[0]
        hi = row.get("health_index")
        tier = row.get("tier", "")
        ea = row.get("energy_anomaly")
        pf = row.get("pf_degradation")
        pi = row.get("phase_imbalance")
        thd = row.get("thd_drift")
        ol = row.get("overload")
        flags = row.get("safety_flags", "")

        lines.append(f"**{row['ahu_id']}** ({row.get('level', '')}):")
        if hi is not None and not pd.isna(hi):
            lines.append(f"  - Health Index: **{hi:.1f}/100** ({tier})")
        score_parts = []
        if ea is not None and not pd.isna(ea): score_parts.append(f"EnergyAnomaly={ea:.1f}")
        if pf is not None and not pd.isna(pf): score_parts.append(f"PFDeg={pf:.1f}")
        if pi is not None and not pd.isna(pi): score_parts.append(f"PhaseImbalance={pi:.1f}")
        if thd is not None and not pd.isna(thd): score_parts.append(f"THDDrift={thd:.1f}")
        if ol is not None and not pd.isna(ol): score_parts.append(f"Overload={ol:.1f}")
        if score_parts:
            lines.append(f"  - FAIR Scores: {', '.join(score_parts)}")
        if flags and str(flags).strip() and str(flags).strip() != "nan":
            lines.append(f"  - Safety Flags: {flags}")
    else:
        # Level summary: all AHUs sorted by health index
        latest_sorted = latest.sort_values("health_index")
        lines.append(f"Level {level} — {len(latest_sorted)} AHUs:")

        # Worst 5
        worst = latest_sorted.head(5)
        lines.append("  Worst health:")
        for _, row in worst.iterrows():
            hi = row.get("health_index")
            tier = row.get("tier", "")
            flags = row.get("safety_flags", "")
            flag_str = f" ⚠ {flags}" if flags and str(flags).strip() and str(flags).strip() != "nan" else ""
            hi_str = f"{hi:.1f}" if hi is not None and not pd.isna(hi) else "?"
            lines.append(f"    - **{row['ahu_id']}**: {hi_str}/100 ({tier}){flag_str}")

        # Best 5
        best = latest_sorted.tail(5).iloc[::-1]
        lines.append("  Best health:")
        for _, row in best.iterrows():
            hi = row.get("health_index")
            tier = row.get("tier", "")
            hi_str = f"{hi:.1f}" if hi is not None and not pd.isna(hi) else "?"
            lines.append(f"    - **{row['ahu_id']}**: {hi_str}/100 ({tier})")

        # Level average
        avg_hi = latest_sorted["health_index"].mean()
        if not pd.isna(avg_hi):
            lines.append(f"  Level average health index: **{avg_hi:.1f}/100**")

    return "\n".join(lines)


async def _get_csv_context(context: Optional[dict]) -> str:
    """Async wrapper around _read_csv_context_sync."""
    if not context:
        return ""
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read_csv_context_sync, context)
    except Exception:
        return ""


@router.post("/chat")
async def chat(body: ChatRequest):
    """
    AI-powered chat endpoint.

    Accepts the full conversation history from the client (stateless).
    Injects dashboard context into the system prompt when provided.
    """
    gemini_history = _build_gemini_history(body.history)
    system_prompt = _build_system_prompt(body.context)

    # Live context for the currently-open dashboard view
    live_ctx = await _get_live_context(body.context)
    if live_ctx:
        system_prompt += live_ctx

    # Computed health scores from ETL CSVs (dashboard view)
    csv_ctx = await _get_csv_context(body.context)
    if csv_ctx:
        system_prompt += csv_ctx

    # If the user asked about a specific level/device different from the
    # current dashboard context, also inject live data for that target so
    # the bot can answer with real readings instead of deflecting.
    nav_target = _extract_navigate_target(body.message)
    if nav_target:
        ctx_level = body.context.get("level") if body.context else None
        ctx_device = body.context.get("device") if body.context else None
        target_differs = (
            nav_target.get("level") != ctx_level
            or nav_target.get("device") != ctx_device
        )
        if target_differs:
            extra_ctx = await _get_live_context(nav_target)
            if extra_ctx:
                system_prompt += "\n\n## Live AHU Readings (mentioned in query)" + extra_ctx.split("## Live AHU Readings", 1)[-1]
            extra_csv = await _get_csv_context(nav_target)
            if extra_csv:
                system_prompt += "\n\n## Computed Health Scores (mentioned in query)" + extra_csv.split("## Computed Health Scores", 1)[-1]

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

    return {"reply": reply, "navigate": nav_target}
