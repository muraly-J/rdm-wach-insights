"""
summarizer.py
─────────────
Generates a short plain-English summary paragraph for a completed query result.
Uses the same LM Studio connection as the translator.

Task 2 additions:
- Full metric labels for all WACH electrical metrics
- Engineering thresholds for diagnostic metrics (power factor, THD, unbalance)
- Action-oriented LLM prompt — tells non-technical staff what to DO, not just what they see
- Threshold context injected into ranking summaries to flag problem devices

Public function:
  summarize() → tuple[str, dict]
"""

from typing import Any

import pandas as pd

# ── Metric labels ─────────────────────────────────────────────────────────────
_METRIC_LABELS = {
    # Power
    "power_total":              "total active power (kW)",
    "power_l1":                 "Phase L1 active power (kW)",
    "power_l2":                 "Phase L2 active power (kW)",
    "power_l3":                 "Phase L3 active power (kW)",
    "power_demand":             "power demand (kW)",
    "max_power_demand":         "maximum power demand (kW)",
    # Energy
    "energy_import":            "imported energy (kWh)",
    "energy_export":            "exported energy (kWh)",
    "reactive_energy_import":   "imported reactive energy (kVArh)",
    "reactive_energy_export":   "exported reactive energy (kVArh)",
    # Apparent
    "apparent_power_total":     "total apparent power (kVA)",
    "apparent_power_l1":        "Phase L1 apparent power (kVA)",
    "apparent_power_l2":        "Phase L2 apparent power (kVA)",
    "apparent_power_l3":        "Phase L3 apparent power (kVA)",
    "apparent_power_demand":    "apparent power demand (kVA)",
    "apparent_energy":          "apparent energy (kVAh)",
    # Reactive
    "reactive_power_total":     "total reactive power (kVAr)",
    "reactive_power_l1":        "Phase L1 reactive power (kVAr)",
    "reactive_power_l2":        "Phase L2 reactive power (kVAr)",
    "reactive_power_l3":        "Phase L3 reactive power (kVAr)",
    "reactive_power_demand":    "reactive power demand (kVAr)",
    # Current
    "current_avg":              "average current (A)",
    "current_l1":               "Phase L1 current (A)",
    "current_l2":               "Phase L2 current (A)",
    "current_l3":               "Phase L3 current (A)",
    "current_l1_thd":           "Phase L1 current harmonic distortion (%THD)",
    "current_l3_thd":           "Phase L3 current harmonic distortion (%THD)",
    "current_unbalance":        "current unbalance (%)",
    # Voltage
    "volts_l_n_avg":            "average line-to-neutral voltage (V)",
    "volts_l_l_avg":            "average line-to-line voltage (V)",
    "volts_l1_n":               "Phase L1-N voltage (V)",
    "volts_l2_n":               "Phase L2-N voltage (V)",
    "volts_l3_n":               "Phase L3-N voltage (V)",
    "volts_l1_l2":              "L1-L2 line voltage (V)",
    "volts_l2_l3":              "L2-L3 line voltage (V)",
    "volts_l3_l1":              "L3-L1 line voltage (V)",
    "volts_l1_thd":             "Phase L1 voltage harmonic distortion (%THD)",
    "volts_l2_thd":             "Phase L2 voltage harmonic distortion (%THD)",
    "volts_l3_thd":             "Phase L3 voltage harmonic distortion (%THD)",
    "volts_unbalance":          "voltage unbalance (%)",
    # Power factor & frequency
    "power_factor_avg":         "average power factor",
    "power_factor_l1":          "Phase L1 power factor",
    "power_factor_l2":          "Phase L2 power factor",
    "power_factor_l3":          "Phase L3 power factor",
    "freq":                     "supply frequency (Hz)",
    # Other
    "digital_input_1_and_2":    "digital input status",
}

_RANGE_LABELS = {
    "last_24h":  "the past 24 hours",
    "last_7d":   "the past 7 days",
    "last_30d":  "the past 30 days",
    "all_time":  "all available data",
}

# ── Engineering thresholds ────────────────────────────────────────────────────
# These are the accepted engineering standards for each diagnostic metric.
# When values breach these thresholds the LLM is instructed to flag it
# and recommend a maintenance action — turning data into decisions.
#
# Format: metric → (threshold_value, direction, standard, action_hint)
#   direction: "below" means bad if value is below threshold
#              "above" means bad if value is above threshold
#   standard:  reference standard or rule of thumb
#   action_hint: plain-English recommendation for the summary

_THRESHOLDS = {
    # Power factor: below 0.85 is poor, below 0.75 is critical
    "power_factor_avg": (0.85, "below",
        "IEC/utility standard",
        "Consider checking for capacitor bank issues, lagging loads, or scheduling a power factor correction review with the facilities team."),
    "power_factor_l1": (0.85, "below",
        "IEC/utility standard",
        "Phase L1 power factor is low. Check for load imbalance or reactive load on this phase."),
    "power_factor_l2": (0.85, "below",
        "IEC/utility standard",
        "Phase L2 power factor is low. Check for load imbalance or reactive load on this phase."),
    "power_factor_l3": (0.85, "below",
        "IEC/utility standard",
        "Phase L3 power factor is low. Check for load imbalance or reactive load on this phase."),

    # Voltage THD: above 5% exceeds IEEE 519 limit for general systems
    "volts_l1_thd": (5.0, "above",
        "IEEE 519 standard (5% limit)",
        "High voltage harmonic distortion can damage sensitive medical equipment. Recommend a harmonic audit and consider installing harmonic filters."),
    "volts_l2_thd": (5.0, "above",
        "IEEE 519 standard (5% limit)",
        "High voltage harmonic distortion detected. A harmonic audit is recommended."),
    "volts_l3_thd": (5.0, "above",
        "IEEE 519 standard (5% limit)",
        "High voltage harmonic distortion detected. A harmonic audit is recommended."),

    # Current THD: above 20% is a concern for branch circuits
    "current_l1_thd": (20.0, "above",
        "IEEE 519 guideline (20% for branch circuits)",
        "High current harmonic distortion may be causing excess heat in wiring and transformers. Inspect connected non-linear loads such as VFDs or UPS units."),
    "current_l3_thd": (20.0, "above",
        "IEEE 519 guideline",
        "High current harmonic distortion detected. Inspect connected non-linear loads."),

    # Voltage unbalance: above 2% is problematic for motors and AHUs
    "volts_unbalance": (2.0, "above",
        "NEMA MG-1 standard (2% limit for motors)",
        "Voltage unbalance above 2% can cause AHU motor overheating and reduced lifespan. Inspect phase loading and notify the electrical maintenance team."),

    # Current unbalance: above 10% is a concern
    "current_unbalance": (10.0, "above",
        "General engineering guideline (10%)",
        "High current unbalance suggests uneven phase loading. Check for single-phase loads or wiring issues."),
}


def _get_threshold_context(metric: str, value: float) -> str | None:
    """
    Returns a plain-English threshold alert string if the value breaches
    the engineering threshold for this metric, or None if within limits.
    """
    if metric not in _THRESHOLDS:
        return None

    threshold, direction, standard, action = _THRESHOLDS[metric]

    if direction == "below" and value < threshold:
        severity = "critically low" if value < threshold * 0.88 else "below acceptable"
        return (
            f"VALUE ALERT: {value:.3f} is {severity} (threshold: {threshold} per {standard}). "
            f"ACTION: {action}"
        )
    elif direction == "above" and value > threshold:
        severity = "critically high" if value > threshold * 1.5 else "above acceptable"
        return (
            f"VALUE ALERT: {value:.3f} is {severity} (threshold: {threshold} per {standard}). "
            f"ACTION: {action}"
        )
    return None


# ── Main summary generator ────────────────────────────────────────────────────

async def generate_summary(
    chart_payload: dict[str, Any],
    query_type: str,
    device_ids: list,
    metric: str,
    time_range: str,
) -> str:
    """
    Generates a 2-4 sentence plain-English summary of the chart data.
    For diagnostic metrics, includes threshold-based flagging and action recommendations.
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

    if query_type == "time_series":
        context = _build_timeseries_context(data, device_ids, metric, metric_label, range_label)
    else:
        context = _build_ranking_context(data, metric, metric_label, range_label)

    system_prompt = (
        "You are a hospital electrical systems analyst. "
        "Your job is to write a clear 2-4 sentence summary for a non-technical hospital administrator. "
        "IMPORTANT RULES:\n"
        "- If the context includes a VALUE ALERT, you MUST mention the specific device and the problem in plain English, and include the recommended action.\n"
        "- If there is no alert, describe what the data shows and whether it looks normal.\n"
        "- Always be specific: name the device IDs, use the actual numbers.\n"
        "- Do not use bullet points. Do not start with 'The data shows' or 'Based on'.\n"
        "- Write as if briefing a facilities manager who needs to decide whether to act."
    )
    try:
        from llm.client_factory import get_chat_client
        client = get_chat_client()
        text = await client.generate_text(
            prompt=context,
            system_instruction=system_prompt,
            temperature=0.3,
            max_output_tokens=300,
        )
        text = text.strip() if text else ""
        return text if text else _fallback_summary(query_type, metric, metric_label, range_label, data)

    except Exception:
        return _fallback_summary(query_type, metric, metric_label, range_label, data)


# ── Context builders ──────────────────────────────────────────────────────────

def _build_timeseries_context(
    data: list,
    device_ids: list,
    metric: str,
    metric_label: str,
    range_label: str,
) -> str:
    device_str = ", ".join(device_ids) if device_ids else "the device"

    values = []
    for row in data:
        for k, v in row.items():
            if k != "time" and isinstance(v, (int, float)):
                values.append(v)

    if not values:
        return (
            f"Device(s): {device_str}. Metric: {metric_label}. "
            f"Time period: {range_label}. No numeric values available."
        )

    avg_val = sum(values) / len(values)
    stats = (
        f"Min: {min(values):.3f}, Max: {max(values):.3f}, "
        f"Average: {avg_val:.3f}. "
        f"First reading: {data[0].get('time', '')}, "
        f"Last reading: {data[-1].get('time', '')}. "
        f"Data points: {len(data)}."
    )

    # Check threshold against the average value
    alert = _get_threshold_context(metric, avg_val)
    alert_str = f"\n{alert}" if alert else ""

    return (
        f"Device(s): {device_str}. Metric: {metric_label}. "
        f"Time period: {range_label}. {stats}{alert_str}"
    )


def _build_ranking_context(
    data: list,
    metric: str,
    metric_label: str,
    range_label: str,
) -> str:
    top3 = data[:3]
    top3_str = ", ".join(
        f"{r.get('device_id', '?')} ({r.get('value', 0):.3f})" for r in top3
    )
    bottom = data[-1] if len(data) > 1 else None
    bottom_str = (
        f"Lowest ranked: {bottom.get('device_id', '?')} ({bottom.get('value', 0):.3f})."
        if bottom else ""
    )

    # Check thresholds for top 3 devices and flag any breaches
    alerts = []
    for r in data[:5]:  # check top 5 for alerts
        val = r.get("value", 0)
        device = r.get("device_id", "unknown")
        alert = _get_threshold_context(metric, val)
        if alert:
            alerts.append(f"Device {device}: {alert}")

    alert_str = "\n" + "\n".join(alerts) if alerts else " All values within acceptable range."

    return (
        f"Metric: {metric_label}. Time period: {range_label}. "
        f"Top {len(data)} devices ranked. "
        f"Highest: {top3_str}. {bottom_str}"
        f"{alert_str}"
    )


# ── Rule-based fallback ───────────────────────────────────────────────────────

def _fallback_summary(
    query_type: str,
    metric: str,
    metric_label: str,
    range_label: str,
    data: list,
) -> str:
    if query_type == "ranking":
        top = data[0] if data else {}
        val = top.get("value", 0)
        alert = _get_threshold_context(metric, val)
        alert_str = f" {alert}" if alert else ""
        return (
            f"Over {range_label}, {top.get('device_id', 'an unknown device')} recorded the highest "
            f"average {metric_label} at {val:.3f}.{alert_str} "
            f"A total of {len(data)} devices were ranked in this result."
        )
    else:
        return (
            f"The chart shows {metric_label} readings over {range_label}. "
            f"{len(data)} data points were returned. "
            f"Review the chart for trends and anomalies."
        )


# ── Anomaly detection for chart callouts ───────────────────────────────────────


def _detect_anomalies(df: Any, structured: Any) -> dict:
    """
    Scan chart data for threshold breaches and return anomaly records
    suitable for visual callouts on the chart.
    
    Returns: {
        "metric": str,
        "anomalies": [
            {"device_id": "e0101", "time": "...", "value": 123.4, 
             "threshold": 5.0, "direction": "above", "alert": "..."},
            ...
        ]
    }
    """
    if hasattr(structured, 'query_type'):
        metric = getattr(structured, 'metric')
        device_ids = getattr(structured, 'device_ids', [])
    else:
        metric = structured.get('metric')
        device_ids = structured.get('device_ids', [])

    if not metric or metric not in _THRESHOLDS:
        return {"metric": metric, "anomalies": []}

    threshold, direction, standard, action = _THRESHOLDS[metric]
    anomalies = []

    if hasattr(df, 'iterrows'):
        # Time series DataFrame
        for ts, row in df.iterrows():
            for d_id in device_ids:
                if d_id in row:
                    val = row[d_id]
                    if pd.notna(val):
                        breached = (direction == "below" and val < threshold) or \
                                   (direction == "above" and val > threshold)
                        if breached:
                            severity = "critically high" if (direction == "above" and val > threshold * 1.5) else \
                                       "critically low" if (direction == "below" and val < threshold * 0.88) else \
                                       "above" if direction == "above" else "below"
                            anomalies.append({
                                "device_id": d_id,
                                "time": ts.strftime("%b %d %H:%M"),
                                "value": round(float(val), 3),
                                "threshold": threshold,
                                "direction": direction,
                                "severity": severity,
                                "metric": metric,
                            })
    elif hasattr(df, 'to_dict'):
        # Ranking DataFrame with columns ['device_id', 'value']
        records = df.to_dict('records')
        for row in records:
            d_id = row.get('device_id')
            val = row.get('value', 0)
            if d_id and isinstance(val, (int, float)):
                breached = (direction == "below" and val < threshold) or \
                           (direction == "above" and val > threshold)
                if breached:
                    severity = "critically high" if (direction == "above" and val > threshold * 1.5) else \
                               "critically low" if (direction == "below" and val < threshold * 0.88) else \
                               "above" if direction == "above" else "below"
                    anomalies.append({
                        "device_id": d_id,
                        "value": round(float(val), 3),
                        "threshold": threshold,
                        "direction": direction,
                        "severity": severity,
                        "metric": metric,
                    })

    return {"metric": metric, "anomalies": anomalies}


# ── Unified entry point ───────────────────────────────────────────────────────

async def summarize(df: Any, structured: Any) -> tuple[str, dict]:
    """
    Dispatcher: takes a DataFrame and StructuredQuery,
    extracts fields, calls generate_summary, and returns anomaly data.
    
    Returns: (summary_text, anomalies_dict)
      anomalies_dict: {
        "metric": str,
        "anomalies": [
          {"device_id": "e0101", "time": "...", "value": 123.4, "metric": "volts_l1_thd", ...}
        ]
      }
    """
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

    data = []
    if hasattr(df, 'to_dict'):
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

    summary = await generate_summary(
        chart_payload=chart_payload,
        query_type=qtype,
        device_ids=device_ids,
        metric=metric,
        time_range=time_range,
    )

    # Detect anomalies for chart callouts
    anomalies = _detect_anomalies(df, structured)

    return summary, anomalies
