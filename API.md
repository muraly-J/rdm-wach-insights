# WACH Insight — Chatbot API Reference

> **Interactive docs**: once deployed, visit `http://localhost:8081/docs` for live Swagger UI.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env                          # fill in 4 lines
cp ward_config.example.yml ward_config.yml    # fill in AHU layout
docker compose up --build

# 2. Verify the API is live
curl http://localhost:8081/health

# 3. Say hello to the chatbot
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"message": "what is the health of level 3?"}'
```

## Authentication

Every request (except `GET /health`) requires an API key header:

```
X-API-Key: <your API_KEY from .env>
```

Generate a key: `openssl rand -base64 32`

---

## Endpoints

### `GET /health`

No auth required. Use for Docker healthchecks and uptime monitoring.

**Response:**
```json
{"status": "ok"}
```

---

### `POST /api/chat` — The chatbot

**Request body:**
```json
{
  "message": "why is e0501 showing a low power factor?",
  "history": [
    {"role": "user", "content": "show me level 5"},
    {"role": "assistant", "content": "Level 5 has 11 AHUs..."}
  ],
  "context": {},
  "persona": "technical"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User's question. Max 1000 characters. |
| `history` | array | No | Previous conversation turns. Each item: `{"role": "user"\|"assistant"\|"model", "content": string}` |
| `context` | object | No | Optional extra context dict passed through to the LLM. |
| `persona` | string | No | Response style hint. One of: `general` (default), `technical`, `technician`, `financial` |

**Response:**
```json
{
  "reply": "AHU e0501 has a power factor of 0.81, below the 0.85 TNB threshold...",
  "navigate": null,
  "thinking_mode": "think"
}
```

| Field | Description |
|-------|-------------|
| `reply` | Markdown-formatted response. Render with a markdown parser. |
| `navigate` | Always `null` in the current release. Reserved for future frontend navigation hints. |
| `thinking_mode` | `"think"` or `"fast"`. Show a subtle "deep reasoning" indicator when `"think"`. |

**Personas explained:**
- `general` — plain language, no jargon, "is this serious / does someone need to fix it"
- `technical` — engineering terminology, IEEE/ASHRAE standards, numerical thresholds
- `technician` — step-by-step repair/diagnostic actions, LOTO safety steps, measurement instructions
- `financial` — leads with RM cost and penalties, ROI framing, TNB tariff calculations

**Persona detection:** the backend auto-detects persona from message content and history. The `persona` field is an optional override.

**Example conversation:**
```bash
# First message
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "which AHUs on level 5 need attention?"}'

# Follow-up with history
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "message": "why is e0507 in the maintenance tier?",
    "history": [
      {"role": "user", "content": "which AHUs on level 5 need attention?"},
      {"role": "assistant", "content": "e0507 and e0509 are in Maintenance tier..."}
    ]
  }'
```

---

### `GET /api/dashboard/ranking`

Top 5 healthiest and top 5 needs-attention AHUs for a level.

**Query params:**
| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `level` | No | `1` | Level number (1–11) |
| `time_range` | No | `last_30d` | One of: `last_24h`, `last_7d`, `last_30d`, `all_time` |

**Example:**
```bash
curl "http://localhost:8081/api/dashboard/ranking?level=5&time_range=last_30d" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "level": "5",
  "time_range": "last_30d",
  "snapshot_time": "2026-04-01T08:00:00Z",
  "best": [
    {"device_id": "e0503", "index": 92.4, "tier": "Healthy", "level": "Level 5"},
    {"device_id": "e0508", "index": 89.1, "tier": "Healthy", "level": "Level 5"}
  ],
  "worst": [
    {"device_id": "e0507", "index": 41.2, "tier": "Maintenance", "level": "Level 5"},
    {"device_id": "e0509", "index": 55.8, "tier": "Monitor", "level": "Level 5"}
  ]
}
```

Up to 5 items in each of `best` and `worst`. Items are sorted: `best` descending by health index, `worst` ascending (lowest first).

---

### `GET /api/dashboard/trend`

Health index time-series with FAIR component scores for all AHUs on a level.

**Query params:**
| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `level` | No | `1` | Level number (1–11) |
| `range` | No | `7d` | One of: `24h`, `7d`, `30d` |

**Bucketing:**
- `24h` — hourly data points
- `7d` / `30d` — daily average data points

**Example:**
```bash
curl "http://localhost:8081/api/dashboard/trend?level=5&range=7d" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "level": "5",
  "range": "7d",
  "ahus": ["e0501", "e0502", "e0503"],
  "series": [
    {
      "timestamp": "2026-03-25T00:00:00Z",
      "device_id": "e0501",
      "health_index": 78.3,
      "energy_anomaly": 0.0421,
      "pf_degradation": 0.1200,
      "phase_imbalance": 0.0080,
      "thd_drift": 0.0310,
      "overload": 0.0000
    }
  ],
  "latest_snapshot": {
    "e0501": 78.3,
    "e0502": 91.0,
    "e0503": 65.4
  },
  "safety_flags": {
    "e0501": [
      {"flag_id": "PF_CHRONIC_LOW", "label": "Low Power Factor", "severity": "Moderate"}
    ],
    "e0502": [],
    "e0503": []
  }
}
```

`series` is sorted by `(timestamp, device_id)`. Each FAIR component score is a penalty value (higher = worse degradation).

---

### `GET /api/levels`

List all available building levels.

**Example:**
```bash
curl "http://localhost:8081/api/levels" -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{"levels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
```

---

### `GET /api/level/{level_id}/scores`

Five FAIR-score breakdown for all AHUs on a level, read from CSV.

**Path params:** `level_id` — integer (1–11)

**Query params:** `time_range` — `24h`, `7d` (default), or `30d`

**Example:**
```bash
curl "http://localhost:8081/api/level/5/scores?time_range=7d" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "level": 5,
  "time_range": "7d",
  "devices": [ ... ],
  "generated_at": "2026-04-01T08:00:00.000000"
}
```

`devices` is a list of per-AHU score objects (shape determined by `core.csv_reader.get_score_breakdown`).

---

### `GET /api/level/{level_id}/health-index`

Health index time series for all AHUs on a level (or a single device), read from CSV.

**Path params:** `level_id` — integer (1–11)

**Query params:**
| Param | Required | Description |
|-------|----------|-------------|
| `device_id` | No | Filter to a single device (e.g., `e0501`) |
| `time_range` | No | `24h`, `7d` (default), or `30d` |

**Response:**
```json
{
  "level": 5,
  "time_range": "7d",
  "devices": [ ... ],
  "generated_at": "2026-04-01T08:00:00.000000"
}
```

`devices` is a list of per-device time-series objects.

---

### `GET /api/device/{device_id}/raw-score-relationship`

Raw sensor data vs. computed FAIR score mapping for a single device.

**Path params:** `device_id` — e.g., `e0501`

**Query params:** `range` — `24h`, `7d` (default), or `30d`

**Response:**
```json
{
  "device_id": "e0501",
  "range": "7d",
  "scores": { ... },
  "generated_at": "2026-04-01T08:00:00.000000"
}
```

---

### `GET /api/device/{device_id}/measurements`

Arbitrary metric time-series from InfluxDB for a single device.

**Path params:** `device_id` — e.g., `e0501`

**Query params:**
| Param | Required | Description |
|-------|----------|-------------|
| `metrics` | Yes | Comma-separated metric names (max 10). See `/docs` for allowed values. |
| `range` | No | `24h`, `7d` (default), or `30d` |

**Example:**
```bash
curl "http://localhost:8081/api/device/e0501/measurements?metrics=power_factor_avg,current_l1&range=24h" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "device_id": "e0501",
  "range": "24h",
  "measurements": {
    "power_factor_avg": [
      {"timestamp": "2026-04-01T07:00:00+00:00", "value": 0.83},
      {"timestamp": "2026-04-01T08:00:00+00:00", "value": 0.84}
    ],
    "current_l1": [
      {"timestamp": "2026-04-01T07:00:00+00:00", "value": 12.4}
    ]
  }
}
```

---

### `GET /api/financial-impact`

Financial impact report — excess energy cost, PF penalties, demand charges, and maintenance risk.

**Query params:**
| Param | Required | Description |
|-------|----------|-------------|
| `level` | Yes | Level number (1–20) |
| `time_range` | No | `24h`, `7d`, or `30d` (default: `30d`) |
| `device_id` | No | Filter to a single AHU |

**Example:**
```bash
curl "http://localhost:8081/api/financial-impact?level=5&time_range=30d" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "currency": "RM",
  "level": 5,
  "range": "30d",
  "grand_total": 1842.50,
  "excess_energy_cost": 320.10,
  "pf_penalty_cost": 195.40,
  "maintenance_risk": 1000.00,
  "demand_charge_myr": 327.00,
  "top_ahus": [
    {
      "ahu_id": "e0507",
      "health_index": 41.2,
      "excess_energy_cost": 88.40,
      "pf_penalty_cost": 52.10,
      "maintenance_risk": 1000.00,
      "demand_charge_myr": 95.30,
      "total_cost": 1235.80
    }
  ]
}
```

`top_ahus` contains up to 10 AHUs sorted by `total_cost` descending.

**Financial config endpoints** (GET and POST `/api/financial-config`) allow updating tariff rate, max demand rate, maintenance cost, and emergency multiplier. See `/docs` for schema.

---

### `GET /api/site/summary`

Fleet-wide summary: total AHUs, average site health, alerts count, level tiles, and trend deltas.

**Query params:** `range` — `24h`, `7d` (default), or `30d`

**Example:**
```bash
curl "http://localhost:8081/api/site/summary?range=7d" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "totalAHUs": 87,
  "avgSiteHealth": 74.3,
  "ahusInAlert": 12,
  "estMonthlyCostMYR": 0.0,
  "starAHU": {
    "id": "e0503",
    "name": "AHU-L5-03",
    "level": 5,
    "healthScore": 96.2,
    "monthlyCostMYR": 0.0,
    "safetyFlags": 0
  },
  "criticalAHU": {
    "id": "e0507",
    "name": "AHU-L5-07",
    "level": 5,
    "healthScore": 38.1,
    "monthlyCostMYR": 0.0,
    "safetyFlags": 0
  },
  "levelTiles": [
    {"level": 1, "avgHealth": 81.2, "ahuCount": 8},
    {"level": 5, "avgHealth": 72.4, "ahuCount": 11}
  ],
  "trendDeltas": [
    {"label": "Energy", "value": -2.3, "unit": "%", "direction": "down"},
    {"label": "Health", "value": 1.4, "unit": "pts", "direction": "up"},
    {"label": "Cost", "value": 0.0, "unit": "MYR", "direction": "down"},
    {"label": "Alerts", "value": -1.0, "unit": "", "direction": "down"}
  ]
}
```

Note: `estMonthlyCostMYR` and `monthlyCostMYR` are `0.0` in the current release. Use `/api/financial-impact` per level for cost data.

---

### `GET /api/forecast/{device_id}`

24-hour power_total forecast using a pre-trained XGBoost model. Returns 7-day historical chart data plus 96-step (15-min interval) forecast.

**Supported devices:** `e0202`, `e0207`, `e0211` only.

**Path params:** `device_id` — one of the supported devices above.

**Example:**
```bash
curl "http://localhost:8081/api/forecast/e0202" \
  -H "X-API-Key: $API_KEY"
```

**Response:**
```json
{
  "query_type": "forecast",
  "device_id": "e0202",
  "history": [
    {"time": "2026-03-25T00:00:00+00:00", "value": 14.3210},
    {"time": "2026-03-25T00:15:00+00:00", "value": 14.1050}
  ],
  "forecast": [
    {"time": "2026-04-01T08:15:00+00:00", "value": 15.4320},
    {"time": "2026-04-01T08:30:00+00:00", "value": 15.2100}
  ],
  "recent_avg": 14.8830,
  "summary": "24-hour power forecast for e0202: predicted average 15.10 kW, peak 18.23 kW at 14:00 UTC.",
  "generated_at": "2026-04-01T08:00:00+00:00"
}
```

`history` contains up to 672 15-min points (7 days). `forecast` contains exactly 96 15-min points (24 hours). Values are in kW.

---

### `GET /api/predictions/{device_id}`

Math-predicted measurements, FAIR scores, and health index at multiple future horizons.

**Path params:** `device_id` — any valid AHU ID (e.g., `e0501`)

**Query params:** `horizons` — comma-separated, default `1h,12h,24h,168h`. Valid values: `1h`, `12h`, `24h`, `168h`.

**Example:**
```bash
curl "http://localhost:8081/api/predictions/e0501?horizons=1h,24h" \
  -H "X-API-Key: $API_KEY"
```

**Response:** Shape determined by `core.prediction_engine.compute_predictions_async`. See `/docs` for the full schema.

---

## FAIR Health Tiers

| Tier | Score | What it means | Recommended action |
|------|-------|---------------|-------------------|
| Healthy | 80–100 | Normal operation | Scheduled PM only |
| Monitor | 60–79 | Early warning signs | Watch closely, investigate trend |
| Maintenance | 40–59 | Needs attention | Book work order within 1–2 weeks |
| Critical | 0–39 | Failure risk | Immediate action, escalate to engineer |

FAIR scores are five component penalty scores: **F**requency anomaly (energy), po**A**wer factor degradation, phase **I**mbalance, THD d**R**ift, and overload.

---

## Safety Flags

| Flag ID | Label | Severity |
|---------|-------|----------|
| `THD_CHRONIC_HIGH` | THD Critical | High |
| `OVERLOAD_CHRONIC` | Overload Risk | High |
| `IMBALANCE_SEVERE` | Severe Imbalance | High |
| `PF_CHRONIC_LOW` | Low Power Factor | Moderate |

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | Invalid query params (e.g., unknown level, unsupported range) |
| `401 Unauthorized` | Missing or invalid `X-API-Key` |
| `404 Not Found` | Device or level has no data in the selected time range |
| `422 Unprocessable Entity` | Invalid request body (check field types/constraints) |
| `429 Too Many Requests` | Rate limit exceeded (default: 100 req/min) |
| `503 Service Unavailable` | InfluxDB, LLM, or CSV data source unreachable |

---

## Multi-Ward Deployment

Each ward deployment is a separate `docker compose up` with its own `.env` and `ward_config.yml`.
Two deployments can run on the same host using different `BACKEND_PORT` values:

```bash
# Ward A on port 8081
BACKEND_PORT=8081 docker compose --project-name wcw up -d

# Ward B on port 8082 (different .env + ward_config.yml in a separate directory)
BACKEND_PORT=8082 docker compose --project-name icu -f ../icu/docker-compose.yml up -d
```
