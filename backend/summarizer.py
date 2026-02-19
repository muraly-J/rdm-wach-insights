"""
summarizer.py
─────────────
Generates a short plain-English summary paragraph for a completed query result.
Uses the same LM Studio connection as the translator.

Public function:
  generate_summary() → str
"""

import os
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

_LMS_BASE_URL = os.getenv("LMS_BASE_URL", "http://localhost:1234/v1")
_LMS_MODEL    = os.getenv("LMS_MODEL", "qwen/qwen3-coder-next")
_LMS_API_KEY  = "lm-studio"

_METRIC_LABELS = {
    "power_total":          "total active power (kW)",
    "energy_import":        "imported energy (kWh)",
    "power_factor_avg":     "average power factor",
    "current_avg":          "average current (A)",
    "volts_l_n_avg":        "average line-to-neutral voltage (V)",
    "apparent_power_total": "total apparent power (kVA)",
    "power_demand":         "power demand (kW)",
    "reactive_power_total": "total reactive power (kVAr)",
}

_RANGE_LABELS = {
    "last_24h":  "the past 24 hours",
    "last_7d":   "the past 7 days",
    "last_30d":  "the past 30 days",
    "all_time":  "all available data",
}


async def generate_summary(
    chart_payload: Dict[str, Any],
    query_type: str,
    device_ids: list,
    metric: str,
    time_range: str,
) -> str:
    """
    Generates a 2-3 sentence plain-English summary of the chart data.
    Falls back to a rule-based summary if the LLM call fails.
    """
    metric_label = _METRIC_LABELS.get(metric, metric)
    range_label  = _RANGE_LABELS.get(time_range, time_range)
    data         = chart_payload.get("data", [])

    if not data:
        return (
            f"No data was found for the requested query. "
            f"This may mean the device was offline or no readings were recorded "
            f"for {metric_label} during {range_label}."
        )

    # Build a compact data summary to feed to the LLM
    if query_type == "time_series":
        context = _build_timeseries_context(data, device_ids, metric_label, range_label)
    else:
        context = _build_ranking_context(data, metric_label, range_label)

    try:
        client = AsyncOpenAI(base_url=_LMS_BASE_URL, api_key=_LMS_API_KEY)
        response = await client.chat.completions.create(
            model=_LMS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a hospital energy analyst assistant. "
                        "Write a concise 2-3 sentence plain-English summary of the data provided. "
                        "Be factual and specific. Use numbers where helpful. "
                        "Do not use bullet points. Do not start with 'The data shows' or 'Based on'. "
                        "Write as if explaining to a non-technical hospital administrator."
                    ),
                },
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_tokens=150,
        )
        text = response.choices[0].message.content or ""
        # Strip any thinking tags from qwen3
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return text if text else _fallback_summary(query_type, metric_label, range_label, data)

    except Exception:
        return _fallback_summary(query_type, metric_label, range_label, data)


# ── Context builders ──────────────────────────────────────────────────────────

def _build_timeseries_context(
    data: list,
    device_ids: list,
    metric_label: str,
    range_label: str,
) -> str:
    device_str = ", ".join(device_ids) if device_ids else "the device"

    # Sample first, last, and a rough min/max from numeric values
    values = []
    for row in data:
        for k, v in row.items():
            if k != "time" and isinstance(v, (int, float)):
                values.append(v)

    if values:
        stats = (
            f"Min: {min(values):.2f}, Max: {max(values):.2f}, "
            f"Average: {sum(values)/len(values):.2f}. "
            f"First reading: {data[0].get('time', '')}, "
            f"Last reading: {data[-1].get('time', '')}."
        )
    else:
        stats = "No numeric values available."

    return (
        f"Device(s): {device_str}. Metric: {metric_label}. "
        f"Time period: {range_label}. Data points: {len(data)}. {stats}"
    )


def _build_ranking_context(
    data: list,
    metric_label: str,
    range_label: str,
) -> str:
    top3 = data[:3]
    top3_str = ", ".join(
        f"{r['device_id']} ({r['value']:.2f})" for r in top3
    )
    bottom = data[-1] if len(data) > 1 else None
    bottom_str = f"Lowest in list: {bottom['device_id']} ({bottom['value']:.2f})." if bottom else ""

    return (
        f"Metric: {metric_label}. Time period: {range_label}. "
        f"Top {len(data)} devices ranked by average value. "
        f"Highest consumers: {top3_str}. {bottom_str}"
    )


# ── Rule-based fallback ───────────────────────────────────────────────────────

def _fallback_summary(
    query_type: str,
    metric_label: str,
    range_label: str,
    data: list,
) -> str:
    if query_type == "ranking":
        top = data[0] if data else {}
        return (
            f"Over {range_label}, {top.get('device_id', 'an unknown device')} recorded the highest "
            f"average {metric_label} at {top.get('value', 0):.2f}. "
            f"A total of {len(data)} devices were ranked in this result."
        )
    else:
        return (
            f"The chart shows {metric_label} readings over {range_label}. "
            f"{len(data)} data points were returned. "
            f"Review the chart for trends and peak consumption periods."
        )


# ── Unified entry point ───────────────────────────────────────────────────────

async def summarize(df: Any, structured: Dict[str, Any]) -> str:

    """
    Dispatcher: takes a DataFrame (or chart payload) and StructuredQuery,
    extracts bits, and calls generate_summary.
    """
    # handle both dict and object (pydantic)
    if hasattr(structured, 'query_type'):
        qtype      = getattr(structured, 'query_type')
        metric     = getattr(structured, 'metric')
        time_range = getattr(structured, 'time_range')
        device_ids = getattr(structured, 'device_ids', [])
    else:
        qtype      = structured.get('query_type')
        metric     = structured.get('metric')
        time_range = structured.get('time_range')
        device_ids = structured.get('device_ids', [])

    # The generate_summary function expects the chart payload (with 'data' key)
    # But query.py passes 'df'. We need to make sure we pass what it expects.
    # Actually, build_chart was just called, but its result is NOT passed to summarize in query.py.
    # query.py: summary = await summarize(df, structured)
    # So we need to convert df to a records list if it's a DataFrame.

    data = []
    if hasattr(df, 'to_dict'):
        # For ranking, it's a simple list of records
        # For time_series, we need to format it like build_line_chart does
        if qtype == 'time_series':
            for ts, row in df.iterrows():
                entry = {"time": ts.strftime("%b %d %H:%M")}
                for d in device_ids:
                    if d in row:
                        entry[d] = row[d]
                data.append(entry)
        else:
            data = df.to_dict(orient='records')
    
    chart_payload = {"data": data}

    return await generate_summary(
        chart_payload=chart_payload,
        query_type=qtype,
        device_ids=device_ids,
        metric=metric,
        time_range=time_range
    )
