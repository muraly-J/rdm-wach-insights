# WACH Insight — Claude Code Configuration

## Project Overview

**WACH Insight** is a building health monitoring and analysis platform for HVAC systems. It tracks air handling unit (AHU) performance across 11 building levels with real-time data ingestion, predictive maintenance, and AI-powered chatbot insights.

- **Backend**: Python FastAPI running on port 8081 (`backend/main.py`)
- **Frontend**: React + Vite + TypeScript + Tailwind CSS 3 running on port 3000 (`frontend/src/main.tsx`)
- **Databases**: InfluxDB Cloud (time-series), ChromaDB (vector, RAG), SQLite (local)
- **Deployment**: Docker Compose for local dev, Docker container for production (Vercel frontend, Railway/Cloudflare backend)

---

## Directory Structure

```
.
├── backend/                    # Python FastAPI application
│   ├── main.py                # Entry point, FastAPI setup, route registration
│   ├── config.py              # Environment variables and configuration
│   ├── core/                  # Business logic (risk engine, scoring, ML models)
│   ├── routes/                # API endpoints (dashboard, forecast, health, chat, etc.)
│   ├── models/                # Data models and schemas
│   ├── middleware/            # Request/response middleware (CORS, logging, etc.)
│   ├── rag/                   # RAG pipeline for chatbot context
│   ├── llm/                   # LLM integrations (Gemini, Qwen, embeddings)
│   ├── data/                  # SQLite db, ChromaDB, exported reports
│   ├── requirements.txt        # Production dependencies
│   ├── requirements-dev.txt    # Dev dependencies (pytest, etc.)
│   └── pytest.ini             # Pytest configuration
├── frontend/                  # React + Vite application
│   ├── src/
│   │   ├── main.tsx           # React app entry point
│   │   ├── App.tsx            # Root component
│   │   ├── index.css          # Global TailwindCSS + custom styles
│   │   ├── store/             # Zustand state management (useAppStore.ts)
│   │   ├── components/        # React components (Dashboard, Chat, Charts, etc.)
│   │   ├── mocks/             # Mock data generators (generateMockData.ts)
│   │   └── utils/             # Utility functions
│   ├── public/                # Static assets
│   ├── vite.config.ts         # Vite build configuration
│   ├── tsconfig.json          # TypeScript configuration
│   ├── index.html             # HTML entry point
│   ├── package.json           # Dependencies (React, Zustand, Recharts, etc.)
│   └── tailwind.config.cjs    # Tailwind CSS configuration (must be .cjs for ESM)
├── docs/                      # Project documentation
│   ├── superpowers/           # Phase plans and feature specs
│   │   ├── plans/             # Implementation plans (Phase 1, Phase 5, etc.)
│   │   └── specs/             # Specifications (production readiness, design docs)
│   ├── CONSTITUTION.md        # Tech stack, AHU ID convention, conventions
│   ├── implementation/        # Architecture notes and decisions
│   └── reference/             # API docs, how-to guides
├── scripts/                   # Utility scripts
│   ├── infra/                 # Infrastructure scripts (Docker, deployment)
│   └── debug/                 # Debug utilities
├── .github/workflows/         # CI/CD pipelines (GitHub Actions)
├── docker/                    # Docker configs (multistage build)
├── data/                      # Data files, exports (not in git)
├── docker-compose.yml         # Local dev environment
├── Dockerfile                 # Container image
├── .env.example               # Environment variables template
├── .vercel/                   # Vercel project link
└── API.md                     # API endpoint reference

```

---

## Development Setup

### Prerequisites

- **Node 20+** (frontend)
- **Python 3.11+** (backend)
- **pip** (Python package manager)
- **Docker & Docker Compose** (optional, for containerized dev)

### Frontend Dev

```bash
cd frontend
npm install
npm run dev         # Start dev server (port 3000)
npm run build       # Production build
npm run preview     # Preview production build
npm test            # Run Jest tests
npm run test:watch  # Watch mode
npm run test:coverage  # Coverage report
```

**Important:** The frontend's Vite dev server proxies `/api` requests to `http://localhost:8081` (configured in Vite). This allows API calls to work during development without CORS issues.

### Backend Dev

```bash
cd backend
pip install -r requirements-dev.txt
python main.py      # Start server (port 8081)
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

**Important:** Backend requires `.env` file with InfluxDB and LLM credentials. See `.env.example`.

### Local Docker (Full Stack)

```bash
docker-compose up
# Backend: http://localhost:8081
# Frontend: http://localhost:3000
# InfluxDB UI: http://localhost:8086 (if included in compose)
```

---

## Key Conventions

### Code Style

**Frontend:**
- TypeScript, React functional components with hooks
- Zustand for state management (no context API)
- TailwindCSS v3 for styling (must use `@apply` in component files, not inline)
- Recharts for charts, Framer Motion for animations
- Jest + React Testing Library for tests

**Backend:**
- Python with type hints (PEP 484)
- FastAPI route handlers with async/await
- Pydantic models for request/response validation
- Pytest for unit and integration tests
- Uvicorn as ASGI server

**CSS:**
- TailwindCSS v3 with custom components in `frontend/index.css`
- PostCSS for processing (must use `postcss.config.cjs` in ESM projects)
- `@import` directives must come **before** `@tailwind` directives in CSS files

### Branch Naming

- **Feature:** `feature/description` (e.g., `feature/chatbot-v2`)
- **Bug fix:** `fix/description` (e.g., `fix/chart-rendering-issue`)
- **Refactor:** `refactor/description` (e.g., `refactor/state-management`)
- **Docs:** `docs/description`
- **Chore:** `chore/description`

### Commit Messages

Follow the format: `<type>: <description>` where type is one of:
- `feat` — New feature
- `fix` — Bug fix
- `refactor` — Code refactor
- `chore` — Build, deps, tooling
- `docs` — Documentation
- `test` — Test changes
- `perf` — Performance improvement

Examples:
- `feat: add AHU health scoring algorithm`
- `fix: resolve CORS issue on /api/chat endpoint`
- `refactor: extract Dashboard component into smaller modules`
- `docs: update CLAUDE.md with deployment instructions`

### File Organization

- **React components**: Each component in its own file, optionally with a `.module.css` file
- **Backend modules**: Related logic grouped in `core/`, `routes/`, `llm/`, `rag/` directories
- **Python packages**: Use `__init__.py` to define public APIs
- **Tests**: Mirror source structure (e.g., `backend/routes/test_dashboard.py` for `backend/routes/dashboard.py`)

---

## API Endpoints

### Dashboard & Metrics

- `GET /api/dashboard/trend?level=N&range=...` — Health index time series for a building level
- `GET /api/dashboard/ranking?level=N&range=...` — Top/worst AHU rankings for a level
- `GET /api/health-scores` — Overall health metrics
- `GET /api/predictions/{ahu_id}` — Predictive maintenance for a device
- `GET /api/financial-impact` — Cost/savings analysis

### Chat

- `POST /api/chat` — Submit message, get AI response (uses RAG + LLM)

### Query & Data

- `GET /api/query` — Query raw time-series data
- `GET /api/measurements/{ahu_id}` — Raw sensor measurements

---

## Important Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app setup, route registration, middleware config |
| `backend/config.py` | Environment variables, API keys, configuration |
| `backend/models/schemas.py` | Data models, AHU_LEVEL_CONFIG (device IDs) |
| `frontend/src/App.tsx` | Root React component |
| `frontend/src/store/useAppStore.ts` | Zustand store (single source of truth) |
| `frontend/src/index.css` | Global styles (TailwindCSS + custom) |
| `frontend/vite.config.ts` | Vite build and dev server config |
| `docs/CONSTITUTION.md` | Tech stack, AHU convention, architecture |
| `docker-compose.yml` | Local dev environment setup |
| `Dockerfile` | Production container image |
| `.github/workflows/` | CI/CD pipelines |

---

## AHU ID Convention

**Format:** `e[LEVEL][NN]`

- `LEVEL` = two-digit building level (01–11)
- `NN` = two-digit device number (01–21 depending on level)
- **Validation regex:** `^e\d{4}$`
- **Examples:** `e0101` (Level 1, AHU 1), `e0507` (Level 5, AHU 7), `e1108` (Level 11, AHU 8)

**Rule:** Never invent or guess device IDs. Only reference devices that exist in `backend/models/schemas.py → AHU_LEVEL_CONFIG`.

Level distribution:
```
L1: 21  L2: 15  L3: 16  L4: 13  L5: 12
L6: 11  L7:  4  L8:  5  L9:  8  L10: 8  L11: 8
```

---

## Testing

### Frontend

```bash
cd frontend
npm test                    # Run all tests
npm run test:watch         # Watch mode
npm run test:coverage      # Generate coverage report
```

Uses Jest with React Testing Library. Test files should be colocated with components (e.g., `Button.test.tsx` next to `Button.tsx`).

### Backend

```bash
cd backend
python -m pytest tests/ -v
python -m pytest tests/ -v --cov=. --cov-report=term-missing  # With coverage
python -m pytest tests/ -k "test_dashboard" -v  # Run specific test
```

---

## Deployment

### Local (Docker Compose)

```bash
docker-compose up --build
# Backend: http://localhost:8081
# Frontend: http://localhost:3000
```

### Production Build

**Frontend:**
```bash
cd frontend
npm run build
# Output: frontend/dist/
# Deploy to Vercel or any static host
```

**Backend:**
```bash
# Docker image builds both frontend and backend
docker build -t wach-insight:latest .
docker run -p 8081:8081 wach-insight:latest
```

Environment variables must be set via `.env` file or `VERCEL_ENV` / Docker secrets.

---

## State Management (Frontend)

**Zustand store** (`frontend/src/store/useAppStore.ts`) is the single source of truth. All components import and use hooks from this store:

```typescript
import { useAppStore } from '@/store/useAppStore';

function MyComponent() {
  const { selectedLevel, dashboardData } = useAppStore();
  // Use state directly, no prop drilling
}
```

**Important:** Do NOT use React Context API or prop drilling. Zustand avoids unnecessary re-renders and keeps the component tree flat.

---

## Common Patterns

### Adding a New API Endpoint

1. Create route file in `backend/routes/` (e.g., `backend/routes/my_feature.py`)
2. Define FastAPI route with type hints
3. Register router in `backend/main.py`: `app.include_router(router, prefix="/api")`
4. Test with `pytest`

### Adding a React Component

1. Create component file in `frontend/src/components/`
2. Use TypeScript with strict mode
3. Import Zustand store if state is needed (no props)
4. Add tests colocated with the component

### Styling

- Use TailwindCSS utility classes in JSX
- For complex styles, use `@apply` in CSS files
- Avoid inline CSS; use TailwindCSS tokens
- Custom colors defined in `tailwind.config.cjs`

---

## Debugging

**Frontend:**
- React DevTools browser extension
- `console.log()` statements
- Browser DevTools Network tab for API calls

**Backend:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Debug: {variable}")
```

Run with `python main.py` to see logs in stdout.

---

## Notes for Claude

- **State management**: Use Zustand store directly in components; avoid prop drilling
- **Lazy loading**: Some components are code-split for performance; check dynamic imports in App.tsx
- **Mock data**: Use `frontend/src/mocks/generateMockData.ts` for testing UI without backend
- **CSS**: TailwindCSS v3 + PostCSS; `@import` directives must come before `@tailwind`
- **Type safety**: Maintain type hints in backend; use TypeScript strictly in frontend
- **Device validation**: Always validate AHU IDs against `AHU_LEVEL_CONFIG` in backend
- **LLM integrations**: Two providers available — Gemini 2.0 Flash (cloud) and Qwen (local via LM Studio)
- **RAG context**: ChromaDB stores vectorized building knowledge; chat uses this for answers

---

## Current Development Status

**Phase 1 (First Impressions & CI Scaffold):** In progress
- Completed: `.gitignore`, file reorganization, CI/release workflows
- Current: Documentation and verification tasks

**Phase 5 (Layered Documentation):** Planned for rollout in 2026-04-08+

See `docs/superpowers/plans/` and `docs/superpowers/specs/` for detailed plans and specifications.

---

## Quick Reference Links

- **Constitution**: `docs/CONSTITUTION.md` — Tech stack, conventions
- **API Reference**: `API.md` — Endpoint details
- **Deployment**: `DEPLOYMENT.md` — Deployment instructions
- **Plans**: `docs/superpowers/plans/` — Phase implementation plans
- **Specs**: `docs/superpowers/specs/` — Feature specifications
