# RDMI-003 — WACH Source Portability Audit

**Date:** 2026-05-28
**Ticket:** RDMI-003
**Source:** `wach-insight/backend/`
**Target:** `apps/api/sites/wach/` in RDM Insight monorepo
**Unblocks:** Plan B T1–T7 (WACH adapter port)

## Legend

- **LIFT** — copy verbatim into `sites/wach/`. Self-contained or only touches WACH-specific structure.
- **SEAM** — needs an interface seam before lift. Logic stays WACH; the boundary moves up to the adapter Protocol or to `core/`.
- **CORE** — promote to `apps/api/core/` (shared across all sites). Generic, not WACH-specific.
- **LEAVE** — do not port. Either dead, replaced by RDM Insight equivalent, or out of scope for parity.

`Pts` = rough port effort in story points (1 = trivial copy, 5 = significant rework).

---

## core/ (15 files, 7233 lines)

| File | LOC | Verdict | Target | Pts | Notes |
|------|-----|---------|--------|-----|-------|
| `fair_health_scoring.py` | 1149 | **LIFT** | `sites/wach/scoring.py` | 1 | The scoring engine. Self-contained pure math. RDMI-004 documents the formula; this file is the implementation. Imports only numpy/pandas. |
| `risk_engine.py` | 1822 | **LIFT** | `sites/wach/risk.py` | 2 | Rule-based electrical risk. Pure logic. Imports `score_normalize`, `fair_health_scoring`, schemas. WACH-specific thresholds (PF, THD, imbalance) are domain truth — keep as-is. |
| `score_normalize.py` | 48 | **CORE** | `core/scoring/normalize.py` | 1 | Canonical 0–100 high=good representation. Generic, not WACH. All sites need this. |
| `prediction_engine.py` | 542 | **LIFT** | `sites/wach/prediction.py` | 2 | Math-only forecasting. Tied to FAIR scores, so lifts with `fair_health_scoring`. |
| `influx_client.py` | 710 | **SEAM** | `sites/wach/ingest/influx_writer.py` | 3 | Plan A addendum reshapes this: live queries move to DuckDB; this file becomes the **ETL writer** that pulls from Influx Cloud and writes to DuckDB via `IngestRunner` Protocol (Plan A A.26). Currently doubles as query path — split during port. |
| `healthdb.py` | 496 | **SEAM** | `sites/wach/duckdb_client.py` + `core/duckdb/` | 3 | DuckDB wrapper for health scores. The connection layer is generic (→ `core/duckdb/`); the schema and queries are WACH-specific (→ `sites/wach/`). Split. |
| `db_reader.py` | 584 | **LIFT** | `sites/wach/queries.py` | 2 | DuckDB query layer for health-index, breakdown, raw-score relationship. WACH schema-aware. Adapter methods (`WachAdapter.get_trend`, `get_ranking`) call into this. |
| `agentdb.py` | 585 | **LEAVE (MVP)** | — | — | Agent state DB (work orders, watchman queue, agent memory). Multi-agent V3 chat feature. RDM Insight MVP chat is simpler (single Qwen call + RAG). Defer to Phase 2. Mark in spec. |
| `watchman.py` | 146 | **LEAVE (MVP)** | — | — | Background pulse for proactive alerts. Depends on `agentdb`. Same deferral. |
| `alerter.py` | 89 | **CORE** | `core/observability/alerter.py` | 1 | Sliding-window 5xx tracker → webhook. Generic infra, useful for both tenants. |
| `logger.py` | 59 | **CORE** | `core/logging.py` | 1 | JSON structured logger + ContextVar request_id. Generic. Already part of Plan A T4 scaffolding — confirm parity. |
| `charts.py` | 179 | **LEAVE** | — | — | Recharts payload shaper for legacy `/api/query`. Plan B/C uses visx + adapter DTOs; the API contract changes. Drop. |
| `summarizer.py` | 458 | **SEAM** | `sites/wach/summarizer.py` | 2 | Result-summary LLM caller. Couples query result shape + LLM prompts. Lift but rewire to `core/llm/` client. |
| `query_classifier.py` | 75 | **LIFT** | `sites/wach/query_classifier.py` | 1 | Heuristic /think vs /no_think router. Pure regex. Trivial. |
| `floor_ward_map.py` | 278 | **LIFT** | `sites/wach/wards.py` | 1 | Hardcoded floor → device-id map and ward labels. Pure WACH domain data. |

**core/ port total: ~22 pts** (excluding LEAVE items).

---

## models/ (3 files, 847 lines)

| File | LOC | Verdict | Target | Pts | Notes |
|------|-----|---------|--------|-----|-------|
| `schemas.py` | 721 | **SEAM** | split: `sites/wach/schemas.py` + `core/dto/` | 3 | Mixed bag. `StructuredQuery`, `ChatHistoryItem`, `QueryType`, `ALLOWED_METRICS`, `AHU_LEVEL_CONFIG` all live here. AHU-specific constants → `sites/wach/`. Chat/query DTOs → `core/dto/` so other sites reuse. Plan B T1 references `AHU_LEVEL_CONFIG` + `e\d{4}` regex — those are WACH. |
| `feature_schema.py` | 74 | **LIFT** | `sites/wach/feature_schema.py` | 1 | ML feature row for AHU. WACH-specific column set. |
| `cmms_event.py` | 52 | **LEAVE (MVP)** | — | — | CMMS event value-object for work-orders feature. Tied to `agentdb` deferral. Phase 2. |

---

## llm/ (6 files, 1319 lines)

| File | LOC | Verdict | Target | Pts | Notes |
|------|-----|---------|--------|-----|-------|
| `qwen_client.py` | 237 | **CORE** | `core/llm/qwen.py` | 2 | OpenAI-compatible client for LM Studio. Generic. Plan B T5 wants it async (current uses `asyncio.to_thread` over sync OpenAI SDK — fine, but verify cancellation). |
| `circuit_breaker.py` | 81 | **CORE** | `core/llm/circuit_breaker.py` | 1 | In-memory CLOSED/OPEN/HALF_OPEN. Reusable. |
| `client_factory.py` | 12 | **CORE** | `core/llm/factory.py` | 1 | One-liner factory. Will grow when we add provider switching. |
| `prompts.py` | 608 | **LIFT** | `sites/wach/prompts.py` | 2 | System prompts with **hardcoded AHU layout**. WACH-specific. Each site needs its own `prompts.py`. |
| `translator.py` | 267 | **SEAM** | `sites/wach/translator.py` (calls `core/llm/`) | 2 | NL → StructuredQuery via LLM. Pipeline is generic but allowlists are WACH. |
| `persona_detector.py` | 114 | **LIFT** | `sites/wach/persona.py` | 1 | Regex-based persona classifier (general/technical/technician/financial). WACH wards are healthcare; Cyberview personas will differ. Lift per-site, generalize later. |

---

## rag/ (5 files, 249 lines)

| File | LOC | Verdict | Target | Pts | Notes |
|------|-----|---------|--------|-----|-------|
| `vector_store.py` | 56 | **CORE** | `core/rag/vector_store.py` | 1 | ChromaDB wrapper. Collection name passed in → already supports per-site scoping. Plan B T4 (`wach_knowledge` collection) just instantiates with site-scoped name. |
| `embedder.py` | 20 | **CORE** | `core/rag/embedder.py` | 1 | Thin wrapper over QwenEmbedder. Generic. |
| `qwen_embedder.py` | 50 | **CORE** | `core/rag/qwen_embedder.py` | 1 | Local Qwen3-Embedding-0.6B. Generic. |
| `retriever.py` | 23 | **CORE** | `core/rag/retriever.py` | 1 | Combines embedder + store. Generic. |
| `ingest.py` | 100 | **CORE** | `core/rag/ingest.py` | 2 | PDF/TXT chunking CLI. Generic. Plan C T4 (knowledge upload background job) wraps this. |

**rag/ ports cleanly to `core/rag/` — Chroma collection name is the only site-scoping needed.**

---

## routes/ (11 files, 2734 lines)

> **All routes get reshaped, not lifted.** RDM Insight routes are tenant-aware (`X-Site-Id` header → adapter dispatch → DTO response). The WACH routes are direct InfluxDB/DuckDB callers. Lift the **business logic** out of route handlers into adapter methods.

| File | LOC | Verdict | Target | Pts | Notes |
|------|-----|---------|--------|-----|-------|
| `dashboard.py` | 854 | **SEAM** | logic → `WachAdapter.get_trend/get_ranking`, route stays generic | 4 | The N+1 fix lives here. Current code loops over devices doing per-device queries. Plan B T3 mandates `query_all_device_scores(level)` single-query. Surgery, not lift. |
| `chat.py` | 192 | **SEAM** | logic → `WachAdapter.chat()`, route stays generic | 3 | V3 multi-agent chat. Plan B reduces to V1 (single Qwen + RAG); the V3 agent-router complexity ships in Phase 2 with `agentdb`. |
| `health_scores.py` | 196 | **SEAM** | `WachAdapter.get_health_scores` | 2 | UI Revamp endpoints. Maps to adapter DTOs. |
| `query.py` | 300 | **LEAVE (MVP)** | — | — | Legacy `/api/query` POST with NL translation + chart payload. Spec §4 routes are dashboard + chat only. Drop for MVP. |
| `predictions.py` | 40 | **SEAM** | `WachAdapter.get_predictions` | 1 | Thin wrapper over `prediction_engine`. |
| `delta_forecast.py` | 81 | **SEAM** | `WachAdapter.get_delta_forecast` | 1 | Same as predictions. |
| `forecast.py` | 391 | **SEAM** | `WachAdapter.get_forecast` | 3 | XGBoost 24h forecast. Tied to pre-trained models for 3 devices. Lift logic + ship model artifacts under `sites/wach/models/`. |
| `measurements.py` | 77 | **SEAM** | `WachAdapter.get_measurements` | 1 | Raw metric time-series. Wraps `fetch_time_series`. |
| `financial_impact.py` | 181 | **SEAM** | `WachAdapter.get_financial_impact` | 2 | Cost breakdown computed from DuckDB. |
| `on_off_periods.py` | 30 | **SEAM** | `WachAdapter.get_on_off_periods` | 1 | Thin DB query. |
| `site_summary.py` | 270 | **SEAM** | `WachAdapter.get_summary` | 2 | Summary payload. |
| `work_orders.py` | 222 | **LEAVE (MVP)** | — | — | Work-order CRUD, depends on `agentdb`. Phase 2. |

**routes/ port total: ~20 pts** of seam work (no verbatim lifts).

---

## Cross-cutting Findings

### 1. The async cascade (Plan A critical fix)

WACH routes are mostly sync; they wrap blocking I/O in `asyncio.to_thread` or call `compute_predictions_async`. The port to RDM Insight requires every adapter method to be `async def` (Plan A T16 + Plan B T6).

- **Influx queries** — `influxdb_client.InfluxDBClient` is sync. Either keep `to_thread` wrap (acceptable) or move to `influxdb-client-python` async variant. Decide before Plan B T3.
- **DuckDB queries** — `duckdb` is sync. Wrap in `to_thread`. Lightweight queries hit the GIL briefly; acceptable for MVP.
- **OpenAI SDK** — Plan B T5 reshapes to `httpx.AsyncClient` to LM Studio directly. Drop the OpenAI SDK dependency. Cleaner cancellation semantics.

### 2. N+1 dashboard (Plan B critical fix)

`routes/dashboard.py` ranking endpoint currently:
```python
for device in devices_at_level:
    fetch_time_series(device, ...)   # one Influx call per device
```
At Level 1 (21 devices) → 21 round-trips. Plan B T3 must implement `query_all_device_scores(level)` as a single Flux query with `filter(fn: (r) => contains(value: r.device, set: [...]))`.

### 3. The scoring formula source of truth

`fair_health_scoring.py:1149 lines` is the algorithm. The aggregate health-index call surface lives at `calculate_health_index()` (referenced by `prediction_engine`). RDMI-004 produces the formula extraction note that Plan B T2 turns into the WACH scoring module + CI guard.

### 4. Imports outside the audit scope

WACH source imports from `agents/` (chat V3), `config`, `middleware/`. These are out of scope here but flagged:
- `agents/router.py`, `agents/` package — V3 multi-agent. Defer to Phase 2 with `agentdb` / `watchman`.
- `config.py` — settings shim. RDM Insight has its own `core/config.py` (Plan A T4). Map field-by-field during port.
- `middleware/` — request-id, CORS, etc. RDM Insight has these (Plan A T15 tenant middleware extends).

### 5. ETL boundary moves up

Per Plan A addendum (A.26/A.27/A.28), ingest is a generic framework. `influx_client.py` no longer serves dashboard reads — it becomes a `IngestRunner` implementation that writes to DuckDB on a cron. The dashboard reads DuckDB only. This is a structural change captured in the SEAM verdict above.

---

## Port Sequence (matches Plan B sprints)

Plan B Sprint 4 (Jun 22–26) port order, in dependency order:

1. **Scaffolding:** `sites/wach/__init__.py`, register `WachAdapter` skeleton (Plan A T17 already set up `_default`).
2. **CORE promotions first** — `score_normalize`, `logger`, LLM clients, RAG modules. These have no WACH-specific dependencies and become shared infra. (~8 pts)
3. **WACH constants** — `AHU_LEVEL_CONFIG`, `e\d{4}` regex, `floor_ward_map`, allowlists. (Plan B T1) (~1 pt)
4. **Scoring + risk** — `fair_health_scoring`, `risk_engine`, `score_normalize` integration. Driven by RDMI-004 note. (Plan B T2) (~3 pts after RDMI-004)
5. **DuckDB layer split** — `healthdb` (split: core conn + wach schema), `db_reader`. (~3 pts)
6. **Influx wrapper** — `influx_client` reshaped as `IngestRunner` (A.26 protocol). N+1 fix. (Plan B T3) (~3 pts)
7. **RAG + LLM site bindings** — `prompts.py`, `translator.py`, `persona_detector.py` lifted. (Plan B T4/T5) (~3 pts)
8. **Adapter implementation** — `WachAdapter` methods wired to the above. (Plan B T6) (~2 pts)
9. **Dashboard route + integration test** — Plan B T7. (~2 pts)

Sprint 4 total: ~25 pts. Matches the 5-day plan.

---

## Out-of-Scope For MVP (Phase 2 backlog)

| Module/Feature | Files | Reason |
|---|---|---|
| Multi-agent chat V3 | `agentdb.py`, `watchman.py`, `routes/chat.py` (V3 parts), `routes/work_orders.py`, `models/cmms_event.py`, `agents/` package | RDM Insight MVP chat = single Qwen call + RAG (spec §4). V3 router + HITL drafts ship in Phase 2. |
| Legacy `/api/query` | `routes/query.py`, `core/charts.py` | API contract changes; adapter DTOs replace chart payloads. |
| XGBoost forecast | `routes/forecast.py` + model artifacts | Optional for MVP. Demo target is dashboard + chat. Lift in Phase 2 if Raj wants. |

---

## Verification

- [x] All 44 files under `backend/{core,rag,llm,models,routes}` accounted for.
- [x] Each file has LIFT / SEAM / CORE / LEAVE verdict + target path.
- [x] Critical fixes (async cascade, N+1, scoring source) cross-referenced to plan tasks.
- [x] Port sequence aligns with Plan B Sprint 4 tasks.
- [x] Out-of-scope items flagged with reason + Phase 2 home.

## Next

- RDMI-004 — extract scoring formula from `fair_health_scoring.py`. This audit pinpoints the entry function (`calculate_health_index`) and the file (1149 LOC). RDMI-004 produces the natural-language spec of inputs/weights/edges.
- RDMI-005 — Cyberview MQTT ADR (separate ticket, this audit doesn't touch Cyberview).
