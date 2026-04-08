# WACH Insight — Project Constitution

> Load this file into every Claude/Coder/AI session before making changes.
> It is the canonical reference for architecture, conventions, and env vars.
> Last updated: 2026-03-24

---

## 1. Tech Stack

| Layer | Technology | Version/Notes |
|-------|-----------|---------------|
| Backend | FastAPI + Uvicorn | Python 3.11, port 8081 (dev) |
| Frontend | React + Vite + TypeScript | Tailwind v3, Recharts, Framer Motion, Zustand |
| Time-series DB | InfluxDB Cloud | Org: `wach`, Bucket: `wach_bucket_3` |
| Vector DB | ChromaDB | RAG for chatbot context (`data/chroma/`) |
| ML Models | XGBoost | Saved at `paraquet_data/models/saved/` (e0202, e0207, e0211 only) |
| LLM (cloud) | Gemini 2.0 Flash | via Google AI Studio |
| LLM (local) | Qwen (qwen3-coder-next) | via LM Studio on `localhost:1234` |
| Frontend host | Vercel | `frontend/dist/` output |
| Backend tunnel | Cloudflare Tunnel | `*.trycloudflare.com` subdomain |
| Container | Docker | `python:3.11-slim`, port from `$PORT` env var |

**Dev URLs:**
- Frontend → `http://localhost:3000` (proxies `/api` → `http://localhost:8081`)
- Backend → `http://localhost:8081`

---

## 2. AHU ID Convention

**Format:** `e[LEVEL][NN]`

- `LEVEL` = two-digit building level (01–11)
- `NN` = two-digit device number within the level (01–21 depending on level)
- **Validation regex:** `^e\d{4}$`
- **Examples:** `e0101` (Level 1, AHU 1), `e0507` (Level 5, AHU 7), `e1108` (Level 11, AHU 8)
- **Total:** 121 AHUs across 11 levels

Source of truth for valid device IDs: `backend/models/schemas.py → AHU_LEVEL_CONFIG`

Level distribution (device count):
```
L1: 21  L2: 15  L3: 16  L4: 13  L5: 12
L6: 11  L7:  4  L8:  5  L9:  8  L10: 8  L11: 8
```

> **Rule:** Never invent or guess device IDs. Only reference devices that exist in `AHU_LEVEL_CONFIG`.
> The chat system prompt enforces this — responses citing non-existent devices are a bug.

---

## 3. API Route Patterns

All routes under `/api/*` require authentication:
- Header: `Authorization: Bearer <API_KEY>`
- Query param: `?api_key=<API_KEY>`

Rate limit: 200 req / 60 s (env vars: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check (no auth) |
| GET | `/api/levels` | List levels 1–11 |
| GET | `/api/level/{id}/scores` | FAIR 5-score breakdown for every AHU on a level |
| GET | `/api/level/{id}/health-index` | Health index time series |
| GET | `/api/device/{id}/raw-score-relationship` | Raw metric ↔ component score mapping |
| GET | `/api/dashboard/ranking?level=N&range=...` | Top-5 best/worst AHUs |
| GET | `/api/dashboard/trend?level=N&range=...` | Health trend chart data |
| POST | `/api/forecast/{device_id}` | 24 h XGBoost power forecast (e0202, e0207, e0211 only) |
| GET | `/api/predictions/{device_id}` | Multi-horizon forecasts (1h, 12h, 24h, 168h) |
| GET | `/api/device/{device_id}/delta-forecast` | 23 hourly delta-kWh predictions |
| POST | `/api/chat` | Conversational query (Gemini 2.0 Flash or Qwen) |
| POST | `/api/query` | NLU → InfluxDB structured query |
| GET | `/api/financial-config` | Load TNB tariff rates & maintenance costs |
| POST | `/api/financial-config` | Save financial parameters |
| GET | `/api/financial-impact` | Cost breakdown: excess energy + PF penalty + maintenance risk |
| GET | `/api/measurements/{device_id}` | Latest instantaneous readings |

---

## 4. FAIR Score Weights & Interpretation

FAIR = per-AHU fault/anomaly scoring using robust statistics (not cross-fleet comparisons).

### Component Weights (sum to 1.0)

```
energy_anomaly   → 15%   hourly delta vs predicted seasonal baseline
power_factor     → 25%   PF degradation below 0.85 target
phase_imbalance  → 25%   current unbalance %, NEMA MG-1 target <2%
thd_drift        → 15%   THD composite 24 h rolling mean, IEEE 519 target <5%
overload         → 20%   power_total vs robust median × 1.2 threshold
```

Source: `backend/core/fair_health_scoring.py → HEALTH_INDEX_WEIGHTS`

### Scoring Formula

Each component produces a value in [0, 1]:

```
component_score = 0.70 × sigmoid(z × sensitivity) + 0.30 × sigmoid(slope_7d × 3.0)
```

- **70% level term** — how bad is it RIGHT NOW? (z-score vs own historical baseline)
- **30% trend term** — is it GETTING WORSE? (7-day slope direction and magnitude)

### Health Index

```
health_index = 100 × (1 − Σ weight_i × component_score_i)
```

| Range | Tier | Recommended Action |
|-------|------|--------------------|
| 80–100 | Healthy | No action needed |
| 60–79 | Monitor | Watch trend, schedule check |
| 40–59 | Maintenance Soon | Schedule service |
| 0–39 | Critical | Immediate intervention |

### Baselines

Per-AHU robust statistics (median + MAD), **not** cross-fleet averages.
Each AHU is compared only against its own history.

Minimum robust-std floors (prevent division-by-zero):
```
delta_kwh: 0.05  |  power_factor_avg: 0.008  |  current_unbalance: 0.15
composite_thd_24h: 0.15  |  power_total: 0.05
```

### Safety Flags (non-scoring, engineering audit only)

Safety flags do NOT move the health index. They are separate audit markers.

| Flag | Trigger Condition |
|------|------------------|
| `THD_CHRONIC_HIGH` | AHU's own median THD > 5% |
| `IMBALANCE_SEVERE` | AHU's own median unbalance > 5% |
| `PF_CHRONIC_LOW` | AHU's own median PF < 0.85 |
| `OVERLOAD_CHRONIC` | AHU's own median power > computed threshold |

In chat responses, always translate flag codes to plain English (e.g., "chronic high harmonic distortion").

---

## 5. hospital_id Parameterisation

```python
# backend/config.py
def get_hospital_id() -> str:
    return os.getenv("HOSPITAL_ID", "wach")
```

- **Default:** `"wach"` (single-tenant mode, current production)
- **Status:** Defined but not yet wired into API route logic (reserved for multi-tenant expansion)
- **Usage:** Set `HOSPITAL_ID=<slug>` in `.env` when deploying for a different facility

---

## 6. LLM_BACKEND Env Var

The env var is **`LLM_BACKEND`** (not `LLM_PROVIDER` — that name is wrong and should not be used).

| Value | Backend | Required env vars | Default model |
|-------|---------|------------------|---------------|
| `qwen` **(default)** | LM Studio (local) | `LMS_BASE_URL`, `LMS_MODEL`, `LMS_API_KEY` | `qwen/qwen3-coder-next` |
| `gemini` | Google AI Studio | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_EMBED_MODEL` | `gemini-2.0-flash` |

`.env` snippet:
```
LLM_BACKEND=gemini
GEMINI_API_KEY=<key>
# --- or for local ---
LLM_BACKEND=qwen
LMS_BASE_URL=http://localhost:1234/v1
LMS_MODEL=qwen/qwen3-coder-next
LMS_API_KEY=lm-studio
```

Source: `backend/llm/client_factory.py`

---

## 7. Vercel + Cloudflare Tunnel Deployment Pattern

```
Browser
  └─► Vercel (serves frontend/dist/ as static SPA)
          └─► /api/* rewrite ──► Cloudflare Tunnel URL (*.trycloudflare.com)
                                        └─► FastAPI uvicorn (port 8081)
                                                └─► InfluxDB Cloud
```

**vercel.json rewrite pattern** (current production):
```json
{
  "buildCommand": "cd frontend && npm ci && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://<tunnel-subdomain>.trycloudflare.com/api/$1"
    },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**Deploying a new tunnel (when tunnel URL changes):**
1. Start backend: `uvicorn backend.main:app --host 0.0.0.0 --port 8081`
2. Expose tunnel: `cloudflared tunnel --url http://localhost:8081`
3. Copy the `*.trycloudflare.com` URL printed to stdout
4. Update `vercel.json` rewrite destination with new URL
5. Redeploy frontend: `vercel --prod` (or push to GitHub for auto-deploy)
6. Set backend env: `CORS_ORIGINS=https://<your-app>.vercel.app`

> Note: Cloudflare free tunnels (`trycloudflare.com`) generate a new subdomain each restart. For stable production use, set up a named tunnel with a persistent domain.

---

## 8. Data Pipeline

```
InfluxDB Cloud (source of truth, real-time)
    │
    ▼  scripts/etl/run_health_etl.py  (run hourly via cron)
    │
    ├── data/health_all_levels.csv    121 devices × hourly rows (~121K rows, 35 cols)
    └── data/predictions.csv          energy anomaly cache, latest value per AHU (~121 rows)
    │
    ▼  FastAPI
    ├── csv_reader.py   reads CSVs for dashboard/chat context (no InfluxDB needed for most reads)
    └── influx_client.py  fetches live data for /api/measurements and fresh score computation
    │
    ▼  Frontend (React) + Chatbot (Gemini/Qwen)
```

**ETL entry points:**
```bash
# Full health score refresh (writes to health_all_levels.csv)
python scripts/etl/run_health_etl.py --level all

# Regenerate energy anomaly predictions (writes to predictions.csv)
python scripts/etl/run_prediction_etl.py

# Multi-horizon forecast cache (writes to data/predictions_multihorizon.csv)
python scripts/generate_predictions.py --mode append
```

---

## 9. Key File Map

| Concern | File |
|---------|------|
| App entry (backend) | `backend/main.py` |
| Env config & validation | `backend/config.py` |
| FAIR health algorithm | `backend/core/fair_health_scoring.py` |
| InfluxDB queries | `backend/core/influx_client.py` |
| CSV reader (dashboard data) | `backend/core/csv_reader.py` |
| Risk engine | `backend/core/risk_engine.py` |
| LLM routing | `backend/llm/client_factory.py` |
| Chat system prompts | `backend/llm/prompts.py` |
| Chat endpoint | `backend/routes/chat.py` |
| Device schemas & AHU map | `backend/models/schemas.py` |
| Frontend app entry | `frontend/src/App.tsx` |
| Frontend state (Zustand) | `frontend/src/store/useAppStore.ts` |
| Frontend API client | `frontend/src/api/client.ts` |
| Deployment config | `vercel.json`, `Dockerfile`, `DEPLOYMENT.md` |
| Known integration gaps | `docs/INTEGRATION_BUGS.md` |
