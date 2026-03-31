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

A single line:
```
${ETL_SCHEDULE} python -m scripts.etl.run_health_etl
```

`ETL_SCHEDULE` defaults to `0 * * * *` (hourly). Colleagues can change it in `.env` — e.g. `ETL_SCHEDULE=*/30 * * * *` for every 30 minutes.

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

Full `.env.example`:

```bash
# ── Identity ─────────────────────────────────────────────────────────────────
# Used in chatbot system prompt and logs. Change per hospital deployment.
WACH_BUILDING_NAME=Hospital Kuala Lumpur
WACH_DEPARTMENT=Engineering
HOSPITAL_ID=hkl

# ── InfluxDB ──────────────────────────────────────────────────────────────────
# Required. Point at the hospital's InfluxDB instance.
INFLUX_URL=http://192.168.1.10:8086
INFLUX_TOKEN=your-influxdb-token-here
INFLUX_ORG=wach
INFLUX_BUCKET=wach_bucket_3
# Set to true if InfluxDB runs plain HTTP on a non-localhost address
INFLUX_SKIP_TLS=false

# ── LLM ──────────────────────────────────────────────────────────────────────
# Point at LM Studio on host (Mac/Windows) or a shared GPU server.
# For Docker Desktop on Mac/Windows: host.docker.internal works out of the box.
# For Linux hosts: use the host's actual IP (e.g. http://172.17.0.1:1234/v1).
LMS_BASE_URL=http://host.docker.internal:1234/v1
LMS_MODEL=qwen/qwen3-coder-next
LMS_API_KEY=lm-studio

# ── Security ──────────────────────────────────────────────────────────────────
# Required. Generate with: openssl rand -base64 32
API_KEY=change-this-to-a-long-random-string

# Allowed frontend origins (comma-separated). Add your frontend URL here.
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ── ETL Schedule ──────────────────────────────────────────────────────────────
# Cron syntax. Default: every hour on the hour.
ETL_SCHEDULE=0 * * * *

# ── Backend Port ─────────────────────────────────────────────────────────────
# Default: 8081. Change if port is taken.
BACKEND_PORT=8081

# ── Optional ─────────────────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
DEBUG=false
```

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

Each hospital deployment is an independent `docker compose up` with its own `.env`. No shared state between deployments.

```
Hospital A (HKL)          Hospital B (PPUM)
─────────────────         ─────────────────
.env:                     .env:
  HOSPITAL_ID=hkl           HOSPITAL_ID=ppum
  INFLUX_BUCKET=wach_hkl    INFLUX_BUCKET=wach_ppum
  WACH_BUILDING_NAME=HKL    WACH_BUILDING_NAME=PPUM
  BACKEND_PORT=8081          BACKEND_PORT=8082

docker compose up         docker compose up
→ API at :8081            → API at :8082
→ own DuckDB volume       → own DuckDB volume
→ own ChromaDB volume     → own ChromaDB volume
```

Each instance has isolated data volumes. Both can run on the same VM by changing `BACKEND_PORT`.

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
