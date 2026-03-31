# WACH AI System Guide

## What is WACH?

WACH (Ward Air Conditioning Health) Insight is a real-time monitoring and AI analytics platform for Air Handling Units (AHUs) in a Malaysian hospital. It continuously monitors 121 AHUs across 11 building levels, calculating hourly health scores and providing an AI chatbot for natural language queries.

## What WACH Monitors

- **121 AHUs** across Levels 1–11 of the hospital building
- **Electrical health**: power factor, current THD, phase imbalance, energy consumption, motor overload
- **FAIR health scores**: composite 0–100 score updated hourly, broken into 5 component scores
- **Safety flags**: binary alerts for chronic threshold breaches (PF_CHRONIC_LOW, THD_CHRONIC_HIGH, PHASE_IMBALANCE_HIGH, OVERLOAD_ACTIVE)
- **Financial impact**: estimated excess energy cost and TNB PF penalty exposure per level

## How to Use the Dashboard

**Site Summary (top of page)**
Shows building-wide health at a glance: tier distribution (how many AHUs are Healthy/Monitor/Maintenance/Critical), level heat map (click any level tile to jump to that floor's detail).

**Level Selector Bar (sticky)**
Click a level number (1–11) to view all AHUs on that floor.

**Dashboard Section**
Shows ranking of best/worst AHUs for the selected level, individual AHU health cards with sparklines, score breakdown for each FAIR component.

**Prediction Section**
Shows 24-hour health score forecasts for the selected level.

## How to Use the AI Chat

The chat widget (bottom-right corner) accepts natural language questions about any AHU, level, or the building as a whole.

**Questions it can answer well:**
- "What is the current health status of the building?" → queries all levels at once using the building summary tool
- "Which AHUs on Level 5 are worst?" → retrieves and ranks Level 5 AHUs
- "Why does e0501 have a low power factor score?" → retrieves PF data + searches documentation for explanation
- "What is the financial impact on Level 3?" → calculates estimated TNB penalty + energy cost for Level 3
- "What maintenance should I do for e0601?" → retrieves AHU health + recommends action based on dominant fault
- "How does FAIR scoring work?" → retrieves methodology documentation
- "What causes high THD?" → retrieves electrical health guide

**Questions it cannot answer:**
- Real-time maintenance team availability or work order status
- Spare parts inventory
- Contractor quotes or pricing
- Clinical decisions or medical advice
- Events before the health database coverage period

## Health Score Interpretation

| Score | Tier | Meaning | What to Do |
|---|---|---|---|
| 80–100 | Healthy | All indicators normal | Scheduled PM only |
| 60–79 | Monitor | One or more indicators showing early drift | Investigate, consider early intervention |
| 40–59 | Maintenance | Clear degradation, action needed | Book work order within 1–2 weeks |
| 0–39 | Critical | Severe degradation, failure risk | Act now |

**Important context for Clinical Zones:**
- An AHU in Critical tier serving Level 5 (ICU/PICU/OT) is a clinical safety concern — escalate to on-call engineer immediately
- The same score in Level 9 (paediatric ward) warrants urgent but not emergency response
- WACH does not know the clinical load — an ICU AHU at score 45 in the middle of the night with active patients requires faster response than one with the same score during a scheduled maintenance downtime

## Understanding the Five Component Scores

When an AHU has a low health_index, look at the component scores to identify the primary fault:

| Component | Score Low Means | Primary Fault | First Action |
|---|---|---|---|
| energy_anomaly | High energy vs baseline | Filters clogged / coil fouled | Check filter ΔP |
| pf_degradation | Low power factor | Capacitor bank fault / VFD issue | Test capacitor bank |
| phase_imbalance | Unequal phase currents | Loose terminals / contactor / supply issue | Check supply voltages, terminals |
| thd_drift | Rising current THD | VFD harmonic filter degrading | Check VFD line reactor |
| overload | Overcurrent | Filters / coil / belt / ambient temp | Check filters, belt, coil |

## Escalation Paths

**When to call on-call engineer (any hour):**
- Any AHU in Critical tier on Level 5 (PICU, ICU, OT), Level 4 (BMT, Maternity OT)
- Critical AHU + patient activity in zone confirmed with Ward Manager
- Multiple AHUs on same level dropping to Critical simultaneously (may indicate chiller or power supply event)

**When to book a work order (next business day):**
- AHU in Maintenance tier (40–59) in ward or support zone
- AHU in Monitor tier with safety flag raised (e.g., PF_CHRONIC_LOW)
- Energy anomaly sustained > 3 days

**When to monitor only:**
- Single AHU in Monitor tier (60–79) without safety flag
- Health score drop on hot day (> 35°C ambient) that recovers in cooler hours

## Data Coverage

WACH health data is stored in a DuckDB database updated hourly by the ETL pipeline. Coverage: from the point of system commissioning onwards. Typical queries can access up to 30 days of hourly data per request.

If an AHU shows no data: the energy meter for that device may be offline or not yet commissioned. This is different from a low health score — no data means WACH is blind to that AHU, not that it is healthy.
