# RDM Insight — Multi-Tenant Building Intelligence Platform (Design)

**Status:** Draft — MVP scope (two-tenant demo)
**Date:** 2026-05-25
**Owner:** Jinendra Muraly
**Codename:** `rdm-insight`

---

## 1. Problem & Goal

WACH Insight is a single-site building health platform. The next product generalizes it: a multi-tenant SaaS for BMS/EMS-driven building intelligence that any RDM Asia site (WACH, Cyberview, future) can use. End users only ever see data for sites they are entitled to (a Cyberview user must never see WACH data).

**MVP goal — two-tenant demo:**

1. WACH user logs in → WACH dashboard + chat only.
2. Cyberview user logs in → Cyberview dashboard + chat only.
3. Super-admin (RDM Asia) sees both via a site switcher.
4. Cross-tenant API access → 403.

Optimization, anomaly detection, and ML forecasting are **out of scope** for the MVP. They are first-class concerns of the platform's later phases and are accommodated by the architecture below.

## 2. Non-Goals (MVP)

- MQTT/BMS ingestion implementation (middleware exists for Cyberview; integration is Phase 2).
- Automated analytics / trend detection engine (Phase 3).
- Energy optimization algorithms (Phase 4).
- ML forecasting models (Phase 5).
- Cross-site chat for super-admin (Phase 3).
- SSO, MFA, password reset, email verification.
- Billing / usage metering.
- Self-service site onboarding UX (super-admin provisions sites for MVP).
- Cyberview-specific Python adapter (Cyberview starts as `_default`).
- pgvector migration (ChromaDB stays).
- Production observability (Sentry, OpenTelemetry) — add when the first paying tenant onboards.

## 3. Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                    rdm-insight (Turborepo)                     │
│                                                                │
│  apps/web (Vite/React/Zustand)  ←──── browser, tenant-themed   │
│       │                                                        │
│       │  HTTPS + JWT (Authorization: Bearer)                   │
│       ▼                                                        │
│  apps/api (FastAPI)                                            │
│   ├─ core/        platform engine (auth, registry, dispatch)   │
│   ├─ sites/       per-site adapters: wach/, cyberview/, _default/│
│   ├─ chat/        RAG + Qwen orchestration                     │
│   └─ ingest/      MQTT consumer + Influx writer (later)        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
        │                    │                       │
        ▼                    ▼                       ▼
   Neon Postgres        InfluxDB Cloud         ChromaDB (per-site)
   (orgs/sites/         (telemetry, one        (RAG vectors,
    users/configs)       bucket per site)        site-scoped collections)

Deploy:  apps/web → Vercel    apps/api → Railway    LM Studio (Qwen) → operator workstation
```

**Request flow:** browser → `apps/web` → `/api/*` → FastAPI validates JWT → resolves `(user, org, site)` → dispatches to site adapter (or `_default` engine) → reads Postgres/Influx/Chroma → response.

**Tenant boundary** enforced in two places:

1. JWT + tenant middleware injects `tenant_ctx` into request scope.
2. Every data-access function takes `tenant_ctx` as first argument and raises if missing.

## 4. Repository Layout

```
rdm-insight/
├── apps/
│   ├── web/                          # Vite + React + Zustand (ports WACH frontend)
│   │   ├── src/
│   │   │   ├── shell/                # tenant-aware layout, site switcher, auth UI
│   │   │   ├── features/
│   │   │   │   ├── dashboard/        # generic dashboard reading site config
│   │   │   │   ├── chat/             # multi-site chat panel
│   │   │   │   └── admin/            # org/site/user mgmt
│   │   │   ├── store/                # Zustand: auth, tenantCtx, dashboardState
│   │   │   └── api/                  # typed API client (shares types from packages/types)
│   │   └── package.json
│   │
│   └── api/                          # FastAPI
│       ├── core/
│       │   ├── auth/                 # JWT, session, RBAC
│       │   ├── tenancy/              # OrgService, SiteService, TenantContext
│       │   ├── registry/             # site registry loader, adapter dispatch
│       │   └── engine/               # default scoring/anomaly engine
│       ├── sites/
│       │   ├── _default/             # generic engine adapter
│       │   ├── wach/                 # ports core/, rag/, llm/ from WACH
│       │   └── cyberview/            # placeholder; uses _default + JSON config
│       ├── chat/                     # RAG + Qwen wrapper (site-scoped)
│       ├── ingest/                   # MQTT consumer (placeholder for now)
│       ├── routes/                   # FastAPI routers: auth, dashboard, chat, admin
│       └── main.py
│
├── packages/
│   ├── types/                        # shared TS types (generated from Pydantic)
│   ├── ui/                           # shared React components (port WACH revamp pieces)
│   └── config/                       # eslint, tsconfig, tailwind preset
│
├── infra/
│   ├── migrations/                   # Alembic
│   ├── docker-compose.yml            # local: api + postgres + chroma
│   └── railway.json                  # Railway service config
│
├── docs/
│   ├── CONSTITUTION.md
│   ├── superpowers/
│   │   ├── specs/
│   │   └── plans/
│   └── adapters/                     # how to write a site adapter
│
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

- pnpm workspaces + Turborepo. Cache builds/tests across apps.
- `packages/types` generated from Pydantic models via `datamodel-code-generator`. Manual fallback if tooling is finicky early.
- `apps/api` is the only Python in the repo; everything else TypeScript.
- WACH frontend revamp pieces (ScoreCard, LevelSelectorBar, CombinedScoresChart) lift into `packages/ui` once tenant-agnostic.

## 5. Data Model (Postgres)

```sql
-- Tenancy
orgs
  id            uuid pk
  slug          text unique           -- 'wach', 'cyberview'
  name          text
  theme         jsonb                 -- brand colors, logo URL
  created_at    timestamptz

sites
  id            uuid pk
  org_id        uuid fk -> orgs
  slug          text                  -- 'wach-main', 'cyberview-block-a'
  name          text
  adapter       text                  -- 'wach' | 'cyberview' | '_default'
  influx_bucket text                  -- per-site Influx bucket
  config        jsonb                 -- point map, scoring weights, schedule, chat config
  created_at    timestamptz
  unique (org_id, slug)

-- Identity
users
  id              uuid pk
  email           citext unique
  password_hash   text                -- argon2id
  name            text
  is_super_admin  bool default false
  created_at      timestamptz

-- RBAC
org_memberships
  user_id  uuid fk -> users
  org_id   uuid fk -> orgs
  role     text                      -- 'org_admin'
  pk (user_id, org_id)

site_memberships
  user_id  uuid fk -> users
  site_id  uuid fk -> sites
  role     text                      -- 'site_viewer' | 'site_operator'
  pk (user_id, site_id)

-- Sessions
sessions
  id            uuid pk
  user_id       uuid fk -> users
  refresh_hash  text
  expires_at    timestamptz
  user_agent    text
  created_at    timestamptz

-- Audit (write actions only)
audit_log
  id          uuid pk
  user_id     uuid
  site_id     uuid null
  action      text                   -- 'override_schedule', 'acknowledge_alert'
  payload     jsonb
  created_at  timestamptz
```

**Tenant resolution** — single function `resolve_tenant_ctx(user, requested_site_id)`:

1. Super-admin → access any site.
2. `org_memberships.role = 'org_admin'` for the site's org → access.
3. `site_memberships` row exists → access with that role.
4. Else 403.

Application-layer enforcement only — no Postgres RLS for MVP. Consistency comes from every route depending on the same middleware-injected `tenant_ctx`.

**InfluxDB isolation:** one bucket per site (`sites.influx_bucket`). Adapter passes the bucket name into every Flux query. No tenant_id tag needed; the bucket is the boundary.

**ChromaDB isolation:** collection name `site:{site_id}`. Adapter scopes all RAG calls; orchestrator never queries any other collection.

## 6. Auth & Tenant Isolation

**Token model (self-hosted JWT):**

- Access token: 15 min, HS256, signed with `JWT_SECRET`. Claims:
  `sub`, `email`, `is_super_admin`, `org_memberships`, `site_memberships`, `exp`, `iat`.
- Refresh token: 30 days, opaque, stored hashed in `sessions.refresh_hash`. Rotates on use.
- Browser storage: access in memory (Zustand); refresh in `httpOnly; Secure; SameSite=Strict` cookie scoped to API origin.

**Auth endpoints:**

```
POST /auth/login    {email, password}        → access JWT + Set-Cookie refresh
POST /auth/refresh  (cookie auto-sent)       → rotates session, returns new access JWT
POST /auth/logout                            → invalidates session, clears cookie
```

Argon2id password hashing, minimum 12 characters, no rotation requirement. No email verification or password reset in MVP — super-admin creates accounts manually.

**Middleware chain (every `/api/*`):**

1. `auth_middleware` — verify JWT → `request.state.user`.
2. `tenant_middleware` — read `X-Site-Id` header or path param → `resolve_tenant_ctx` → `request.state.tenant_ctx` (or 403).
3. Route handler receives `tenant_ctx: TenantContext = Depends(get_tenant_ctx)`.

**RBAC at route level:**

```python
@router.post("/sites/{site_id}/override")
def override(ctx: TenantContext = Depends(require_role("site_operator"))):
    ...
```

`require_role` accepts the minimum role; super-admin and org-admin always pass.

**Frontend:**

- `useAuthStore` holds user, access token, active `siteId`.
- API client attaches `Authorization: Bearer …` and `X-Site-Id: …` on every call.
- On 401 → silent refresh; on refresh failure → redirect to login.
- Site switcher calls `setActiveSite(id)` → resets React Query cache for `['site', oldId]` keys and site-scoped Zustand slices.

**Cross-site leak protection:**

- No global "list all devices" endpoints — every data endpoint requires `site_id`.
- Background jobs (later) carry explicit `site_id` in payload.
- Cross-tenant test suite (see §10) asserts 403 on every site-scoped route when caller lacks access.

## 7. Site Adapter Contract

```python
# apps/api/core/registry/protocol.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class SiteAdapter(Protocol):
    slug: str                          # 'wach', 'cyberview', '_default'

    # Dashboard
    def health_trend(self, ctx: TenantContext, range: TimeRange) -> TrendSeries: ...
    def device_ranking(self, ctx: TenantContext, range: TimeRange) -> Ranking: ...
    def device_detail(self, ctx: TenantContext, device_id: str, range: TimeRange) -> DeviceDetail: ...

    # Chat
    def chat_context(self, ctx: TenantContext, query: str) -> ChatContext: ...
    # returns: relevant_devices, recent_alerts, rag_snippets, sql_facts

    # Metadata
    def list_devices(self, ctx: TenantContext) -> list[Device]: ...
    def validate_device_id(self, device_id: str) -> bool: ...
```

**Dispatch:**

```python
# apps/api/core/registry/dispatch.py
def get_adapter(site: Site) -> SiteAdapter:
    if site.adapter == "wach":     return WachAdapter(site.config)
    if site.adapter == "_default": return DefaultAdapter(site.config)
    raise UnknownAdapter(site.adapter)
```

**`_default` adapter** — reads `site.config` JSONB:

```json
{
  "devices": [{"id": "ahu-01", "type": "ahu", "points": {...}}],
  "scoring": {"weights": {"energy": 0.4, "fault": 0.6}, "thresholds": {...}},
  "influx": {"measurement": "telemetry", "tags": {"site": "cyberview"}}
}
```

Generic Flux query templates parameterized by point map; generic scoring engine consumes weights + thresholds. No site-specific Python required.

**`wach` adapter** — ports `backend/core/`, `backend/llm/`, `backend/rag/` from WACH Insight into `apps/api/sites/wach/`. Hardcodes WACH-specific logic (`AHU_LEVEL_CONFIG`, `e\d{4}` validation, RDM scoring formulas). Implements the same protocol.

**Onboarding a new site (config-driven path):**

1. `INSERT INTO sites (org_id, slug, adapter='_default', influx_bucket, config=…)`.
2. Create Influx bucket.
3. (Later) load knowledge docs into ChromaDB collection `site:{site_id}`.
4. No code change, no deploy.

**Onboarding a site that needs custom logic:**

1. Create `apps/api/sites/<slug>/adapter.py` implementing the protocol.
2. Register in `dispatch.get_adapter`.
3. Set `sites.adapter = '<slug>'`.
4. Deploy.

## 8. Chatbot Architecture

```
User in apps/web  → POST /api/chat  {message, site_id (X-Site-Id)}
                          │
                          ▼
        ┌────────────────────────────────────────┐
        │  chat/orchestrator.py                  │
        │  1. tenant_ctx resolved                │
        │  2. adapter = get_adapter(site)        │
        │  3. context = adapter.chat_context(    │
        │       ctx, query)                      │
        │     ├─ rag.search(collection=          │
        │     │    f"site:{site.id}", k=5)       │
        │     ├─ recent_alerts(ctx, since=24h)   │
        │     └─ structured_facts(ctx, query)    │
        │  4. prompt = build_prompt(             │
        │       system=site.config.chat.persona, │
        │       context, history)                │
        │  5. llm.stream(prompt)                 │
        │  6. log to audit_log if write intent   │
        └────────────────────────────────────────┘
                          │
                          ▼
              Qwen via LM Studio (localhost:1234)
              ENABLE_LLM flag → rule-based parser fallback
```

**Per-site `sites.config.chat`:**

```json
{
  "persona": "You are an HVAC analyst for {{site_name}}…",
  "rag": {"enabled": true, "k": 5, "min_score": 0.3},
  "tools": ["health_trend", "device_detail", "recent_alerts"],
  "guardrails": {"scope": "site", "refuse_cross_site": true}
}
```

**Tenant isolation in chat:**

- ChromaDB query **always** filtered by `collection = f"site:{site_id}"`. No fallback across collections.
- Structured facts (SQL/Influx) reach the LLM only via the adapter, which only sees its own `ctx`.
- LLM prompt never includes other sites' data — enforced by construction, not LLM behavior.
- Super-admin cross-site chat is a separate post-MVP endpoint (`/api/chat/cross-site`) with a distinct code path.

**Streaming:** server-sent events via FastAPI `StreamingResponse`; frontend uses fetch + ReadableStream (POST). Token-by-token render in `features/chat/MessageStream.tsx`.

**RAG ingestion (per site):**

- Site admin uploads docs via admin UI → `POST /api/admin/sites/{id}/knowledge`.
- Background task: chunk → embed (sentence-transformers, same as WACH) → upsert to `site:{site_id}`.
- MVP: WACH collection pre-seeded from existing WACH Chroma dump. Cyberview collection empty (chat answers from structured data only until docs upload).

**LLM fallback (`ENABLE_LLM=false`):** existing WACH rule-based intent parser ported. Each adapter must provide intent handlers for the demo path: "what's the worst AHU", "show energy for level 5", etc.

## 9. Frontend Shell

```
apps/web/src/
├── shell/
│   ├── AppShell.tsx              # auth gate, top bar, site switcher, theme provider
│   ├── SiteSwitcher.tsx          # reads useAuthStore.memberships, sets activeSiteId
│   ├── ThemeProvider.tsx         # consumes org.theme (colors, logo)
│   └── routes.tsx                # protected routes, role-gated nav
├── features/
│   ├── dashboard/
│   │   ├── DashboardPage.tsx     # generic page; adapter response drives layout
│   │   ├── HealthTrend.tsx       # ported from WACH CombinedScoresChart
│   │   ├── DeviceRanking.tsx
│   │   └── DeviceDetail.tsx
│   ├── chat/
│   │   ├── ChatPanel.tsx         # streaming SSE
│   │   └── ChatHistory.tsx
│   └── admin/
│       ├── OrgList.tsx           # super-admin only
│       ├── SiteList.tsx          # super-admin + org-admin
│       ├── UserList.tsx
│       └── KnowledgeUpload.tsx   # per-site doc upload
└── store/
    ├── useAuthStore.ts           # user, tokens, memberships, activeSiteId
    ├── useTenantStore.ts         # cached site/org metadata
    └── useDashboardStore.ts      # date range, level filter, etc.
```

- **Theming.** `org.theme` JSONB: `{primary, accent, bgDark, logoUrl}`. `ThemeProvider` writes CSS variables to `:root`; Tailwind tokens reference `var(--primary)` etc. WACH theme = existing dark luxury (`#0B0F14` / `#00E5A0`); Cyberview gets its own palette.
- **Site switcher.** Top bar (when user has >1 site). On switch: clears site-scoped Zustand slices, resets React Query cache for `['site', oldId]` keys, updates `X-Site-Id`. Persists `activeSiteId` in `localStorage`.
- **Role gating.** `<Gate role="site_operator">` hides write actions for viewers. Admin nav appears only for `is_super_admin` or matching `org_admin`. Server is always source of truth; UI gating is UX only.
- **Auth pages.** `/login`, `/logout`. No signup or password reset in MVP.
- **Data fetching.** React Query for server state (new vs WACH), Zustand for client state. React Query's per-key invalidation cleanly handles site-switch cache resets.
- **Loading / error.** Skeleton components per panel (port from WACH). 403 on site access → "You don't have access to this site" + site switcher prompt. Generic `ErrorBoundary` at shell level.

## 10. Testing Strategy

**Backend (pytest, mirroring WACH conventions):**

- Unit: `core/auth`, `core/tenancy`, `core/registry`, default engine logic. In-memory SQLite for speed.
- Integration: real Postgres via testcontainers (or dockerized in CI). Auth flow, tenant middleware, adapter dispatch.
- **Cross-tenant isolation suite** (critical): parameterized test runs every site-scoped endpoint with a user from a different org → asserts 403. Catches new endpoints that forget the tenant check.
- Chat: mock LLM (no LM Studio in CI). Assert RAG query uses the correct collection name; assert prompt never contains other-site data.
- Adapter conformance: `tests/adapters/test_protocol.py` runs the same protocol-compliance suite against every registered adapter.

**Frontend (Jest + RTL, mirroring WACH):**

- Components in `packages/ui`, shell pieces (SiteSwitcher, Gate).
- Auth/tenant Zustand slice transitions.
- API client: mocked fetch, verify `Authorization` + `X-Site-Id` headers attached.
- React Query integration: site switch resets cached site-scoped queries.

**E2E (Playwright, minimum suite for MVP):**

1. WACH viewer login → dashboard loads → chat responds → cannot access Cyberview URL.
2. Cyberview viewer login → only Cyberview data visible.
3. Super-admin login → site switcher works, both sites accessible.
4. Operator override action → `audit_log` row written.

**CI** (`.github/workflows/`):

- `ci.yml`: pnpm install → turbo build → turbo lint → turbo typecheck → turbo test.
- `e2e.yml`: docker-compose + Playwright, on PR + nightly.
- Test DB seeded with fixture orgs/sites/users for deterministic runs.

**Coverage targets (soft):** backend 70% line, 100% on `core/auth` + `core/tenancy`; frontend 60% line.

**Not tested in MVP:** LM Studio behavior (mocked), real InfluxDB queries (mocked at adapter boundary; manual smoke via seeded WACH bucket), load/perf (defer until first real tenant onboards).

## 11. Risk Callouts

- **LM Studio dependency** = single-operator-machine bottleneck. Acceptable for the demo; cloud LLM via Vercel AI Gateway is the obvious next step once a tenant pays.
- **WACH adapter port** may surface coupling to WACH-specific globals (`AHU_LEVEL_CONFIG` imports, hardcoded device-ID regex). Budget refactor time during the port; some pieces lift cleanly, others need an interface seam first.
- **`packages/types` Pydantic → TS generation** with `datamodel-code-generator` can be finicky around generics and unions. Start manual if it stalls; revisit when the first 2–3 schema drifts cost more than the tooling setup.
- **Application-layer tenant isolation** (no Postgres RLS) means a missing `Depends(get_tenant_ctx)` on a new route is a security bug, not a 500. The cross-tenant isolation test suite (§10) is the safety net — keep it complete.

## 12. Resolved Decisions

- **`_default` adapter MVP scope:** historical aggregation only — `health_trend`, `device_ranking`, `device_detail` driven by `site.config` point map and Flux templates. No anomaly detection in `_default` for MVP; anomaly engine is a Phase 3 concern with its own design.
- **Cyberview seed data:** pull from existing `scripts/research` (Cyberview health index design + device analysis, commit `2d6f78e`). Build a `seed_cyberview.py` script that maps that research into the `_default` config schema. Fall back to fixtures only for fields the research does not cover.
- **Site routing:** `X-Site-Id` header for MVP. Tenant middleware reads the header and resolves `tenant_ctx`. Path-based variant (`/api/sites/{id}/…`) is deferred to Phase 2+ when a public API ships.

## 12b. Plan Review Fixes (applied 2026-05-26)

Applied to Plans A/B/C after first-pass review. All changes are in the committed plan files; this section is a quick audit trail.

| # | Issue | Fix |
|---|-------|-----|
| 1 | Missing operator user in seed | Added `operator.wach@example.com` with site_operator role on WACH site. E2E users (`viewer.wach`, `viewer.cyberview`, `super`) already present. |
| 2 | `vercel.ts` referenced non-existent `@vercel/config` | Replaced with `vercel.json` at repo root. |
| 3 | Scoring placeholder could ship silently | Plan B Task 2 marked `[BLOCKED until real formula inlined]`; CI grep guard fails build if the placeholder marker remains. |
| 4 | Blocking Influx/Chroma I/O on async loop | Adapter protocol methods made `async`; `sites/wach/influx.py` and `_default` adapter wrap all sync clients in `asyncio.to_thread`. |
| 5 | N+1 Influx queries in device_ranking | New `query_all_device_scores` (single grouped Flux) used by both `wach` and `_default` adapters. |
| 6 | Chat history dropped by frontend | `useChatStream.ts` now passes prior turns as `history`. |
| 7 | Missing indexes + role CHECK | Added `ix_sessions_refresh_hash`, `ix_site_memberships_site_id`, `ix_audit_log_*`, `ix_sites_org_id`, and CHECK constraints on `role` columns to `0001_init.py`. |
| 8 | Deprecated `event_loop` fixture | Removed; rely on `asyncio_mode = "auto"`. |
| 9 | SiteSwitcher shows raw UUIDs | Added `GET /me/sites` returning `{id, slug, name}`; switcher renders `name`. |
| 10 | ThemeProvider flash on first load | `:root` defaults in `apps/web/src/index.css` set synchronously before query resolves. |

## 13. Phase Roadmap (post-MVP)

| Phase | Focus                                  | Pulls in                                       |
|-------|----------------------------------------|------------------------------------------------|
| 2     | MQTT ingestion + Cyberview live data   | `apps/api/ingest/`, ingestion observability    |
| 3     | Automated analytics & trend detection  | Generic anomaly engine, cross-site super-admin chat |
| 4     | Energy optimization                    | Per-site profile, optimizer service            |
| 5     | ML forecasting                         | Training pipeline, model registry, batch infra |
