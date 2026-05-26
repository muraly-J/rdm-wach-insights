# RDM Insight — Plan A: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the multi-tenant platform skeleton — Turborepo monorepo, Postgres schema, JWT auth, tenant middleware, site adapter registry, and a stub `_default` adapter — so any future tenant work has a working chassis.

**Architecture:** pnpm + Turborepo monorepo. FastAPI backend (`apps/api`) with self-hosted JWT, application-layer tenant isolation, and adapter dispatch. Vite/React/Zustand frontend (`apps/web`) with protected routes and an API client that attaches `Authorization` + `X-Site-Id` headers. Postgres in Docker for local dev; InfluxDB and ChromaDB clients added but unused (Plan B exercises them).

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic + argon2-cffi + PyJWT; Node 20 + Vite + React 18 + Zustand + TanStack Query; pnpm 9 + Turborepo 2; Postgres 16; pytest + Jest + Playwright; GitHub Actions.

**Spec reference:** `docs/superpowers/specs/2026-05-25-rdm-insight-platform-design.md`

**Repository assumption:** A new repo `rdm-insight` is initialized at the start. All paths in this plan are relative to that repo root. If executing inside `wach-insight` for now, treat paths as relative to a sibling directory; create a worktree or branch as appropriate.

---

## File Structure

```
rdm-insight/
├── package.json                                  # root, pnpm workspaces
├── pnpm-workspace.yaml
├── turbo.json
├── .gitignore
├── .nvmrc                                        # 20
├── README.md
├── .github/workflows/ci.yml
├── infra/
│   ├── docker-compose.yml                        # postgres + chroma
│   ├── migrations/                               # Alembic env + versions
│   │   ├── env.py
│   │   └── versions/0001_init.py
│   └── alembic.ini
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── main.py                               # FastAPI app factory
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py                       # Pydantic settings
│   │   │   ├── db/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── session.py                    # async engine + Session dep
│   │   │   │   └── models.py                     # SQLAlchemy ORM models
│   │   │   ├── auth/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── password.py                   # argon2 hash/verify
│   │   │   │   ├── jwt.py                        # encode/decode access tokens
│   │   │   │   ├── sessions.py                   # refresh-token table helpers
│   │   │   │   ├── middleware.py                 # AuthenticationMiddleware
│   │   │   │   └── dependencies.py               # get_current_user
│   │   │   ├── tenancy/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── context.py                    # TenantContext dataclass
│   │   │   │   ├── service.py                    # resolve_tenant_ctx
│   │   │   │   ├── middleware.py                 # TenancyMiddleware
│   │   │   │   └── rbac.py                       # require_role dependency
│   │   │   ├── registry/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── protocol.py                   # SiteAdapter Protocol + DTOs
│   │   │   │   └── dispatch.py                   # get_adapter(site)
│   │   │   └── engine/
│   │   │       ├── __init__.py
│   │   │       └── default.py                    # default engine helpers (stubs)
│   │   ├── sites/
│   │   │   ├── __init__.py
│   │   │   └── _default/
│   │   │       ├── __init__.py
│   │   │       └── adapter.py                    # DefaultAdapter (stub returns)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                           # login/refresh/logout
│   │   │   ├── health.py                         # /healthz
│   │   │   └── dashboard.py                      # /sites/me, /dashboard/*
│   │   ├── scripts/
│   │   │   └── seed.py                           # demo org/site/users
│   │   └── tests/
│   │       ├── conftest.py                       # fixtures: db, client, users
│   │       ├── unit/
│   │       │   ├── test_password.py
│   │       │   ├── test_jwt.py
│   │       │   ├── test_resolve_tenant_ctx.py
│   │       │   ├── test_dispatch.py
│   │       │   └── test_default_adapter.py
│   │       ├── integration/
│   │       │   ├── test_auth_routes.py
│   │       │   ├── test_dashboard_routes.py
│   │       │   └── test_cross_tenant_isolation.py
│   │       └── README.md
│   └── web/
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── index.html
│       ├── src/
│       │   ├── main.tsx
│       │   ├── App.tsx
│       │   ├── shell/
│       │   │   ├── AppShell.tsx
│       │   │   ├── ProtectedRoute.tsx
│       │   │   └── LoginPage.tsx
│       │   ├── api/
│       │   │   └── client.ts                     # fetch wrapper with auth/site headers
│       │   ├── store/
│       │   │   └── useAuthStore.ts
│       │   └── pages/
│       │       └── DashboardStub.tsx
│       └── tests/
│           └── App.test.tsx
└── packages/
    └── types/
        ├── package.json
        ├── tsconfig.json
        └── src/index.ts                          # User, Org, Site, TenantContext, etc.
```

**Boundary notes:**
- `core/auth` knows nothing about tenancy. `core/tenancy` knows nothing about adapters. `core/registry` knows nothing about HTTP. This keeps the protocol layer testable without spinning up FastAPI.
- `sites/_default` is the only adapter in this plan. Plan B adds `sites/wach`.
- `packages/types` is hand-maintained in Plan A; Pydantic→TS codegen is a Plan C task.

---

## Task 1: Initialize monorepo root

**Files:**
- Create: `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `.gitignore`, `.nvmrc`, `README.md`

- [ ] **Step 1: Create `.nvmrc`**

```
20
```

- [ ] **Step 2: Create `pnpm-workspace.yaml`**

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 3: Create root `package.json`**

```json
{
  "name": "rdm-insight",
  "version": "0.0.0",
  "private": true,
  "packageManager": "pnpm@9.12.0",
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "lint": "turbo run lint",
    "typecheck": "turbo run typecheck",
    "test": "turbo run test"
  },
  "devDependencies": {
    "turbo": "^2.1.0"
  }
}
```

- [ ] **Step 4: Create `turbo.json`**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**", ".next/**"] },
    "dev": { "cache": false, "persistent": true },
    "lint": {},
    "typecheck": {},
    "test": { "dependsOn": ["^build"] }
  }
}
```

- [ ] **Step 5: Create `.gitignore`**

```
node_modules/
dist/
.turbo/
.venv/
__pycache__/
*.pyc
.env
.env.local
.DS_Store
.vscode/
.idea/
coverage/
playwright-report/
test-results/
```

- [ ] **Step 6: Create `README.md`**

```markdown
# RDM Insight

Multi-tenant building intelligence platform. See `docs/superpowers/specs/` for design.

## Local dev

```bash
nvm use
pnpm install
docker compose -f infra/docker-compose.yml up -d
pnpm --filter @rdm/api dev      # FastAPI on :8081
pnpm --filter @rdm/web dev      # Vite on :3000
```
```

- [ ] **Step 7: Initialize git + commit**

```bash
git init
git add .
git commit -m "chore: initialize monorepo skeleton"
```

---

## Task 2: Set up Docker compose for local infra

**Files:**
- Create: `infra/docker-compose.yml`

- [ ] **Step 1: Write `infra/docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: rdm
      POSTGRES_PASSWORD: rdm
      POSTGRES_DB: rdm_insight
    ports:
      - "5432:5432"
    volumes:
      - rdm_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rdm"]
      interval: 5s
      timeout: 5s
      retries: 5

  chroma:
    image: chromadb/chroma:0.5.20
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - rdm_chroma_data:/chroma/.chroma

volumes:
  rdm_pg_data:
  rdm_chroma_data:
```

- [ ] **Step 2: Start services and verify**

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps
```

Expected: both services `Up (healthy)` for postgres, `Up` for chroma.

- [ ] **Step 3: Commit**

```bash
git add infra/docker-compose.yml
git commit -m "chore(infra): add postgres + chroma compose"
```

---

## Task 3: Scaffold `apps/api` Python project

**Files:**
- Create: `apps/api/pyproject.toml`, `apps/api/main.py`, `apps/api/core/__init__.py`, `apps/api/core/settings.py`, `apps/api/package.json`

- [ ] **Step 1: Create `apps/api/pyproject.toml`**

```toml
[project]
name = "rdm-api"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "sqlalchemy[asyncio]==2.0.35",
    "asyncpg==0.29.0",
    "alembic==1.13.3",
    "pydantic==2.9.2",
    "pydantic-settings==2.5.2",
    "argon2-cffi==23.1.0",
    "pyjwt==2.9.0",
    "python-multipart==0.0.12",
    "httpx==0.27.2",
    "chromadb==0.5.20",
    "influxdb-client==1.46.0",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "pytest-cov==5.0.0",
    "ruff==0.6.9",
    "mypy==1.11.2",
    "testcontainers[postgres]==4.8.1",
    "freezegun==1.5.1",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: Create `apps/api/package.json` (Turborepo glue)**

```json
{
  "name": "@rdm/api",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "uvicorn main:app --reload --port 8081",
    "test": "pytest -v --cov=core --cov=routes --cov=sites",
    "lint": "ruff check .",
    "typecheck": "mypy core routes sites",
    "build": "python -c 'print(\"ok\")'"
  }
}
```

- [ ] **Step 3: Create `apps/api/core/settings.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://rdm:rdm@localhost:5432/rdm_insight"
    jwt_secret: str = "dev-change-me"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 60 * 60 * 24 * 30
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
```

- [ ] **Step 4: Create `apps/api/core/__init__.py`**

```python
```

- [ ] **Step 5: Create `apps/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(title="RDM Insight API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 6: Install dependencies and verify boot**

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn main:app --port 8081 &
sleep 1
curl -fsS http://localhost:8081/healthz
kill %1
```

Expected: `{"status":"ok"}`.

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat(api): scaffold FastAPI app with healthz"
```

---

## Task 4: Scaffold `apps/web` Vite project

**Files:**
- Create: `apps/web/package.json`, `apps/web/vite.config.ts`, `apps/web/tsconfig.json`, `apps/web/index.html`, `apps/web/src/main.tsx`, `apps/web/src/App.tsx`

- [ ] **Step 1: Create `apps/web/package.json`**

```json
{
  "name": "@rdm/web",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --port 3000",
    "build": "tsc -b && vite build",
    "preview": "vite preview --port 3000",
    "lint": "eslint src --ext ts,tsx --max-warnings 0",
    "typecheck": "tsc -b --noEmit",
    "test": "jest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.59.0",
    "@rdm/types": "workspace:*"
  },
  "devDependencies": {
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.0",
    "@types/jest": "^29.5.13",
    "@vitejs/plugin-react": "^4.3.2",
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.6.0",
    "eslint": "^9.12.0",
    "@typescript-eslint/eslint-plugin": "^8.8.0",
    "@typescript-eslint/parser": "^8.8.0",
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0",
    "ts-jest": "^29.2.5",
    "typescript": "^5.6.2",
    "vite": "^5.4.8"
  }
}
```

- [ ] **Step 2: Create `apps/web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 3: Create `apps/web/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 3000,
    proxy: {
      "/api": "http://localhost:8081",
    },
  },
});
```

- [ ] **Step 4: Create `apps/web/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RDM Insight</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `apps/web/src/App.tsx`**

```tsx
export default function App() {
  return <main>RDM Insight booting...</main>;
}
```

- [ ] **Step 6: Create `apps/web/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 7: Install, build, verify**

```bash
pnpm install
pnpm --filter @rdm/web build
```

Expected: `vite build` exits 0 and emits `apps/web/dist/index.html`.

- [ ] **Step 8: Commit**

```bash
git add apps/web pnpm-lock.yaml
git commit -m "feat(web): scaffold Vite + React + Zustand app"
```

---

## Task 5: Create `packages/types` shared TS types

**Files:**
- Create: `packages/types/package.json`, `packages/types/tsconfig.json`, `packages/types/src/index.ts`

- [ ] **Step 1: Create `packages/types/package.json`**

```json
{
  "name": "@rdm/types",
  "version": "0.0.0",
  "private": true,
  "main": "src/index.ts",
  "types": "src/index.ts",
  "scripts": {
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.6.2"
  }
}
```

- [ ] **Step 2: Create `packages/types/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "declaration": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create `packages/types/src/index.ts`**

```ts
export type Role = "site_viewer" | "site_operator" | "org_admin";

export interface OrgMembership {
  org_id: string;
  role: "org_admin";
}

export interface SiteMembership {
  site_id: string;
  role: "site_viewer" | "site_operator";
}

export interface User {
  id: string;
  email: string;
  name: string;
  is_super_admin: boolean;
  org_memberships: OrgMembership[];
  site_memberships: SiteMembership[];
}

export interface Org {
  id: string;
  slug: string;
  name: string;
  theme: Record<string, unknown>;
}

export interface Site {
  id: string;
  org_id: string;
  slug: string;
  name: string;
  adapter: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
}

export interface TenantContext {
  user_id: string;
  org_id: string;
  site_id: string;
  role: Role | "super_admin";
}
```

- [ ] **Step 4: Verify typecheck**

```bash
pnpm --filter @rdm/types typecheck
```

Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add packages/types
git commit -m "feat(types): add shared TS types package"
```

---

## Task 6: Alembic init + initial schema migration

**Files:**
- Create: `infra/alembic.ini`, `infra/migrations/env.py`, `infra/migrations/versions/0001_init.py`

- [ ] **Step 1: Create `infra/alembic.ini`**

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+psycopg2://rdm:rdm@localhost:5432/rdm_insight

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 2: Create `infra/migrations/env.py`**

```python
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
fileConfig(config.config_file_name)
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Create `infra/migrations/versions/0001_init.py`**

```python
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "orgs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("theme", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("adapter", sa.Text(), nullable=False),
        sa.Column("influx_bucket", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "slug", name="uq_sites_org_slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "org_memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "org_id"),
    )

    op.create_table(
        "site_memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "site_id"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Indexes for hot paths
    op.create_index("ix_sessions_refresh_hash", "sessions", ["refresh_hash"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_site_memberships_site_id", "site_memberships", ["site_id"])
    op.create_index("ix_org_memberships_org_id", "org_memberships", ["org_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_site_id", "audit_log", ["site_id"])
    op.create_index("ix_sites_org_id", "sites", ["org_id"])

    # CHECK constraints on role columns
    op.create_check_constraint("ck_org_memberships_role", "org_memberships", "role IN ('org_admin')")
    op.create_check_constraint("ck_site_memberships_role", "site_memberships",
                               "role IN ('site_viewer', 'site_operator')")


def downgrade() -> None:
    for t in ["audit_log", "sessions", "site_memberships", "org_memberships", "users", "sites", "orgs"]:
        op.drop_table(t)
```

- [ ] **Step 4: Install psycopg2-binary in api dev deps temporarily, run migration**

```bash
cd apps/api && pip install psycopg2-binary
cd ../../infra && alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade  -> 0001`.

- [ ] **Step 5: Verify schema**

```bash
psql postgresql://rdm:rdm@localhost:5432/rdm_insight -c "\dt"
```

Expected: 7 tables listed.

- [ ] **Step 6: Commit**

```bash
git add infra
git commit -m "feat(infra): initial Postgres schema migration"
```

---

## Task 7: SQLAlchemy ORM models

**Files:**
- Create: `apps/api/core/db/__init__.py`, `apps/api/core/db/models.py`, `apps/api/core/db/session.py`

- [ ] **Step 1: Create `apps/api/core/db/__init__.py`**

```python
from core.db.session import get_session, async_session_factory  # noqa: F401
from core.db.models import (  # noqa: F401
    Base, Org, Site, User, OrgMembership, SiteMembership, Session, AuditLog,
)
```

- [ ] **Step 2: Create `apps/api/core/db/models.py`**

```python
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID, CITEXT, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Org(Base):
    __tablename__ = "orgs"
    id: Mapped[uuid.UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    theme: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    sites: Mapped[list["Site"]] = relationship(back_populates="org")


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_sites_org_slug"),)
    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    adapter: Mapped[str] = mapped_column(Text, nullable=False)
    influx_bucket: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    org: Mapped[Org] = relationship(back_populates="sites")


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class OrgMembership(Base):
    __tablename__ = "org_memberships"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)


class SiteMembership(Base):
    __tablename__ = "site_memberships"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
```

- [ ] **Step 3: Create `apps/api/core/db/session.py`**

```python
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.settings import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 4: Smoke import in shell**

```bash
cd apps/api && python -c "from core.db import Org, Site, User; print('ok')"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add apps/api/core/db
git commit -m "feat(api): add SQLAlchemy models + async session"
```

---

## Task 8: Argon2 password hashing (TDD)

**Files:**
- Create: `apps/api/core/auth/__init__.py`, `apps/api/core/auth/password.py`
- Test: `apps/api/tests/unit/test_password.py`

- [ ] **Step 1: Write failing test `tests/unit/test_password.py`**

```python
from core.auth.password import hash_password, verify_password


def test_hash_password_returns_argon2_string():
    h = hash_password("hunter2hunter2")
    assert h.startswith("$argon2id$")


def test_verify_password_accepts_correct():
    h = hash_password("correctpassword!!")
    assert verify_password("correctpassword!!", h) is True


def test_verify_password_rejects_wrong():
    h = hash_password("correctpassword!!")
    assert verify_password("wrong", h) is False
```

- [ ] **Step 2: Run test, expect failure**

```bash
cd apps/api && pytest tests/unit/test_password.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.auth.password'`.

- [ ] **Step 3: Implement `core/auth/__init__.py`**

```python
```

- [ ] **Step 4: Implement `core/auth/password.py`**

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    if len(plain) < 12:
        raise ValueError("password must be at least 12 characters")
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False
```

- [ ] **Step 5: Run test, expect pass**

```bash
pytest tests/unit/test_password.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/core/auth apps/api/tests/unit/test_password.py
git commit -m "feat(auth): add argon2id password hashing"
```

---

## Task 9: JWT access-token utilities (TDD)

**Files:**
- Create: `apps/api/core/auth/jwt.py`
- Test: `apps/api/tests/unit/test_jwt.py`

- [ ] **Step 1: Write failing test `tests/unit/test_jwt.py`**

```python
from uuid import uuid4
from freezegun import freeze_time
import pytest

from core.auth.jwt import encode_access_token, decode_access_token, InvalidToken


def _claims():
    return {
        "sub": str(uuid4()),
        "email": "u@example.com",
        "is_super_admin": False,
        "org_memberships": [],
        "site_memberships": [],
    }


def test_encode_decode_roundtrip():
    c = _claims()
    token = encode_access_token(c)
    decoded = decode_access_token(token)
    assert decoded["sub"] == c["sub"]
    assert decoded["email"] == "u@example.com"


def test_expired_token_rejected():
    with freeze_time("2026-01-01 00:00:00"):
        token = encode_access_token(_claims())
    with freeze_time("2026-01-01 01:00:00"):
        with pytest.raises(InvalidToken):
            decode_access_token(token)


def test_tampered_token_rejected():
    token = encode_access_token(_claims()) + "x"
    with pytest.raises(InvalidToken):
        decode_access_token(token)
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/unit/test_jwt.py -v
```

Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `core/auth/jwt.py`**

```python
from datetime import datetime, timezone, timedelta
from typing import Any

import jwt as pyjwt

from core.settings import settings


class InvalidToken(Exception):
    pass


def encode_access_token(claims: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.jwt_access_ttl_seconds)).timestamp()),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return pyjwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except pyjwt.PyJWTError as e:
        raise InvalidToken(str(e)) from e
```

- [ ] **Step 4: Run test, expect pass**

```bash
pytest tests/unit/test_jwt.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/core/auth/jwt.py apps/api/tests/unit/test_jwt.py
git commit -m "feat(auth): add JWT access-token encode/decode"
```

---

## Task 10: Pytest fixtures (db, app, users)

**Files:**
- Create: `apps/api/tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import uuid
from datetime import datetime, timezone
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.db.models import Base, Org, Site, User, OrgMembership, SiteMembership
from core.auth.password import hash_password

# Note: pytest-asyncio >= 0.23 handles the event loop automatically via
# asyncio_mode = "auto" (set in pyproject.toml). Do not override event_loop.


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    url = "postgresql+asyncpg://rdm:rdm@localhost:5432/rdm_insight_test"
    engine = create_async_engine(url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def app_client(db_session):
    from main import create_app
    from core.db.session import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded(db_session) -> dict:
    now = datetime.now(timezone.utc)
    org_a = Org(id=uuid.uuid4(), slug="org-a", name="Org A", theme={}, created_at=now)
    org_b = Org(id=uuid.uuid4(), slug="org-b", name="Org B", theme={}, created_at=now)
    site_a = Site(id=uuid.uuid4(), org_id=org_a.id, slug="site-a", name="Site A",
                  adapter="_default", influx_bucket="bucket-a", config={}, created_at=now)
    site_b = Site(id=uuid.uuid4(), org_id=org_b.id, slug="site-b", name="Site B",
                  adapter="_default", influx_bucket="bucket-b", config={}, created_at=now)
    viewer = User(id=uuid.uuid4(), email="viewer.a@example.com", password_hash=hash_password("password1234"),
                  name="Viewer A", is_super_admin=False, created_at=now)
    operator = User(id=uuid.uuid4(), email="op.b@example.com", password_hash=hash_password("password1234"),
                    name="Op B", is_super_admin=False, created_at=now)
    superadmin = User(id=uuid.uuid4(), email="super@example.com", password_hash=hash_password("password1234"),
                      name="Super", is_super_admin=True, created_at=now)
    db_session.add_all([org_a, org_b, site_a, site_b, viewer, operator, superadmin])
    await db_session.flush()
    db_session.add_all([
        SiteMembership(user_id=viewer.id, site_id=site_a.id, role="site_viewer"),
        SiteMembership(user_id=operator.id, site_id=site_b.id, role="site_operator"),
    ])
    await db_session.commit()
    return {
        "org_a": org_a, "org_b": org_b, "site_a": site_a, "site_b": site_b,
        "viewer": viewer, "operator": operator, "superadmin": superadmin,
    }
```

- [ ] **Step 2: Create the test database**

```bash
psql postgresql://rdm:rdm@localhost:5432/postgres -c "CREATE DATABASE rdm_insight_test;"
psql postgresql://rdm:rdm@localhost:5432/rdm_insight_test -c "CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
```

Expected: `CREATE DATABASE` then `CREATE EXTENSION` x2.

- [ ] **Step 3: Smoke the fixture**

Add temporary `tests/unit/test_fixture_smoke.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_seeded_smoke(seeded):
    assert seeded["site_a"].slug == "site-a"
    assert seeded["viewer"].email == "viewer.a@example.com"
```

Run:

```bash
pytest tests/unit/test_fixture_smoke.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Delete the smoke test and commit fixtures**

```bash
rm tests/unit/test_fixture_smoke.py
git add tests/conftest.py
git commit -m "test(api): add db + app + seeded fixtures"
```

---

## Task 11: `resolve_tenant_ctx` service (TDD)

**Files:**
- Create: `apps/api/core/tenancy/__init__.py`, `apps/api/core/tenancy/context.py`, `apps/api/core/tenancy/service.py`
- Test: `apps/api/tests/unit/test_resolve_tenant_ctx.py`

- [ ] **Step 1: Write failing test `tests/unit/test_resolve_tenant_ctx.py`**

```python
import pytest

from core.tenancy.service import resolve_tenant_ctx, TenancyError


@pytest.mark.asyncio
async def test_super_admin_can_access_any_site(db_session, seeded):
    ctx = await resolve_tenant_ctx(db_session, user_id=seeded["superadmin"].id, site_id=seeded["site_b"].id)
    assert ctx.role == "super_admin"
    assert ctx.site_id == seeded["site_b"].id


@pytest.mark.asyncio
async def test_site_viewer_access_to_own_site(db_session, seeded):
    ctx = await resolve_tenant_ctx(db_session, user_id=seeded["viewer"].id, site_id=seeded["site_a"].id)
    assert ctx.role == "site_viewer"


@pytest.mark.asyncio
async def test_viewer_denied_other_org_site(db_session, seeded):
    with pytest.raises(TenancyError):
        await resolve_tenant_ctx(db_session, user_id=seeded["viewer"].id, site_id=seeded["site_b"].id)


@pytest.mark.asyncio
async def test_operator_role_returned(db_session, seeded):
    ctx = await resolve_tenant_ctx(db_session, user_id=seeded["operator"].id, site_id=seeded["site_b"].id)
    assert ctx.role == "site_operator"
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/unit/test_resolve_tenant_ctx.py -v
```

Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `core/tenancy/__init__.py`**

```python
from core.tenancy.context import TenantContext  # noqa: F401
from core.tenancy.service import resolve_tenant_ctx, TenancyError  # noqa: F401
```

- [ ] **Step 4: Implement `core/tenancy/context.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID
from typing import Literal

Role = Literal["super_admin", "org_admin", "site_operator", "site_viewer"]


@dataclass(frozen=True)
class TenantContext:
    user_id: UUID
    org_id: UUID
    site_id: UUID
    role: Role
```

- [ ] **Step 5: Implement `core/tenancy/service.py`**

```python
from __future__ import annotations
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import Site, User, OrgMembership, SiteMembership
from core.tenancy.context import TenantContext


class TenancyError(Exception):
    pass


async def resolve_tenant_ctx(session: AsyncSession, *, user_id: UUID, site_id: UUID) -> TenantContext:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise TenancyError("unknown user")
    site = (await session.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
    if site is None:
        raise TenancyError("unknown site")

    if user.is_super_admin:
        return TenantContext(user_id=user.id, org_id=site.org_id, site_id=site.id, role="super_admin")

    org_role = (await session.execute(
        select(OrgMembership).where(OrgMembership.user_id == user.id, OrgMembership.org_id == site.org_id)
    )).scalar_one_or_none()
    if org_role is not None:
        return TenantContext(user_id=user.id, org_id=site.org_id, site_id=site.id, role="org_admin")

    site_role = (await session.execute(
        select(SiteMembership).where(SiteMembership.user_id == user.id, SiteMembership.site_id == site.id)
    )).scalar_one_or_none()
    if site_role is not None:
        return TenantContext(user_id=user.id, org_id=site.org_id, site_id=site.id, role=site_role.role)

    raise TenancyError("forbidden")
```

- [ ] **Step 6: Run test, expect pass**

```bash
pytest tests/unit/test_resolve_tenant_ctx.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/core/tenancy apps/api/tests/unit/test_resolve_tenant_ctx.py
git commit -m "feat(tenancy): add resolve_tenant_ctx with super/org/site rules"
```

---

## Task 12: Sessions table helpers + refresh-token rotation

**Files:**
- Create: `apps/api/core/auth/sessions.py`
- Test: `apps/api/tests/unit/test_sessions.py`

- [ ] **Step 1: Write failing test `tests/unit/test_sessions.py`**

```python
import pytest

from core.auth.sessions import create_session, rotate_session, revoke_session, find_session_by_refresh
from core.db.models import User
from datetime import datetime, timezone
import uuid


@pytest.mark.asyncio
async def test_create_and_find_session(db_session):
    user = User(id=uuid.uuid4(), email="s@example.com", password_hash="x", name="S",
                is_super_admin=False, created_at=datetime.now(timezone.utc))
    db_session.add(user)
    await db_session.commit()

    refresh = await create_session(db_session, user_id=user.id, user_agent="pytest")
    found = await find_session_by_refresh(db_session, refresh)
    assert found is not None and found.user_id == user.id


@pytest.mark.asyncio
async def test_rotate_session_invalidates_old(db_session):
    user = User(id=uuid.uuid4(), email="r@example.com", password_hash="x", name="R",
                is_super_admin=False, created_at=datetime.now(timezone.utc))
    db_session.add(user)
    await db_session.commit()
    old = await create_session(db_session, user_id=user.id, user_agent=None)
    new = await rotate_session(db_session, old_refresh=old)
    assert new != old
    assert await find_session_by_refresh(db_session, old) is None
    assert await find_session_by_refresh(db_session, new) is not None
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/unit/test_sessions.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `core/auth/sessions.py`**

```python
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import Session as SessionRow
from core.settings import settings


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_session(session: AsyncSession, *, user_id: UUID, user_agent: str | None) -> str:
    raw = secrets.token_urlsafe(48)
    row = SessionRow(
        id=uuid4(),
        user_id=user_id,
        refresh_hash=_hash(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    await session.commit()
    return raw


async def find_session_by_refresh(session: AsyncSession, raw: str) -> SessionRow | None:
    result = await session.execute(select(SessionRow).where(SessionRow.refresh_hash == _hash(raw)))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at < datetime.now(timezone.utc):
        return None
    return row


async def rotate_session(session: AsyncSession, *, old_refresh: str) -> str:
    row = await find_session_by_refresh(session, old_refresh)
    if row is None:
        raise ValueError("invalid refresh token")
    user_id = row.user_id
    user_agent = row.user_agent
    await session.execute(delete(SessionRow).where(SessionRow.id == row.id))
    await session.commit()
    return await create_session(session, user_id=user_id, user_agent=user_agent)


async def revoke_session(session: AsyncSession, *, raw: str) -> None:
    await session.execute(delete(SessionRow).where(SessionRow.refresh_hash == _hash(raw)))
    await session.commit()
```

- [ ] **Step 4: Run test, expect pass**

```bash
pytest tests/unit/test_sessions.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/core/auth/sessions.py apps/api/tests/unit/test_sessions.py
git commit -m "feat(auth): add refresh-token session rotation"
```

---

## Task 13: Auth routes `/auth/login|refresh|logout` (TDD)

**Files:**
- Create: `apps/api/routes/__init__.py`, `apps/api/routes/auth.py`
- Modify: `apps/api/main.py`
- Test: `apps/api/tests/integration/test_auth_routes.py`

- [ ] **Step 1: Write failing test `tests/integration/test_auth_routes.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_login_returns_access_token_and_sets_cookie(app_client, seeded):
    r = await app_client.post("/auth/login", json={"email": "viewer.a@example.com", "password": "password1234"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert body["user"]["email"] == "viewer.a@example.com"
    assert "rdm_refresh" in r.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(app_client, seeded):
    r = await app_client.post("/auth/login", json={"email": "viewer.a@example.com", "password": "nope"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_access(app_client, seeded):
    r1 = await app_client.post("/auth/login", json={"email": "viewer.a@example.com", "password": "password1234"})
    r2 = await app_client.post("/auth/refresh", cookies={"rdm_refresh": r1.cookies["rdm_refresh"]})
    assert r2.status_code == 200
    assert r2.json()["access_token"] != r1.json()["access_token"]


@pytest.mark.asyncio
async def test_logout_clears_cookie(app_client, seeded):
    r1 = await app_client.post("/auth/login", json={"email": "viewer.a@example.com", "password": "password1234"})
    r2 = await app_client.post("/auth/logout", cookies={"rdm_refresh": r1.cookies["rdm_refresh"]})
    assert r2.status_code == 204
    # subsequent refresh fails
    r3 = await app_client.post("/auth/refresh", cookies={"rdm_refresh": r1.cookies["rdm_refresh"]})
    assert r3.status_code == 401
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/integration/test_auth_routes.py -v
```

Expected: FAIL (route not found).

- [ ] **Step 3: Implement `routes/__init__.py`**

```python
```

- [ ] **Step 4: Implement `routes/auth.py`**

```python
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import encode_access_token
from core.auth.password import verify_password
from core.auth.sessions import create_session, revoke_session, rotate_session, find_session_by_refresh
from core.db.models import OrgMembership, SiteMembership, User
from core.db.session import get_session
from core.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE = "rdm_refresh"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    is_super_admin: bool
    org_memberships: list[dict]
    site_memberships: list[dict]


class LoginOut(BaseModel):
    user: UserOut
    access_token: str


def _refresh_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE, value,
        max_age=settings.jwt_refresh_ttl_seconds,
        httponly=True, secure=False, samesite="lax", path="/auth",
    )


async def _claims_for_user(session: AsyncSession, user: User) -> dict:
    org_rows = (await session.execute(
        select(OrgMembership).where(OrgMembership.user_id == user.id)
    )).scalars().all()
    site_rows = (await session.execute(
        select(SiteMembership).where(SiteMembership.user_id == user.id)
    )).scalars().all()
    return {
        "sub": str(user.id),
        "email": user.email,
        "is_super_admin": user.is_super_admin,
        "org_memberships": [{"org_id": str(r.org_id), "role": r.role} for r in org_rows],
        "site_memberships": [{"site_id": str(r.site_id), "role": r.role} for r in site_rows],
    }


@router.post("/login", response_model=LoginOut)
async def login(payload: LoginIn, response: Response, request: Request, session: AsyncSession = Depends(get_session)):
    row = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if row is None or not verify_password(payload.password, row.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    refresh = await create_session(session, user_id=row.id, user_agent=request.headers.get("user-agent"))
    claims = await _claims_for_user(session, row)
    access = encode_access_token(claims)
    _refresh_cookie(response, refresh)
    return {
        "user": {
            "id": row.id, "email": row.email, "name": row.name, "is_super_admin": row.is_super_admin,
            "org_memberships": claims["org_memberships"], "site_memberships": claims["site_memberships"],
        },
        "access_token": access,
    }


@router.post("/refresh", response_model=LoginOut)
async def refresh(response: Response, rdm_refresh: str | None = Cookie(default=None),
                  session: AsyncSession = Depends(get_session)):
    if rdm_refresh is None:
        raise HTTPException(status_code=401, detail="missing refresh cookie")
    row = await find_session_by_refresh(session, rdm_refresh)
    if row is None:
        raise HTTPException(status_code=401, detail="invalid refresh")
    new_refresh = await rotate_session(session, old_refresh=rdm_refresh)
    user = (await session.execute(select(User).where(User.id == row.user_id))).scalar_one()
    claims = await _claims_for_user(session, user)
    _refresh_cookie(response, new_refresh)
    return {
        "user": {
            "id": user.id, "email": user.email, "name": user.name, "is_super_admin": user.is_super_admin,
            "org_memberships": claims["org_memberships"], "site_memberships": claims["site_memberships"],
        },
        "access_token": encode_access_token(claims),
    }


@router.post("/logout", status_code=204)
async def logout(response: Response, rdm_refresh: str | None = Cookie(default=None),
                 session: AsyncSession = Depends(get_session)):
    if rdm_refresh:
        await revoke_session(session, raw=rdm_refresh)
    response.delete_cookie(REFRESH_COOKIE, path="/auth")
    return Response(status_code=204)
```

- [ ] **Step 5: Wire router in `main.py`**

Replace the contents of `apps/api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.settings import settings
from routes import auth as auth_routes


def create_app() -> FastAPI:
    app = FastAPI(title="RDM Insight API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_routes.router)
    return app


app = create_app()
```

- [ ] **Step 6: Run tests, expect pass**

```bash
pytest tests/integration/test_auth_routes.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes apps/api/main.py apps/api/tests/integration/test_auth_routes.py
git commit -m "feat(auth): add login/refresh/logout routes"
```

---

## Task 14: Auth dependency `get_current_user`

**Files:**
- Create: `apps/api/core/auth/dependencies.py`
- Test: extended in Task 15

- [ ] **Step 1: Implement `core/auth/dependencies.py`**

```python
from __future__ import annotations
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import decode_access_token, InvalidToken
from core.db.models import User
from core.db.session import get_session


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = decode_access_token(token)
    except InvalidToken:
        raise HTTPException(status_code=401, detail="invalid token")
    user = (await session.execute(select(User).where(User.id == UUID(claims["sub"])))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="unknown user")
    return user
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/core/auth/dependencies.py
git commit -m "feat(auth): add get_current_user dependency"
```

---

## Task 15: Tenant middleware + `get_tenant_ctx` (TDD)

**Files:**
- Create: `apps/api/core/tenancy/middleware.py`, `apps/api/core/tenancy/rbac.py`
- Modify: `apps/api/main.py`
- Test: `apps/api/tests/integration/test_tenant_middleware.py`

- [ ] **Step 1: Write failing test `tests/integration/test_tenant_middleware.py`**

```python
import pytest

from main import create_app
from core.tenancy.rbac import require_role
from fastapi import Depends
from httpx import AsyncClient, ASGITransport


def _attach_demo_route(app):
    @app.get("/demo/site")
    async def demo_site(ctx=Depends(require_role("site_viewer"))):
        return {"site_id": str(ctx.site_id), "role": ctx.role}

    @app.post("/demo/operator")
    async def demo_op(ctx=Depends(require_role("site_operator"))):
        return {"ok": True}


@pytest.mark.asyncio
async def test_viewer_can_read_own_site(db_session, seeded):
    from core.db.session import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    _attach_demo_route(app)
    # login
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        login = await c.post("/auth/login", json={"email": "viewer.a@example.com", "password": "password1234"})
        token = login.json()["access_token"]
        r = await c.get("/demo/site", headers={
            "Authorization": f"Bearer {token}",
            "X-Site-Id": str(seeded["site_a"].id),
        })
    assert r.status_code == 200
    assert r.json()["role"] == "site_viewer"


@pytest.mark.asyncio
async def test_viewer_denied_other_site(db_session, seeded):
    from core.db.session import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    _attach_demo_route(app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        login = await c.post("/auth/login", json={"email": "viewer.a@example.com", "password": "password1234"})
        token = login.json()["access_token"]
        r = await c.get("/demo/site", headers={
            "Authorization": f"Bearer {token}",
            "X-Site-Id": str(seeded["site_b"].id),
        })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_denied_operator_route(db_session, seeded):
    from core.db.session import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    _attach_demo_route(app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        login = await c.post("/auth/login", json={"email": "viewer.a@example.com", "password": "password1234"})
        token = login.json()["access_token"]
        r = await c.post("/demo/operator", headers={
            "Authorization": f"Bearer {token}",
            "X-Site-Id": str(seeded["site_a"].id),
        })
    assert r.status_code == 403
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/integration/test_tenant_middleware.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `core/tenancy/middleware.py`**

```python
from __future__ import annotations
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.models import User
from core.db.session import get_session
from core.tenancy.context import TenantContext
from core.tenancy.service import TenancyError, resolve_tenant_ctx


async def get_tenant_ctx(
    x_site_id: str | None = Header(default=None, alias="X-Site-Id"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TenantContext:
    if x_site_id is None:
        raise HTTPException(status_code=400, detail="X-Site-Id header required")
    try:
        site_uuid = UUID(x_site_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid X-Site-Id")
    try:
        return await resolve_tenant_ctx(session, user_id=user.id, site_id=site_uuid)
    except TenancyError as e:
        raise HTTPException(status_code=403, detail=str(e))
```

- [ ] **Step 4: Implement `core/tenancy/rbac.py`**

```python
from __future__ import annotations
from typing import Callable

from fastapi import Depends, HTTPException

from core.tenancy.context import Role, TenantContext
from core.tenancy.middleware import get_tenant_ctx

_RANK: dict[Role, int] = {
    "site_viewer": 1,
    "site_operator": 2,
    "org_admin": 3,
    "super_admin": 4,
}


def require_role(min_role: Role) -> Callable:
    threshold = _RANK[min_role]

    def _dep(ctx: TenantContext = Depends(get_tenant_ctx)) -> TenantContext:
        if _RANK[ctx.role] < threshold:
            raise HTTPException(status_code=403, detail=f"requires {min_role}")
        return ctx

    return _dep
```

- [ ] **Step 5: Run tests, expect pass**

```bash
pytest tests/integration/test_tenant_middleware.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/core/tenancy apps/api/tests/integration/test_tenant_middleware.py
git commit -m "feat(tenancy): add tenant middleware + require_role dependency"
```

---

## Task 16: Site adapter `Protocol` + DTOs

**Files:**
- Create: `apps/api/core/registry/__init__.py`, `apps/api/core/registry/protocol.py`
- Test: `apps/api/tests/unit/test_dispatch.py` (next task)

- [ ] **Step 1: Implement `core/registry/__init__.py`**

```python
from core.registry.protocol import (  # noqa: F401
    SiteAdapter, Device, DeviceDetail, TimeRange, TrendSeries, Ranking, ChatContext,
)
from core.registry.dispatch import get_adapter, UnknownAdapter  # noqa: F401
```

- [ ] **Step 2: Implement `core/registry/protocol.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from core.tenancy.context import TenantContext


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime


@dataclass
class Device:
    id: str
    type: str
    name: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TrendPoint:
    ts: datetime
    value: float


@dataclass
class TrendSeries:
    series: list[TrendPoint] = field(default_factory=list)
    unit: str = ""


@dataclass
class RankingRow:
    device_id: str
    score: float


@dataclass
class Ranking:
    top: list[RankingRow] = field(default_factory=list)
    worst: list[RankingRow] = field(default_factory=list)


@dataclass
class DeviceDetail:
    device: Device
    metrics: dict[str, float] = field(default_factory=dict)
    trend: TrendSeries | None = None


@dataclass
class ChatContext:
    rag_snippets: list[str] = field(default_factory=list)
    structured_facts: dict = field(default_factory=dict)
    recent_alerts: list[dict] = field(default_factory=list)


@runtime_checkable
class SiteAdapter(Protocol):
    slug: str

    # Async methods so adapters can safely await blocking I/O wrapped in
    # asyncio.to_thread (Influx, Chroma, HTTP). Sync helpers (list_devices,
    # validate_device_id) stay sync because they don't do I/O.
    async def health_trend(self, ctx: TenantContext, range: TimeRange) -> TrendSeries: ...
    async def device_ranking(self, ctx: TenantContext, range: TimeRange) -> Ranking: ...
    async def device_detail(self, ctx: TenantContext, device_id: str, range: TimeRange) -> DeviceDetail: ...
    async def chat_context(self, ctx: TenantContext, query: str) -> ChatContext: ...
    def list_devices(self, ctx: TenantContext) -> list[Device]: ...
    def validate_device_id(self, device_id: str) -> bool: ...
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/core/registry/__init__.py apps/api/core/registry/protocol.py
git commit -m "feat(registry): add SiteAdapter Protocol + DTOs"
```

---

## Task 17: `_default` adapter stub

**Files:**
- Create: `apps/api/sites/__init__.py`, `apps/api/sites/_default/__init__.py`, `apps/api/sites/_default/adapter.py`
- Test: `apps/api/tests/unit/test_default_adapter.py`

- [ ] **Step 1: Write failing test `tests/unit/test_default_adapter.py`**

```python
from datetime import datetime, timezone, timedelta
import uuid

from core.registry import SiteAdapter, TimeRange
from core.tenancy.context import TenantContext
from sites._default.adapter import DefaultAdapter


def _ctx(site_id=None):
    return TenantContext(user_id=uuid.uuid4(), org_id=uuid.uuid4(),
                         site_id=site_id or uuid.uuid4(), role="site_viewer")


def test_default_adapter_is_protocol_compliant():
    a = DefaultAdapter(config={"devices": []})
    assert isinstance(a, SiteAdapter)


async def test_health_trend_returns_empty_series_when_no_config():
    a = DefaultAdapter(config={})
    s = await a.health_trend(_ctx(), TimeRange(start=datetime.now(timezone.utc) - timedelta(hours=1),
                                               end=datetime.now(timezone.utc)))
    assert s.series == []


def test_list_devices_reads_config():
    a = DefaultAdapter(config={"devices": [{"id": "x-1", "type": "ahu", "name": "X-1"}]})
    devs = a.list_devices(_ctx())
    assert len(devs) == 1 and devs[0].id == "x-1"


def test_validate_device_id_matches_config():
    a = DefaultAdapter(config={"devices": [{"id": "x-1", "type": "ahu"}]})
    assert a.validate_device_id("x-1") is True
    assert a.validate_device_id("not-in-config") is False
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/unit/test_default_adapter.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `sites/__init__.py`**

```python
```

- [ ] **Step 4: Implement `sites/_default/__init__.py`**

```python
from sites._default.adapter import DefaultAdapter  # noqa: F401
```

- [ ] **Step 5: Implement `sites/_default/adapter.py`**

```python
from __future__ import annotations
from typing import Any

from core.registry.protocol import (
    ChatContext, Device, DeviceDetail, Ranking, TimeRange, TrendSeries,
)
from core.tenancy.context import TenantContext


class DefaultAdapter:
    slug = "_default"

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._devices = [Device(**d) for d in config.get("devices", [])]

    async def health_trend(self, ctx: TenantContext, range: TimeRange) -> TrendSeries:
        return TrendSeries(series=[], unit="score")

    async def device_ranking(self, ctx: TenantContext, range: TimeRange) -> Ranking:
        return Ranking()

    async def device_detail(self, ctx: TenantContext, device_id: str, range: TimeRange) -> DeviceDetail:
        dev = next((d for d in self._devices if d.id == device_id), None)
        if dev is None:
            dev = Device(id=device_id, type="unknown")
        return DeviceDetail(device=dev)

    async def chat_context(self, ctx: TenantContext, query: str) -> ChatContext:
        return ChatContext()

    def list_devices(self, ctx: TenantContext) -> list[Device]:
        return list(self._devices)

    def validate_device_id(self, device_id: str) -> bool:
        return any(d.id == device_id for d in self._devices)
```

- [ ] **Step 6: Run tests, expect pass**

```bash
pytest tests/unit/test_default_adapter.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/sites apps/api/tests/unit/test_default_adapter.py
git commit -m "feat(sites): add _default adapter stub (historical-only)"
```

---

## Task 18: Adapter dispatch (TDD)

**Files:**
- Create: `apps/api/core/registry/dispatch.py`
- Test: `apps/api/tests/unit/test_dispatch.py`

- [ ] **Step 1: Write failing test `tests/unit/test_dispatch.py`**

```python
import pytest
from core.registry import get_adapter, UnknownAdapter
from core.db.models import Site
import uuid
from datetime import datetime, timezone


def _site(adapter: str):
    return Site(id=uuid.uuid4(), org_id=uuid.uuid4(), slug="s", name="S",
                adapter=adapter, influx_bucket=None, config={"devices": []},
                created_at=datetime.now(timezone.utc))


def test_dispatch_default():
    a = get_adapter(_site("_default"))
    assert a.slug == "_default"


def test_dispatch_unknown_raises():
    with pytest.raises(UnknownAdapter):
        get_adapter(_site("not-real"))
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/unit/test_dispatch.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `core/registry/dispatch.py`**

```python
from __future__ import annotations

from core.db.models import Site
from core.registry.protocol import SiteAdapter
from sites._default.adapter import DefaultAdapter


class UnknownAdapter(Exception):
    pass


def get_adapter(site: Site) -> SiteAdapter:
    if site.adapter == "_default":
        return DefaultAdapter(site.config or {})
    raise UnknownAdapter(site.adapter)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/unit/test_dispatch.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/core/registry/dispatch.py apps/api/tests/unit/test_dispatch.py
git commit -m "feat(registry): add adapter dispatch with UnknownAdapter"
```

---

## Task 19: Dashboard routes wired through adapter (TDD)

**Files:**
- Create: `apps/api/routes/dashboard.py`, `apps/api/routes/health.py`
- Modify: `apps/api/main.py`
- Test: `apps/api/tests/integration/test_dashboard_routes.py`

- [ ] **Step 1: Write failing test `tests/integration/test_dashboard_routes.py`**

```python
import pytest


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_health_trend_returns_empty_for_default_adapter(app_client, seeded):
    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.get("/dashboard/health-trend?range=24h", headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_a"].id),
    })
    assert r.status_code == 200
    body = r.json()
    assert body == {"series": [], "unit": "score"}


@pytest.mark.asyncio
async def test_missing_site_header_returns_400(app_client, seeded):
    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.get("/dashboard/health-trend?range=24h", headers={
        "Authorization": f"Bearer {token}",
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_unauthorized_without_token(app_client, seeded):
    r = await app_client.get("/dashboard/health-trend?range=24h", headers={"X-Site-Id": str(seeded["site_a"].id)})
    assert r.status_code == 401
```

- [ ] **Step 2: Run test, expect failure**

```bash
pytest tests/integration/test_dashboard_routes.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `routes/health.py`**

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz():
    return {"status": "ok"}
```

- [ ] **Step 4: Implement `routes/dashboard.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import Site
from core.db.session import get_session
from core.registry import get_adapter
from core.registry.protocol import TimeRange
from core.tenancy.context import TenantContext
from core.tenancy.rbac import require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _parse_range(spec: str) -> TimeRange:
    now = datetime.now(timezone.utc)
    table = {"1h": 1, "24h": 24, "7d": 24 * 7, "30d": 24 * 30}
    hours = table.get(spec)
    if hours is None:
        raise HTTPException(status_code=400, detail="invalid range")
    return TimeRange(start=now - timedelta(hours=hours), end=now)


async def _adapter_for(ctx: TenantContext, session: AsyncSession):
    site = (await session.execute(select(Site).where(Site.id == ctx.site_id))).scalar_one()
    return get_adapter(site)


@router.get("/health-trend")
async def health_trend(range: str = "24h",
                       ctx: TenantContext = Depends(require_role("site_viewer")),
                       session: AsyncSession = Depends(get_session)):
    adapter = await _adapter_for(ctx, session)
    series = await adapter.health_trend(ctx, _parse_range(range))
    return {
        "series": [{"ts": p.ts.isoformat(), "value": p.value} for p in series.series],
        "unit": series.unit,
    }


@router.get("/ranking")
async def ranking(range: str = "24h",
                  ctx: TenantContext = Depends(require_role("site_viewer")),
                  session: AsyncSession = Depends(get_session)):
    adapter = await _adapter_for(ctx, session)
    r = await adapter.device_ranking(ctx, _parse_range(range))
    return {
        "top": [{"device_id": row.device_id, "score": row.score} for row in r.top],
        "worst": [{"device_id": row.device_id, "score": row.score} for row in r.worst],
    }


@router.get("/devices/{device_id}")
async def device_detail(device_id: str, range: str = "24h",
                        ctx: TenantContext = Depends(require_role("site_viewer")),
                        session: AsyncSession = Depends(get_session)):
    adapter = await _adapter_for(ctx, session)
    d = await adapter.device_detail(ctx, device_id, _parse_range(range))
    return {
        "device": {"id": d.device.id, "type": d.device.type, "name": d.device.name, "metadata": d.device.metadata},
        "metrics": d.metrics,
        "trend": None if d.trend is None else {
            "series": [{"ts": p.ts.isoformat(), "value": p.value} for p in d.trend.series],
            "unit": d.trend.unit,
        },
    }
```

- [ ] **Step 5: Update `main.py` to register routers**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.settings import settings
from routes import auth as auth_routes
from routes import dashboard as dashboard_routes
from routes import health as health_routes


def create_app() -> FastAPI:
    app = FastAPI(title="RDM Insight API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(dashboard_routes.router)
    return app


app = create_app()
```

- [ ] **Step 6: Run tests, expect pass**

```bash
pytest tests/integration/test_dashboard_routes.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes/dashboard.py apps/api/routes/health.py apps/api/main.py apps/api/tests/integration/test_dashboard_routes.py
git commit -m "feat(api): add dashboard routes dispatched through adapter"
```

---

## Task 20: Cross-tenant isolation parameterized suite (security-critical)

**Files:**
- Create: `apps/api/tests/integration/test_cross_tenant_isolation.py`

- [ ] **Step 1: Write the test**

```python
import pytest

SITE_SCOPED_ROUTES = [
    ("GET", "/dashboard/health-trend?range=24h"),
    ("GET", "/dashboard/ranking?range=24h"),
    ("GET", "/dashboard/devices/anything"),
]


async def _bearer(c, email):
    r = await c.post("/auth/login", json={"email": email, "password": "password1234"})
    return r.json()["access_token"]


@pytest.mark.parametrize("method,path", SITE_SCOPED_ROUTES)
@pytest.mark.asyncio
async def test_viewer_a_cannot_access_site_b(app_client, seeded, method, path):
    token = await _bearer(app_client, "viewer.a@example.com")
    r = await app_client.request(method, path, headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_b"].id),
    })
    assert r.status_code == 403, f"{method} {path} expected 403 got {r.status_code}: {r.text}"


@pytest.mark.parametrize("method,path", SITE_SCOPED_ROUTES)
@pytest.mark.asyncio
async def test_super_admin_can_access_any_site(app_client, seeded, method, path):
    token = await _bearer(app_client, "super@example.com")
    r = await app_client.request(method, path, headers={
        "Authorization": f"Bearer {token}",
        "X-Site-Id": str(seeded["site_b"].id),
    })
    assert r.status_code == 200, f"{method} {path} expected 200 got {r.status_code}"


@pytest.mark.asyncio
async def test_no_token_blocked(app_client, seeded):
    r = await app_client.get("/dashboard/health-trend?range=24h",
                             headers={"X-Site-Id": str(seeded["site_a"].id)})
    assert r.status_code == 401
```

- [ ] **Step 2: Run, expect pass**

```bash
pytest tests/integration/test_cross_tenant_isolation.py -v
```

Expected: 7 passed.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/integration/test_cross_tenant_isolation.py
git commit -m "test(security): cross-tenant 403 + super-admin access matrix"
```

---

## Task 21: Seed script for local dev

**Files:**
- Create: `apps/api/scripts/__init__.py`, `apps/api/scripts/seed.py`

- [ ] **Step 1: Implement `apps/api/scripts/__init__.py`**

```python
```

- [ ] **Step 2: Implement `apps/api/scripts/seed.py`**

```python
"""Seed local dev DB with two demo orgs + sites + users.

Usage: python -m scripts.seed
"""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete

from core.auth.password import hash_password
from core.db.models import Org, Site, User, SiteMembership
from core.db.session import async_session_factory


async def main() -> None:
    now = datetime.now(timezone.utc)
    async with async_session_factory() as s:
        for tbl in [SiteMembership, User, Site, Org]:
            await s.execute(delete(tbl))
        org_a = Org(id=uuid.uuid4(), slug="wach", name="WACH", theme={"primary": "#00E5A0"}, created_at=now)
        org_b = Org(id=uuid.uuid4(), slug="cyberview", name="Cyberview", theme={"primary": "#4C6FFF"}, created_at=now)
        site_a = Site(id=uuid.uuid4(), org_id=org_a.id, slug="wach-main", name="WACH Main",
                      adapter="_default", influx_bucket="wach", config={"devices": []}, created_at=now)
        site_b = Site(id=uuid.uuid4(), org_id=org_b.id, slug="cyberview-a", name="Cyberview Block A",
                      adapter="_default", influx_bucket="cyberview", config={"devices": []}, created_at=now)
        viewer_a = User(id=uuid.uuid4(), email="viewer.wach@example.com",
                        password_hash=hash_password("password1234"), name="Viewer WACH",
                        is_super_admin=False, created_at=now)
        viewer_b = User(id=uuid.uuid4(), email="viewer.cyberview@example.com",
                        password_hash=hash_password("password1234"), name="Viewer Cyberview",
                        is_super_admin=False, created_at=now)
        operator_a = User(id=uuid.uuid4(), email="operator.wach@example.com",
                          password_hash=hash_password("password1234"), name="Operator WACH",
                          is_super_admin=False, created_at=now)
        super_u = User(id=uuid.uuid4(), email="super@example.com",
                       password_hash=hash_password("password1234"), name="Super",
                       is_super_admin=True, created_at=now)
        s.add_all([org_a, org_b, site_a, site_b, viewer_a, viewer_b, operator_a, super_u])
        await s.flush()
        s.add_all([
            SiteMembership(user_id=viewer_a.id, site_id=site_a.id, role="site_viewer"),
            SiteMembership(user_id=viewer_b.id, site_id=site_b.id, role="site_viewer"),
            SiteMembership(user_id=operator_a.id, site_id=site_a.id, role="site_operator"),
        ])
        await s.commit()
        print("Seeded:")
        print(f"  super         super@example.com / password1234")
        print(f"  viewer wach   viewer.wach@example.com / password1234  site={site_a.id}")
        print(f"  viewer cv     viewer.cyberview@example.com / password1234  site={site_b.id}")
        print(f"  operator wach operator.wach@example.com / password1234  site={site_a.id}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run the seed against local DB**

```bash
cd apps/api && python -m scripts.seed
```

Expected: prints three users with credentials.

- [ ] **Step 4: Commit**

```bash
git add apps/api/scripts
git commit -m "feat(scripts): add local-dev seed script"
```

---

## Task 22: Frontend auth store + API client

**Files:**
- Create: `apps/web/src/store/useAuthStore.ts`, `apps/web/src/api/client.ts`

- [ ] **Step 1: Implement `src/store/useAuthStore.ts`**

```ts
import { create } from "zustand";
import type { User } from "@rdm/types";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  activeSiteId: string | null;
  setSession: (u: User, token: string) => void;
  setActiveSite: (siteId: string | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  activeSiteId: typeof localStorage !== "undefined" ? localStorage.getItem("activeSiteId") : null,
  setSession: (user, token) => set({ user, accessToken: token }),
  setActiveSite: (siteId) => {
    if (siteId) localStorage.setItem("activeSiteId", siteId);
    else localStorage.removeItem("activeSiteId");
    set({ activeSiteId: siteId });
  },
  clear: () => set({ user: null, accessToken: null, activeSiteId: null }),
}));
```

- [ ] **Step 2: Implement `src/api/client.ts`**

```ts
import { useAuthStore } from "@/store/useAuthStore";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function refresh(): Promise<string | null> {
  const r = await fetch("/api/auth/refresh", { method: "POST", credentials: "include" });
  if (!r.ok) return null;
  const data = await r.json();
  useAuthStore.getState().setSession(data.user, data.access_token);
  return data.access_token;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { accessToken, activeSiteId } = useAuthStore.getState();
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (activeSiteId) headers.set("X-Site-Id", activeSiteId);
  headers.set("Content-Type", "application/json");

  let r = await fetch(`/api${path}`, { ...init, headers, credentials: "include" });
  if (r.status === 401 && accessToken) {
    const fresh = await refresh();
    if (!fresh) throw new ApiError(401, "session expired");
    headers.set("Authorization", `Bearer ${fresh}`);
    r = await fetch(`/api${path}`, { ...init, headers, credentials: "include" });
  }
  if (!r.ok) throw new ApiError(r.status, await r.text());
  return r.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  const r = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new ApiError(r.status, "login failed");
  const data = await r.json();
  useAuthStore.getState().setSession(data.user, data.access_token);
  return data;
}

export async function logout() {
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  useAuthStore.getState().clear();
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/store apps/web/src/api
git commit -m "feat(web): add auth store + fetch client with refresh"
```

---

## Task 23: Login page + protected shell + stub dashboard

**Files:**
- Create: `apps/web/src/shell/LoginPage.tsx`, `apps/web/src/shell/ProtectedRoute.tsx`, `apps/web/src/shell/AppShell.tsx`, `apps/web/src/pages/DashboardStub.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Implement `src/shell/LoginPage.tsx`**

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "@/api/client";
import { useAuthStore } from "@/store/useAuthStore";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const setActiveSite = useAuthStore((s) => s.setActiveSite);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const data = await login(email, password);
      const first = data.user.site_memberships[0]?.site_id ?? null;
      setActiveSite(first);
      navigate("/dashboard");
    } catch {
      setError("Invalid credentials");
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ maxWidth: 320, margin: "4rem auto", display: "grid", gap: 8 }}>
      <h1>RDM Insight</h1>
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" type="email" required />
      <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" required />
      <button type="submit">Sign in</button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </form>
  );
}
```

- [ ] **Step 2: Implement `src/shell/ProtectedRoute.tsx`**

```tsx
import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
```

- [ ] **Step 3: Implement `src/shell/AppShell.tsx`**

```tsx
import { Outlet } from "react-router-dom";
import { logout } from "@/api/client";
import { useAuthStore } from "@/store/useAuthStore";

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const activeSiteId = useAuthStore((s) => s.activeSiteId);
  const setActiveSite = useAuthStore((s) => s.setActiveSite);
  const siteOptions = user?.site_memberships ?? [];

  return (
    <div>
      <header style={{ display: "flex", gap: 12, padding: 12, borderBottom: "1px solid #ddd" }}>
        <strong>RDM Insight</strong>
        {siteOptions.length > 0 && (
          <select value={activeSiteId ?? ""} onChange={(e) => setActiveSite(e.target.value || null)}>
            {siteOptions.map((s) => (
              <option key={s.site_id} value={s.site_id}>{s.site_id}</option>
            ))}
          </select>
        )}
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

- [ ] **Step 4: Implement `src/pages/DashboardStub.tsx`**

```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "@/api/client";

interface TrendResponse { series: { ts: string; value: number }[]; unit: string }

export function DashboardStub() {
  const [data, setData] = useState<TrendResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<TrendResponse>("/dashboard/health-trend?range=24h")
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p>Error: {err}</p>;
  if (!data) return <p>Loading...</p>;
  return (
    <section>
      <h2>Health Trend</h2>
      <p>{data.series.length === 0 ? "No data yet (default adapter)." : `${data.series.length} points`}</p>
    </section>
  );
}
```

- [ ] **Step 5: Replace `src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginPage } from "@/shell/LoginPage";
import { ProtectedRoute } from "@/shell/ProtectedRoute";
import { AppShell } from "@/shell/AppShell";
import { DashboardStub } from "@/pages/DashboardStub";

const qc = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
            <Route path="/dashboard" element={<DashboardStub />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 6: Manual smoke test**

```bash
# terminal 1
cd apps/api && uvicorn main:app --port 8081 --reload
# terminal 2
pnpm --filter @rdm/web dev
```

Open `http://localhost:3000`, log in as `viewer.wach@example.com / password1234`, confirm dashboard shows "No data yet (default adapter)."

- [ ] **Step 7: Commit**

```bash
git add apps/web/src
git commit -m "feat(web): add login, protected shell, stub dashboard"
```

---

## Task 24: Frontend Jest setup + smoke test

**Files:**
- Create: `apps/web/jest.config.ts`, `apps/web/tests/App.test.tsx`, `apps/web/tests/setup.ts`

- [ ] **Step 1: Create `apps/web/jest.config.ts`**

```ts
import type { Config } from "jest";

const config: Config = {
  preset: "ts-jest",
  testEnvironment: "jsdom",
  setupFilesAfterEach: ["<rootDir>/tests/setup.ts"],
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1", "^@rdm/types$": "<rootDir>/../../packages/types/src/index.ts" },
  testMatch: ["<rootDir>/tests/**/*.test.tsx", "<rootDir>/tests/**/*.test.ts"],
};
export default config;
```

- [ ] **Step 2: Create `apps/web/tests/setup.ts`**

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 3: Create `apps/web/tests/App.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "@/shell/LoginPage";

test("login page renders email + password", () => {
  render(<MemoryRouter><LoginPage /></MemoryRouter>);
  expect(screen.getByPlaceholderText("email")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("password")).toBeInTheDocument();
});
```

- [ ] **Step 4: Run test**

```bash
pnpm --filter @rdm/web test
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/web/jest.config.ts apps/web/tests
git commit -m "test(web): add Jest setup + login smoke test"
```

---

## Task 25: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: rdm
          POSTGRES_PASSWORD: rdm
          POSTGRES_DB: rdm_insight_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install
        working-directory: apps/api
        run: |
          pip install -e ".[dev]"
      - name: Enable citext
        run: |
          PGPASSWORD=rdm psql -h localhost -U rdm -d rdm_insight_test -c 'CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
      - name: Lint
        working-directory: apps/api
        run: ruff check .
      - name: Tests
        working-directory: apps/api
        run: pytest -v --cov=core --cov=routes --cov=sites --cov-report=term-missing

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter @rdm/web typecheck
      - run: pnpm --filter @rdm/web test
      - run: pnpm --filter @rdm/web build
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lint, test, build for api + web"
```

---

## Self-Review (Plan A)

- **Spec coverage:** §3 architecture (tasks 1–4), §4 repo layout (1–5), §5 data model (6–7), §6 auth + tenancy (8–15, 20), §7 adapter contract (16–18), §9 frontend shell minimum (22–24), §10 testing strategy partial — cross-tenant suite in task 20, adapter conformance is a Plan B addition (mark as carry-over in Plan B). Chat (§8), theming, admin UI, deployment intentionally deferred to Plans B and C.
- **Placeholder scan:** none — every code block is concrete; the `_default` adapter returns explicit empty values, not "TBD".
- **Type consistency:** `TenantContext` fields (`user_id`, `org_id`, `site_id`, `role`) used identically across `tenancy/context.py`, `tenancy/service.py`, `tenancy/rbac.py`, and routes. `SiteAdapter` methods used in `dashboard.py` match `protocol.py` signatures. Cookie name `rdm_refresh` consistent across login/refresh/logout.

**Carry-over to Plan B:**
- Adapter conformance test suite (`tests/adapters/test_protocol.py`)
- Chat orchestrator + RAG + Qwen pipeline
- `wach` adapter port
- React Query usage in real data pages (only used as boilerplate in Plan A)
