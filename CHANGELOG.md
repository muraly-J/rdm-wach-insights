# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.5.0] — 2026-04-14

### Added
- User guide for hospital staff (`docs/user-guide.md`)
- Developer guide for engineers (`docs/developer-guide.md`)
- Comprehensive API reference covering all 22 endpoints (`docs/api-reference.md`)
- System overview architecture diagram (`docs/architecture/system-overview.md`)
- Chat pipeline architecture diagram (`docs/architecture/chat-pipeline.md`)
- `README.md` documentation hub with links to all layered docs

## [1.4.0] — 2026-04-13

### Added
- AHU on/off period shading across all single-device charts (offPeriods API)
- Enhanced device ID handling with fallback naming in fleet directory and rankings
- LatestOverview dashboard as empty state replacement
- Per-device off-periods detection and visualization

### Fixed
- Resolve Python 3.9 compatibility issues across backend
- Remove dead code (showColorSegments prop, orphaned MeasurementHistoryChart offPeriods)
- Fix E402 import order, B904 exception handling, F811 duplicates, F821 undefined names
- Restore missing whitespace fixes (W293, W291)

### Changed
- Prettier check now gates CI pipeline for TS/TSX files
- Ruff linter auto-fixes applied (614 violations across backend)
- Settings singleton replaces direct os.getenv calls for configuration
- Deep Dive mode greyed out until a device is selected

## [1.3.0] — 2026-04-10

### Added
- AHU on/off period shading design specification and implementation plan
- GET `/api/on-off-periods/{ahu_id}` endpoint for fetching on/off periods
- `get_off_periods` function in db_reader for DuckDB queries
- OffPeriod type and fetchOffPeriods client function for frontend
- renderOffPeriodAreas utility for Recharts ReferenceArea shading

## [1.2.0] — 2026-03-30

### Added
- Agentic chatbot V2: tool-augmented generation with 5 tools (HealthDB, InfluxDB, RAG, financial, site_summary)
- Persona detection: auto-classifies queries as general / technical / technician / financial
- ChromaDB RAG knowledge base for WACH domain documents
- Query complexity routing: `/think` vs `/no_think` prefix for Qwen inference

### Changed
- LevelSelectorBar now uses Zustand store directly instead of prop drilling
- Chat message ID generation and state management improved via Zustand

### Fixed
- useEffect dependencies fixed in DeepDive component
- Extracted metric hook and chart configuration

## [1.1.0] — 2026-03-10

### Added
- Full dark luxury UI redesign: `#0B0F14` background, `#00E5A0` teal-green accent
- Plus Jakarta Sans / DM Sans / JetBrains Mono font stack
- Single-page scroll layout: WelcomeHero → DashboardGate → LevelSelectorBar → Dashboard
- ScoreDerivationSection lazy-loaded (code-split)

### Fixed
- CSS import order: `@import url(...)` must precede `@tailwind` directives
- `index.css` was not imported in `main.tsx`
- Tailwind v3 requires `postcss.config.cjs` (project is ESM)
- LevelSelectorBar: used Zustand store directly instead of missing props

## [1.0.0] — 2025-09-01

### Added
- Initial release: FastAPI backend + React + Vite + TypeScript + Tailwind frontend
- InfluxDB time-series integration for AHU electrical data (11 levels, ~120 AHU devices)
- Dashboard: health index trend charts and AHU ranking per level
- Basic chatbot with preset prompts
- Docker Compose deployment with Gunicorn + Nginx
