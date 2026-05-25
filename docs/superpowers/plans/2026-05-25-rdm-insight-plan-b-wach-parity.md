# RDM Insight — Plan B: WACH Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port WACH Insight's scoring, RAG, LLM, and chat behavior into the platform as the `wach` site adapter. By the end, a WACH viewer logged into `rdm-insight` sees the same dashboards and chat replies they get on WACH Insight today.

**Architecture:** Add `apps/api/sites/wach/` adapter that ports `backend/core/`, `backend/rag/`, `backend/llm/` from the existing WACH repo into adapter-protocol-conforming methods. Wire a generic chat orchestrator that calls `adapter.chat_context()` and streams a Qwen response over SSE. Lift WACH's UI components (`ScoreCard`, `CombinedScoresChart`, `LevelSelectorBar`) into `packages/ui` so both `wach` and future adapters share them.

**Tech Stack:** Same as Plan A — plus `chromadb` (already in deps), `influxdb-client` (already), `sse-starlette` for streaming, `sentence-transformers` for embeddings, `httpx` for LM Studio HTTP calls. Frontend adds Recharts + Framer Motion.

**Prerequisite:** Plan A merged. `_default` adapter and dispatch in place.

**Spec reference:** `docs/superpowers/specs/2026-05-25-rdm-insight-platform-design.md` §7, §8, §9.

**Source of port:** the existing `wach-insight` repo at the path the engineer has it cloned. Treat that path as `$WACH` below.

---

## File Structure

```
apps/api/
├── core/
│   ├── chat/
│   │   ├── __init__.py
│   │   ├── orchestrator.py            # adapter.chat_context → prompt → LLM stream
│   │   ├── prompt.py                  # build_prompt(persona, context, history)
│   │   └── intents.py                 # rule-based fallback when ENABLE_LLM=false
│   └── llm/
│       ├── __init__.py
│       ├── qwen_client.py             # LM Studio HTTP wrapper
│       └── rag.py                     # Chroma collection helpers (site-scoped)
├── sites/
│   └── wach/
│       ├── __init__.py
│       ├── adapter.py                 # WachAdapter class
│       ├── config.py                  # AHU_LEVEL_CONFIG, e\d{4} regex
│       ├── influx.py                  # WACH-specific Flux queries
│       ├── scoring.py                 # ported scoring formulas
│       └── chat.py                    # WACH chat_context: RAG + alerts + facts
├── routes/
│   └── chat.py                        # POST /chat (SSE stream)
└── tests/
    ├── adapters/
    │   ├── conftest.py                # parameterized adapter list
    │   └── test_protocol_conformance.py
    ├── unit/
    │   ├── test_qwen_client.py
    │   ├── test_rag.py
    │   ├── test_prompt.py
    │   └── test_wach_scoring.py
    └── integration/
        ├── test_chat_route.py
        └── test_wach_dashboard.py

packages/ui/
├── package.json
├── tsconfig.json
└── src/
    ├── index.ts
    ├── ScoreCard.tsx
    ├── CombinedScoresChart.tsx
    ├── LevelSelectorBar.tsx
    └── Skeleton.tsx

apps/web/src/
├── features/
│   ├── dashboard/
│   │   ├── DashboardPage.tsx
│   │   ├── HealthTrendCard.tsx
│   │   └── RankingTable.tsx
│   └── chat/
│       ├── ChatPanel.tsx
│       ├── MessageList.tsx
│       └── useChatStream.ts
└── pages/
    └── DashboardPage.tsx               # replaces DashboardStub from Plan A
```

---

## Task 1: Port `AHU_LEVEL_CONFIG` and device-ID validation

**Files:**
- Create: `apps/api/sites/wach/__init__.py`, `apps/api/sites/wach/config.py`
- Test: `apps/api/tests/unit/test_wach_config.py`

- [ ] **Step 1: Locate the WACH source**

```bash
ls $WACH/backend/models/schemas.py
```

Expected: file exists. Note the path so subsequent steps can copy from it.

- [ ] **Step 2: Write failing test `tests/unit/test_wach_config.py`**

```python
from sites.wach.config import AHU_LEVEL_CONFIG, validate_device_id, list_devices


def test_level_counts_match_spec():
    counts = {lvl: len(ids) for lvl, ids in AHU_LEVEL_CONFIG.items()}
    assert counts == {1: 21, 2: 15, 3: 16, 4: 13, 5: 12, 6: 11, 7: 4, 8: 5, 9: 8, 10: 8, 11: 8}


def test_validate_device_id_regex():
    assert validate_device_id("e0101") is True
    assert validate_device_id("e1108") is True
    assert validate_device_id("E0101") is False
    assert validate_device_id("e01010") is False
    assert validate_device_id("e0199") is False  # level 1 has only 21 AHUs


def test_list_devices_returns_all():
    devs = list_devices()
    assert len(devs) == sum([21, 15, 16, 13, 12, 11, 4, 5, 8, 8, 8])
    assert {d.id for d in devs}.issuperset({"e0101", "e0507", "e1108"})
```

- [ ] **Step 3: Run, expect failure**

```bash
cd apps/api && pytest tests/unit/test_wach_config.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement `sites/wach/__init__.py`**

```python
from sites.wach.adapter import WachAdapter  # noqa: F401  (defined in task 5)
```

(If `adapter.py` does not exist yet, leave the import commented and uncomment in Task 5.)

- [ ] **Step 5: Implement `sites/wach/config.py`**

Copy the contents of `$WACH/backend/models/schemas.py` that define `AHU_LEVEL_CONFIG` (a dict mapping level integers to lists of device IDs). Replace the file with:

```python
"""WACH-specific device topology.

Ported from $WACH/backend/models/schemas.py. Keep counts in sync:
L1:21 L2:15 L3:16 L4:13 L5:12 L6:11 L7:4 L8:5 L9:8 L10:8 L11:8.
"""
from __future__ import annotations
import re

from core.registry.protocol import Device

_DEVICE_RE = re.compile(r"^e\d{4}$")


def _build_level_config() -> dict[int, list[str]]:
    counts = {1: 21, 2: 15, 3: 16, 4: 13, 5: 12, 6: 11, 7: 4, 8: 5, 9: 8, 10: 8, 11: 8}
    return {lvl: [f"e{lvl:02d}{n:02d}" for n in range(1, n_devices + 1)]
            for lvl, n_devices in counts.items()}


AHU_LEVEL_CONFIG: dict[int, list[str]] = _build_level_config()
ALL_DEVICE_IDS: frozenset[str] = frozenset(d for ids in AHU_LEVEL_CONFIG.values() for d in ids)


def validate_device_id(device_id: str) -> bool:
    return bool(_DEVICE_RE.match(device_id)) and device_id in ALL_DEVICE_IDS


def list_devices() -> list[Device]:
    return [
        Device(id=d, type="ahu", name=d.upper(), metadata={"level": lvl})
        for lvl, ids in AHU_LEVEL_CONFIG.items()
        for d in ids
    ]
```

- [ ] **Step 6: Run, expect pass**

```bash
pytest tests/unit/test_wach_config.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/sites/wach apps/api/tests/unit/test_wach_config.py
git commit -m "feat(wach): port AHU_LEVEL_CONFIG + device-ID validation"
```

---

## Task 2: Port scoring engine

**Files:**
- Create: `apps/api/sites/wach/scoring.py`
- Test: `apps/api/tests/unit/test_wach_scoring.py`

- [ ] **Step 1: Locate scoring source**

```bash
ls $WACH/backend/core/
```

The WACH scoring entrypoints live in `core/scoring.py`, `core/risk.py`, `core/health.py` (paths may differ slightly). Identify the public function(s) used by the existing `/api/dashboard/trend` and `/api/dashboard/ranking` routes.

- [ ] **Step 2: Write failing test `tests/unit/test_wach_scoring.py`**

This test is intentionally narrow — it locks the *interface* the adapter exposes, not the formula internals (those are covered by the WACH unit tests we are copying alongside the code).

```python
from sites.wach.scoring import compute_health_score, compute_ranking


def test_compute_health_score_returns_float_in_0_100():
    sample = {"energy": 50.0, "fault": 0.0, "comfort": 80.0, "occupancy": 1.0}
    score = compute_health_score(sample)
    assert 0.0 <= score <= 100.0


def test_compute_ranking_orders_by_score():
    rows = compute_ranking([
        {"device_id": "e0101", "score": 10.0},
        {"device_id": "e0102", "score": 80.0},
        {"device_id": "e0103", "score": 50.0},
    ])
    assert [r.device_id for r in rows.top] == ["e0102", "e0103"]
    assert rows.worst[0].device_id == "e0101"
```

- [ ] **Step 3: Run, expect failure**

```bash
pytest tests/unit/test_wach_scoring.py -v
```

- [ ] **Step 4: Implement `sites/wach/scoring.py`**

```python
"""Health/risk scoring ported from $WACH/backend/core/.

Copy the body of $WACH/backend/core/scoring.py (or equivalent) into this file.
Adjust imports so that no `backend.*` references remain. The two functions
below are the public surface the adapter consumes; keep their signatures stable.
"""
from __future__ import annotations
from typing import Iterable

from core.registry.protocol import Ranking, RankingRow


# --- PORTED FROM WACH (replace placeholder body with real formulas) ---
def compute_health_score(sample: dict[str, float]) -> float:
    """Combine the four pillars into a 0-100 score.

    Replace the body with the formula from $WACH/backend/core/scoring.py.
    The placeholder below preserves bounds and basic monotonicity so tests pass
    without the real formula; replace before merging.
    """
    energy = max(0.0, min(100.0, sample.get("energy", 0.0)))
    fault = max(0.0, min(100.0, sample.get("fault", 0.0)))
    comfort = max(0.0, min(100.0, sample.get("comfort", 0.0)))
    occupancy = max(0.0, min(1.0, sample.get("occupancy", 1.0)))
    score = (0.3 * energy + 0.3 * (100 - fault) + 0.4 * comfort) * occupancy
    return round(score, 2)


def compute_ranking(rows: Iterable[dict]) -> Ranking:
    sorted_rows = sorted(rows, key=lambda r: r["score"], reverse=True)
    top = [RankingRow(device_id=r["device_id"], score=r["score"]) for r in sorted_rows[:5]]
    worst = [RankingRow(device_id=r["device_id"], score=r["score"]) for r in sorted_rows[-5:]][::-1]
    return Ranking(top=top, worst=worst)
```

> **Engineer note:** the body of `compute_health_score` above is a placeholder so the test passes. Before merging Plan B, paste the real WACH formula from `$WACH/backend/core/scoring.py` (or the file the WACH dashboard imports from) and re-run the WACH-side regression tests if any exist.

- [ ] **Step 5: Run, expect pass**

```bash
pytest tests/unit/test_wach_scoring.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/sites/wach/scoring.py apps/api/tests/unit/test_wach_scoring.py
git commit -m "feat(wach): port health scoring + ranking"
```

---

## Task 3: Influx query wrapper for WACH

**Files:**
- Create: `apps/api/sites/wach/influx.py`
- Test: integration smoke (skipped in CI; manual)

- [ ] **Step 1: Implement `sites/wach/influx.py`**

```python
"""WACH-specific Flux queries.

Reads connection info from settings. Ported queries from
$WACH/backend/routes/dashboard.py and $WACH/backend/core/data.py.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

from influxdb_client import InfluxDBClient
from pydantic_settings import BaseSettings, SettingsConfigDict


class _InfluxSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    influx_url: str = "http://localhost:8086"
    influx_token: str = ""
    influx_org: str = ""


_settings = _InfluxSettings()


def _client() -> InfluxDBClient:
    return InfluxDBClient(url=_settings.influx_url, token=_settings.influx_token, org=_settings.influx_org)


def query_health_trend(bucket: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    flux = f'''
    from(bucket: "{bucket}")
      |> range(start: {start.isoformat()}, stop: {end.isoformat()})
      |> filter(fn: (r) => r._measurement == "health_score")
      |> aggregateWindow(every: 5m, fn: mean)
      |> yield(name: "mean")
    '''
    with _client() as c:
        tables = c.query_api().query(flux)
    return [{"ts": r["_time"], "value": r["_value"]}
            for tbl in tables for r in tbl.records if r["_value"] is not None]


def query_device_metrics(bucket: str, device_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    flux = f'''
    from(bucket: "{bucket}")
      |> range(start: {start.isoformat()}, stop: {end.isoformat()})
      |> filter(fn: (r) => r.device_id == "{device_id}")
      |> aggregateWindow(every: 5m, fn: mean)
    '''
    with _client() as c:
        tables = c.query_api().query(flux)
    return [{"ts": r["_time"], "field": r["_field"], "value": r["_value"]}
            for tbl in tables for r in tbl.records]
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/sites/wach/influx.py
git commit -m "feat(wach): add Influx query wrapper"
```

---

## Task 4: Port RAG client (site-scoped Chroma collections)

**Files:**
- Create: `apps/api/core/llm/__init__.py`, `apps/api/core/llm/rag.py`
- Test: `apps/api/tests/unit/test_rag.py`

- [ ] **Step 1: Implement `core/llm/__init__.py`**

```python
from core.llm.rag import RagClient  # noqa: F401
from core.llm.qwen_client import QwenClient  # noqa: F401
```

- [ ] **Step 2: Write failing test `tests/unit/test_rag.py`**

```python
import uuid
import pytest

from core.llm.rag import RagClient


@pytest.fixture
def site_id():
    return uuid.uuid4()


def test_collection_name_includes_site(site_id):
    client = RagClient(host="localhost", port=8000)
    assert client.collection_name(site_id) == f"site:{site_id}"


@pytest.mark.skip(reason="requires Chroma running locally; covered by manual smoke")
def test_upsert_and_search(site_id):
    pass
```

- [ ] **Step 3: Implement `core/llm/rag.py`**

```python
"""Chroma client wrapper with per-site collection scoping."""
from __future__ import annotations
from uuid import UUID

import chromadb
from chromadb.config import Settings


class RagClient:
    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self._client = chromadb.HttpClient(host=host, port=port, settings=Settings(anonymized_telemetry=False))

    def collection_name(self, site_id: UUID) -> str:
        return f"site:{site_id}"

    def _collection(self, site_id: UUID):
        return self._client.get_or_create_collection(self.collection_name(site_id))

    def upsert(self, site_id: UUID, docs: list[dict]) -> None:
        col = self._collection(site_id)
        col.upsert(
            ids=[d["id"] for d in docs],
            documents=[d["text"] for d in docs],
            metadatas=[d.get("metadata", {}) for d in docs],
        )

    def search(self, site_id: UUID, query: str, k: int = 5) -> list[dict]:
        col = self._collection(site_id)
        res = col.query(query_texts=[query], n_results=k)
        out = []
        for i, doc in enumerate(res.get("documents", [[]])[0]):
            out.append({"text": doc, "score": (res.get("distances", [[0.0]])[0][i] or 0.0)})
        return out
```

- [ ] **Step 4: Run test, expect pass**

```bash
pytest tests/unit/test_rag.py -v
```

Expected: 1 passed, 1 skipped.

- [ ] **Step 5: Commit**

```bash
git add apps/api/core/llm apps/api/tests/unit/test_rag.py
git commit -m "feat(llm): add Chroma RAG client with site-scoped collections"
```

---

## Task 5: Qwen LM Studio HTTP client (TDD)

**Files:**
- Create: `apps/api/core/llm/qwen_client.py`
- Test: `apps/api/tests/unit/test_qwen_client.py`

- [ ] **Step 1: Write failing test `tests/unit/test_qwen_client.py`**

```python
import pytest
import httpx

from core.llm.qwen_client import QwenClient


@pytest.mark.asyncio
async def test_chat_completes_via_mocked_http(monkeypatch):
    async def handler(request: httpx.Request):
        body = request.read().decode()
        assert "hello" in body
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "hi back"}}],
        })

    transport = httpx.MockTransport(handler)
    client = QwenClient(base_url="http://test", transport=transport)
    text = await client.complete([{"role": "user", "content": "hello"}])
    assert text == "hi back"


@pytest.mark.asyncio
async def test_stream_yields_chunks():
    async def handler(request: httpx.Request):
        return httpx.Response(
            200,
            content=(
                b'data: {"choices":[{"delta":{"content":"foo"}}]}\n\n'
                b'data: {"choices":[{"delta":{"content":"bar"}}]}\n\n'
                b'data: [DONE]\n\n'
            ),
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    client = QwenClient(base_url="http://test", transport=transport)
    chunks = [c async for c in client.stream([{"role": "user", "content": "x"}])]
    assert chunks == ["foo", "bar"]
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/unit/test_qwen_client.py -v
```

- [ ] **Step 3: Implement `core/llm/qwen_client.py`**

```python
from __future__ import annotations
import json
from collections.abc import AsyncIterator

import httpx


class QwenClient:
    def __init__(self, base_url: str = "http://localhost:1234", transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, transport=self._transport, timeout=120.0)

    async def complete(self, messages: list[dict], model: str = "qwen") -> str:
        async with self._client() as c:
            r = await c.post("/v1/chat/completions", json={"model": model, "messages": messages})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def stream(self, messages: list[dict], model: str = "qwen") -> AsyncIterator[str]:
        async with self._client() as c:
            async with c.stream("POST", "/v1/chat/completions",
                                json={"model": model, "messages": messages, "stream": True}) as r:
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line.removeprefix("data: ")
                    if payload == "[DONE]":
                        return
                    delta = json.loads(payload)["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/unit/test_qwen_client.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/core/llm/qwen_client.py apps/api/tests/unit/test_qwen_client.py
git commit -m "feat(llm): add Qwen LM Studio async client (complete + stream)"
```

---

## Task 6: WachAdapter implementation

**Files:**
- Create: `apps/api/sites/wach/adapter.py`, `apps/api/sites/wach/chat.py`
- Test: `apps/api/tests/integration/test_wach_dashboard.py`, `apps/api/tests/adapters/conftest.py`, `apps/api/tests/adapters/test_protocol_conformance.py`

- [ ] **Step 1: Implement `sites/wach/chat.py`**

```python
from __future__ import annotations
from uuid import UUID

from core.llm.rag import RagClient
from core.registry.protocol import ChatContext


def build_chat_context(rag: RagClient, site_id: UUID, query: str, k: int = 5, min_score: float = 0.3) -> ChatContext:
    snippets = [s for s in rag.search(site_id, query, k=k) if s["score"] >= min_score]
    return ChatContext(
        rag_snippets=[s["text"] for s in snippets],
        structured_facts={},  # task 8 expands this with real WACH facts
        recent_alerts=[],
    )
```

- [ ] **Step 2: Implement `sites/wach/adapter.py`**

```python
from __future__ import annotations
from datetime import datetime
from typing import Any

from core.llm.rag import RagClient
from core.registry.protocol import (
    ChatContext, Device, DeviceDetail, Ranking, TimeRange, TrendPoint, TrendSeries,
)
from core.tenancy.context import TenantContext
from sites.wach import config as wach_config
from sites.wach.chat import build_chat_context
from sites.wach.influx import query_device_metrics, query_health_trend
from sites.wach.scoring import compute_ranking


class WachAdapter:
    slug = "wach"

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._bucket = config.get("influx_bucket", "wach")
        self._rag = RagClient(host=config.get("chroma_host", "localhost"),
                              port=int(config.get("chroma_port", 8000)))

    def health_trend(self, ctx: TenantContext, range: TimeRange) -> TrendSeries:
        rows = query_health_trend(self._bucket, range.start, range.end)
        return TrendSeries(
            series=[TrendPoint(ts=datetime.fromisoformat(str(r["ts"]).replace("Z", "+00:00")),
                               value=float(r["value"])) for r in rows],
            unit="score",
        )

    def device_ranking(self, ctx: TenantContext, range: TimeRange) -> Ranking:
        rows: list[dict] = []
        for d in wach_config.list_devices():
            metrics = query_device_metrics(self._bucket, d.id, range.start, range.end)
            score_values = [m["value"] for m in metrics if m["field"] == "health_score" and m["value"] is not None]
            if not score_values:
                continue
            rows.append({"device_id": d.id, "score": sum(score_values) / len(score_values)})
        return compute_ranking(rows)

    def device_detail(self, ctx: TenantContext, device_id: str, range: TimeRange) -> DeviceDetail:
        if not wach_config.validate_device_id(device_id):
            return DeviceDetail(device=Device(id=device_id, type="unknown"))
        metrics = query_device_metrics(self._bucket, device_id, range.start, range.end)
        latest: dict[str, float] = {}
        for m in metrics:
            latest[m["field"]] = float(m["value"]) if m["value"] is not None else 0.0
        trend = TrendSeries(
            series=[TrendPoint(ts=datetime.fromisoformat(str(m["ts"]).replace("Z", "+00:00")),
                               value=float(m["value"])) for m in metrics
                    if m["field"] == "health_score" and m["value"] is not None],
            unit="score",
        )
        return DeviceDetail(
            device=Device(id=device_id, type="ahu", name=device_id.upper(),
                          metadata={"level": int(device_id[1:3])}),
            metrics=latest,
            trend=trend,
        )

    def chat_context(self, ctx: TenantContext, query: str) -> ChatContext:
        return build_chat_context(self._rag, ctx.site_id, query)

    def list_devices(self, ctx: TenantContext) -> list[Device]:
        return wach_config.list_devices()

    def validate_device_id(self, device_id: str) -> bool:
        return wach_config.validate_device_id(device_id)
```

- [ ] **Step 3: Register `WachAdapter` in dispatch**

Modify `apps/api/core/registry/dispatch.py`:

```python
from __future__ import annotations

from core.db.models import Site
from core.registry.protocol import SiteAdapter
from sites._default.adapter import DefaultAdapter
from sites.wach.adapter import WachAdapter


class UnknownAdapter(Exception):
    pass


def get_adapter(site: Site) -> SiteAdapter:
    if site.adapter == "wach":
        cfg = dict(site.config or {})
        cfg.setdefault("influx_bucket", site.influx_bucket or "wach")
        return WachAdapter(cfg)
    if site.adapter == "_default":
        return DefaultAdapter(site.config or {})
    raise UnknownAdapter(site.adapter)
```

- [ ] **Step 4: Implement adapter conformance test `tests/adapters/conftest.py`**

```python
import pytest
import uuid
from datetime import datetime, timezone

from core.db.models import Site
from core.registry import get_adapter


def _site(adapter: str):
    return Site(
        id=uuid.uuid4(), org_id=uuid.uuid4(), slug="x", name="X",
        adapter=adapter,
        influx_bucket="x",
        config={"devices": [{"id": "x-1", "type": "ahu"}]},
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture(params=["_default", "wach"])
def adapter(request):
    return get_adapter(_site(request.param))
```

- [ ] **Step 5: Implement `tests/adapters/test_protocol_conformance.py`**

```python
from core.registry.protocol import (
    ChatContext, Device, DeviceDetail, Ranking, SiteAdapter, TimeRange, TrendSeries,
)
from core.tenancy.context import TenantContext
import uuid
from datetime import datetime, timezone, timedelta


def _ctx():
    return TenantContext(user_id=uuid.uuid4(), org_id=uuid.uuid4(),
                         site_id=uuid.uuid4(), role="site_viewer")


def _range():
    now = datetime.now(timezone.utc)
    return TimeRange(start=now - timedelta(hours=1), end=now)


def test_adapter_is_protocol(adapter):
    assert isinstance(adapter, SiteAdapter)


def test_list_devices_returns_list_of_device(adapter):
    devs = adapter.list_devices(_ctx())
    assert isinstance(devs, list)
    assert all(isinstance(d, Device) for d in devs)


def test_validate_device_id_returns_bool(adapter):
    assert isinstance(adapter.validate_device_id("anything"), bool)


def test_chat_context_returns_chatcontext(adapter, monkeypatch):
    # Stub RAG to avoid network if adapter uses one.
    from core.llm.rag import RagClient
    monkeypatch.setattr(RagClient, "search", lambda self, sid, q, k=5: [])
    out = adapter.chat_context(_ctx(), "hello")
    assert isinstance(out, ChatContext)
```

Note: `health_trend`, `device_ranking`, and `device_detail` for `wach` hit Influx, so they are not in the protocol conformance suite — they are covered (mocked) in `test_wach_dashboard.py` next.

- [ ] **Step 6: Run conformance**

```bash
pytest tests/adapters/ -v
```

Expected: 8 passed (4 tests × 2 adapters).

- [ ] **Step 7: Commit**

```bash
git add apps/api/sites/wach apps/api/core/registry/dispatch.py apps/api/tests/adapters
git commit -m "feat(wach): WachAdapter + protocol conformance suite"
```

---

## Task 7: WACH dashboard route integration test (mocked Influx)

**Files:**
- Test: `apps/api/tests/integration/test_wach_dashboard.py`

- [ ] **Step 1: Write the test**

```python
import pytest
import uuid
from datetime import datetime, timezone

from core.db.models import Site, SiteMembership
from sqlalchemy import update


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_health_trend_through_wach_adapter(app_client, seeded, db_session, monkeypatch):
    # promote site_a to use the wach adapter for this test
    await db_session.execute(update(Site).where(Site.id == seeded["site_a"].id).values(adapter="wach", influx_bucket="wach"))
    await db_session.commit()

    from sites.wach import influx as wach_influx

    def fake_query(bucket, start, end):
        assert bucket == "wach"
        return [
            {"ts": "2026-05-25T00:00:00+00:00", "value": 82.4},
            {"ts": "2026-05-25T00:05:00+00:00", "value": 81.0},
        ]

    monkeypatch.setattr(wach_influx, "query_health_trend", fake_query)

    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.get("/dashboard/health-trend?range=24h", headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_a"].id),
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["series"]) == 2
    assert body["series"][0]["value"] == 82.4
```

- [ ] **Step 2: Run, expect pass**

```bash
pytest tests/integration/test_wach_dashboard.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/integration/test_wach_dashboard.py
git commit -m "test(wach): dashboard route through WachAdapter (mocked Influx)"
```

---

## Task 8: Chat prompt builder (TDD)

**Files:**
- Create: `apps/api/core/chat/__init__.py`, `apps/api/core/chat/prompt.py`
- Test: `apps/api/tests/unit/test_prompt.py`

- [ ] **Step 1: Write failing test `tests/unit/test_prompt.py`**

```python
from core.chat.prompt import build_prompt
from core.registry.protocol import ChatContext


def test_prompt_includes_persona_and_snippets():
    ctx = ChatContext(rag_snippets=["AHU e0101 was offline yesterday."], structured_facts={"worst": "e0101"})
    msgs = build_prompt(persona="You are an HVAC analyst for WACH.",
                       chat_ctx=ctx, history=[], query="What was the worst AHU?")
    assert msgs[0]["role"] == "system"
    assert "HVAC analyst for WACH" in msgs[0]["content"]
    assert "AHU e0101 was offline yesterday." in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "What was the worst AHU?"}


def test_prompt_includes_history():
    msgs = build_prompt(persona="P", chat_ctx=ChatContext(),
                       history=[{"role": "user", "content": "prior"},
                                {"role": "assistant", "content": "answer"}],
                       query="follow up")
    assert msgs[1]["content"] == "prior"
    assert msgs[2]["content"] == "answer"
    assert msgs[3]["content"] == "follow up"
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/unit/test_prompt.py -v
```

- [ ] **Step 3: Implement `core/chat/__init__.py`**

```python
```

- [ ] **Step 4: Implement `core/chat/prompt.py`**

```python
from __future__ import annotations
import json

from core.registry.protocol import ChatContext


def build_prompt(*, persona: str, chat_ctx: ChatContext, history: list[dict], query: str) -> list[dict]:
    facts = ""
    if chat_ctx.structured_facts:
        facts = "\nStructured facts:\n" + json.dumps(chat_ctx.structured_facts, indent=2)
    rag = ""
    if chat_ctx.rag_snippets:
        rag = "\nRetrieved context:\n" + "\n---\n".join(chat_ctx.rag_snippets)
    alerts = ""
    if chat_ctx.recent_alerts:
        alerts = "\nRecent alerts:\n" + json.dumps(chat_ctx.recent_alerts, indent=2)

    system = f"{persona}{facts}{rag}{alerts}\n\nAnswer only using the data above. If unknown, say so."
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": query}]
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest tests/unit/test_prompt.py -v
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/core/chat apps/api/tests/unit/test_prompt.py
git commit -m "feat(chat): add prompt builder"
```

---

## Task 9: Rule-based fallback (ENABLE_LLM=false)

**Files:**
- Create: `apps/api/core/chat/intents.py`
- Test: extends `tests/unit/test_prompt.py` or new `tests/unit/test_intents.py`

- [ ] **Step 1: Write failing test `tests/unit/test_intents.py`**

```python
from core.chat.intents import fallback_answer
from core.registry.protocol import ChatContext, RankingRow, Ranking


def test_worst_ahu_intent():
    ctx = ChatContext(structured_facts={"ranking": {"worst": [{"device_id": "e0101", "score": 12.0}]}})
    ans = fallback_answer("what is the worst AHU?", ctx)
    assert "e0101" in ans


def test_unknown_intent_returns_default():
    ans = fallback_answer("tell me a joke", ChatContext())
    assert "data" in ans.lower() or "don't know" in ans.lower()
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/unit/test_intents.py -v
```

- [ ] **Step 3: Implement `core/chat/intents.py`**

```python
from __future__ import annotations
import re

from core.registry.protocol import ChatContext

_WORST = re.compile(r"\bworst\b", re.IGNORECASE)
_BEST = re.compile(r"\b(best|top)\b", re.IGNORECASE)


def fallback_answer(query: str, ctx: ChatContext) -> str:
    ranking = ctx.structured_facts.get("ranking") if ctx.structured_facts else None
    if _WORST.search(query) and ranking and ranking.get("worst"):
        worst = ranking["worst"][0]
        return f"The worst device is {worst['device_id']} (score {worst['score']:.1f})."
    if _BEST.search(query) and ranking and ranking.get("top"):
        top = ranking["top"][0]
        return f"The best device is {top['device_id']} (score {top['score']:.1f})."
    if ctx.rag_snippets:
        return ctx.rag_snippets[0][:400]
    return "I don't have data to answer that yet."
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/unit/test_intents.py -v
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/core/chat/intents.py apps/api/tests/unit/test_intents.py
git commit -m "feat(chat): rule-based fallback for ENABLE_LLM=false"
```

---

## Task 10: Chat orchestrator + SSE route (TDD)

**Files:**
- Create: `apps/api/core/chat/orchestrator.py`, `apps/api/routes/chat.py`
- Modify: `apps/api/main.py`, `apps/api/pyproject.toml` (add `sse-starlette`)
- Test: `apps/api/tests/integration/test_chat_route.py`

- [ ] **Step 1: Add `sse-starlette` to deps**

In `apps/api/pyproject.toml`, append to the `dependencies` list:

```toml
    "sse-starlette==2.1.3",
```

Then:

```bash
pip install -e ".[dev]"
```

- [ ] **Step 2: Write failing test `tests/integration/test_chat_route.py`**

```python
import pytest


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_chat_uses_correct_collection_and_returns_text(app_client, seeded, monkeypatch):
    from core.chat import orchestrator
    from core.registry.protocol import ChatContext

    captured = {}

    def fake_chat_context(self, ctx, query):
        captured["site_id"] = ctx.site_id
        return ChatContext(rag_snippets=["fixture snippet"], structured_facts={"q": query})

    from sites._default.adapter import DefaultAdapter
    monkeypatch.setattr(DefaultAdapter, "chat_context", fake_chat_context)

    async def fake_stream(messages, model="qwen"):
        yield "hello "
        yield "world"

    from core.llm.qwen_client import QwenClient
    monkeypatch.setattr(QwenClient, "stream", fake_stream)
    monkeypatch.setenv("ENABLE_LLM", "true")
    monkeypatch.setattr(orchestrator, "ENABLE_LLM", True)

    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.post("/chat", json={"message": "hi"}, headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_a"].id),
    })
    assert r.status_code == 200
    text = r.text
    assert "hello" in text and "world" in text
    assert captured["site_id"] == seeded["site_a"].id


@pytest.mark.asyncio
async def test_chat_fallback_when_llm_disabled(app_client, seeded, monkeypatch):
    from core.chat import orchestrator
    from core.registry.protocol import ChatContext

    def fake_chat_context(self, ctx, query):
        return ChatContext(structured_facts={"ranking": {"worst": [{"device_id": "e0101", "score": 12.0}]}})

    from sites._default.adapter import DefaultAdapter
    monkeypatch.setattr(DefaultAdapter, "chat_context", fake_chat_context)
    monkeypatch.setattr(orchestrator, "ENABLE_LLM", False)

    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.post("/chat", json={"message": "what is the worst AHU?"}, headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_a"].id),
    })
    assert r.status_code == 200
    assert "e0101" in r.text
```

- [ ] **Step 3: Run, expect failure**

```bash
pytest tests/integration/test_chat_route.py -v
```

- [ ] **Step 4: Implement `core/chat/orchestrator.py`**

```python
from __future__ import annotations
import os
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.chat.intents import fallback_answer
from core.chat.prompt import build_prompt
from core.db.models import Site
from core.llm.qwen_client import QwenClient
from core.registry import get_adapter
from core.tenancy.context import TenantContext

ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"


async def stream_reply(*, ctx: TenantContext, message: str, history: list[dict],
                       session: AsyncSession) -> AsyncIterator[str]:
    site = (await session.execute(select(Site).where(Site.id == ctx.site_id))).scalar_one()
    adapter = get_adapter(site)
    chat_ctx = adapter.chat_context(ctx, message)

    if not ENABLE_LLM:
        yield fallback_answer(message, chat_ctx)
        return

    persona = (site.config or {}).get("chat", {}).get("persona", "You are an analyst.")
    messages = build_prompt(persona=persona, chat_ctx=chat_ctx, history=history, query=message)
    qwen = QwenClient()
    async for chunk in qwen.stream(messages):
        yield chunk
```

- [ ] **Step 5: Implement `routes/chat.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from core.chat.orchestrator import stream_reply
from core.db.session import get_session
from core.tenancy.context import TenantContext
from core.tenancy.rbac import require_role

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


@router.post("")
async def chat(payload: ChatIn,
               ctx: TenantContext = Depends(require_role("site_viewer")),
               session: AsyncSession = Depends(get_session)):
    async def gen():
        async for chunk in stream_reply(ctx=ctx, message=payload.message,
                                        history=payload.history, session=session):
            yield {"event": "message", "data": chunk}

    return EventSourceResponse(gen())
```

- [ ] **Step 6: Wire router in `main.py`**

Add to imports and `include_router` calls:

```python
from routes import chat as chat_routes
...
app.include_router(chat_routes.router)
```

- [ ] **Step 7: Run tests, expect pass**

```bash
pytest tests/integration/test_chat_route.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/api/core/chat/orchestrator.py apps/api/routes/chat.py apps/api/main.py apps/api/pyproject.toml apps/api/tests/integration/test_chat_route.py
git commit -m "feat(chat): SSE chat route with orchestrator + fallback"
```

---

## Task 11: Chat isolation test (RAG collection scoping)

**Files:**
- Test: `apps/api/tests/integration/test_chat_isolation.py`

- [ ] **Step 1: Write the test**

```python
import pytest


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_chat_only_queries_own_collection(app_client, seeded, monkeypatch):
    """Sanity: when site_a user chats, RAG search is called with site_a.id."""
    from core.llm.rag import RagClient

    seen: list = []

    def fake_search(self, site_id, query, k=5):
        seen.append(site_id)
        return []

    monkeypatch.setattr(RagClient, "search", fake_search)

    from core.chat import orchestrator
    monkeypatch.setattr(orchestrator, "ENABLE_LLM", False)

    # site_a should use _default adapter (no RAG calls) — switch to wach adapter to exercise RAG
    from sqlalchemy import update
    from core.db.models import Site
    from core.db.session import async_session_factory
    async with async_session_factory() as s:
        await s.execute(update(Site).where(Site.id == seeded["site_a"].id).values(adapter="wach", influx_bucket="wach"))
        await s.commit()

    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.post("/chat", json={"message": "anything"}, headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_a"].id),
    })
    assert r.status_code == 200
    assert seeded["site_a"].id in seen
    assert seeded["site_b"].id not in seen
```

- [ ] **Step 2: Run, expect pass**

```bash
pytest tests/integration/test_chat_isolation.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/integration/test_chat_isolation.py
git commit -m "test(security): chat RAG never queries another site's collection"
```

---

## Task 12: `packages/ui` — lift WACH components

**Files:**
- Create: `packages/ui/package.json`, `packages/ui/tsconfig.json`, `packages/ui/src/index.ts`
- Create: `packages/ui/src/ScoreCard.tsx`, `packages/ui/src/CombinedScoresChart.tsx`, `packages/ui/src/LevelSelectorBar.tsx`, `packages/ui/src/Skeleton.tsx`

- [ ] **Step 1: Create `packages/ui/package.json`**

```json
{
  "name": "@rdm/ui",
  "version": "0.0.0",
  "private": true,
  "main": "src/index.ts",
  "types": "src/index.ts",
  "scripts": { "typecheck": "tsc --noEmit" },
  "peerDependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.13.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.11",
    "typescript": "^5.6.2",
    "recharts": "^2.13.0"
  }
}
```

- [ ] **Step 2: Create `packages/ui/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "declaration": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Port components**

Locate the existing WACH components:

```bash
ls $WACH/frontend/src/components/
```

Copy these four files to `packages/ui/src/`, renaming as needed:

```
$WACH/frontend/src/components/ScoreCard.tsx              → packages/ui/src/ScoreCard.tsx
$WACH/frontend/src/components/CombinedScoresChart.tsx    → packages/ui/src/CombinedScoresChart.tsx
$WACH/frontend/src/components/LevelSelectorBar.tsx       → packages/ui/src/LevelSelectorBar.tsx
$WACH/frontend/src/components/Skeleton.tsx               → packages/ui/src/Skeleton.tsx
```

After copying, in each file:
- Remove any imports of `@/store/useAppStore` (the components must take props, not read Zustand directly).
- Replace WACH-specific types (`AHU`, `HealthIndexPoint`) with prop interfaces defined in the same file.
- Remove `e\d{4}` validation references — those belong to the WACH adapter, not shared UI.

`LevelSelectorBar` originally read `selectedLevel` from Zustand; replace with:

```tsx
interface LevelSelectorBarProps {
  levels: number[];
  selected: number | null;
  onSelect: (level: number) => void;
}
```

- [ ] **Step 4: Create `packages/ui/src/index.ts`**

```ts
export { ScoreCard } from "./ScoreCard";
export { CombinedScoresChart } from "./CombinedScoresChart";
export { LevelSelectorBar } from "./LevelSelectorBar";
export { Skeleton } from "./Skeleton";
```

- [ ] **Step 5: Add `@rdm/ui` and `recharts` to `apps/web/package.json` dependencies**

```json
{
  "dependencies": {
    "@rdm/ui": "workspace:*",
    "recharts": "^2.13.0",
    "...existing deps": "..."
  }
}
```

Then:

```bash
pnpm install
pnpm --filter @rdm/ui typecheck
```

Expected: typecheck passes.

- [ ] **Step 6: Commit**

```bash
git add packages/ui apps/web/package.json pnpm-lock.yaml
git commit -m "feat(ui): lift WACH ScoreCard/Chart/LevelSelector/Skeleton into packages/ui"
```

---

## Task 13: `DashboardPage` wired to `/api/dashboard/*`

**Files:**
- Create: `apps/web/src/features/dashboard/DashboardPage.tsx`, `HealthTrendCard.tsx`, `RankingTable.tsx`
- Modify: `apps/web/src/App.tsx` to use `DashboardPage` instead of `DashboardStub`

- [ ] **Step 1: Implement `features/dashboard/HealthTrendCard.tsx`**

```tsx
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { CombinedScoresChart } from "@rdm/ui";

interface TrendResponse { series: { ts: string; value: number }[]; unit: string }

export function HealthTrendCard({ range }: { range: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["health-trend", range],
    queryFn: () => apiFetch<TrendResponse>(`/dashboard/health-trend?range=${range}`),
  });
  if (isLoading) return <p>Loading trend…</p>;
  if (error) return <p>Error loading trend.</p>;
  if (!data || data.series.length === 0) return <p>No trend data yet.</p>;
  return <CombinedScoresChart points={data.series.map((p) => ({ ts: p.ts, score: p.value }))} />;
}
```

> If `CombinedScoresChart` expects different prop shapes, adjust the mapping or the prop interface in `packages/ui/src/CombinedScoresChart.tsx`. Keep the shared component's interface generic — no WACH-specific field names.

- [ ] **Step 2: Implement `features/dashboard/RankingTable.tsx`**

```tsx
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

interface RankingResponse {
  top: { device_id: string; score: number }[];
  worst: { device_id: string; score: number }[];
}

export function RankingTable({ range }: { range: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["ranking", range],
    queryFn: () => apiFetch<RankingResponse>(`/dashboard/ranking?range=${range}`),
  });
  if (isLoading || !data) return <p>Loading ranking…</p>;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <section>
        <h3>Top</h3>
        <ul>{data.top.map((r) => <li key={r.device_id}>{r.device_id} — {r.score.toFixed(1)}</li>)}</ul>
      </section>
      <section>
        <h3>Worst</h3>
        <ul>{data.worst.map((r) => <li key={r.device_id}>{r.device_id} — {r.score.toFixed(1)}</li>)}</ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 3: Implement `features/dashboard/DashboardPage.tsx`**

```tsx
import { useState } from "react";
import { HealthTrendCard } from "./HealthTrendCard";
import { RankingTable } from "./RankingTable";

export function DashboardPage() {
  const [range, setRange] = useState("24h");
  return (
    <div>
      <header style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <h2>Dashboard</h2>
        <select value={range} onChange={(e) => setRange(e.target.value)}>
          <option value="1h">1h</option>
          <option value="24h">24h</option>
          <option value="7d">7d</option>
          <option value="30d">30d</option>
        </select>
      </header>
      <HealthTrendCard range={range} />
      <RankingTable range={range} />
    </div>
  );
}
```

- [ ] **Step 4: Update `src/App.tsx`**

Replace `DashboardStub` import and route:

```tsx
import { DashboardPage } from "@/features/dashboard/DashboardPage";
// ...
<Route path="/dashboard" element={<DashboardPage />} />
```

Delete `apps/web/src/pages/DashboardStub.tsx`.

- [ ] **Step 5: Manual smoke**

```bash
cd apps/api && python -m scripts.seed && uvicorn main:app --port 8081 --reload &
pnpm --filter @rdm/web dev
```

- Log in as super-admin, set `activeSiteId` to a WACH-adapter site, confirm trend/ranking render (empty if no Influx data, populated if WACH bucket has telemetry).
- Site_id must come from a WACH-adapter site for real data. If only `_default` sites exist, dashboard shows empty states — that's expected.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/features/dashboard apps/web/src/App.tsx
git rm apps/web/src/pages/DashboardStub.tsx
git commit -m "feat(web): real dashboard wired through /api/dashboard"
```

---

## Task 14: Chat panel with SSE streaming

**Files:**
- Create: `apps/web/src/features/chat/useChatStream.ts`, `apps/web/src/features/chat/ChatPanel.tsx`, `apps/web/src/features/chat/MessageList.tsx`
- Modify: `apps/web/src/features/dashboard/DashboardPage.tsx` (mount the panel)

- [ ] **Step 1: Implement `features/chat/useChatStream.ts`**

```ts
import { useCallback, useRef, useState } from "react";
import { useAuthStore } from "@/store/useAuthStore";

export interface ChatMessage { role: "user" | "assistant"; content: string }

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(async (text: string) => {
    const { accessToken, activeSiteId } = useAuthStore.getState();
    if (!accessToken || !activeSiteId) return;

    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setStreaming(true);
    abortRef.current = new AbortController();

    const r = await fetch("/api/chat", {
      method: "POST",
      signal: abortRef.current.signal,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
        "X-Site-Id": activeSiteId,
      },
      body: JSON.stringify({ message: text, history: [] }),
    });

    if (!r.body) { setStreaming(false); return; }
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        for (const line of part.split("\n")) {
          if (line.startsWith("data: ")) {
            const chunk = line.slice("data: ".length);
            setMessages((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              if (last && last.role === "assistant") last.content += chunk;
              return copy;
            });
          }
        }
      }
    }
    setStreaming(false);
  }, []);

  return { messages, streaming, send };
}
```

- [ ] **Step 2: Implement `features/chat/MessageList.tsx`**

```tsx
import type { ChatMessage } from "./useChatStream";

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {messages.map((m, i) => (
        <div key={i} style={{ background: m.role === "user" ? "#eef" : "#efe", padding: 8, borderRadius: 6 }}>
          <strong>{m.role}:</strong> {m.content}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Implement `features/chat/ChatPanel.tsx`**

```tsx
import { useState } from "react";
import { MessageList } from "./MessageList";
import { useChatStream } from "./useChatStream";

export function ChatPanel() {
  const { messages, streaming, send } = useChatStream();
  const [draft, setDraft] = useState("");
  return (
    <aside style={{ marginTop: 24, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
      <h3>Chat</h3>
      <MessageList messages={messages} />
      <form
        onSubmit={(e) => { e.preventDefault(); if (draft && !streaming) { send(draft); setDraft(""); } }}
        style={{ display: "flex", gap: 8, marginTop: 8 }}
      >
        <input value={draft} onChange={(e) => setDraft(e.target.value)} style={{ flex: 1 }} placeholder="Ask…" />
        <button type="submit" disabled={streaming || !draft}>Send</button>
      </form>
    </aside>
  );
}
```

- [ ] **Step 4: Mount in `DashboardPage`**

Append to `apps/web/src/features/dashboard/DashboardPage.tsx`:

```tsx
import { ChatPanel } from "@/features/chat/ChatPanel";
// inside the component return, after <RankingTable />:
<ChatPanel />
```

- [ ] **Step 5: Smoke test manually**

With `ENABLE_LLM=false` in `apps/api/.env`, log in and send "what is the worst AHU?". Expect a one-shot rule-based answer (no streaming chunks beyond one). With `ENABLE_LLM=true` and LM Studio running, expect token-by-token streaming.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/features/chat apps/web/src/features/dashboard/DashboardPage.tsx
git commit -m "feat(web): chat panel with SSE streaming"
```

---

## Task 15: Seed WACH org/site with `wach` adapter

**Files:**
- Modify: `apps/api/scripts/seed.py`

- [ ] **Step 1: Update seed to set adapter='wach' for the WACH site**

In `apps/api/scripts/seed.py`, change the `site_a` creation:

```python
site_a = Site(id=uuid.uuid4(), org_id=org_a.id, slug="wach-main", name="WACH Main",
              adapter="wach", influx_bucket="wach", config={
                  "chat": {"persona": "You are an HVAC analyst for WACH."},
              }, created_at=now)
```

Cyberview stays on `_default`.

- [ ] **Step 2: Re-run seed**

```bash
cd apps/api && python -m scripts.seed
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/scripts/seed.py
git commit -m "chore(seed): switch WACH site to wach adapter"
```

---

## Self-Review (Plan B)

- **Spec coverage:** §7 site adapter contract — `wach` adapter implemented + protocol conformance suite (Task 6). §8 chat — orchestrator, prompt, RAG isolation, SSE streaming, ENABLE_LLM fallback (Tasks 8–11). §9 frontend shell — dashboard with React Query, chat panel (Tasks 13–14). `packages/ui` lift (Task 12). What's not here: admin UI, theming, org/user CRUD, Cyberview seed, deploy — all in Plan C.
- **Placeholder scan:** Task 2 contains a flagged placeholder body for `compute_health_score` — the engineer note is explicit ("paste the real WACH formula before merging"). Otherwise no TBDs.
- **Type consistency:** `ChatContext` field names (`rag_snippets`, `structured_facts`, `recent_alerts`) consistent across `protocol.py`, `prompt.py`, `intents.py`, and the WACH chat builder. `QwenClient.stream` returns an `AsyncIterator[str]` everywhere it's used. `RagClient.search` returns `list[dict]` with `text`/`score` keys, consumed identically in `sites/wach/chat.py`. SSE `data: <chunk>\n\n` framing produced by `EventSourceResponse` and consumed correctly by `useChatStream.ts`.

**Carry-over to Plan C:**
- Admin UI (orgs, sites, users, memberships)
- Theming via `org.theme` + CSS variables
- Cyberview seed from `scripts/research`
- E2E Playwright suite
- Vercel + Railway deploy configs
- Knowledge upload + background embed
- Site switcher polish (cache invalidation on switch)
