# WACH Insight — Developer Guide

This guide covers local setup, project structure, how the main flows work, and the contribution workflow. It assumes Python 3.10+ and Node 18+ are already installed.

---

## Quick Start

### Docker path (recommended)

```bash
cp .env.example .env        # fill in InfluxDB URL, API key, LLM URL
docker-compose up --build
```

Frontend: `http://localhost:3000`
Backend API: `http://localhost:8081`
Swagger UI: `http://localhost:8081/docs`

### Manual path

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in values
uvicorn main:app --port 8081 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                  # starts Vite dev server on :3000
```

The Vite dev server proxies all `/api/*` requests to `localhost:8081`, so the frontend works against the local backend automatically.

---

## Project Structure

```
wach-insight/
├── backend/
│   ├── main.py               # FastAPI app, router registration, middleware setup
│   ├── routes/               # One file per API area (chat, dashboard, health_scores, …)
│   ├── core/                 # Business logic: persona_detector, query_classifier, risk_engine, …
│   ├── ai/                   # LLM client (qwen_client.py) and tool implementations
│   ├── tools/                # Individual tool modules callable during LLM generation
│   ├── middleware/            # Auth and rate limiting middleware
│   ├── config/               # Settings and AHU level configuration
│   └── tests/                # Unit, integration, and e2e tests (Phase 2 of prod-readiness)
├── frontend/
│   ├── src/
│   │   ├── store/            # Zustand global state (useAppStore.ts)
│   │   ├── components/       # React components (ChatWindow, Dashboard, LevelSelectorBar, …)
│   │   ├── mocks/            # Mock data generators (used when backend is unavailable)
│   │   └── main.tsx          # Vite entry point
│   └── vite.config.ts        # Proxy config (/api → :8081)
├── docs/
│   ├── user-guide.md
│   ├── developer-guide.md    # (this file)
│   ├── api-reference.md
│   ├── architecture/         # System overview and chat pipeline diagrams
│   └── superpowers/specs/    # Architecture decision records and production readiness spec
├── scripts/
│   ├── run_history.sh        # Local dev helper
│   └── infra/                # launchd plist and startup scripts
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── CHANGELOG.md
```

---

## Chat Pipeline (End-to-End)

A request to `POST /api/chat` travels through these layers:

1. **APIKeyAuthMiddleware** (`backend/middleware/`) — validates the Bearer token, returns 401 if absent or wrong.
2. **Global rate limiter** (`backend/main.py`) — 100 requests per 60 seconds per IP.
3. **`routes/chat.py`** — FastAPI route handler. Reads the request body, calls into the AI layer.
4. **Persona Detector** (`backend/core/persona_detector.py`) — classifies the message as `general | technical | technician | financial` based on keywords and history. The selected persona controls the system prompt.
5. **Query Complexity Classifier** (`backend/core/query_classifier.py`) — decides whether to prepend `/think` or `/no_think` to the message before sending to Qwen (controls the LLM's internal reasoning chain).
6. **QwenClient** (`backend/ai/qwen_client.py`) — sends the message to the Qwen LLM with tool definitions. Qwen may call tools zero or more times before producing a final reply.
7. **Tools** (`backend/tools/`) — each tool is a Python callable. The LLM invokes them to fetch data: HealthDB (DuckDB FAIR scores), InfluxDB (raw measurements), RAG (ChromaDB knowledge base), financial, site_summary.
8. **Response** — the final LLM reply is returned as `{"reply": "...", "navigate": null, "thinking_mode": "..."}`.

See `docs/architecture/chat-pipeline.md` for a visual diagram.

---

## Adding a New API Route

1. Create `backend/routes/my_feature.py`:

```python
from fastapi import APIRouter, Depends
from backend.middleware.auth import verify_api_key

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(api_key: str = Depends(verify_api_key)):
    return {"result": "..."}
```

2. Register the router in `backend/main.py`:

```python
from routes import my_feature
app.include_router(my_feature.router, prefix="/api")
```

3. Add the endpoint to `docs/api-reference.md` following the existing format.

---

## Extending the RAG Knowledge Base

The RAG knowledge base lives in ChromaDB (embedded). To add new documents:

1. Place the document (PDF, text, or markdown) in the ingestion source directory.
2. Run the ingestion script:

```bash
cd backend
python scripts/ingest_rag.py --source path/to/document.pdf
```

(Adjust path to the actual ingestion script if it has been moved — check `scripts/` and `backend/core/` for `ingest` or `rag_loader` files.)

3. Restart the backend — ChromaDB embeddings are loaded at startup.

---

## Running Tests

```bash
# Python tests (from repo root)
pytest backend/tests/ -x -v

# Frontend tests
cd frontend
npm run test -- --run
```

Tests are structured as:
- `backend/tests/unit/` — pure logic, no I/O
- `backend/tests/integration/` — real DuckDB, mocked InfluxDB/LLM
- `backend/tests/e2e/` — full HTTP round-trip via FastAPI TestClient

---

## Branch and PR Workflow

In short:

- Branch naming: `feature/short-description`, `fix/short-description`, `docs/short-description`
- All PRs target `main`
- CI must pass before merge (GitHub Actions: `pytest -x` + `npm run build`)
- Add a line to `CHANGELOG.md` under `[Unreleased]` for any user-visible change

---

## Environment Variables

All configuration is in `.env.example`. Key variables:

| Variable | Purpose |
|----------|---------|
| `API_KEY` | Bearer token for all authenticated endpoints |
| `INFLUX_URL` | InfluxDB v2 base URL |
| `INFLUX_TOKEN` | InfluxDB read token |
| `INFLUX_ORG` | InfluxDB organisation |
| `INFLUX_BUCKET` | InfluxDB bucket name |
| `LLM_BASE_URL` | Qwen inference server base URL |
| `LLM_API_KEY` | Qwen API key (if required by your host) |
| `CHROMA_PERSIST_DIR` | ChromaDB persistence directory |
| `DUCKDB_PATH` | Path to the DuckDB file |

---

## Architecture Decision Records

Detailed specs for past and in-progress architectural decisions live in:

```
docs/superpowers/specs/
```

Key documents:
- `2026-04-02-production-readiness-design.md` — the five-phase production readiness plan this guide is part of
