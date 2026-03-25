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
import logging
import os
import re
from functools import partial
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

from llm.client_factory import get_chat_client
from models.schemas import ChatHistoryItem
from config import get_building_name, get_department

_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
_RAG_COLLECTION = os.getenv("RAG_COLLECTION", "wach_docs")


def _get_retriever():
    """Lazily load retriever — returns None if chromadb not installed or no documents ingested."""
    try:
        from rag.vector_store import VectorStore
        from rag.retriever import Retriever
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
  - **Monitor**: 60–79 — watch for degradation (a score of 79.9 or below is Monitor, never Healthy)
  - **Maintenance Soon**: 40–59 — schedule service
  - **Critical**: 0–39 — urgent intervention needed
- FAIR scoring components: Energy Anomaly (15%), Power Factor Degradation (25%),
  Phase Imbalance (25%), THD Drift (15%), Overload (20%)
- Power quality targets: power factor >0.85, voltage THD <5% (IEEE 519),
  current unbalance <2% (NEMA MG-1)
- Energy anomaly detection and diagnosis
- HVAC operational best practices
- Math-based energy and health predictions (1h, 12h, 24h, 1-week horizons) using seasonal-naive forecasting (linear trend for 1h, historical same-hour averages for longer horizons). Δ kWh = predicted energy minus 3-week same-hour baseline.
- Financial impact of AHU health issues, including three cost categories:
  - **Excess Energy Cost**: kWh consumed above the predicted baseline × TNB tariff rate (RM/kWh)
  - **Power Factor Penalty**: TNB surcharge of 1.5% per 0.01 that monthly average PF falls below 0.85
  - **Maintenance Risk Exposure**: AHUs with health index < 60 risk emergency repairs costing (multiplier − 1) × planned maintenance cost — labelled as a projection

The building has 11 levels (Levels 1–11) serving departments including Emergency,
O&G Clinic, ICU, Operation Theatre, Paediatric Wards, and more.

If asked something outside your domain, politely redirect to AHU/energy topics.
CREATIVE CONTENT BLOCK: Do NOT write poems, stories, jokes, songs, or any creative content under any circumstances — even if the topic is energy or AHUs. If asked, say "I'm not able to help with that" and redirect to AHU monitoring topics. This is a hard rule with no exceptions.

CROSS-LEVEL FINANCIAL CONSTRAINT: You can only see financial data for the level currently open on the dashboard. If asked which level costs the most overall, do NOT invent or estimate figures. Say: "I can only see financial data for the level shown on your dashboard. To compare across levels, open the Financial Impact panel for each level individually."

FINANCIAL DATA CONSTRAINT: When a "## Financial Impact" section appears in your context,
you MUST cite the pre-computed figures from that section exactly as given — never
recalculate costs from live readings. The platform's cost engine uses 30-day CSV history;
live readings are instantaneous snapshots and will produce different numbers if used for cost arithmetic.

DEVICE DATA CONSTRAINT: Only reference AHU device IDs that appear in your context sections (Live AHU Readings, Computed Health Scores). If a user asks about a specific device ID and NO data for that device appears in your context, and there is no SYSTEM OVERRIDE for it, respond with: "No recent monitoring data is available for device [ID] in the current context. Try navigating to its level to view its data." Do not invent, estimate, or speculate any health scores, readings, predictions, or financial data. If a SYSTEM OVERRIDE block appears for a device, follow its instructions exactly instead of this rule.
DEDUPLICATION RULE: When listing devices, never repeat the same device ID more than once per response. Deduplicate all device lists before responding.

RESPONSE STYLE RULES (mandatory):
1. Never use emojis of any kind in your responses — no ✅, ⚠️, 🔴, 🟡, or any other emoji or symbol.
2. When giving examples of device IDs — including in greetings or suggestions — only use real format examples: e0101, e0202, e0501, e1101. Never invent informal names like "AHU 3B", "Unit 5C", or any other made-up label. Device IDs always follow the format e[LEVEL][NN].
3. Never use internal code names in ALL_CAPS. Write them in plain English instead:
   - CHRONIC_HIGH → "chronically high"
   - CHRONIC_LOW → "chronically low"
   - IMBALANCE_SEVERE → "severe imbalance"
   - PF_CHRONIC_LOW → "chronic low power factor"
   - THD_CHRONIC_HIGH → "chronically high THD"
   Established acronyms are fine: NEMA, IEEE, FAIR, AHU, PF, THD, kW, kWh, kVA, kVAR.
FAIR COMPONENTS CONTEXT RULE:
The health index is built from five components. Each component scores drift from this device's own historical baseline — NOT whether absolute values meet an external standard. A device with high absolute readings can still be "Healthy" if those readings are stable and normal for that device. Always explain this when asked why a high-reading device is Healthy.

Component details (use these when explaining scores):

1. Energy Anomaly (15% weight) — raw field: "Power=" (kW consumption delta)
   Measures whether hourly energy consumption is unusually high or low compared to this device's own predicted pattern. Also tracks a 7-day rising trend. A high-consuming AHU is Healthy if consumption matches its own forecast.

2. Power Factor Degradation (25% weight) — raw field: "PF=" (power factor 0–1)
   Measures how far PF has fallen below this device's own historical baseline, and whether it is trending further down. A low absolute PF (e.g. 0.5) can still score Healthy if 0.5 has always been this device's normal. PF penalties are suppressed when load is below 60% of the device's own median power.

3. Phase Imbalance (25% weight) — raw field: "phase imbalance=" (current unbalance %)
   Measures whether current unbalance has risen above this device's own baseline and is trending upward. A device with 4% chronic unbalance may score Healthy because 4% is its stable norm. The NEMA MG-1 <2% standard is a safety flag threshold, not the scoring threshold. A device flagged for severe imbalance can still be Healthy if imbalance is not drifting.

4. THD Drift (15% weight) — raw field: "current THD=" (composite current THD %, max of L1 and L3)
   Uses a 24-hour rolling mean of composite current THD, compared to this device's own median THD baseline. Voltage THDs (L1, L2, L3) are separate and typically stay below 5%; always specify "current THD" vs "voltage THD" when citing values. A device with 80% current THD can be Healthy if that is its stable historical baseline and not rising.

5. Overload (20% weight) — raw field: "Power=" (kW, same as energy anomaly)
   Measures whether power is approaching or exceeding this device's own 95th-percentile ceiling, and whether load is trending upward. A device running at 95% of its own ceiling is still Healthy if that ceiling is stable and the load is not increasing.

Universal rule: When asked why a device with high Phase Imbalance / high THD / low PF / high energy / high load is still "Healthy", always explain that the FAIR score measures drift and trend relative to the device's own history — not compliance with external IEEE/NEMA thresholds."""

_MAX_HISTORY = 6  # was 10 — reduced to prevent stale data dumps polluting context
_MAX_HISTORY_CONTENT_LEN = 400  # bot replies truncated; user msgs kept full


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
    """
    Convert ChatHistoryItem list to LLM {role, parts} format.

    Bot replies are truncated to _MAX_HISTORY_CONTENT_LEN chars to prevent
    stale data dumps (device readings, CSV tables) from dominating LLM context
    after many turns. User messages are passed through unchanged.
    """
    def _trim(item: ChatHistoryItem) -> str:
        text = item.content
        if item.role == "model" and len(text) > _MAX_HISTORY_CONTENT_LEN:
            return text[:_MAX_HISTORY_CONTENT_LEN] + "…"
        return text

    return [
        {"role": item.role, "parts": [_trim(item)]}
        for item in history[-_MAX_HISTORY:]
    ]


def _sanitize_context(context: Optional[dict]) -> tuple[Optional[int], Optional[str]]:
    """
    Extract and validate level and device from a context dict.
    Returns (level, device) — invalid values become None (silently dropped).
    """
    if not context:
        return None, None
    raw_level = context.get("level")
    raw_device = context.get("device")
    level = (
        int(raw_level)
        if str(raw_level).isdigit() and 1 <= int(raw_level) <= 11
        else None
    )
    device = (
        raw_device
        if isinstance(raw_device, str) and re.match(r'^e\d{4}$', raw_device)
        else None
    )
    return level, device


def _build_system_prompt(context: Optional[dict]) -> str:
    """Inject optional dashboard context (level, device) into the system prompt."""
    prompt = _WACH_SYSTEM_PROMPT
    if context:
        level, device = _sanitize_context(context)
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


_PREDICTION_PATTERN = re.compile(
    r'\b(predict\w*|forecast\w*|next|upcoming|future|ahead|will\b|tomorrow|expect\w*|projection|estimate|spike)\b',
    re.IGNORECASE,
)

_TIME_OF_DAY_PATTERN = re.compile(
    r'\b(\d{1,2}\s*(am|pm)|(\d{1,2}:\d{2})|morning|afternoon|evening|night|peak\s+hours?|daytime)\b',
    re.IGNORECASE,
)
_DIAGNOSTIC_INTENT_PATTERN = re.compile(
    r'\b(why|explain|deep\s+dive|drop|dip|investigate|cause|reason|diagnose|decrease|degrade)\b',
    re.IGNORECASE,
)


def _is_prediction_query(message: str) -> bool:
    """Return True if the message is asking about future values."""
    return bool(_PREDICTION_PATTERN.search(message))


def _prediction_fallback_from_csv(device_id: str, horizon: str) -> str:
    """
    When InfluxDB data is insufficient for a math-based prediction, fall back to
    the latest CSV health score and instruct the LLM to answer using it as a proxy.
    """
    try:
        import pandas as pd
        project_root = Path(__file__).parent.parent.parent
        csv_path = project_root / "data" / "health_all_levels.csv"
        if not csv_path.exists():
            return ""
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        subset = df[df["ahu_id"] == device_id]
        if subset.empty:
            return ""
        row = subset.sort_values("timestamp").iloc[-1]
        hi = row.get("health_index")
        tier = row.get("tier", "")
        if hi is None or pd.isna(hi):
            return ""
        lines = [f"\n\n## Prediction Context ({device_id}, +{horizon})"]
        lines.append("Note: Insufficient InfluxDB time-series history for a math-based forecast.")
        lines.append(f"Current Health Index: {float(hi):.1f}/100 ({tier}) — use as best available proxy.")
        lines.append(
            "INSTRUCTION: Answer the prediction question directly using the current health index as a baseline. "
            "State the current health level and note that, absent significant operational changes, "
            "the device is likely to remain in a similar range over the requested horizon. "
            "Do NOT give a generic greeting or refuse to answer."
        )
        return "\n".join(lines)
    except Exception:
        return ""


def _get_prediction_context_sync(device_id: str, horizon: str = "1h") -> str:
    """
    Compute prediction for device_id and return a compact text summary
    for injection into the system prompt.
    """
    try:
        from core.prediction_engine import compute_predictions
        horizon_map = {
            "1h": "1h", "6h": "12h",
            "12h": "12h", "24h": "24h", "1d": "24h",
            "168h": "168h", "1w": "168h", "week": "168h",
        }
        h_key = horizon_map.get(horizon.replace(" ", "").lower(), "24h")
        result = compute_predictions(device_id, horizons=[h_key])
        if result is None:
            return _prediction_fallback_from_csv(device_id, h_key)

        h_data = result["horizons"].get(h_key, {})
        hi = h_data.get("predicted_health_index", "?")
        delta = h_data.get("delta_kwh", 0)
        preds = h_data.get("predictions", {})
        scores = h_data.get("fair_scores", {})

        lines = [f"\n\n## Prediction Context ({device_id}, +{h_key})"]
        lines.append(f"Predicted Health Index: {hi:.1f}/100" if isinstance(hi, float) else f"Predicted Health Index: {hi}")
        lines.append(f"Δ kWh vs baseline: {'+' if delta >= 0 else ''}{delta:.2f} kWh")
        if preds.get("energy_import"):
            lines.append(f"Predicted energy: {preds['energy_import']:.2f} kWh")
        if preds.get("power_factor_avg"):
            lines.append(f"Predicted PF: {preds['power_factor_avg']:.3f}")
        if scores:
            score_str = ", ".join(f"{k}={v:.2f}" for k, v in scores.items())
            lines.append(f"FAIR scores: {score_str}")
        return "\n".join(lines)
    except Exception:
        return ""


async def _get_prediction_context(device_id: str, horizon: str = "1h") -> str:
    """Async wrapper."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _get_prediction_context_sync, device_id, horizon
    )


async def _get_live_context(context: Optional[dict]) -> str:
    """
    Fetch live AHU readings from InfluxDB and format as a compact text summary.

    Returns empty string if no level/device context provided, or on any error
    (graceful degradation — live context is best-effort, never blocks chat).
    """
    if not context:
        return ""

    level, device = _sanitize_context(context)

    if not level and not device:
        return ""

    try:
        from core.influx_client import fetch_latest_hourly_data

        loop = asyncio.get_running_loop()
        level_filter = level  # already validated int or None
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
                parts.append(f"current THD={thd:.1f}%")
            if unbalance is not None:
                parts.append(f"phase imbalance={unbalance:.1f}%")
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

    level, device = _sanitize_context(context)

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

    _FLAG_MAP = {
        "THD_CHRONIC_HIGH": "chronically high THD",
        "CHRONIC_HIGH": "chronically high",
        "CHRONIC_LOW": "chronically low",
        "IMBALANCE_SEVERE": "severe imbalance",
        "PF_CHRONIC_LOW": "chronic low power factor",
    }

    def _translate_flags(raw) -> str:
        if not raw or str(raw).strip() in ("", "nan"):
            return ""
        return ", ".join(
            _FLAG_MAP.get(f.strip(), f.strip())
            for f in str(raw).split(",") if f.strip()
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
        if pi is not None and not pd.isna(pi): score_parts.append(f"Phase Imbalance={pi:.1f}")
        if thd is not None and not pd.isna(thd): score_parts.append(f"THDDrift={thd:.1f}")
        if ol is not None and not pd.isna(ol): score_parts.append(f"Overload={ol:.1f}")
        if score_parts:
            lines.append(f"  - FAIR Scores: {', '.join(score_parts)}")
        translated = _translate_flags(flags)
        if translated:
            lines.append(f"  - Safety Flags: {translated}")
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
            translated = _translate_flags(flags)
            flag_str = f" [{translated}]" if translated else ""
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


def _format_financial_context(data: dict, scope: str) -> str:
    """Format a financial impact dict into a system prompt block."""
    cur = data.get("currency", "RM")
    lines = [f"\n\n## Financial Impact — {scope} (data from dashboard)"]
    lines.append("IMPORTANT: These figures come directly from the dashboard the user is looking at.")
    lines.append("Use them verbatim. Do NOT recalculate or estimate costs from live readings.")
    lines.append(f"Grand total: {cur} {data['grand_total']:,.2f}")
    lines.append(f"    Excess energy waste:          {cur} {data['excess_energy_cost']:,.2f}")
    lines.append(f"    TNB power factor penalty:     {cur} {data['pf_penalty_cost']:,.2f}")
    lines.append(f"    Maintenance risk (projected): {cur} {data['maintenance_risk']:,.2f}")

    top = data.get("top_ahus", [])
    if top:
        lines.append(f"\n  Per-AHU breakdown — ranked by total cost:")
        for i, row in enumerate(top, 1):
            lines.append(
                f"  {i}. {row['ahu_id']}: "
                f"TOTAL={cur} {row['total_cost']:,.2f} | "
                f"excess={cur} {row['excess_energy_cost']:,.2f} | "
                f"PF penalty={cur} {row['pf_penalty_cost']:,.2f} | "
                f"maint.risk={cur} {row['maintenance_risk']:,.2f} | "
                f"health={row['health_index']:.0f}/100"
            )
    return "\n".join(lines)


async def _get_financial_context(context: Optional[dict]) -> str:
    """
    Return financial impact context for the system prompt.
    Prefers data passed directly from the frontend (financial_impact key in context)
    so the chatbot always sees exactly what the user sees on screen.
    Falls back to recomputing from CSV only when the frontend data is absent.
    """
    if not context:
        return ""

    # ── Preferred path: frontend passed the data it already has ──────────────
    fi = context.get("financial_impact")
    if fi and isinstance(fi, dict) and fi.get("grand_total") is not None:
        level = context.get("level", "?")
        device = context.get("device")
        scope = device if device else f"Level {level} (all AHUs)"
        try:
            return _format_financial_context(fi, scope)
        except Exception:
            logger.warning("Failed to format frontend financial_impact context", exc_info=True)

    # ── Fallback: recompute from CSV (may differ due to timing/range) ─────────
    level, device = _sanitize_context(context)
    if not level:
        return ""
    try:
        from routes.financial_impact import _compute_impact
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, _compute_impact, level, "30d", device)
        if not data or (data.get("grand_total", 0) == 0 and not data.get("top_ahus")):
            return ""
        scope = device if device else f"Level {level} (all AHUs)"
        return _format_financial_context(data, scope)
    except Exception:
        logger.warning("Financial context fallback computation failed for level=%s device=%s", level, device, exc_info=True)
        return ""


def _needs_time_window_context(message: str, context: Optional[dict]) -> bool:
    """
    Return True when the message is a time-of-day diagnostic question about a
    specific device. Triggers on-demand InfluxDB time-series fetch.
    Both conditions must be met:
      1. A device ID is known (from context or extracted from the message).
      2. The message contains a time-of-day reference AND diagnostic intent.
    """
    ctx_device = context.get("device") if context else None
    if not ctx_device and not re.search(r'\be\d{4}\b', message, re.IGNORECASE):
        return False
    return bool(_TIME_OF_DAY_PATTERN.search(message)) and bool(_DIAGNOSTIC_INTENT_PATTERN.search(message))


def _extract_tw_range(message: str) -> str:
    """Map natural-language time expressions to a fetch_time_series time_range value."""
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in ("30 days", "past month", "last month")):
        return "last_30d"
    if any(kw in msg_lower for kw in ("24 hours", "today", "yesterday")):
        return "last_24h"
    return "last_7d"


async def _get_time_window_context(device_id: str, time_range: str = "last_7d") -> str:
    """
    Read all columns from health_hourly.csv for device_id over time_range,
    group by UTC hour-of-day (mean), and return a markdown table injected into
    the system prompt.

    Uses the CSV (same source as dashboard) rather than live InfluxDB queries
    to avoid the latency of 17+ concurrent remote HTTP connections. The CSV is
    refreshed hourly from InfluxDB by the ETL, so it reflects current data.

    Includes FAIR scores (health_index, energy_anomaly, …) AND all raw_ sensor
    columns (raw_power_total, raw_current_l1, raw_volts_l1_n, …) — the full row.
    Always returns "" on any exception — never blocks chat.
    """
    try:
        import pandas as pd
        from core.csv_reader import HOURLY_CSV_PATH, _filter_time_range

        # Map the _extract_tw_range keys to csv_reader range strings
        RANGE_MAP = {"last_7d": "7d", "last_24h": "24h", "last_30d": "30d"}
        csv_range = RANGE_MAP.get(time_range, "7d")

        loop = asyncio.get_running_loop()

        def _build_table() -> str:
            df = pd.read_csv(HOURLY_CSV_PATH, parse_dates=["timestamp"])
            df = df[df["ahu_id"] == device_id]
            df = _filter_time_range(df, csv_range)
            if df.empty:
                return ""

            df = df.copy()
            df["_hour"] = pd.to_datetime(df["timestamp"], utc=True).dt.hour

            # All meaningful columns: FAIR scores + every raw_ sensor column
            INCLUDE = [
                "health_index",
                "energy_anomaly", "pf_degradation", "phase_imbalance", "thd_drift", "overload",
                "raw_power_total", "raw_energy_import", "raw_power_factor_avg",
                "raw_current_unbalance", "raw_composite_thd",
                "raw_hourly_delta", "raw_predicted_delta",
                "raw_volts_l1_n", "raw_volts_l2_n", "raw_volts_l3_n",
                "raw_current_l1", "raw_current_l2", "raw_current_l3",
                "raw_nema_voltage_imbalance",
                "raw_current_l1_thd", "raw_current_l3_thd",
                "raw_volts_l1_thd", "raw_volts_l2_thd", "raw_volts_l3_thd",
                "raw_apparent_power_total", "raw_p95_current",
            ]
            available = [c for c in INCLUDE if c in df.columns]
            hourly = df.groupby("_hour")[available].mean().round(2)

            COL_LABELS: dict[str, str] = {
                "health_index":              "Health",
                "energy_anomaly":            "EnergyAnomaly",
                "pf_degradation":            "PFDeg",
                "phase_imbalance":           "PhaseImbalance",
                "thd_drift":                 "THDDrift",
                "overload":                  "Overload",
                "raw_power_total":           "Power(kW)",
                "raw_energy_import":         "Energy(kWh)",
                "raw_power_factor_avg":      "PF",
                "raw_current_unbalance":     "I Imbalance(%)",
                "raw_composite_thd":         "Composite THD(%)",
                "raw_hourly_delta":          "Δ kWh",
                "raw_predicted_delta":       "Predicted Δ kWh",
                "raw_volts_l1_n":            "V L1-N(V)",
                "raw_volts_l2_n":            "V L2-N(V)",
                "raw_volts_l3_n":            "V L3-N(V)",
                "raw_current_l1":            "I L1(A)",
                "raw_current_l2":            "I L2(A)",
                "raw_current_l3":            "I L3(A)",
                "raw_nema_voltage_imbalance":"V NEMA Imbalance(%)",
                "raw_current_l1_thd":        "I L1 THD(%)",
                "raw_current_l3_thd":        "I L3 THD(%)",
                "raw_volts_l1_thd":          "V L1 THD(%)",
                "raw_volts_l2_thd":          "V L2 THD(%)",
                "raw_volts_l3_thd":          "V L3 THD(%)",
                "raw_apparent_power_total":  "Apparent(kVA)",
                "raw_p95_current":           "P95 I(A)",
            }

            present = [c for c in available if c in hourly.columns]
            if not present:
                return ""

            header_cols = " | ".join(COL_LABELS.get(c, c) for c in present)
            separator   = " | ".join("---" for _ in present)

            lines = [
                f"\n\n## On-Demand Sensor Readings — {device_id} (hourly averages, {csv_range})",
                "Hourly means from the dashboard CSV. UTC hours — for Malaysia local time add 8 hours.",
                "Use this table to explain why FAIR scores or health index change at specific times of day.",
                f"| UTC Hour | {header_cols} |",
                f"| --- | {separator} |",
            ]
            for hour in range(24):
                if hour not in hourly.index:
                    continue
                row = hourly.loc[hour]
                values = " | ".join(
                    f"{row[c]:.2f}" if pd.notna(row[c]) else "—"
                    for c in present
                )
                lines.append(f"| {hour:02d}:00 | {values} |")

            return "\n".join(lines)

        return await loop.run_in_executor(None, _build_table)

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

    # Block hallucination for device IDs mentioned in the message but not in AHU_LEVEL_CONFIG.
    # Distinguishes between plausible-but-unmatched AHUs (level prefix 01-11) and truly
    # invalid IDs (level prefix out of range), and injects an explicit override accordingly.
    from models.schemas import AHU_LEVEL_CONFIG as _AHU_CONFIG
    _valid_devices: set[str] = {d for cfg in _AHU_CONFIG.values() for d in cfg["device_ids"]}
    _mentioned_devices = re.findall(r'\b(e\d{4})\b', body.message, re.IGNORECASE)
    for _dev in _mentioned_devices:
        _dev_lower = _dev.lower()
        if _dev_lower not in _valid_devices:
            _level_prefix = int(_dev_lower[1:3])
            if 1 <= _level_prefix <= 11:
                # Plausible AHU format but not matched to a monitoring point
                system_prompt += (
                    f'\n\nSYSTEM OVERRIDE: Device {_dev} exists in the physical asset register '
                    f'but could not be matched to a monitoring point in this system. '
                    f'You MUST respond with exactly: '
                    f'"Device {_dev} is listed in the physical asset register but could not be matched '
                    f'to a monitoring point. Its data is unavailable in this dashboard." '
                    f'Do not provide any health scores, readings, or financial data for it.'
                )
            else:
                # Truly invalid device ID
                system_prompt += (
                    f'\n\nSYSTEM OVERRIDE: Device {_dev} is NOT in the monitored device registry '
                    f'and is not a valid device ID. You MUST respond with exactly: '
                    f'"Device {_dev} does not exist in this system." '
                    f'Do not provide any other information.'
                )

    # Live context for the currently-open dashboard view
    live_ctx = await _get_live_context(body.context)
    if live_ctx:
        system_prompt += live_ctx

    # Computed health scores from ETL CSVs (dashboard view)
    csv_ctx = await _get_csv_context(body.context)
    if csv_ctx:
        system_prompt += csv_ctx

    # On-demand time-window context: only for device-specific time-of-day queries.
    # Fetches all raw InfluxDB measurements (matching health_all_levels.csv raw_ columns)
    # and injects a per-UTC-hour table so the LLM can explain score drops at specific times.
    if _needs_time_window_context(body.message, body.context):
        _tw_device = (body.context.get("device") if body.context else None) or (
            _m.group(1).lower()
            if (_m := re.search(r'\b(e\d{4})\b', body.message, re.IGNORECASE))
            else None
        )
        if _tw_device:
            _tw_range = _extract_tw_range(body.message)
            _tw_ctx = await _get_time_window_context(_tw_device, _tw_range)
            if _tw_ctx:
                system_prompt += _tw_ctx

    # Financial impact context (level/device cost breakdown)
    fin_ctx = await _get_financial_context(body.context)
    if fin_ctx:
        system_prompt += fin_ctx

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

    # Cross-level compare: if a second level is mentioned in the message, inject its data too.
    all_level_mentions = [int(m) for m in re.findall(r'\blevel\s*(\d+)\b', body.message, re.IGNORECASE) if 1 <= int(m) <= 11]
    nav_level = nav_target.get("level") if nav_target else None
    for extra_level in all_level_mentions:
        if extra_level != nav_level:
            extra_csv2 = await _get_csv_context({"level": extra_level})
            if extra_csv2:
                system_prompt += f"\n\n## Computed Health Scores (Level {extra_level} — mentioned in query)" + extra_csv2.split("## Computed Health Scores", 1)[-1]

    # Prediction context: if the message asks about future values,
    # inject predicted measurements and scores for the mentioned device/level.
    # Fall back to the dashboard context level when no explicit target is mentioned.
    if _is_prediction_query(body.message) and nav_target is None:
        ctx_level, _ = _sanitize_context(body.context)
        if ctx_level:
            nav_target = {"level": ctx_level}
    if _is_prediction_query(body.message) and nav_target:
        horizon_match = re.search(r'(\d+)\s*(h|hour|day|week)', body.message, re.IGNORECASE)
        horizon_hint = "24h"
        if re.search(r'\btomorrow\b', body.message, re.IGNORECASE):
            horizon_hint = "24h"
        elif horizon_match:
            n, unit = horizon_match.group(1), horizon_match.group(2).lower()
            if unit in ("h", "hour"):
                horizon_hint = f"{n}h"
            elif unit in ("day",):
                horizon_hint = "24h"
            elif unit in ("week",):
                horizon_hint = "168h"
        if nav_target.get("device"):
            # Device-scoped: inject prediction for the specific AHU
            pred_ctx = await _get_prediction_context(nav_target["device"], horizon_hint)
            if pred_ctx:
                system_prompt += pred_ctx
        elif nav_target.get("level"):
            # Level-scoped: sample up to 2 AHUs from the level for representative predictions
            from models.schemas import AHU_LEVEL_CONFIG
            level_num = nav_target["level"]
            sample_devices = AHU_LEVEL_CONFIG.get(level_num, {}).get("device_ids", [])[:2]
            for did in sample_devices:
                pred_ctx = await _get_prediction_context(did, horizon_hint)
                if pred_ctx:
                    system_prompt += pred_ctx
        # Signal the frontend to show the prediction view (device- or level-scoped)
        nav_target["view"] = "prediction"

    # Inject RAG context if documents have been ingested (best-effort, never blocks chat)
    retriever = _get_retriever()
    if retriever:
        try:
            snippets = await retriever.retrieve(body.message, top_k=3)
            if snippets:
                system_prompt += "\n\nRelevant technical documentation:\n" + "\n---\n".join(snippets)
        except Exception as rag_err:
            logger.warning("RAG retrieval failed (skipping): %s", rag_err)

    # Append current user message to history for the Gemini call
    full_messages = gemini_history + [
        {"role": "user", "parts": [body.message]}
    ]

    try:
        client = get_chat_client()
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

    # Strip Qwen3 chain-of-thought <think>...</think> blocks before returning
    reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()

    return {"reply": reply, "navigate": nav_target}
