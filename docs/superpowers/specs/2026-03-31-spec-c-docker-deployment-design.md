# Spec C — Docker Deployment

**Date:** 2026-03-31
**Status:** Approved
**Scope:** Spec C of three — docker-compose packaging of the WACH chatbot backend as a plug-and-play API service

---

## Overview

Package the WACH Insight backend as a self-contained, colleague-deployable chatbot API. The deliverable is a `docker compose up` experience: a colleague clones the repo, fills in five lines of `.env`, runs one command, and has a fully operational chatbot API with DuckDB health data and ChromaDB RAG — ready to build a frontend against.

**What is in scope:**
- `docker-compose.yml` with two services: `backend` and `etl`
- Named volumes for DuckDB and ChromaDB persistence
- ETL sidecar that self-initialises on first boot (migration + RAG ingest) then runs on a cron schedule
- `.env.example` documenting every configurable variable
- `API.md` — narrative integration guide for frontend builders
- FastAPI's auto-generated Swagger UI available at `/docs`

**What is out of scope:**
- Frontend containerisation (frontend stays on Vercel or developer's choice)
- LLM containerisation (LM Studio / Qwen3 remains external)
- InfluxDB containerisation (remains external)

---

## Section 1: Container Architecture

Two containers built from the same `Dockerfile`, two named volumes.

```
docker-compose.yml
│
├── backend   (FastAPI, port 8081)
│   ├── volume: duckdb_data   → /app/data/         (DuckDB file + sentinel)
│   └── volume: chroma_data   → /app/data/chroma/  (ChromaDB embeddings)
│
└── etl       (first-run init + cron scheduler)
    ├── volume: duckdb_data   (same — ETL writes, backend reads read-only)
    └── volume: chroma_data   (same — ETL ingests, backend queries)
```

Markdown RAG docs (`backend/data/rag_docs/*.md`) are **baked into the image** at build time. The ETL reads them from the image filesystem during the first-run ingest. Embeddings are persisted in `chroma_data`. No separate volume for source docs is needed.

**Access modes:**
- `backend` opens DuckDB in read-only mode (`duckdb.connect(path, read_only=True)`)
- `etl` opens DuckDB in read-write mode
- Both are safe to run concurrently — DuckDB supports multiple concurrent readers and one writer

**External dependencies (env vars only, no containers):**
- LLM: `LMS_BASE_URL` — points to LM Studio on host or a shared GPU server
- InfluxDB: `INFLUX_URL` + `INFLUX_TOKEN` — points to the hospital's InfluxDB instance

---

## Section 2: ETL Sidecar — First-Run Init + Cron

### Entrypoint: `docker/etl-entrypoint.sh`

```
On container start:
  1. Check /app/data/.migrated sentinel file
     NOT present →
       run: python -m scripts.etl.migrate_csv_to_duckdb   (~10s)
       run: python -m scripts.ingest_all_docs              (~2min, embeds ~150 chunks)
       touch /app/data/.migrated
     Present →
       skip init entirely

  2. Start supercronic with /app/docker/etl.cron
     (supercronic: Shopify-maintained, PID-1 safe container cron)
```

### Cron file: `docker/etl.cron`

Two lines — both pipelines, matching what the GitHub Actions scheduler runs today:
```
${ETL_SCHEDULE} python -m scripts.etl.run_prediction_etl --level all
${ETL_SCHEDULE} python -m scripts.etl.run_health_etl --level all --output-hourly
```

`ETL_SCHEDULE` defaults to `0 * * * *` (hourly). The GitHub Actions scheduler runs every 30 minutes — if that cadence is needed, set `ETL_SCHEDULE=0,30 * * * *`.

### Relationship to GitHub Actions scheduler

Once the Docker ETL sidecar is running at a hospital deployment, the `etl-scheduler.yml` GitHub Actions workflow is redundant for that deployment. The Actions workflow can have its `schedule` trigger disabled; the `workflow_dispatch` (manual trigger) is worth keeping for ad-hoc debugging.

The Actions workflow currently also **commits output files back to git** (`health_hourly.csv`, `healthdb.duckdb`, etc.) to serve as seed data for new deployments. Once Docker is the primary deployment model, new colleagues don't need pre-seeded files — the ETL populates the DuckDB volume from InfluxDB on first run. The migration script (`migrate_csv_to_duckdb.py`) becomes optional: run it if a pre-populated CSV exists, skip it if not.

### Re-run safety

The ETL script already uses `INSERT OR REPLACE` (idempotent upserts). The migration script also uses upserts. Re-running is always safe.

**To force re-initialisation** (e.g. after a RAG docs update):
```bash
docker compose run etl rm /app/data/.migrated
docker compose restart etl
```

---

## Section 3: File Inventory

### New files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Two-service compose: backend + etl, two named volumes |
| `docker/etl-entrypoint.sh` | Sentinel check → migration/ingest → supercronic |
| `docker/etl.cron` | Cron schedule file consumed by supercronic |
| `.env.example` | Every env var documented with comments and defaults |
| `API.md` | Narrative integration guide + endpoint reference for frontend builders |

### Modified files

| File | Change |
|------|--------|
| `Dockerfile` | Add `supercronic` install; remove Railway-specific PORT default; keep `railway.toml` compatibility |

### Unchanged

Everything in `backend/` is untouched. No application code changes in Spec C.

---

## Section 4: docker-compose.yml Design

```yaml
services:
  backend:
    build: .
    ports:
      - "${BACKEND_PORT:-8081}:8081"
    volumes:
      - duckdb_data:/app/data
      - chroma_data:/app/data/chroma
    env_file: .env
    environment:
      - DUCKDB_READ_ONLY=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  etl:
    build: .
    command: /app/docker/etl-entrypoint.sh
    volumes:
      - duckdb_data:/app/data
      - chroma_data:/app/data/chroma
    env_file: .env
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  duckdb_data:
  chroma_data:
```

`depends_on: backend` ensures the ETL container starts after the backend container has been created (not necessarily healthy). The ETL's migration writes to the shared volume directly — it does not call the backend. The healthcheck on the backend is for monitoring and `docker ps` visibility only.

---

## Section 5: Environment Variables

The `.env.example` ships **pre-configured for the Women and Child Ward, Hospital Kuala Lumpur**. A colleague fills in three required values and nothing else. This is the intended minimum viable setup.

### What the colleague fills in (3 required + 1 security)

```bash
INFLUX_URL=           # your InfluxDB server URL
INFLUX_TOKEN=         # your InfluxDB API token (read access)
INFLUX_BUCKET=        # your InfluxDB bucket name
API_KEY=              # generate with: openssl rand -base64 32
```

### Full `.env.example` (shipped with defaults pre-set)

```bash
# ═══════════════════════════════════════════════════════════════════
# WACH Insight — Women and Child Ward, Hospital Kuala Lumpur
# ═══════════════════════════════════════════════════════════════════
# To deploy for a different ward or hospital, update the Identity
# section below and point the InfluxDB vars at the new data source.
# Everything else can stay as-is.
# ═══════════════════════════════════════════════════════════════════

# ── YOU MUST FILL THESE IN ────────────────────────────────────────
INFLUX_URL=http://YOUR_INFLUXDB_HOST:8086
INFLUX_TOKEN=your-influxdb-token-here
INFLUX_BUCKET=your-bucket-name-here
API_KEY=generate-with-openssl-rand-base64-32

# ── Identity (pre-set for Women & Child Ward HKL) ────────────────
# Change these when deploying for a different ward or hospital.
WACH_BUILDING_NAME=Hospital Kuala Lumpur
WACH_DEPARTMENT=Women and Child Ward
HOSPITAL_ID=hkl-wcw

# ── LLM ──────────────────────────────────────────────────────────
# Docker Desktop (Mac/Windows): host.docker.internal works as-is.
# Linux host: replace with the host machine's LAN IP.
LMS_BASE_URL=http://host.docker.internal:1234/v1
LMS_MODEL=qwen/qwen3-coder-next
LMS_API_KEY=lm-studio

# ── InfluxDB extras ───────────────────────────────────────────────
INFLUX_ORG=wach
# Set true only if InfluxDB runs plain HTTP on a non-localhost address
INFLUX_SKIP_TLS=false

# ── Networking ────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
BACKEND_PORT=8081

# ── ETL Schedule (cron syntax) ────────────────────────────────────
ETL_SCHEDULE=0 * * * *

# ── Optional ─────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
DEBUG=false
```

### Scalability model

This repo is a **ward profile**. Deploying for a new ward or hospital means:

1. Clone the repo
2. `cp .env.example .env`
3. Fill in the 4 required vars (InfluxDB credentials + API key)
4. Update the Identity block (building name, department, hospital ID)
5. `docker compose up`

No code changes. No Dockerfile changes. The chatbot's system prompt, tool descriptions, and all business logic adapt automatically via the identity env vars.

```
Clone → Configure .env → docker compose up
         ↑ 4 lines max
```

**Scaling path:**
```
Women & Child Ward (HKL)   →  repo + .env A
ICU (HKL)                  →  same repo + .env B  (different bucket)
Paediatric Ward (PPUM)     →  same repo + .env C  (different hospital)
```

Each deployment is fully isolated. Same codebase, different identities and data sources.

---

## Section 6: API.md Structure

`API.md` in the repo root. Audience: a developer building a frontend who has never seen this codebase.

### Contents outline

```
# WACH Insight Chatbot API

## Quick Start (3 steps)
## Authentication
## Base URL & Health Check
## Endpoints
  ### POST /api/chat            ← primary — this is the chatbot
  ### GET  /api/dashboard/trend
  ### GET  /api/dashboard/ranking
  ### GET  /api/health-scores
  ### GET  /api/measurements
  ### GET  /api/financial-impact
  ### GET  /api/site-summary
  ### GET  /api/forecast
  ### GET  /api/predictions
## Response Fields Explained
  - thinking_mode: what it means, when to show an indicator
  - nav_target: how to use it for frontend navigation
  - FAIR tiers: Healthy / Monitor / Maintenance / Critical
## Streaming (future)
## Error Codes
## Multi-Ward Notes
## Interactive Docs (Swagger)
```

Each endpoint section includes: method + path, description, all query params / request body fields, full example request (`curl`), full example response (JSON), and notes on what to do with the data.

The `/api/chat` section is the longest — it explains `message`, `history`, `persona` (the four roles), `thinking_mode` in the response, and gives example conversations.

---

## Section 7: Multi-Ward Deployment Pattern

See Section 5 (Scalability model) for the full pattern. In brief: each ward/hospital is an independent `docker compose up` with its own `.env`. No shared state between deployments. Two instances can run on the same VM by setting different `BACKEND_PORT` values.

```
Women & Child Ward (HKL)      ICU (HKL)
────────────────────────       ──────────────────────
HOSPITAL_ID=hkl-wcw            HOSPITAL_ID=hkl-icu
WACH_DEPARTMENT=Women...       WACH_DEPARTMENT=ICU
INFLUX_BUCKET=wcw_bucket       INFLUX_BUCKET=icu_bucket
BACKEND_PORT=8081               BACKEND_PORT=8082

→ API at :8081                 → API at :8082
→ own DuckDB volume            → own DuckDB volume
→ own ChromaDB volume          → own ChromaDB volume
```

---

## Section 8: Dockerfile Changes

Two additions to the existing `Dockerfile`:

1. **Install supercronic** (lightweight container cron):
```dockerfile
RUN curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64 \
    -o /usr/local/bin/supercronic && chmod +x /usr/local/bin/supercronic
```

2. **Copy docker/ entrypoint scripts** into the image:
```dockerfile
COPY docker/ ./docker/
RUN chmod +x docker/etl-entrypoint.sh
```

The `CMD` in the Dockerfile remains the uvicorn command (for Railway). The ETL container overrides it with `command: /app/docker/etl-entrypoint.sh` in compose.

---

## Section 9: Verification Checklist

After `docker compose up`:

1. `curl http://localhost:8081/health` → `{"status": "ok"}`
2. `curl http://localhost:8081/docs` → Swagger UI loads in browser
3. ETL logs show: `[init] Running first-time migration...` then `[init] RAG ingest complete` then `[cron] supercronic started`
4. `docker compose logs etl | grep migrated` → sentinel file created
5. POST `/api/chat` with `{"message": "what is the health of level 3?"}` → non-empty `reply`
6. Second `docker compose up` (restart) → ETL logs show `[init] Already initialised, skipping migration`

---

## Out of Scope

- Frontend containerisation
- InfluxDB containerisation
- Kubernetes / Helm (can be added later — compose is the foundation)
- CI/CD pipeline (image build and push)
- TLS termination / reverse proxy (nginx as ingress — future Spec D if needed)
