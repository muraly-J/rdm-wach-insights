"""
tools/tool_registry.py
──────────────────────
OpenAI-format tool definitions and async dispatcher.

TOOLS: list of dicts in OpenAI function-calling schema.
dispatch_tool(name, args): routes a tool call to its handler.
"""

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_building_summary",
            "description": (
                "Get a single-call building-wide health overview: tier counts and average health index "
                "per level, plus totals. USE THIS FIRST when asked about overall building health, "
                "site status, or 'how is the building doing'. Never loop through levels manually."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_health_scores",
            "description": (
                "Query FAIR health scores and component scores for AHUs from the Health DB. "
                "Use for: overall building health status, health index trends, component breakdowns "
                "(energy anomaly, PF, phase imbalance, THD, overload), comparing devices over a time range. "
                "IMPORTANT: Omit both ahu_ids and level to get a building-wide summary aggregated by level "
                "(fastest way to answer 'what is the building health status'). "
                "Specify level (1-11) to get all AHUs on that floor. "
                "Specify ahu_ids for individual device detail."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ahu_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Device IDs to query, e.g. ['e0101', 'e0102']. Omit for all devices in level.",
                    },
                    "level": {
                        "type": "integer",
                        "description": "Floor level (1–11). Filters to AHUs on that level.",
                    },
                    "start": {
                        "type": "string",
                        "description": "Start of time range in ISO format, e.g. '2026-03-22T00:00:00Z'. Omit for latest snapshot.",
                    },
                    "end": {
                        "type": "string",
                        "description": "End of time range in ISO format. Omit for now.",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Columns to return. Omit for all. Options: health_index, tier, "
                            "energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload, "
                            "raw_power_factor_avg, raw_current_unbalance, raw_composite_thd, safety_flags"
                        ),
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_live_readings",
            "description": (
                "Get the most recent sensor readings from InfluxDB: power total, power factor, "
                "current THD, voltage per phase, current per phase. "
                "Use when asked about current/right-now status, live conditions, or real-time values."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ahu_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Device IDs to fetch. Omit for all devices in level.",
                    },
                    "level": {
                        "type": "integer",
                        "description": "Filter to a specific floor level (1–11).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_ranking",
            "description": (
                "Rank AHUs by a health metric using their latest readings. "
                "Omit level to rank across ALL floors (use for 'worst AHUs in the building', "
                "'which AHUs have lowest health scores across all levels'). "
                "Specify level (1–11) to rank within a single floor. "
                "Use for: 'worst devices', 'top N by PF', 'which AHUs need attention', best/worst comparisons."
            ),
            "parameters": {
                "type": "object",
                "required": ["metric"],
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Floor level to rank within (1–11). Omit to rank across all levels.",
                    },
                    "metric": {
                        "type": "string",
                        "description": (
                            "Metric to rank by: health_index, energy_anomaly, pf_degradation, "
                            "phase_imbalance, thd_drift, overload, raw_power_factor_avg, "
                            "raw_current_unbalance, raw_composite_thd"
                        ),
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of results to return (default 5).",
                    },
                    "order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "'asc' = lowest first (worst for health_index), 'desc' = highest first.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_financial_impact",
            "description": (
                "Get financial impact analysis for a level: excess energy cost (RM), "
                "power factor penalty (RM), maintenance risk exposure (RM), and the top "
                "cost-contributing AHUs. Use when asked about costs, financial impact, or RM values."
            ),
            "parameters": {
                "type": "object",
                "required": ["level"],
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Floor level to analyse (1–11).",
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["24h", "7d", "30d"],
                        "description": "Time window for cost calculation (default '7d').",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": (
                "Search technical documentation about AHU components, electrical health indicators, "
                "FAIR scoring methodology, and maintenance guidance. "
                "Use when asked 'why', 'what causes X', 'how does X work', 'what is X', "
                "or any question needing domain/technical knowledge rather than live data."
            ),
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query.",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of document chunks to return (default 3, max 8).",
                    },
                },
            },
        },
    },
]


_KNOWN_TOOLS = {
    "query_building_summary",
    "query_health_scores",
    "query_live_readings",
    "query_ranking",
    "query_financial_impact",
    "search_docs",
}


async def dispatch_tool(name: str, args: dict) -> dict[str, Any]:
    """
    Route a tool call by name to its handler.
    Returns a plain dict (serialised to JSON and fed back to the model).
    """
    if name not in _KNOWN_TOOLS:
        logger.warning(f"dispatch_tool: unknown tool '{name}'")
        return {"error": f"Unknown tool: {name}"}

    logger.info(f"tool_call: {name}({args})")

    from tools.health_tools import (
        handle_query_building_summary,
        handle_query_financial_impact,
        handle_query_health_scores,
        handle_query_live_readings,
        handle_query_ranking,
        handle_search_docs,
    )

    handlers = {
        "query_building_summary":  handle_query_building_summary,
        "query_health_scores":    handle_query_health_scores,
        "query_live_readings":    handle_query_live_readings,
        "query_ranking":          handle_query_ranking,
        "query_financial_impact": handle_query_financial_impact,
        "search_docs":            handle_search_docs,
    }

    try:
        return await handlers[name](**args)
    except Exception as e:
        logger.error(f"dispatch_tool: tool '{name}' raised {e}", exc_info=True)
        return {"error": f"Tool '{name}' failed: {str(e)}"}
