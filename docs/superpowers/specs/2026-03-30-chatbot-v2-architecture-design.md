# Chatbot V2 Architecture — Design Spec
**Date:** 2026-03-30
**Status:** Approved
**Scope:** Spec A of three — covers Health DB, Agentic Tool-Use, Thinking Toggle

---

## Overview

Three interconnected improvements that replace the chatbot's current context-stuffing architecture with a tool-augmented, query-adaptive system backed by a purpose-built time-series database.

**What changes at a high level:**
- CSV files are retired as the chatbot's data source. A DuckDB database (`data/healthdb.duckdb`) becomes the single source of truth for all FAIR-scored health data.
- The chatbot stops pre-loading 8+ context blocks on every request. Instead, Qwen3 calls structured tools to fetch exactly what it needs.
- A heuristic classifier prepends `/think` or `/no_think` to every user message, giving complex queries deep reasoning and simple queries fast answers — using Qwen3's native capability, no extra model required.

---

## Component 1: Health DB (DuckDB)

### Why DuckDB
Embedded (no server), analytical queries on millions of rows in milliseconds, single file (`data/healthdb.duckdb`), zero setup for Docker deployments. Multiple concurrent readers, one writer — ETL and API can run simultaneously without locking.

### Schema

```sql
CREATE TABLE IF NOT EXISTS health_hourly (
    timestamp              TIMESTAMPTZ NOT NULL,
    device_id              VARCHAR     NOT NULL,
    level                  INTEGER     NOT NULL,
    health_index           FLOAT,
    tier                   VARCHAR,
    -- FAIR component scores
    energy_anomaly         FLOAT,
    pf_degradation         FLOAT,
    phase_imbalance        FLOAT,
    thd_drift              FLOAT,
    overload               FLOAT,
    -- Raw sensor metrics
    raw_power_total        FLOAT,
    raw_energy_import      FLOAT,
    raw_hourly_delta       FLOAT,
    raw_predicted_delta    FLOAT,
    raw_power_factor_avg   FLOAT,
    raw_current_unbalance  FLOAT,
    raw_composite_thd      FLOAT,
    raw_current_l1         FLOAT,
    raw_current_l2         FLOAT,
    raw_current_l3         FLOAT,
    raw_volts_l1_n         FLOAT,
    raw_volts_l2_n         FLOAT,
    raw_volts_l3_n         FLOAT,
    -- Safety flags
    flag_thd_chronic       BOOLEAN DEFAULT FALSE,
    flag_imbalance_severe  BOOLEAN DEFAULT FALSE,
    flag_pf_chronic        BOOLEAN DEFAULT FALSE,
    flag_overload_chronic  BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (timestamp, device_id)
);

CREATE INDEX IF NOT EXISTS idx_device_time ON health_hourly (device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_level_time  ON health_hourly (level, timestamp);
```

Column set mirrors the current `health_hourly.csv` exactly to simplify migration.

### New file: `backend/core/healthdb.py`

Singleton DuckDB connection with the following public interface:

```python
def get_latest_snapshot(device_ids: list[str] | None, level: int | None) -> pd.DataFrame
def get_time_range(device_ids, level, start, end, metrics) -> pd.DataFrame
def get_ranking(level, metric, n, order) -> pd.DataFrame
def get_latest_timestamp() -> datetime | None
def upsert(df: pd.DataFrame) -> int   # returns rows written
```

- API process opens connection in **read-only** mode (`duckdb.connect(path, read_only=True)`).
- ETL process opens connection in **read-write** mode.
- Both are safe to run concurrently.

### ETL changes: `scripts/etl/run_health_etl.py`

Add `save_health_duckdb(results_df)` immediately after the existing `save_health_csv()` call. Both run during the transition period. Once the chatbot is confirmed stable on DuckDB, CSV writes are disabled via a `--no-csv` flag.

`save_health_duckdb()` uses DuckDB's `INSERT OR REPLACE` semantics for idempotent upserts — safe to re-run after failures.

### Migration script: `scripts/etl/migrate_csv_to_duckdb.py`

One-time script run manually after deployment:

```bash
python scripts/etl/migrate_csv_to_duckdb.py
```

- Streams `data/health_hourly.csv` into DuckDB in 10,000-row batches.
- Idempotent (upsert on primary key) — safe to re-run.
- Prints: rows imported, date range covered, device count.
- Runtime estimate: ~5–10 seconds for the current 156MB CSV.

After migration, `health_hourly.csv` is retained as a read-only export artifact but is no longer read by the chatbot or any backend route.

---

## Component 2: Agentic Tool-Use

### Architecture change

**Before (context-stuffing):**
Every request pre-loads 8+ context blocks (CSV reads, InfluxDB calls, financial calculations, RAG) and dumps them into a single giant system prompt regardless of what the user actually asked.

**After (tool-augmented generation):**
Qwen3 receives a lean system prompt and tool definitions. It calls tools on demand, pulling exactly the data the query requires. Tool results are fed back; the model continues until it has enough context to answer.

### New file: `backend/tools/tool_registry.py`

Defines five tools in OpenAI function-calling schema and a `dispatch_tool(name, args)` dispatcher.

**Tool: `query_health_scores`**
- Description: Query FAIR health scores and component scores for AHUs over a time range. Use for trends, breakdowns, flag history, device comparisons.
- Parameters: `device_ids` (list|null), `level` (int|null), `start` (ISO str|null), `end` (ISO str|null), `metrics` (list|null)
- Backed by: `healthdb.get_time_range()` or `healthdb.get_latest_snapshot()`

**Tool: `query_live_readings`**
- Description: Latest sensor readings from InfluxDB — power, power factor, THD, voltage, current. Use for "right now" or "current status" questions.
- Parameters: `device_ids` (list|null), `level` (int|null)
- Backed by: existing `fetch_latest_hourly_data()` in `influx_client.py`

**Tool: `query_ranking`**
- Description: Rank AHUs within a level by a health metric. Use for "worst", "best", "top N", "which devices need attention".
- Parameters: `level` (int), `metric` (str), `n` (int, default 5), `order` ("asc"|"desc")
- Backed by: `healthdb.get_ranking()`

**Tool: `query_financial_impact`**
- Description: Financial impact analysis — excess energy cost, PF penalty, maintenance risk, top cost-contributing AHUs.
- Parameters: `level` (int), `time_range` ("24h"|"7d"|"30d")
- Backed by: existing `_compute_impact()` in `financial_impact.py`

**Tool: `search_docs`**
- Description: Search technical documentation about AHU components, electrical health, FAIR scoring, maintenance guidance. Use for "why", "what causes", "how does X work".
- Parameters: `query` (str), `k` (int, default 3, max 8)
- Backed by: existing `retriever.retrieve()` in `rag/retriever.py`

### New file: `backend/tools/health_tools.py`

Handler implementations. Each is a thin wrapper:

| Tool | Calls |
|------|-------|
| `query_health_scores` | `healthdb.get_time_range()` / `healthdb.get_latest_snapshot()` |
| `query_live_readings` | `influx_client.fetch_latest_hourly_data()` |
| `query_ranking` | `healthdb.get_ranking()` |
| `query_financial_impact` | `financial_impact._compute_impact()` |
| `search_docs` | `rag.retriever.retrieve()` |

Handlers return plain Python dicts. No markdown formatting at this layer — Qwen3 formats the final response.

### `backend/llm/qwen_client.py` extension

New method:

```python
async def generate_with_tools(
    system_prompt: str,
    messages: list,
    tools: list,
    tool_dispatcher: callable,
    max_tool_rounds: int = 5
) -> str
```

Loop:
1. Send messages + tool definitions to Qwen3 via OpenAI function-calling API.
2. If response contains `tool_calls` → execute each via `tool_dispatcher` → append tool results as `role: tool` messages.
3. Repeat until no `tool_calls` or `max_tool_rounds` reached.
4. Strip `<think>...</think>` blocks from final text response.
5. Return clean response string.

`max_tool_rounds = 5` prevents runaway loops. Typical queries: 1–2 rounds. Complex multi-device analyses: 3–4 rounds.

### `backend/routes/chat.py` changes

**Removed (~600 lines):**
- `_get_live_context()`
- `_read_csv_context_sync()`
- `_get_time_window_context()`
- `_get_time_series_context()`
- `_get_ranking_context()`
- `_get_financial_context()`
- `_get_prediction_context_sync()`
- All query-type detection logic (time-series detection, ranking detection, comparison detection, navigation target detection, cross-level detection)

**Replaces with (~80 lines):**

```python
complexity = classify_query_complexity(message, history)
prefix = "/think " if complexity == "think" else "/no_think "

response = await qwen_client.generate_with_tools(
    system_prompt=build_system_prompt(),
    messages=history + [{"role": "user", "content": prefix + message}],
    tools=TOOLS,
    tool_dispatcher=dispatch_tool
)
```

### System prompt changes

Current: ~1,500 words including pre-loaded data, health scores, device lists.
New: ~400 words covering:
- Building identity (configurable via env: `WACH_BUILDING_NAME`, `WACH_DEPARTMENT`)
- FAIR scoring definitions and tier thresholds (model needs domain understanding)
- Device ID format rules (`e[LEVEL][NN]`, valid range e0101–e1108)
- Response style rules (no emojis, cite tool data only, markdown formatting)
- Instruction to use tools rather than guess or fabricate data

---

## Component 3: Thinking Toggle

### New file: `backend/core/query_classifier.py`

```python
def classify_query_complexity(
    message: str,
    history: list[dict]
) -> Literal["think", "fast"]:
    """
    Heuristic classifier. Returns "think" or "fast". ~1ms, no external calls.
    """
```

**Fast signals (evaluated first):**
- Message length < 60 chars and no think keywords → `fast`
- Matches fast regex patterns:
  - `^what (is|are) the (health|status|score)` — simple status lookups
  - `^(show|list|give) me .{0,40}$` — short list requests
  - `^is e\d{4}` — single device status check
  - `^how many` — count queries

**Think signals:**
- Keywords present: `why`, `cause`, `reason`, `explain`, `analyse`, `analyze`, `compare`, `versus`, `vs`, `trend`, `over time`, `pattern`, `recommend`, `should i`, `what should`, `root cause`, `diagnose`, `investigate`, `worsen`, `deteriorat`, `forecast`, `predict`, `next week`, `next month`
- 3+ device IDs mentioned (`e\d{4}` pattern)
- 2+ level references (`level N`)
- Conversation history ≥ 6 turns AND message > 80 chars (mid-conversation deep dive)

**Default:** `fast` (when no think signals detected and not clearly fast)

### Integration in `chat.py`

```python
complexity = classify_query_complexity(message, history)
prefix = "/think " if complexity == "think" else "/no_think "
user_content = prefix + message
```

The prefix is applied to the outgoing message only — not stored in the conversation history object, so it does not accumulate or leak across turns.

### API response

```json
{
  "reply": "...",
  "nav_target": null,
  "thinking_mode": "think"
}
```

The `thinking_mode` field is added to the existing response schema. The frontend can use this to show a subtle indicator on responses that used deep reasoning.

### Tuning path

`query_logger.py` already logs all queries to SQLite. `thinking_mode` is added to that log. After one week of real use, the log provides a corpus to review classifier accuracy and refine heuristics. No retraining required — heuristic adjustments are a few lines of code.

---

## File Inventory

### New files
| File | Purpose |
|------|---------|
| `backend/core/healthdb.py` | DuckDB connection, schema init, query interface |
| `backend/core/query_classifier.py` | Think/fast heuristic classifier |
| `backend/tools/__init__.py` | Package marker |
| `backend/tools/tool_registry.py` | Tool definitions (OpenAI schema) + dispatcher |
| `backend/tools/health_tools.py` | Tool handler implementations |
| `scripts/etl/migrate_csv_to_duckdb.py` | One-time CSV → DuckDB migration |

### Modified files
| File | Change |
|------|--------|
| `backend/llm/qwen_client.py` | Add `generate_with_tools()` method |
| `backend/routes/chat.py` | Remove context-stuffing (~600 lines), add tool loop (~80 lines) |
| `scripts/etl/run_health_etl.py` | Add `save_health_duckdb()` step |
| `backend/requirements.txt` | Add `duckdb` |

---

## Migration & Rollout Strategy

1. **Deploy DuckDB alongside CSVs** — ETL writes both. Chatbot still reads CSVs. Zero risk.
2. **Run migration script** — import historical CSV data into DuckDB.
3. **Deploy `healthdb.py` + tool layer** — new code paths, not yet active in chat.
4. **Switch chat route to tool-based** — agentic chat goes live. Monitor via query logs.
5. **Disable CSV writes** (`--no-csv` flag on ETL) once chat is confirmed stable for 1 week.

---

## Out of Scope (Spec B and C)

- **RAG knowledge base expansion** (Spec B): Writing new AHU component documents, electrical health guides. Independent — can start any time.
- **Docker deployment** (Spec C): docker-compose wrapping backend + DuckDB + ChromaDB, env-configurable for multi-ward expansion. Depends on Spec A architecture being settled.

---

## Future Considerations

- **Multi-ward expansion**: `WACH_BUILDING_NAME` and `WACH_DEPARTMENT` are already env-configurable. AHU level config (`AHU_LEVEL_CONFIG` in `schemas.py`) will need to be made data-driven (loaded from a config file or DB table) rather than hardcoded for true multi-building support.
- **Prediction tool**: A sixth tool `query_predictions(device_ids, horizon)` can be added once the agentic architecture is proven, replacing the current `_get_prediction_context_sync` path.
- **Classifier improvement**: If heuristics prove insufficient for edge cases, the classifier can be upgraded to a small embedding-based model trained on logged query/complexity pairs — same interface, drop-in replacement.
