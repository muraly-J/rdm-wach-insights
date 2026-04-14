# WACH Insight — API Reference

**Base URL:** `https://<your-host>/api`  
**Local development:** `http://localhost:8081/api`

This document covers all endpoints. For a machine-readable spec, visit `/docs` (Swagger UI) or `/openapi.json`.

---

## Authentication

All endpoints except `/health`, `/docs`, `/redoc`, and `/openapi.json` require an API key.

**Header:**
```
Authorization: Bearer <api_key>
```

**Query param (alternative):**
```
?api_key=<api_key>
```

Missing or invalid key → `401 Unauthorized`.

---

## Rate Limiting

| Scope | Limit |
|-------|-------|
| Global (all endpoints) | 100 requests / 60 seconds per IP |
| `POST /api/query` (additional) | 20 requests / 60 seconds per IP |

Exceeded limit → `429 Too Many Requests`.

---

## Common Error Shape

```json
{
  "detail": {
    "error": "Human-readable description",
    "suggestion": "What to do next"
  }
}
```

---

## Health

### GET `/health`

No authentication required. Used by load balancers and uptime monitors.

**Response:**
```json
{ "status": "ok" }
```

---

## Chat

### POST `/api/chat`

Conversational AI endpoint. Uses tool-augmented generation with persona detection.

**Request body:**
```json
{
  "message": "Which AHUs on level 3 are underperforming?",
  "history": [
    { "role": "user", "content": "What is a FAIR score?" },
    { "role": "assistant", "content": "A FAIR score is..." }
  ],
  "context": {},
  "persona": "general"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string (max 1000 chars) | Yes | User message |
| `history` | array of `{role, content}` | No | Prior conversation turns |
| `context` | object | No | Arbitrary extra context |
| `persona` | `general \| technical \| technician \| financial` | No | Override auto-detection |

**Response:**
```json
{
  "reply": "Level 3 has three AHUs with scores below 60...",
  "navigate": null,
  "thinking_mode": "think"
}
```

**Errors:** `503` if the LLM is unavailable.

**Example:**
```bash
curl -X POST https://<host>/api/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Which units on level 5 need attention?"}'
```

---

## Structured Query

### POST `/api/query`

Translates a natural-language query into a structured InfluxDB query, executes it, and returns the result. Unlike `/api/chat`, this endpoint is for programmatic integrations that need structured data rather than a conversational reply.

**Additional rate limit:** 20 requests / 60 seconds per IP (on top of the global 100/60s limit).

**Request body:**
```json
{ "user_query": "Show power factor for e0101 last 7 days", "session_id": "uuid-optional" }
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_query` | string (max 400 chars) | Yes | Natural-language query |
| `session_id` | UUID string | No | Session tracking |

**Response:**
```json
{
  "query_type": "time_series",
  "metric": "pf_degradation",
  "device_ids": ["e0101"],
  "time_range": "last_7d",
  "top_n": null,
  "chart": { "labels": [...], "datasets": [...] },
  "summary": "Power factor for e0101 over the last 7 days averaged 0.87.",
  "csv_available": true
}
```

**Errors:**
- `400` — prompt injection detected or input validation failed
- `422` — LLM could not parse the query into a structured form
- `429` — per-endpoint rate limit exceeded
- `502` — InfluxDB query failed

**Example:**
```bash
curl -X POST https://<host>/api/query \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_query": "Show THD for e0202 last 30 days"}'
```

---

## Levels & Devices

### GET `/api/levels`

Returns the list of all building levels.

**Response:**
```json
{ "levels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] }
```

**Example:**
```bash
curl https://<host>/api/levels -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/level/{level_id}/devices`

Returns the list of AHU device IDs on a given level. Reads from static configuration — always available regardless of database state.

**Path params:** `level_id` (int, 1–11)

**Response:**
```json
{ "level": 3, "devices": ["e0301", "e0302", "e0303"] }
```

**Errors:** `404` if level_id is out of range.

**Example:**
```bash
curl https://<host>/api/level/3/devices -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/level/{level_id}/scores`

FAIR score breakdown per AHU on a level, aggregated over the requested time range.

**Path params:** `level_id` (int, 1–11)  
**Query params:** `time_range` (string, default `7d`) — `24h | 7d | 30d | all`

**Response:**
```json
{
  "level": 3,
  "time_range": "7d",
  "devices": [
    {
      "device_id": "e0301",
      "health_index": 87.3,
      "energy_anomaly": 0.001,
      "pf_degradation": 0.002,
      "phase_imbalance": 0.0,
      "thd_drift": 0.003,
      "overload": 0.0,
      "tier": "Healthy"
    }
  ]
}
```

**Example:**
```bash
curl "https://<host>/api/level/3/scores?time_range=30d" -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/level/{level_id}/health-index`

Health index time-series for all AHUs on a level (or a single device if filtered).

**Path params:** `level_id` (int, 1–11)  
**Query params:**
- `time_range` (string, default `7d`) — `24h | 7d | 30d | all`
- `device_id` (string, optional) — filter to a single AHU

**Response:**
```json
{
  "level": 3,
  "time_range": "7d",
  "series": [
    { "timestamp": "2026-04-01T00:00:00Z", "device_id": "e0301", "health_index": 87.3 }
  ]
}
```

**Example:**
```bash
curl "https://<host>/api/level/3/health-index?time_range=7d&device_id=e0301" \
  -H "Authorization: Bearer $API_KEY"
```

---

## Dashboard

### GET `/api/dashboard/ranking`

Top 5 healthiest and top 5 lowest-scoring AHUs on a level for the given time range.

**Query params:**
- `level` (string, default `"1"`) — 1–11
- `time_range` (string, default `"last_30d"`) — `last_24h | last_7d | last_30d | all_time`

**Response:**
```json
{
  "level": "3",
  "time_range": "last_30d",
  "snapshot_time": "2026-04-08T10:00:00Z",
  "best": [
    { "device_id": "e0301", "index": 94.2, "tier": "Healthy", "level": "Level 3" }
  ],
  "worst": [
    { "device_id": "e0312", "index": 41.0, "tier": "At Risk", "level": "Level 3" }
  ]
}
```

**Example:**
```bash
curl "https://<host>/api/dashboard/ranking?level=3&time_range=last_7d" \
  -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/dashboard/trend`

Health index time-series and FAIR component scores per AHU for a level. Also includes active safety flags.

**Query params:**
- `level` (string, default `"1"`) — 1–11
- `range` (string, default `"7d"`) — `24h | 7d | 30d | all`

**Response:**
```json
{
  "level": "1",
  "range": "7d",
  "ahus": ["e0101", "e0102"],
  "series": [
    {
      "timestamp": "2026-04-01T00:00:00Z",
      "device_id": "e0101",
      "health_index": 87.3,
      "energy_anomaly": 0.0012,
      "pf_degradation": 0.0034,
      "phase_imbalance": 0.0001,
      "thd_drift": 0.0056,
      "overload": 0.0
    }
  ],
  "latest_snapshot": { "e0101": 87.3 },
  "safety_flags": {
    "e0101": [{ "flag_id": "THD_CHRONIC_HIGH", "label": "THD Critical", "severity": "High" }]
  }
}
```

**Example:**
```bash
curl "https://<host>/api/dashboard/trend?level=1&range=30d" -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/dashboard/trend/csv`

Same data as `/api/dashboard/trend` but returns the time-series as an embedded CSV string. Useful for exporting to spreadsheets.

**Query params:** Same as `/api/dashboard/trend` (`level`, `range`).

**Response:**
```json
{
  "level": "1",
  "range": "7d",
  "column_names": ["timestamp","device_id","health_index","energy_anomaly","pf_degradation","phase_imbalance","thd_drift","overload"],
  "row_count": 42,
  "csv_content": "timestamp,device_id,health_index,...\n2026-04-01T00:00:00Z,e0101,87.3,..."
}
```

**Note:** The response is JSON, not `text/csv`. Parse `csv_content` for the spreadsheet data.

**Example:**
```bash
curl "https://<host>/api/dashboard/trend/csv?level=1&range=7d" -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/dashboard/summary`

LLM-generated narrative summaries for each FAIR dimension on a level. Only level 1 returns AI-generated text; all other levels return static fallback strings.

**Query params:**
- `level` (string, default `"1"`) — 1–11
- `range` (string, default `"7d"`) — `24h | 7d | 30d | all`
- `ahu_id` (string, optional) — accepted and echoed back; per-device filtering is not yet implemented

**Response:**
```json
{
  "level": "1",
  "range": "7d",
  "device_id": null,
  "summaries": {
    "energy_anomaly": { "title": "Energy Anomaly", "summary": "Level 1 AHUs showed a 12% spike in energy anomaly on Wednesday..." },
    "pf_degradation": { "title": "Power Factor Degradation", "summary": "..." },
    "phase_imbalance": { "title": "Phase Imbalance", "summary": "..." },
    "thd_drift":       { "title": "THD Drift", "summary": "..." },
    "overload":        { "title": "Overload", "summary": "..." }
  }
}
```

**Example:**
```bash
curl "https://<host>/api/dashboard/summary?level=1&range=7d" -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/dashboard/safety-flags`

Safety flags that have been persistently active on a level over the requested time range.

**Query params:**
- `level` (string, default `"1"`) — 1–11
- `time_range` (string, default `"last_30d"`) — `last_24h | last_7d | last_30d`

**Flag IDs and severities:**

| Flag ID | Severity | Meaning |
|---------|----------|---------|
| `THD_CHRONIC_HIGH` | High | Total harmonic distortion consistently above 15% |
| `IMBALANCE_SEVERE` | High | Phase imbalance exceeding safety threshold |
| `PF_CHRONIC_LOW` | Moderate | Sustained low power factor (increases energy cost) |
| `OVERLOAD_CHRONIC` | High | Recurring overload on the unit |

**Response:**
```json
{
  "level": "1",
  "time_range": "last_30d",
  "generated_at": "2026-04-08T10:00:00Z",
  "safety_flags": [
    {
      "device_id": "e0101",
      "flags": [
        { "flag_id": "THD_CHRONIC_HIGH", "label": "THD Critical", "severity": "High", "threshold": ">15.0%" }
      ]
    }
  ]
}
```

Devices with no active flags are omitted.

**Example:**
```bash
curl "https://<host>/api/dashboard/safety-flags?level=1&time_range=last_7d" \
  -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/dashboard/ahu-heatmap`

Hourly average health and FAIR scores for a single AHU, broken down by hour of day (0–23). Useful for identifying recurring patterns at specific times.

**Query params:**
- `ahu_id` (string, **required**) — e.g. `e0101`
- `range` (string, default `"7d"`) — `24h | 7d | 30d | all`

**Response:**
```json
{
  "ahu_id": "e0101",
  "range": "7d",
  "hours": [
    {
      "hour": 0,
      "avg_health": 87.2,
      "scores": {
        "energy_anomaly": 0.001,
        "pf_degradation": 0.002,
        "phase_imbalance": 0.0,
        "thd_drift": 0.003,
        "overload": 0.0
      }
    }
  ]
}
```

Array always has 24 entries (hour 0–23). `avg_health` and score values are `null` for hours with no data.

**Example:**
```bash
curl "https://<host>/api/dashboard/ahu-heatmap?ahu_id=e0101&range=30d" \
  -H "Authorization: Bearer $API_KEY"
```

---

## Device-Level Endpoints

### GET `/api/device/{device_id}/raw-score-relationship`

Raw sensor measurements mapped against the computed FAIR score for a single device. Used to understand which sensor readings are driving health score changes.

**Path params:** `device_id` — must match pattern `e\d{4}` and be in the allowed device list  
**Query params:** `range` (string, default `"7d"`) — `24h | 7d | 30d | all`

**Response:** time-series of `{timestamp, raw_value, score}` pairs per FAIR dimension.

**Errors:** `404` if device_id is not in the allowed list or doesn't match `e\d{4}`.

**Example:**
```bash
curl "https://<host>/api/device/e0101/raw-score-relationship?range=7d" \
  -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/device/{device_id}/measurements`

Arbitrary metric time-series from InfluxDB for a device. Use this when you need the raw sensor data rather than derived FAIR scores.

**Path params:** `device_id` — `e\d{4}` format  
**Query params:** `metric` (string), `time_range` (string, default `7d`)

**Example:**
```bash
curl "https://<host>/api/device/e0101/measurements?metric=power_total&time_range=24h" \
  -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/device/{device_id}/delta-forecast`

23-hour forward forecast of energy delta (kWh change per hour) using historical anchor points at -1 day, -7 days, and -14 days.

**Path params:** `device_id` — must be one of the supported forecast devices: `e0202`, `e0207`, `e0211`, or other devices in `ALLOWED_DEVICES`.

**Response:**
```json
{
  "device_id": "e0202",
  "generated_at": "2026-04-08T10:00:00Z",
  "t_now": "2026-04-08T10:00:00Z",
  "forecast": [
    { "hour": 1, "target_time": "2026-04-08T11:00:00Z", "predicted_delta_kwh": 0.1234 },
    { "hour": 2, "target_time": "2026-04-08T12:00:00Z", "predicted_delta_kwh": null }
  ]
}
```

`predicted_delta_kwh` is `null` when all three historical anchors are missing or negative (meter resets). Always 23 entries.

**Example:**
```bash
curl https://<host>/api/device/e0202/delta-forecast -H "Authorization: Bearer $API_KEY"
```

---

## Forecasting

### GET `/api/forecast/{device_id}`

24-hour XGBoost power consumption forecast. Only available for devices `e0202`, `e0207`, and `e0211`.

**Path params:** `device_id` — one of `e0202`, `e0207`, `e0211`

**Errors:** `404` if device_id is not in the supported set.

**Example:**
```bash
curl https://<host>/api/forecast/e0202 -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/predictions/{device_id}`

Math-derived predicted measurements and FAIR scores at multiple future time horizons.

**Path params:** `device_id`

**Example:**
```bash
curl https://<host>/api/predictions/e0101 -H "Authorization: Bearer $API_KEY"
```

---

## Financial

### GET `/api/financial-impact`

Financial impact report for the site: excess energy costs, power factor penalties, and demand charges derived from FAIR score data.

**Example:**
```bash
curl https://<host>/api/financial-impact -H "Authorization: Bearer $API_KEY"
```

---

### GET `/api/financial-config`

Get the current tariff and maintenance cost configuration.

**Response:** JSON object with tariff rates, maintenance cost per tier, and demand charge thresholds.

**Example:**
```bash
curl https://<host>/api/financial-config -H "Authorization: Bearer $API_KEY"
```

---

### POST `/api/financial-config`

Update tariff and maintenance cost configuration.

**Request body:** Same shape as the GET response. All fields optional — only provided fields are updated.

**Example:**
```bash
curl -X POST https://<host>/api/financial-config \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tariff_per_kwh": 0.42}'
```

---

## Site

### GET `/api/site/summary`

Fleet-wide summary: total AHU count, overall site health index, active alerts, per-level tile data, and trend deltas.

**Example:**
```bash
curl https://<host>/api/site/summary -H "Authorization: Bearer $API_KEY"
```

---

## Error Reference

| Code | Meaning |
|------|---------|
| `400` | Bad request — input validation failed or injection detected |
| `401` | Unauthorized — missing or invalid API key |
| `404` | Not found — device ID or level out of range |
| `422` | Unprocessable — LLM could not parse the query |
| `429` | Too many requests — rate limit exceeded |
| `502` | InfluxDB query failed |
| `503` | Service unavailable — LLM or upstream dependency is down |

---

## FAIR Health Tier Reference

| Score | Tier | Recommended action |
|-------|------|--------------------|
| 80–100 | Healthy | None — monitor routinely |
| 60–79 | Monitor | Watch for downward trend |
| 40–59 | Maintenance | Schedule preventive visit |
| 0–39 | Critical | Escalate to facilities team |
