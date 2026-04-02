# WACH Insight — Production Readiness Design

**Date:** 2026-04-02  
**Author:** Jinendra Muraly  
**Status:** Approved  

---

## Overview

WACH Insight is a hospital AHU electrical analytics chatbot. It has grown from an in-premises experiment into a system with Docker deployment, DuckDB-backed ETL, a RAG knowledge base, persona detection, and prompt-injection hardening. This document defines a five-phase plan to bring the entire repository — code, tests, observability, and documentation — to industrial production standard.

**Approach:** Outside-in, phased delivery. Each phase is a standalone session with a clear deliverable. Work proceeds under CI guardrails established in Phase 1.

**Constraints:**
- Single developer, session-by-session
- Single-server deployment now; designed to scale horizontally later without major rework
- CI-gated: no merge without passing tests
- Layered docs for three audiences: end users, developers, and future-you

---

## Phase 1 — First Impressions & CI Scaffold

**Deliverable:** A professional-looking repo that gates merges from day one.

### README overhaul

Replace `README.md` with a structured document containing:
- One-paragraph "what is this" summary
- ASCII architecture diagram
- 5-minute quickstart (Docker path + local dev path)
- Configuration reference table
- Feature list
- Links to layered docs (user guide, developer guide, API reference)

The README is the front door — concise, not exhaustive.

### Remove debug artifacts

- Delete `backend/core/risk_engine.py.bak`, `.bak2`, `.bak3`
- Move one-off debug scripts (`tests/trace_*.py`, `tests/debug_*.py`, `tests/check_*.py`) to `scripts/debug/` with a note that these are not part of the test suite
- Remove `nohup.out` from git tracking; add to `.gitignore`
- Remove `frontend_backup_20260310.tar.gz` from the repo; add to `.gitignore`

### `.env.example`

Create `.env.example` at the repo root with every environment variable documented inline. This consolidates variables currently scattered across `DEPLOYMENT.md` and `README.md`.

### GitHub Actions CI (`.github/workflows/ci.yml`)

Trigger: push and PR to `main`.

Steps:
1. Checkout
2. Python 3.10 setup → `pip install -r backend/requirements-dev.txt`
3. `pytest backend/tests/ -x` (fail fast)
4. Node 18 setup → `npm ci` in `frontend/`
5. `npm run build`

Tests don't exist yet (Phase 2), but the scaffold gates merges immediately so Phase 2 tests are enforced from the moment they're written.

### `CONTRIBUTING.md`

One page covering:
- Local setup (Docker path + manual path)
- Branch naming convention
- PR checklist
- How to run tests

---

## Phase 2 — Test Suite

**Deliverable:** CI-gated tests covering every critical path. No regression goes undetected.

### Structure

```
backend/tests/
  unit/         — pure logic, no I/O, no network
  integration/  — real DuckDB, real ChromaDB, mocked InfluxDB/LLM
  e2e/          — full HTTP round-trip via FastAPI TestClient
```

### Unit tests

| File | What it covers |
|------|----------------|
| `unit/test_persona_detector.py` | All four personas, edge cases, explicit vs keyword detection |
| `unit/test_query_classifier.py` | `QueryType` routing logic |
| `unit/test_fair_health_scoring.py` | Scoring formula correctness (promote from existing one-off scripts) |
| `unit/test_prompts.py` | System prompt injection guard patterns |
| `unit/test_validator.py` | Structured query allowlist validation |

### Integration tests

| File | What it covers |
|------|----------------|
| `integration/test_rag_pipeline.py` | Ingest a known document, retrieve it, assert it appears in top-k results |
| `integration/test_chat_endpoint.py` | POST `/api/query` with valid session; assert structured JSON response shape |
| `integration/test_rate_limiter.py` | Exceed the rate limit; assert 429 response |

### E2E smoke test

`e2e/test_smoke.py` — health check, one preset prompt, one chat message; assert no 5xx responses.

### Frontend tests

`npm run test` via Vitest. One smoke test per major component: `ChatWindow`, `LevelSelectorBar`, `DashboardGate`.

### CI integration

- `pytest -x` (fail fast on first failure)
- Coverage report uploaded as CI artifact (no minimum threshold initially)
- Frontend: `npm run test -- --run` (non-interactive)

### Explicitly out of scope for Phase 2

Live InfluxDB queries, the Qwen LLM API, and the full Docker stack. These require network access and are better validated in Phase 3 observability work.

---

## Phase 3 — Observability & Reliability

**Deliverable:** When something goes wrong you find out immediately, know where to look, and the service recovers without manual intervention.

### Structured logging

Replace `logging.basicConfig` in `main.py` with a JSON-structured logger (`structlog` or `python-json-logger`). Every log line emits: `timestamp`, `level`, `module`, `request_id`, `session_id` (where available), `message`.

Centralised in `backend/core/logger.py`. All modules import from here — no more scattered `logging.getLogger` calls.

This makes logs ready for any aggregator (Loki, Datadog, CloudWatch) without future code changes.

### Request ID middleware

A lightweight middleware that stamps every incoming request with a `X-Request-ID` UUID (generated if absent from headers). The ID threads through all log lines for that request, enabling full request trace reconstruction from logs alone.

### `/metrics` endpoint

Expose a Prometheus-compatible `/metrics` endpoint via `prometheus-fastapi-instrumentator` (single import). Tracks: request count by route, latency histogram, error rate, active connections.

The `docker-compose.yml` gets a commented-out Prometheus + Grafana sidecar block that teams can opt into. Wired up and ready, not running by default.

### Crash recovery & graceful shutdown

- `SIGTERM` handler in `main.py` flushes the query log SQLite DB before shutdown
- FastAPI `lifespan` startup check verifies DuckDB and ChromaDB are readable on boot; logs a clear error (not a silent crash) if they aren't
- Docker `restart: unless-stopped` already in place

### Alerting hook

A single configurable `ALERT_WEBHOOK_URL` env variable. If set, a background task posts a JSON payload to that URL when the 5xx error rate exceeds 5% over a 60-second window. Compatible with Slack, Teams, or any webhook — no vendor lock-in.

### Rate limiter consolidation

The rate limiter is currently duplicated between `main.py` and `routes/query.py`. Move to `middleware/rate_limiter.py` as a proper `BaseHTTPMiddleware`. Remove both duplicates. This is code hygiene with a direct reliability impact.

---

## Phase 4 — Code Hygiene

**Deliverable:** Any competent engineer can read any file and understand what it does, why it exists, and how it fits — without asking.

### Module-level docstrings

Every Python file gets a concise module docstring (3–5 lines): what it does, what it exposes, what it depends on. Standardise the format across all files. No auto-generated docstrings; only where purpose isn't obvious from the code.

### Type hints

All public function signatures in `backend/` get type hints where missing. Private helpers are lower priority. Add `mypy --strict` to CI as a warning (not a blocker) initially, graduating to a blocker once the backlog is clear.

### Remove dead code

- Confirm `routes/update_level_endpoint.py` is registered and used; remove if not
- Clean up `sys.path.insert` path duplication in `main.py`
- Confirm all scripts moved to `scripts/debug/` in Phase 1 are not imported anywhere

### Consolidate configuration

All `os.getenv` calls move to `config.py` as a single `Settings` Pydantic model using `pydantic-settings`. No raw `os.getenv` outside that file. This keeps `.env.example` from Phase 1 automatically in sync.

### Frontend hygiene

- Audit `frontend/src` for debug `console.log` statements
- Add JSDoc comments to all Zustand store actions

### Linting & formatting gates

Add to CI:
- `ruff check backend/` (Python linter + formatter, check mode only)
- `prettier --check frontend/src/` (JS/TS formatter, check mode only)

Both fail the build in check mode but do not auto-commit. Keeps the codebase consistent without being prescriptive locally.

---

## Phase 5 — Layered Documentation

**Deliverable:** Three audiences each find exactly what they need without wading through content meant for someone else.

### User Guide (`docs/user-guide.md`)

Audience: hospital staff, ward managers, non-engineers.

Covers:
- What WACH Insight is (one paragraph)
- How to open the dashboard
- What the health scores mean
- How to use the chatbot (example questions for each persona: general, technical, technician, financial)
- Who to contact when something looks wrong

No code, no architecture. Plain language.

### Developer Guide (`docs/developer-guide.md`)

Audience: engineers contributing to or extending the system.

Covers:
- Local setup (Docker path + manual path)
- Project structure map (which directory does what)
- Chat pipeline end-to-end: query → persona detection → RAG retrieval → LLM → response
- How to add a new route
- How to extend the RAG knowledge base
- How to run tests
- Branch/PR workflow (references `CONTRIBUTING.md`)
- Links to specs in `docs/superpowers/specs/` for architectural decision context

### API Reference (`docs/api-reference.md`)

Audience: engineers integrating with or calling the API.

A human-readable companion to the Swagger UI. For every endpoint: method, path, auth requirement, request shape, response shape, example `curl`, and common error codes. Explains *why* each endpoint exists and when to use it. Supersedes and replaces the current `API.md`.

### Architecture diagrams (`docs/architecture/`)

Two diagrams committed as Mermaid source + rendered PNG:

1. **System overview** — Frontend → Backend → InfluxDB / DuckDB / ChromaDB / Qwen, with Docker boundaries shown
2. **Chat pipeline** — Request → rate limiter → injection check → persona detector → query classifier → RAG retrieval → LLM → validator → response

### Changelog (`CHANGELOG.md`)

Keep a Changelog format, starting from current state. Each phase of this work becomes an entry. Going forward, every PR with a user-visible change adds a line. Hand-written, one sentence per change.

### README as hub

The overhauled README from Phase 1 links to all five of the above by Phase 5. Nothing is orphaned.

---

## Sequencing Summary

| Phase | Deliverable | Key files touched |
|-------|-------------|-------------------|
| 1 | First impressions & CI scaffold | `README.md`, `.env.example`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`, artifact cleanup |
| 2 | Test suite | `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/e2e/`, `frontend/src/**/*.test.tsx` |
| 3 | Observability & reliability | `backend/core/logger.py`, `backend/middleware/rate_limiter.py`, `backend/main.py`, `docker-compose.yml` |
| 4 | Code hygiene | `backend/config.py`, all `backend/**/*.py` (type hints + docstrings), `ruff`/`prettier` CI gates |
| 5 | Layered documentation | `docs/user-guide.md`, `docs/developer-guide.md`, `docs/api-reference.md`, `docs/architecture/`, `CHANGELOG.md` |

## Design Principles

- **YAGNI:** No features or abstractions beyond what each phase requires. Scalability is designed in (Prometheus endpoint, stateless rate limiter) but not activated until needed.
- **Session-by-session:** Each phase is independently shippable. Phase N does not require Phase N+1 to be useful.
- **CI as the backbone:** The scaffold from Phase 1 enforces every improvement made in Phases 2–4.
- **No vendor lock-in:** Alerting webhook, log format, and metrics endpoint are all generic interfaces.
