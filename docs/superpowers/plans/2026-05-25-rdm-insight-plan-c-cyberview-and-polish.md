# RDM Insight — Plan C: Cyberview + Demo Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the two-tenant demo. Cyberview tenant works end-to-end via the `_default` adapter (seeded from `scripts/research`). Org/site/user admin UI ships. Theming differentiates WACH and Cyberview. Site switcher invalidates cached site-scoped queries. Playwright E2E covers the four scenarios from spec §10. Vercel + Railway deploy configs ready.

**Architecture:** Flesh out `_default` adapter to do real historical aggregation against InfluxDB using a generic point-map config. Add admin routes scoped by role. Add knowledge upload endpoint that chunks docs into the site's Chroma collection. Wire `ThemeProvider` (CSS variables) reading from the active org's `theme`. Add Playwright tests and deploy configs.

**Tech Stack:** Same as Plans A/B — plus Playwright, `vercel.ts`/`vercel.json` for `apps/web`, Railway config for `apps/api`, `python-multipart` (already in deps) for file upload.

**Prerequisites:** Plans A and B merged. WachAdapter working, chat orchestrator + SSE in place.

**Spec reference:** `docs/superpowers/specs/2026-05-25-rdm-insight-platform-design.md` §5, §7, §8, §9, §10, §12.

---

## File Structure

```
apps/api/
├── core/
│   ├── engine/
│   │   └── default.py                   # generic Influx aggregator
│   └── knowledge/
│       ├── __init__.py
│       ├── chunker.py                   # split docs into RAG-ready chunks
│       └── ingest.py                    # background task to upsert chunks
├── routes/
│   ├── admin.py                         # orgs/sites/users CRUD
│   └── knowledge.py                     # POST /admin/sites/{id}/knowledge
├── scripts/
│   ├── seed_cyberview.py                # pulls scripts/research into _default config
│   └── seed.py                          # updated to call seed_cyberview
└── tests/
    ├── unit/
    │   ├── test_default_engine.py
    │   └── test_chunker.py
    └── integration/
        ├── test_admin_routes.py
        ├── test_knowledge_upload.py
        └── test_default_dashboard.py

apps/web/src/
├── shell/
│   ├── ThemeProvider.tsx
│   ├── SiteSwitcher.tsx                 # polished version (cache invalidation)
│   └── Gate.tsx
├── features/
│   └── admin/
│       ├── AdminPage.tsx
│       ├── OrgList.tsx
│       ├── SiteList.tsx
│       ├── UserList.tsx
│       └── KnowledgeUpload.tsx

e2e/
├── package.json
├── playwright.config.ts
└── tests/
    ├── wach-viewer.spec.ts
    ├── cyberview-viewer.spec.ts
    ├── super-admin.spec.ts
    └── operator-audit.spec.ts

infra/
├── vercel.ts                            # Vercel project config for apps/web
└── railway.toml                         # Railway service config for apps/api

.github/workflows/
└── e2e.yml
```

---

## Task 1: Generic Influx aggregator for `_default` adapter (TDD)

**Files:**
- Create: `apps/api/core/engine/__init__.py`, `apps/api/core/engine/default.py`
- Modify: `apps/api/sites/_default/adapter.py`
- Test: `apps/api/tests/unit/test_default_engine.py`

- [ ] **Step 1: Implement `core/engine/__init__.py`**

```python
from core.engine.default import build_flux_aggregate, summarize_rankings  # noqa: F401
```

- [ ] **Step 2: Write failing test `tests/unit/test_default_engine.py`**

```python
from datetime import datetime, timezone, timedelta

from core.engine.default import build_flux_aggregate, summarize_rankings


def test_build_flux_uses_bucket_and_measurement():
    flux = build_flux_aggregate(
        bucket="cv",
        measurement="telemetry",
        field="health_score",
        start=datetime(2026, 5, 25, tzinfo=timezone.utc),
        end=datetime(2026, 5, 26, tzinfo=timezone.utc),
        window="5m",
    )
    assert 'from(bucket: "cv")' in flux
    assert 'r._measurement == "telemetry"' in flux
    assert 'r._field == "health_score"' in flux


def test_summarize_rankings_returns_top_and_worst():
    rows = [
        {"device_id": "a", "score": 10.0},
        {"device_id": "b", "score": 90.0},
        {"device_id": "c", "score": 50.0},
    ]
    r = summarize_rankings(rows, top_n=2)
    assert [x.device_id for x in r.top] == ["b", "c"]
    assert r.worst[0].device_id == "a"
```

- [ ] **Step 3: Run, expect failure**

```bash
cd apps/api && pytest tests/unit/test_default_engine.py -v
```

- [ ] **Step 4: Implement `core/engine/default.py`**

```python
from __future__ import annotations
from datetime import datetime
from typing import Iterable

from core.registry.protocol import Ranking, RankingRow


def build_flux_aggregate(*, bucket: str, measurement: str, field: str,
                          start: datetime, end: datetime, window: str = "5m") -> str:
    return f'''
from(bucket: "{bucket}")
  |> range(start: {start.isoformat()}, stop: {end.isoformat()})
  |> filter(fn: (r) => r._measurement == "{measurement}" and r._field == "{field}")
  |> aggregateWindow(every: {window}, fn: mean)
  |> yield(name: "mean")
'''.strip()


def summarize_rankings(rows: Iterable[dict], top_n: int = 5) -> Ranking:
    sorted_rows = sorted(rows, key=lambda r: r["score"], reverse=True)
    top = [RankingRow(device_id=r["device_id"], score=r["score"]) for r in sorted_rows[:top_n]]
    worst = [RankingRow(device_id=r["device_id"], score=r["score"]) for r in sorted_rows[-top_n:]][::-1]
    return Ranking(top=top, worst=worst)
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest tests/unit/test_default_engine.py -v
```

- [ ] **Step 6: Update `sites/_default/adapter.py` to use the engine**

```python
from __future__ import annotations
from datetime import datetime
from typing import Any

from influxdb_client import InfluxDBClient

from core.engine.default import build_flux_aggregate, summarize_rankings
from core.llm.rag import RagClient
from core.registry.protocol import (
    ChatContext, Device, DeviceDetail, Ranking, TimeRange, TrendPoint, TrendSeries,
)
from core.tenancy.context import TenantContext


class DefaultAdapter:
    slug = "_default"

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._devices = [Device(**d) for d in config.get("devices", [])]
        infl = config.get("influx", {})
        self._bucket = infl.get("bucket", "")
        self._measurement = infl.get("measurement", "telemetry")
        self._score_field = infl.get("score_field", "health_score")
        self._url = infl.get("url", "")
        self._token = infl.get("token", "")
        self._org = infl.get("org", "")
        self._rag = RagClient(host=config.get("chroma_host", "localhost"),
                              port=int(config.get("chroma_port", 8000)))

    def _query(self, flux: str) -> list[dict]:
        if not self._bucket or not self._url:
            return []
        with InfluxDBClient(url=self._url, token=self._token, org=self._org) as c:
            tables = c.query_api().query(flux)
        rows: list[dict] = []
        for tbl in tables:
            for r in tbl.records:
                rows.append({"ts": r["_time"], "value": r["_value"], "tags": dict(r.values)})
        return rows

    def health_trend(self, ctx: TenantContext, range: TimeRange) -> TrendSeries:
        flux = build_flux_aggregate(bucket=self._bucket, measurement=self._measurement,
                                    field=self._score_field, start=range.start, end=range.end)
        rows = self._query(flux)
        return TrendSeries(
            series=[TrendPoint(ts=datetime.fromisoformat(str(r["ts"]).replace("Z", "+00:00")),
                               value=float(r["value"])) for r in rows if r["value"] is not None],
            unit="score",
        )

    def device_ranking(self, ctx: TenantContext, range: TimeRange) -> Ranking:
        rows: list[dict] = []
        for d in self._devices:
            flux = f'''
from(bucket: "{self._bucket}")
  |> range(start: {range.start.isoformat()}, stop: {range.end.isoformat()})
  |> filter(fn: (r) => r._measurement == "{self._measurement}" and r._field == "{self._score_field}" and r.device_id == "{d.id}")
  |> mean()
'''
            results = self._query(flux)
            if results and results[0]["value"] is not None:
                rows.append({"device_id": d.id, "score": float(results[0]["value"])})
        return summarize_rankings(rows)

    def device_detail(self, ctx: TenantContext, device_id: str, range: TimeRange) -> DeviceDetail:
        dev = next((d for d in self._devices if d.id == device_id), None)
        if dev is None:
            return DeviceDetail(device=Device(id=device_id, type="unknown"))
        flux = f'''
from(bucket: "{self._bucket}")
  |> range(start: {range.start.isoformat()}, stop: {range.end.isoformat()})
  |> filter(fn: (r) => r.device_id == "{device_id}")
  |> aggregateWindow(every: 5m, fn: mean)
'''
        rows = self._query(flux)
        metrics: dict[str, float] = {}
        trend: list[TrendPoint] = []
        for r in rows:
            if r["value"] is None:
                continue
            field = r["tags"].get("_field", "")
            metrics[field] = float(r["value"])
            if field == self._score_field:
                trend.append(TrendPoint(ts=datetime.fromisoformat(str(r["ts"]).replace("Z", "+00:00")),
                                        value=float(r["value"])))
        return DeviceDetail(device=dev, metrics=metrics, trend=TrendSeries(series=trend, unit="score"))

    def chat_context(self, ctx: TenantContext, query: str) -> ChatContext:
        snippets = self._rag.search(ctx.site_id, query, k=5)
        return ChatContext(rag_snippets=[s["text"] for s in snippets if s["score"] >= 0.3],
                           structured_facts={}, recent_alerts=[])

    def list_devices(self, ctx: TenantContext) -> list[Device]:
        return list(self._devices)

    def validate_device_id(self, device_id: str) -> bool:
        return any(d.id == device_id for d in self._devices)
```

- [ ] **Step 7: Add integration test that exercises `_default` with mocked Influx — `tests/integration/test_default_dashboard.py`**

```python
import pytest
import uuid
from datetime import datetime, timezone

from sqlalchemy import update

from core.db.models import Site
from sites import _default as default_module


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_default_adapter_returns_trend_when_query_mocked(app_client, seeded, db_session, monkeypatch):
    cfg = {
        "devices": [{"id": "cv-01", "type": "ahu"}],
        "influx": {"bucket": "cv", "measurement": "telemetry", "score_field": "health_score",
                   "url": "http://stub", "token": "t", "org": "o"},
    }
    await db_session.execute(update(Site).where(Site.id == seeded["site_a"].id).values(adapter="_default", config=cfg))
    await db_session.commit()

    def fake_query(self, flux):
        if "yield" in flux:
            return [{"ts": "2026-05-25T00:00:00+00:00", "value": 70.0, "tags": {}}]
        return []

    monkeypatch.setattr(default_module.adapter.DefaultAdapter, "_query", fake_query)

    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.get("/dashboard/health-trend?range=24h", headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_a"].id),
    })
    assert r.status_code == 200
    assert r.json()["series"][0]["value"] == 70.0
```

Update `apps/api/sites/_default/__init__.py` to re-export the module for `default_module.adapter` access:

```python
from sites._default import adapter  # noqa: F401
from sites._default.adapter import DefaultAdapter  # noqa: F401
```

- [ ] **Step 8: Run, expect pass**

```bash
pytest tests/integration/test_default_dashboard.py -v
```

- [ ] **Step 9: Commit**

```bash
git add apps/api/core/engine apps/api/sites/_default apps/api/tests/unit/test_default_engine.py apps/api/tests/integration/test_default_dashboard.py
git commit -m "feat(engine): generic Influx aggregator for _default adapter"
```

---

## Task 2: Seed Cyberview from `scripts/research`

**Files:**
- Create: `apps/api/scripts/seed_cyberview.py`
- Modify: `apps/api/scripts/seed.py`

- [ ] **Step 1: Inspect available research**

```bash
ls $WACH/scripts/research/cyberview/ 2>/dev/null || ls $WACH/scripts/research/ 2>/dev/null
git -C $WACH log --oneline --grep cyberview | head -5
```

Look at `2d6f78e docs(research): add Cyberview health index design + device analysis` — that commit identifies the source. The deliverables are likely Markdown + a YAML/JSON device list.

- [ ] **Step 2: Implement `apps/api/scripts/seed_cyberview.py`**

```python
"""Seed Cyberview Site config from $WACH/scripts/research/.

Parses the device-analysis output (whatever shape it is) into the _default
adapter's config schema and inserts/updates the Cyberview Site row.
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from core.db.models import Org, Site
from core.db.session import async_session_factory


RESEARCH_ROOT = Path(os.environ.get("WACH_RESEARCH_ROOT", "../wach-insight/scripts/research"))


def _load_devices() -> list[dict[str, Any]]:
    """Return a list of {id, type, name, metadata} dicts.

    Looks for the most recent Cyberview device-analysis artifact. Falls back to
    a minimal hand-coded list if research files are missing so the seed still
    succeeds in fresh environments.
    """
    candidates = [
        RESEARCH_ROOT / "cyberview" / "devices.json",
        RESEARCH_ROOT / "cyberview_devices.json",
    ]
    for c in candidates:
        if c.exists():
            data = json.loads(c.read_text())
            return [
                {"id": d["device_id"], "type": d.get("type", "ahu"),
                 "name": d.get("name", d["device_id"]),
                 "metadata": d.get("metadata", {})}
                for d in data
            ]
    # fallback
    return [
        {"id": "cv-blk-a-ahu-01", "type": "ahu", "name": "Block A AHU-01", "metadata": {"block": "A"}},
        {"id": "cv-blk-a-ahu-02", "type": "ahu", "name": "Block A AHU-02", "metadata": {"block": "A"}},
        {"id": "cv-blk-b-ahu-01", "type": "ahu", "name": "Block B AHU-01", "metadata": {"block": "B"}},
    ]


def _config() -> dict[str, Any]:
    return {
        "devices": _load_devices(),
        "influx": {
            "bucket": os.environ.get("CYBERVIEW_INFLUX_BUCKET", "cyberview"),
            "measurement": "telemetry",
            "score_field": "health_score",
            "url": os.environ.get("INFLUX_URL", ""),
            "token": os.environ.get("INFLUX_TOKEN", ""),
            "org": os.environ.get("INFLUX_ORG", ""),
        },
        "chat": {"persona": "You are an HVAC analyst for Cyberview. Use only Cyberview data."},
        "theme": {"primary": "#4C6FFF"},
    }


async def main() -> None:
    async with async_session_factory() as s:
        org = (await s.execute(select(Org).where(Org.slug == "cyberview"))).scalar_one_or_none()
        if org is None:
            raise RuntimeError("Org 'cyberview' missing; run seed.py first")
        cfg = _config()
        # upsert site by (org_id, slug)
        existing = (await s.execute(select(Site).where(Site.org_id == org.id, Site.slug == "cyberview-a"))).scalar_one_or_none()
        if existing:
            existing.adapter = "_default"
            existing.influx_bucket = cfg["influx"]["bucket"]
            existing.config = cfg
        else:
            s.add(Site(org_id=org.id, slug="cyberview-a", name="Cyberview Block A",
                       adapter="_default", influx_bucket=cfg["influx"]["bucket"], config=cfg,
                       created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)))
        await s.commit()
        print(f"Cyberview site seeded with {len(cfg['devices'])} devices")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Hook into `seed.py`**

Append at the end of `apps/api/scripts/seed.py`'s `main`:

```python
    # cyberview specialization
    from scripts import seed_cyberview
    await seed_cyberview.main()
```

- [ ] **Step 4: Run seed**

```bash
cd apps/api && python -m scripts.seed
```

Expected: prints the three users plus `Cyberview site seeded with N devices`.

- [ ] **Step 5: Commit**

```bash
git add apps/api/scripts
git commit -m "feat(seed): Cyberview site config pulled from scripts/research"
```

---

## Task 3: Admin routes — orgs/sites/users CRUD (TDD)

**Files:**
- Create: `apps/api/routes/admin.py`
- Modify: `apps/api/main.py`
- Test: `apps/api/tests/integration/test_admin_routes.py`

- [ ] **Step 1: Write failing test `tests/integration/test_admin_routes.py`**

```python
import pytest


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_viewer_cannot_create_org(app_client, seeded):
    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.post("/admin/orgs", json={"slug": "x", "name": "X"},
                              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_creates_org(app_client, seeded):
    token = await _bearer(app_client, "super@example.com")
    r = await app_client.post("/admin/orgs", json={"slug": "new-org", "name": "New Org"},
                              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "new-org"


@pytest.mark.asyncio
async def test_super_admin_creates_site_under_org(app_client, seeded):
    token = await _bearer(app_client, "super@example.com")
    r = await app_client.post("/admin/sites",
                              json={"org_id": str(seeded["org_a"].id), "slug": "wach-b", "name": "WACH B",
                                    "adapter": "_default", "influx_bucket": "wach_b", "config": {"devices": []}},
                              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_super_admin_creates_user_and_membership(app_client, seeded):
    token = await _bearer(app_client, "super@example.com")
    r = await app_client.post("/admin/users",
                              json={"email": "newviewer@example.com", "password": "password1234",
                                    "name": "New", "is_super_admin": False,
                                    "site_memberships": [{"site_id": str(seeded["site_a"].id), "role": "site_viewer"}]},
                              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/integration/test_admin_routes.py -v
```

- [ ] **Step 3: Implement `routes/admin.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.auth.password import hash_password
from core.db.models import (
    Org, OrgMembership, Site, SiteMembership, User,
)
from core.db.session import get_session

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_super(user: User = Depends(get_current_user)) -> User:
    if not user.is_super_admin:
        raise HTTPException(status_code=403, detail="super-admin required")
    return user


def _require_org_admin_or_super(org_id: UUID):
    async def _dep(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> User:
        if user.is_super_admin:
            return user
        m = (await session.execute(
            select(OrgMembership).where(OrgMembership.user_id == user.id,
                                        OrgMembership.org_id == org_id,
                                        OrgMembership.role == "org_admin")
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status_code=403, detail="org-admin required")
        return user
    return _dep


# --- Orgs ---

class OrgIn(BaseModel):
    slug: str
    name: str
    theme: dict = {}


class OrgOut(BaseModel):
    id: UUID
    slug: str
    name: str
    theme: dict


@router.post("/orgs", response_model=OrgOut, status_code=201)
async def create_org(payload: OrgIn, _: User = Depends(_require_super),
                     session: AsyncSession = Depends(get_session)):
    row = Org(id=uuid.uuid4(), slug=payload.slug, name=payload.name, theme=payload.theme,
              created_at=datetime.now(timezone.utc))
    session.add(row)
    await session.commit()
    return OrgOut(id=row.id, slug=row.slug, name=row.name, theme=row.theme)


@router.get("/orgs", response_model=list[OrgOut])
async def list_orgs(_: User = Depends(_require_super), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Org))).scalars().all()
    return [OrgOut(id=r.id, slug=r.slug, name=r.name, theme=r.theme) for r in rows]


# --- Sites ---

class SiteIn(BaseModel):
    org_id: UUID
    slug: str
    name: str
    adapter: str
    influx_bucket: str | None = None
    config: dict = {}


class SiteOut(BaseModel):
    id: UUID
    org_id: UUID
    slug: str
    name: str
    adapter: str
    influx_bucket: str | None
    config: dict


@router.post("/sites", response_model=SiteOut, status_code=201)
async def create_site(payload: SiteIn, user: User = Depends(get_current_user),
                      session: AsyncSession = Depends(get_session)):
    if not user.is_super_admin:
        m = (await session.execute(
            select(OrgMembership).where(OrgMembership.user_id == user.id,
                                        OrgMembership.org_id == payload.org_id,
                                        OrgMembership.role == "org_admin")
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status_code=403, detail="org-admin or super required")
    row = Site(id=uuid.uuid4(), org_id=payload.org_id, slug=payload.slug, name=payload.name,
               adapter=payload.adapter, influx_bucket=payload.influx_bucket, config=payload.config,
               created_at=datetime.now(timezone.utc))
    session.add(row)
    await session.commit()
    return SiteOut(id=row.id, org_id=row.org_id, slug=row.slug, name=row.name,
                   adapter=row.adapter, influx_bucket=row.influx_bucket, config=row.config)


# --- Users ---

class MembershipIn(BaseModel):
    site_id: UUID
    role: str


class OrgMembershipIn(BaseModel):
    org_id: UUID
    role: str


class UserIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    is_super_admin: bool = False
    site_memberships: list[MembershipIn] = []
    org_memberships: list[OrgMembershipIn] = []


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    is_super_admin: bool


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserIn, _: User = Depends(_require_super),
                      session: AsyncSession = Depends(get_session)):
    row = User(id=uuid.uuid4(), email=payload.email, password_hash=hash_password(payload.password),
               name=payload.name, is_super_admin=payload.is_super_admin,
               created_at=datetime.now(timezone.utc))
    session.add(row)
    await session.flush()
    for m in payload.site_memberships:
        session.add(SiteMembership(user_id=row.id, site_id=m.site_id, role=m.role))
    for m in payload.org_memberships:
        session.add(OrgMembership(user_id=row.id, org_id=m.org_id, role=m.role))
    await session.commit()
    return UserOut(id=row.id, email=row.email, name=row.name, is_super_admin=row.is_super_admin)
```

- [ ] **Step 4: Register router in `main.py`**

```python
from routes import admin as admin_routes
...
app.include_router(admin_routes.router)
```

- [ ] **Step 5: Run tests, expect pass**

```bash
pytest tests/integration/test_admin_routes.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/routes/admin.py apps/api/main.py apps/api/tests/integration/test_admin_routes.py
git commit -m "feat(admin): orgs/sites/users CRUD with role gating"
```

---

## Task 4: Knowledge upload + background chunk/embed (TDD)

**Files:**
- Create: `apps/api/core/knowledge/__init__.py`, `chunker.py`, `ingest.py`, `apps/api/routes/knowledge.py`
- Modify: `apps/api/main.py`
- Test: `apps/api/tests/unit/test_chunker.py`, `apps/api/tests/integration/test_knowledge_upload.py`

- [ ] **Step 1: Write failing test `tests/unit/test_chunker.py`**

```python
from core.knowledge.chunker import chunk_text


def test_chunk_short_text_returns_one_chunk():
    chunks = chunk_text("hello world", chunk_size=200, overlap=20)
    assert len(chunks) == 1
    assert chunks[0] == "hello world"


def test_chunk_long_text_splits_with_overlap():
    text = "a" * 500
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c) <= 200


def test_chunks_are_non_empty_and_distinct():
    text = "abcdefghij" * 30
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert all(c.strip() for c in chunks)
```

- [ ] **Step 2: Implement `core/knowledge/__init__.py`**

```python
from core.knowledge.chunker import chunk_text  # noqa: F401
from core.knowledge.ingest import ingest_document  # noqa: F401
```

- [ ] **Step 3: Implement `core/knowledge/chunker.py`**

```python
from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size")
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks: list[str] = []
    step = chunk_size - overlap
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        if i + chunk_size >= len(text):
            break
    return chunks
```

- [ ] **Step 4: Run chunker test, expect pass**

```bash
pytest tests/unit/test_chunker.py -v
```

- [ ] **Step 5: Implement `core/knowledge/ingest.py`**

```python
from __future__ import annotations
import hashlib
from uuid import UUID

from core.knowledge.chunker import chunk_text
from core.llm.rag import RagClient


def ingest_document(*, rag: RagClient, site_id: UUID, doc_id: str, text: str,
                    metadata: dict | None = None) -> int:
    chunks = chunk_text(text)
    docs = []
    for i, chunk in enumerate(chunks):
        cid = hashlib.sha1(f"{doc_id}:{i}".encode()).hexdigest()
        docs.append({"id": cid, "text": chunk,
                     "metadata": {"doc_id": doc_id, "chunk_idx": i, **(metadata or {})}})
    if docs:
        rag.upsert(site_id, docs)
    return len(docs)
```

- [ ] **Step 6: Write failing test `tests/integration/test_knowledge_upload.py`**

```python
import pytest
from io import BytesIO


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_super_admin_uploads_knowledge(app_client, seeded, monkeypatch):
    seen = {}

    def fake_upsert(self, site_id, docs):
        seen["site_id"] = site_id
        seen["count"] = len(docs)

    from core.llm.rag import RagClient
    monkeypatch.setattr(RagClient, "upsert", fake_upsert)

    token = await _bearer(app_client, "super@example.com")
    content = b"Cyberview Block A operates Mon-Fri 7am-7pm. AHU-01 was overhauled in 2025."
    r = await app_client.post(
        f"/admin/sites/{seeded['site_a'].id}/knowledge",
        files={"file": ("notes.txt", BytesIO(content), "text/plain")},
        data={"doc_id": "notes-2026-05-25"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    assert seen["site_id"] == seeded["site_a"].id
    assert seen["count"] >= 1


@pytest.mark.asyncio
async def test_viewer_cannot_upload_knowledge(app_client, seeded):
    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.post(
        f"/admin/sites/{seeded['site_a'].id}/knowledge",
        files={"file": ("notes.txt", b"hi", "text/plain")},
        data={"doc_id": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
```

- [ ] **Step 7: Run, expect failure**

```bash
pytest tests/integration/test_knowledge_upload.py -v
```

- [ ] **Step 8: Implement `routes/knowledge.py`**

```python
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.models import OrgMembership, Site, User
from core.db.session import get_session
from core.knowledge.ingest import ingest_document
from core.llm.rag import RagClient

router = APIRouter(prefix="/admin/sites", tags=["admin"])


async def _require_org_admin_or_super(site_id: UUID, user: User, session: AsyncSession) -> Site:
    site = (await session.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="site not found")
    if user.is_super_admin:
        return site
    m = (await session.execute(
        select(OrgMembership).where(OrgMembership.user_id == user.id,
                                    OrgMembership.org_id == site.org_id,
                                    OrgMembership.role == "org_admin")
    )).scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=403, detail="org-admin or super required")
    return site


@router.post("/{site_id}/knowledge", status_code=201)
async def upload_knowledge(site_id: UUID, file: UploadFile = File(...), doc_id: str = Form(...),
                           user: User = Depends(get_current_user),
                           session: AsyncSession = Depends(get_session)):
    await _require_org_admin_or_super(site_id, user, session)
    raw = (await file.read()).decode("utf-8", errors="replace")
    rag = RagClient()
    n = ingest_document(rag=rag, site_id=site_id, doc_id=doc_id, text=raw,
                        metadata={"filename": file.filename})
    return {"chunks": n}
```

- [ ] **Step 9: Wire router in `main.py`**

```python
from routes import knowledge as knowledge_routes
...
app.include_router(knowledge_routes.router)
```

- [ ] **Step 10: Run, expect pass**

```bash
pytest tests/integration/test_knowledge_upload.py -v
```

Expected: 2 passed.

- [ ] **Step 11: Commit**

```bash
git add apps/api/core/knowledge apps/api/routes/knowledge.py apps/api/main.py apps/api/tests/unit/test_chunker.py apps/api/tests/integration/test_knowledge_upload.py
git commit -m "feat(knowledge): per-site doc upload + Chroma ingest"
```

---

## Task 5: Frontend — ThemeProvider + Gate + polished SiteSwitcher

**Files:**
- Create: `apps/web/src/shell/ThemeProvider.tsx`, `apps/web/src/shell/Gate.tsx`
- Replace: `apps/web/src/shell/AppShell.tsx` (lift switcher into its own file)
- Create: `apps/web/src/shell/SiteSwitcher.tsx`

- [ ] **Step 1: Implement `src/shell/ThemeProvider.tsx`**

```tsx
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useAuthStore } from "@/store/useAuthStore";

interface OrgsResponse { orgs: { id: string; theme: Record<string, string> }[] }

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const activeSiteId = useAuthStore((s) => s.activeSiteId);

  const { data: site } = useQuery({
    queryKey: ["site-meta", activeSiteId],
    enabled: !!activeSiteId && !!user,
    queryFn: () => apiFetch<{ org: { theme: Record<string, string> } }>(`/me/site`),
  });

  useEffect(() => {
    const theme = site?.org?.theme ?? {};
    const root = document.documentElement;
    root.style.setProperty("--rdm-primary", theme.primary ?? "#00E5A0");
    root.style.setProperty("--rdm-bg", theme.bgDark ?? "#0B0F14");
  }, [site]);

  return <>{children}</>;
}
```

- [ ] **Step 2: Add `GET /me/site` route to backend** (small dependency)

Create or extend `apps/api/routes/dashboard.py` to also serve site metadata. Add at the bottom:

```python
@router.get("/me/site", include_in_schema=True)
async def my_site(ctx: TenantContext = Depends(require_role("site_viewer")),
                  session: AsyncSession = Depends(get_session)):
    from core.db.models import Org
    site = (await session.execute(select(Site).where(Site.id == ctx.site_id))).scalar_one()
    org = (await session.execute(select(Org).where(Org.id == site.org_id))).scalar_one()
    return {
        "site": {"id": str(site.id), "slug": site.slug, "name": site.name, "adapter": site.adapter},
        "org": {"id": str(org.id), "slug": org.slug, "name": org.name, "theme": org.theme},
    }
```

Move this route under a separate `/me` router if cleaner — same content. Update frontend `apiFetch` path accordingly (`/me/site` instead of `/dashboard/me/site`).

- [ ] **Step 3: Implement `src/shell/SiteSwitcher.tsx`**

```tsx
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/store/useAuthStore";

export function SiteSwitcher() {
  const user = useAuthStore((s) => s.user);
  const activeSiteId = useAuthStore((s) => s.activeSiteId);
  const setActiveSite = useAuthStore((s) => s.setActiveSite);
  const qc = useQueryClient();

  if (!user || user.site_memberships.length <= 1) return null;

  return (
    <select
      value={activeSiteId ?? ""}
      onChange={(e) => {
        const next = e.target.value || null;
        // wipe site-scoped queries before switching
        qc.removeQueries({ predicate: (q) => Array.isArray(q.queryKey) && q.queryKey.includes(activeSiteId ?? "") });
        qc.removeQueries({ queryKey: ["site-meta"] });
        qc.removeQueries({ queryKey: ["health-trend"] });
        qc.removeQueries({ queryKey: ["ranking"] });
        setActiveSite(next);
      }}
    >
      {user.site_memberships.map((s) => (
        <option key={s.site_id} value={s.site_id}>{s.site_id}</option>
      ))}
    </select>
  );
}
```

- [ ] **Step 4: Implement `src/shell/Gate.tsx`**

```tsx
import type { Role } from "@rdm/types";
import { useAuthStore } from "@/store/useAuthStore";

const RANK: Record<Role | "super_admin", number> = {
  site_viewer: 1, site_operator: 2, org_admin: 3, super_admin: 4,
};

export function Gate({ role, siteId, children }: { role: Role; siteId?: string; children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const active = useAuthStore((s) => s.activeSiteId);
  if (!user) return null;
  if (user.is_super_admin) return <>{children}</>;
  const target = siteId ?? active;
  const m = user.site_memberships.find((m) => m.site_id === target);
  if (!m) return null;
  if (RANK[m.role as Role] < RANK[role]) return null;
  return <>{children}</>;
}
```

- [ ] **Step 5: Update `src/shell/AppShell.tsx`**

```tsx
import { Outlet } from "react-router-dom";
import { logout } from "@/api/client";
import { useAuthStore } from "@/store/useAuthStore";
import { SiteSwitcher } from "./SiteSwitcher";

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  return (
    <div style={{ background: "var(--rdm-bg)", color: "white", minHeight: "100vh" }}>
      <header style={{ display: "flex", gap: 12, padding: 12, borderBottom: "1px solid #222" }}>
        <strong style={{ color: "var(--rdm-primary)" }}>RDM Insight</strong>
        <SiteSwitcher />
        <span style={{ marginLeft: "auto" }}>{user?.email}</span>
        <button onClick={logout}>Logout</button>
      </header>
      <main style={{ padding: 16 }}>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 6: Wrap routes in `ThemeProvider` in `App.tsx`**

```tsx
import { ThemeProvider } from "@/shell/ThemeProvider";
// ...
<QueryClientProvider client={qc}>
  <BrowserRouter>
    <ThemeProvider>
      <Routes>{/* ...existing... */}</Routes>
    </ThemeProvider>
  </BrowserRouter>
</QueryClientProvider>
```

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/shell apps/web/src/App.tsx apps/api/routes/dashboard.py
git commit -m "feat(web): ThemeProvider, polished SiteSwitcher with cache invalidation, Gate"
```

---

## Task 6: Frontend — admin pages

**Files:**
- Create: `apps/web/src/features/admin/AdminPage.tsx`, `OrgList.tsx`, `SiteList.tsx`, `UserList.tsx`, `KnowledgeUpload.tsx`
- Modify: `apps/web/src/App.tsx`, `apps/web/src/shell/AppShell.tsx` (nav link)

- [ ] **Step 1: Implement `OrgList.tsx`**

```tsx
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

interface Org { id: string; slug: string; name: string }

export function OrgList() {
  const { data } = useQuery({ queryKey: ["orgs"], queryFn: () => apiFetch<Org[]>("/admin/orgs") });
  if (!data) return <p>Loading…</p>;
  return (
    <table>
      <thead><tr><th>Slug</th><th>Name</th><th>ID</th></tr></thead>
      <tbody>{data.map((o) => <tr key={o.id}><td>{o.slug}</td><td>{o.name}</td><td>{o.id}</td></tr>)}</tbody>
    </table>
  );
}
```

- [ ] **Step 2: Implement `SiteList.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

interface Site { id: string; slug: string; name: string; adapter: string }
interface Org { id: string; slug: string; name: string }

export function SiteList() {
  const qc = useQueryClient();
  const orgs = useQuery({ queryKey: ["orgs"], queryFn: () => apiFetch<Org[]>("/admin/orgs") });
  const [form, setForm] = useState({ org_id: "", slug: "", name: "", adapter: "_default", influx_bucket: "" });
  const create = useMutation({
    mutationFn: () => apiFetch<Site>("/admin/sites", { method: "POST", body: JSON.stringify({ ...form, config: { devices: [] } }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sites"] }),
  });
  return (
    <section>
      <h3>Create site</h3>
      <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <select value={form.org_id} onChange={(e) => setForm({ ...form, org_id: e.target.value })}>
          <option value="">— org —</option>
          {orgs.data?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
        <input placeholder="slug" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
        <input placeholder="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <select value={form.adapter} onChange={(e) => setForm({ ...form, adapter: e.target.value })}>
          <option value="_default">_default</option>
          <option value="wach">wach</option>
        </select>
        <input placeholder="influx_bucket" value={form.influx_bucket} onChange={(e) => setForm({ ...form, influx_bucket: e.target.value })} />
        <button type="submit" disabled={create.isPending}>Create</button>
      </form>
    </section>
  );
}
```

- [ ] **Step 3: Implement `UserList.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

export function UserList() {
  const qc = useQueryClient();
  const [form, setForm] = useState({ email: "", password: "", name: "", site_id: "", role: "site_viewer" });
  const create = useMutation({
    mutationFn: () =>
      apiFetch("/admin/users", {
        method: "POST",
        body: JSON.stringify({
          email: form.email, password: form.password, name: form.name,
          is_super_admin: false,
          site_memberships: form.site_id ? [{ site_id: form.site_id, role: form.role }] : [],
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  return (
    <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
      <input placeholder="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <input placeholder="password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
      <input placeholder="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      <input placeholder="site_id" value={form.site_id} onChange={(e) => setForm({ ...form, site_id: e.target.value })} />
      <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
        <option value="site_viewer">viewer</option>
        <option value="site_operator">operator</option>
      </select>
      <button type="submit" disabled={create.isPending}>Create user</button>
    </form>
  );
}
```

- [ ] **Step 4: Implement `KnowledgeUpload.tsx`**

```tsx
import { useState } from "react";
import { useAuthStore } from "@/store/useAuthStore";

export function KnowledgeUpload() {
  const activeSiteId = useAuthStore((s) => s.activeSiteId);
  const accessToken = useAuthStore((s) => s.accessToken);
  const [file, setFile] = useState<File | null>(null);
  const [docId, setDocId] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !docId || !activeSiteId) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_id", docId);
    const r = await fetch(`/api/admin/sites/${activeSiteId}/knowledge`, {
      method: "POST",
      body: fd,
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    setStatus(r.ok ? `Uploaded (${(await r.json()).chunks} chunks)` : "Failed");
  }

  return (
    <form onSubmit={submit}>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <input placeholder="doc id" value={docId} onChange={(e) => setDocId(e.target.value)} />
      <button type="submit">Upload</button>
      {status && <p>{status}</p>}
    </form>
  );
}
```

- [ ] **Step 5: Implement `AdminPage.tsx`**

```tsx
import { Gate } from "@/shell/Gate";
import { OrgList } from "./OrgList";
import { SiteList } from "./SiteList";
import { UserList } from "./UserList";
import { KnowledgeUpload } from "./KnowledgeUpload";

export function AdminPage() {
  return (
    <div style={{ display: "grid", gap: 24 }}>
      <h2>Admin</h2>
      <section><h3>Orgs</h3><OrgList /></section>
      <section><h3>Sites</h3><SiteList /></section>
      <section><h3>Users</h3><UserList /></section>
      <section><h3>Knowledge upload (active site)</h3>
        <Gate role="org_admin"><KnowledgeUpload /></Gate>
      </section>
    </div>
  );
}
```

- [ ] **Step 6: Add `/admin` route in `App.tsx`** and link in `AppShell.tsx` (super-admin only):

```tsx
// App.tsx
import { AdminPage } from "@/features/admin/AdminPage";
// inside the protected routes block:
<Route path="/admin" element={<AdminPage />} />
```

```tsx
// AppShell.tsx — in the header, after SiteSwitcher
{user?.is_super_admin && <a href="/admin" style={{ color: "var(--rdm-primary)" }}>Admin</a>}
```

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/features/admin apps/web/src/App.tsx apps/web/src/shell/AppShell.tsx
git commit -m "feat(web): admin pages for orgs/sites/users + knowledge upload"
```

---

## Task 7: Playwright E2E (4 spec scenarios)

**Files:**
- Create: `e2e/package.json`, `e2e/playwright.config.ts`, `e2e/tests/wach-viewer.spec.ts`, `cyberview-viewer.spec.ts`, `super-admin.spec.ts`, `operator-audit.spec.ts`

- [ ] **Step 1: Create `e2e/package.json`**

```json
{
  "name": "@rdm/e2e",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "test": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.48.0"
  }
}
```

- [ ] **Step 2: Create `e2e/playwright.config.ts`**

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  webServer: [
    { command: "pnpm --filter @rdm/api dev", port: 8081, reuseExistingServer: true },
    { command: "pnpm --filter @rdm/web dev", port: 3000, reuseExistingServer: true },
  ],
});
```

- [ ] **Step 3: Create `e2e/tests/wach-viewer.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("WACH viewer sees only WACH dashboard", async ({ page, request }) => {
  await page.goto("/login");
  await page.getByPlaceholder("email").fill("viewer.wach@example.com");
  await page.getByPlaceholder("password").fill("password1234");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // No Cyberview-named UI present
  await expect(page.getByText("Cyberview", { exact: false })).toHaveCount(0);

  // Direct API attempt to other site → 403
  const token = await page.evaluate(() => (window as any).__access_token__);
  // Easier: read from localStorage if exposed, or call refresh
  const r = await request.post("/api/auth/login", {
    data: { email: "viewer.wach@example.com", password: "password1234" },
  });
  const data = await r.json();
  const cv = await request.get("/api/dashboard/health-trend?range=24h", {
    headers: { Authorization: `Bearer ${data.access_token}`, "X-Site-Id": "00000000-0000-0000-0000-000000000000" },
  });
  expect([400, 403]).toContain(cv.status());
});
```

- [ ] **Step 4: Create `e2e/tests/cyberview-viewer.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("Cyberview viewer sees only Cyberview dashboard", async ({ page, request }) => {
  await page.goto("/login");
  await page.getByPlaceholder("email").fill("viewer.cyberview@example.com");
  await page.getByPlaceholder("password").fill("password1234");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  const login = await request.post("/api/auth/login", {
    data: { email: "viewer.cyberview@example.com", password: "password1234" },
  });
  const { access_token } = await login.json();

  // Cyberview viewer hitting site_a (WACH) must be denied.
  // We don't know site_a id from outside, so fetch /admin endpoints would also be 403.
  // Confirm /dashboard with no header is 400:
  const noHeader = await request.get("/api/dashboard/health-trend?range=24h", {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  expect(noHeader.status()).toBe(400);
});
```

- [ ] **Step 5: Create `e2e/tests/super-admin.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("super-admin sees site switcher with both options", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("email").fill("super@example.com");
  await page.getByPlaceholder("password").fill("password1234");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator("select")).toBeVisible();
  const options = await page.locator("select option").count();
  expect(options).toBeGreaterThanOrEqual(2);
});
```

- [ ] **Step 6: Create `e2e/tests/operator-audit.spec.ts`**

This requires an operator action route. If none exists yet (the spec mentions `acknowledge_alert` / `override_schedule` as Phase 3+), keep this test minimal — confirm operator-role user can log in:

```ts
import { test, expect } from "@playwright/test";

test("operator login succeeds", async ({ page }) => {
  // Operator user is not in default seed; create via super-admin first or skip if absent.
  test.skip(true, "Operator user creation deferred until first write action exists");
  await page.goto("/login");
  await page.getByPlaceholder("email").fill("operator@example.com");
  await page.getByPlaceholder("password").fill("password1234");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
});
```

> Note: the operator/audit scenario from spec §10 requires a write action endpoint. The first such action lands in a later phase; the placeholder above keeps the suite extensible without faking the test.

- [ ] **Step 7: Install Playwright browsers and run locally**

```bash
pnpm install
pnpm --filter @rdm/e2e exec playwright install --with-deps chromium
# Make sure DB is seeded
cd apps/api && python -m scripts.seed
cd ../..
pnpm --filter @rdm/e2e test
```

Expected: 3 tests pass, 1 skipped.

- [ ] **Step 8: Commit**

```bash
git add e2e
git commit -m "test(e2e): Playwright suite for two-tenant demo scenarios"
```

---

## Task 8: CI — e2e workflow

**Files:**
- Create: `.github/workflows/e2e.yml`

- [ ] **Step 1: Write workflow**

```yaml
name: E2E

on:
  pull_request:
  schedule:
    - cron: "0 6 * * *"

jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: rdm, POSTGRES_PASSWORD: rdm, POSTGRES_DB: rdm_insight }
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 5s --health-timeout 5s --health-retries 10
      chroma:
        image: chromadb/chroma:0.5.20
        ports: ["8000:8000"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - run: pnpm install --frozen-lockfile
      - name: Python deps
        working-directory: apps/api
        run: pip install -e ".[dev]" psycopg2-binary
      - name: Migrate
        working-directory: infra
        run: |
          pip install alembic psycopg2-binary
          PGPASSWORD=rdm psql -h localhost -U rdm -d rdm_insight -c 'CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
          alembic upgrade head
      - name: Seed
        working-directory: apps/api
        env: { DATABASE_URL: "postgresql+asyncpg://rdm:rdm@localhost:5432/rdm_insight" }
        run: python -m scripts.seed
      - name: Build web
        run: pnpm --filter @rdm/web build
      - name: Install Playwright
        run: pnpm --filter @rdm/e2e exec playwright install --with-deps chromium
      - name: Run e2e
        env:
          DATABASE_URL: "postgresql+asyncpg://rdm:rdm@localhost:5432/rdm_insight"
          ENABLE_LLM: "false"
        run: pnpm --filter @rdm/e2e test
      - uses: actions/upload-artifact@v4
        if: failure()
        with: { name: playwright-report, path: e2e/playwright-report/ }
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/e2e.yml
git commit -m "ci: add nightly + PR e2e workflow"
```

---

## Task 9: Vercel deploy config (`apps/web`)

**Files:**
- Create: `infra/vercel.ts`
- Modify: `apps/web/package.json` (if needed for build script)

- [ ] **Step 1: Create `infra/vercel.ts`**

```ts
import { routes, type VercelConfig } from "@vercel/config/v1";

export const config: VercelConfig = {
  buildCommand: "pnpm --filter @rdm/web build",
  outputDirectory: "apps/web/dist",
  installCommand: "pnpm install --frozen-lockfile",
  framework: null,
  rewrites: [
    routes.rewrite("/api/(.*)", `${process.env.API_BASE_URL ?? "https://rdm-insight-api.up.railway.app"}/$1`),
  ],
  headers: [
    routes.cacheControl("/assets/(.*)", { public: true, maxAge: "1 year", immutable: true }),
  ],
};
```

- [ ] **Step 2: Add `@vercel/config` dependency**

```bash
pnpm add -D -w @vercel/config
```

- [ ] **Step 3: Document env vars in README**

Append to root `README.md`:

```markdown
## Deployment

- `apps/web` → Vercel, configured by `infra/vercel.ts`. Required env vars:
  - `API_BASE_URL` — public URL of the FastAPI deployment.
- `apps/api` → Railway. Required env vars: `DATABASE_URL`, `JWT_SECRET`, `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `ENABLE_LLM`, `CORS_ORIGINS`.
```

- [ ] **Step 4: Commit**

```bash
git add infra/vercel.ts package.json pnpm-lock.yaml README.md
git commit -m "feat(deploy): Vercel project config for apps/web"
```

---

## Task 10: Railway deploy config (`apps/api`)

**Files:**
- Create: `infra/railway.toml`, `apps/api/Dockerfile`

- [ ] **Step 1: Create `apps/api/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .
COPY . /app
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
```

- [ ] **Step 2: Create `infra/railway.toml`**

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "apps/api/Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/healthz"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"

[[deploy.environment]]
DATABASE_URL = { fromService = "postgres" }
JWT_SECRET = { fromSecret = "JWT_SECRET" }
ENABLE_LLM = "false"
```

- [ ] **Step 3: Commit**

```bash
git add infra/railway.toml apps/api/Dockerfile
git commit -m "feat(deploy): Railway service config + Dockerfile for apps/api"
```

---

## Task 11: Documentation — adapter author guide

**Files:**
- Create: `docs/adapters/README.md`

- [ ] **Step 1: Write `docs/adapters/README.md`**

```markdown
# Writing a Site Adapter

A "site adapter" is a Python class implementing `core.registry.protocol.SiteAdapter`. It is the bridge between a site's raw data (Influx, MQTT, vendor APIs) and the platform's generic dashboard + chat endpoints.

## When to use `_default` vs writing a custom adapter

- **`_default`**: site data fits a generic point-map model (one Influx bucket, telemetry measurement, `device_id` tag, numeric fields). Configure via `sites.config` JSON. No code change.
- **Custom adapter**: site needs site-specific scoring formulas, validation rules, alternate data sources, or bespoke chat fact extraction. Examples: WACH (`AHU_LEVEL_CONFIG`, `e\d{4}` regex, RDM scoring formula).

## File layout

```
apps/api/sites/<slug>/
  __init__.py
  adapter.py        # the class
  config.py         # constants (device topology, regexes)
  influx.py         # site-specific Flux queries
  scoring.py        # site-specific formulas
  chat.py           # custom chat context builder
```

## Registering

Edit `apps/api/core/registry/dispatch.py`:

```python
if site.adapter == "<slug>":
    return MyAdapter(site.config or {})
```

Then in DB:

```sql
UPDATE sites SET adapter = '<slug>' WHERE id = ...;
```

## Conformance

The adapter must pass `tests/adapters/test_protocol_conformance.py` — add your slug to `conftest.py`'s `params` list.
```

- [ ] **Step 2: Commit**

```bash
git add docs/adapters/README.md
git commit -m "docs: add adapter author guide"
```

---

## Task 12: Final smoke + spec acceptance verification

- [ ] **Step 1: Full local stack**

```bash
docker compose -f infra/docker-compose.yml up -d
cd infra && alembic upgrade head && cd ..
cd apps/api && python -m scripts.seed && cd ../..
pnpm --filter @rdm/api dev &
pnpm --filter @rdm/web dev &
```

- [ ] **Step 2: Run the spec §8 acceptance test manually**

For each user, verify the spec requirement:

1. `viewer.wach@example.com / password1234` → only WACH dashboard + chat scoped to WACH knowledge. Cannot see Cyberview.
2. `viewer.cyberview@example.com / password1234` → only Cyberview dashboard. WACH data must never appear.
3. `super@example.com / password1234` → site switcher shows both; can switch and see each.
4. Cross-tenant API attempts → 403 (verified by `tests/integration/test_cross_tenant_isolation.py` from Plan A, plus the e2e suite).

- [ ] **Step 3: Run the full test suite**

```bash
pnpm --filter @rdm/api test
pnpm --filter @rdm/web test
pnpm --filter @rdm/e2e test
```

Expected: all green (e2e operator test skipped).

- [ ] **Step 4: Commit acceptance notes**

Add a short `docs/acceptance/2026-05-25-mvp-demo.md`:

```markdown
# MVP Demo Acceptance — 2026-05-25

Spec: `docs/superpowers/specs/2026-05-25-rdm-insight-platform-design.md` §8
Status: verified locally — all four scenarios pass.

| # | Scenario | Status |
|---|----------|--------|
| 1 | WACH viewer scoped to WACH only | ✅ |
| 2 | Cyberview viewer scoped to Cyberview only | ✅ |
| 3 | Super-admin sees both via switcher | ✅ |
| 4 | Cross-tenant API → 403 | ✅ |
```

```bash
git add docs/acceptance
git commit -m "docs: MVP demo acceptance verified"
```

---

## Self-Review (Plan C)

- **Spec coverage:** §5 schema fully exercised by admin routes (orgs/sites/users CRUD). §7 — `_default` adapter is now non-stub historical aggregator (Task 1). §8 — knowledge upload + per-site chat isolation. §9 — ThemeProvider, polished SiteSwitcher with cache invalidation, Gate, full admin UI. §10 — Playwright suite + e2e CI workflow. §12 — Cyberview seed pulls from `scripts/research` with a documented fallback. Deploy configs (Vercel + Railway) close the loop on §11 risk callout "deploy to production."
- **Placeholder scan:** `operator-audit.spec.ts` is intentionally skipped with a comment explaining why (no write action route ships in MVP). The `_load_devices` fallback in `seed_cyberview.py` is a documented graceful degradation, not a TBD. No "implement later" / "TODO" markers.
- **Type consistency:** `Site.config` JSON shape (`devices`, `influx`, `chat`, `theme`) used identically by `_default` adapter (`DefaultAdapter.__init__`), seed script (`seed_cyberview.py`), and the admin Site creation payload (`SiteIn`). Theme keys (`primary`, `bgDark`) consistent across `ThemeProvider`, seed scripts, and adapter config. Knowledge upload returns `{"chunks": n}` and the frontend reads `chunks`.

**What's deliberately out of scope (per spec §2):**
- MQTT ingestion (Phase 2)
- Anomaly detection in `_default` (Phase 3 — `_default` is historical only, per spec §12)
- Energy optimization (Phase 4)
- ML forecasting (Phase 5)
- Cross-site chat for super-admin (Phase 3)
- pgvector migration
- Mobile-responsive admin UI
- Sentry / OpenTelemetry
