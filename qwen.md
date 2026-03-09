# WACH Insight Project Documentation

## Project Overview

**WACH Insight** is an AHU (Air Handling Unit) analytics dashboard for the Women & Child Ward at Hospital KL. The system analyzes 112+ AHUs using InfluxDB for time-series electrical metrics and provides:

- **Health Scoring**: FAIR (Fairness via Individual Robustness) algorithm assigns health indices 0-100
- **Conversational Interface**: Natural language queries for AHU performance data
- **Predictive Analytics**: 24-hour power predictions using weighted seasonal averages
- **Dashboard Views**: Fleet health rankings, trend charts, and electrical risk assessment

### Key Technologies

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python), Uvicorn worker, Gunicorn |
| Frontend | React + Vite |
| Database | InfluxDB (bucket: wach_bucket_3) |
| Scoring | Rule-based FAIR algorithm (no ML training needed) |

## Directory Structure

```
wach-insight/
├── backend/                   # FastAPI server
│   ├── core/                 # Business logic
│   │   ├── charts.py         # Chart builder utilities
│   │   ├── fair_health_scoring.py    # FAIR scoring engine (per-AHU baseline)
│   │   ├── influx_client.py  # InfluxDB query client
│   │   ├── risk_engine.py    # Health scoring engine (FAIR algorithm)
│   │   └── summarizer.py     # LLM response summarization
│   ├── llm/                  # LLM query translation
│   │   ├── prompts.py        # System prompt for translator.py
│   │   └── translator.py     # Converts natural language to structured queries
│   ├── middleware/           # Request handling
│   │   ├── query_logger.py   # Logs all queries to database
│   │   └── validator.py      # Input validation middleware
│   ├── models/               # Data schemas
│   │   └── schemas.py        # Pydantic models and allowed values
│   ├── routes/               # API endpoints
│   │   ├── dashboard.py      # Fleet Dashboard endpoints
│   │   ├── electrical_risk.py
│   │   └── forecast.py       # Prediction endpoints (e0202, e0207, e0211)
│   │   └── query.py          # Main LLM query endpoint
│   ├── main.py               # FastAPI application entry point
│   └── config.py             # Environment configuration
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── AhuHealthTrendDashboard.jsx  # Fleet Dashboard
│   │   │   ├── ChatPanel.jsx      # LLM query input panel
│   │   │   ├── ChatView.jsx       # Main chat interface
│   │   │   ├── ElectricalRiskView.jsx  # Risk analysis view
│   │   │   └── OutputPanel.jsx    # LLM response output
│   │   ├── api.js              # Frontend API client
│   │   ├── App.jsx             # Main app component
│   │   └── main.jsx            # React entry point
│   ├── dist/                   # Production build output
│   └── vite.config.js          # Vite bundler configuration
├── scripts/                    # Automation & utilities
│   ├── etl/                    # ETL pipeline scripts
│   │   ├── history_generator.py
│   │   ├── run_health_etl.py        # Health scoring ETL
│   │   └── run_prediction_etl.py    # Prediction ETL
│   ├── fetch/                  # Data fetching utilities
│   │   ├── fetch_all_ahus_latest.py
│   │   └── fetch_raw_data.py
│   ├── generate/               # Score generation scripts
│   │   ├── generate_level1_health_scores.py
│   │   ├── generate_all_levels_health_scores.py
│   │   └── generate_fair_health_scores.py
│   ├── test/                   # Test scripts
│   │   └── test_backend_presets.py, etc.
│   └── scheduler/              # Automated execution
│       ├── scheduler.py        # Continuous 30-min loop
│       └── *.sh                # LaunchAgent setup scripts
├── docs/                       # Documentation & archives
│   ├── architecture/           # Architecture docs
│   │   ├── learning_history.md
│   │   └── qwen_archived.md
│   ├── etl_reports/            # ETL pipeline documentation
│   ├── scoring/                # FAIR health scoring docs
│   ├── implementation/         # Feature implementation reports
│   ├── automation/             # Automation setup docs
│   ├── planning/               # Project plans (PRD, jinendra_plan)
│   ├── weekly/                 # Weekly progress logs
│   └── archive/                # Backed-up files
├── data/                       # Generated output CSVs
│   ├── health_all_levels.csv
│   ├── predictions.csv
│   └── level1_hourly_health_*.csv (time range variants)
├── paraquet_data/              # Parquet data storage
├── logs/                       # Log files
│   ├── health_etl.log
│   ├── prediction_etl.log
│   └── scheduler.log
└── tests/                      # Unit and integration tests
```

## Health Scoring: FAIR Algorithm

### Core Principle

Each AHU's health score uses **60% relative** (per-AHU baseline) + **40% absolute** (fleet percentile):

```
Health Index = 100 - weighted_penalty × 100

Where: weighted_penalty = 
    energy_anomaly     × 0.15
    + power_factor     × 0.25
    + phase_imbalance  × 0.25
    + thd_drift        × 0.15
    + overload         × 0.20
```

### Scoring Components

#### 1. Energy Anomaly (weight: 0.15)
- **Relative**: Z-score comparing to each AHU's historical delta_kwh mean
- **Absolute**: Percentile rank within fleet distribution
- Uses hourly `delta_kwh` (not cumulative energy)

#### 2. Power Factor Degradation (weight: 0.25)
- **Relative**: Z-score comparing to each AHU's historical PF mean
- **Absolute**: Percentile rank within fleet distribution
- **Load Discount**: If running <60% of own mean power, penalize less

#### 3. Phase Imbalance (weight: 0.25)
- **Relative**: Z-score comparing to each AHU's historical imbalance mean
- **Absolute**: Percentile rank within fleet distribution

#### 4. THD Drift (weight: 0.15)
- **Relative**: Z-score comparing to each AHU's historical THD mean
- **Absolute**: Percentile rank within fleet distribution

#### 5. Overload (weight: 0.20)
- Uses p95 ceiling per AHU for normalization
- Compare current power to historical max acceptable load

### Health Index Tiers

| Tier | Range | Color |
|------|-------|-------|
| Healthy | 80-100 | Green |
| Monitor | 60-79 | Yellow/Amber |
| Maintenance Soon | 40-59 | Orange |
| Critical | 0-39 | Red |

### Why Robust Stats (Median + MAD)?

For well-behaved distributions: median ≈ mean and MAD-std ≈ regular std.
Robust stats are strictly better because they handle outliers:

- e0111 has L1 THD alternating between ~14% and ~97% (bimodal)
- Mean = 52%, std = 40% — useless as a baseline
- Median = 15.4%, MAD-std = 3.5% — correctly identifies normal state

## Building and Running

### Prerequisites
- Python 3.9+
- Node.js 18+
- InfluxDB Cloud account with `wach_bucket_3`

### Environment Setup

```bash
# Root directory: /Users/rdmasia/wach-insight

# Create .env file
cp .env.example .env
# Edit .env with your InfluxDB credentials:
INFLUX_URL=https://us-east-1-1.aws.cloud.influxdata.com
INFLUX_TOKEN=your-influx-token-here
INFLUX_ORG=wach
INFLUX_BUCKET=wach_bucket_3
```

### Local Development

```bash
# Terminal 1: Start backend (port 8081)
cd /Users/rdmasia/wach-insight
./start.sh

# Terminal 2: Start frontend (port 3000)
cd frontend
npm run dev

# Open http://localhost:3000 in browser
```

### Build for Production

```bash
cd frontend
npm install
npm run build

# Serve built static files
cd frontend/dist
python3 -m http.server 8080
```

## Development Conventions

### Backend Structure

**Imports use relative paths:**
```python
# Correct:
from core.influx_client import fetch_time_series
from models.schemas import ALLOWED_DEVICES

# Do NOT use absolute imports like:
# from backend.core.influx_client import ...
```

**FastAPI Router Pattern:**
```python
from fastapi import APIRouter

router = APIRouter(prefix="/dashboard")  # NO /api prefix here!

@app.get("/ranking")
async def get_ranking():
    return {"devices": [...]}

# Register in main.py:
app.include_router(router, prefix="/api")  # Adds /api prefix
```

### Script Directory Structure

Scripts are organized by function:

| Folder | Purpose |
|--------|---------|
| `scripts/etl/` | ETL pipelines (fetch → transform → load) |
| `scripts/generate/` | Health score generation |
| `scripts/fetch/` | Raw data fetching utilities |
| `scripts/test/` | Unit and integration tests |
| `scripts/scheduler/` | Automated execution scripts |

**Script Import Pattern:**
```python
import sys
import os

# Add backend to path (scripts/generate → .. → scripts → .. → backend)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from core.influx_client import fetch_time_series
```

### Documentation Structure

| Folder | Contents |
|--------|----------|
| `docs/architecture/` | Architecture docs, learning history |
| `docs/etl_reports/` | 8 ETL pipeline documentation files |
| `docs/scoring/` | FAIR health scoring docs (9 files) |
| `docs/implementation/` | Feature implementation reports (12 files) |
| `docs/automation/` | Automation setup/architecture docs |
| `docs/planning/` | PRD, project plans |
| `docs/weekly/` | Weekly progress logs |
| `docs/archive/` | Backed-up files |

## Key API Endpoints

### Dashboard Routes (no /api prefix)
- `GET /dashboard/ranking` - Fleet health rankings
- `GET /dashboard/trend?level=1&time_range=24h` - Health trends
- `GET /dashboard/summary?level=1&time_range=24h` - LLM summaries

### Query Routes (`/api/query`)
- `POST /api/query` - Natural language → InfluxDB query
  ```json
  { "user_query": "Show power consumption for e0101 last 7 days", "session_id": "uuid" }
  ```

### Forecast Routes (`/api/forecast`)
- `GET /api/forecast/e0202` - 24-hour power prediction
- `GET /api/forecast/e0207` - 24-hour power prediction
- `GET /api/forecast/e0211` - 24-hour power prediction

## Data Flow

```
User Query → LLM Translator → Structured Query → InfluxDB
                                                    ↓
                                        Health Scoring (FAIR)
                                                    ↓
                                        Frontend Dashboard
```

### ETL Pipeline

```python
# Two-phase ETL (runs every 30 minutes via scheduler)

Phase 1: Prediction ETL
├── Fetch energy at t, t-24h, t-168h, t-336h
├── Compute prediction: ŷ(t) = (E(t−24h) + E(t−168h) + E(t−336h)) / 3
└── Compute delta: Δkwh = E(t) − ŷ(t)

Phase 2: Health Scoring ETL
├── Fetch raw metrics from InfluxDB
├── Apply FAIR scoring (per-AHU baseline)
└── Output: health_all_levels.csv
```

## Testing

### Backend Tests
```bash
# Run specific test files
python scripts/test/test_backend_presets.py
python scripts/test/test_fair_scoring.py
```

### Frontend Tests
```bash
cd frontend
npm test                    # Run jest tests
npm run test:coverage       # With coverage report
```

### ETL Pipeline Testing
```bash
# Run health scoring ETL
python scripts/etl/run_health_etl.py --level 1

# Run prediction ETL
python scripts/etl/run_prediction_etl.py --level 1

# Run both
python scripts/etl/history_generator.py --level all
```

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `INFLUX_URL` | Yes | (none) |
| `INFLUX_TOKEN` | Yes | (none) |
| `INFLUX_ORG` | No | wach |
| `INFLUX_BUCKET` | No | wach_bucket_3 |
| `CORS_ORIGIN` | No | http://localhost:3000 |
| `ENABLE_LLM` | No | false |
| `LMS_BASE_URL` | No | http://localhost:1234/v1 |

## AHU ID Convention

| Pattern | Example | Level |
|---------|---------|-------|
| e01xx | e0101, e0105 | Level 1 (21 devices) |
| e02xx | e0207, e0213 | Level 2 |
| ... | ... | ... |
| e11xx | e1103, e1112 | Level 11 |

## Common Tasks

### Regenerate Health Scores
```bash
# All levels, all time ranges
python scripts/generate/generate_all_levels_health_scores.py --all-ranges

# Specific level and time range
python scripts/generate/generate_level1_health_scores.py --range 7d

# Fetch raw data only (for re-scoring later)
python scripts/generate/generate_level1_health_scores.py --fetch-only

# Compute scores from existing raw data
python scripts/generate/generate_level1_health_scores.py --compute-only
```

### Fetch Latest Data
```bash
# All AHUs, latest hourly snapshot
python scripts/fetch/fetch_all_ahus_latest.py

# Level 1 devices only
python scripts/fetch/fetch_all_ahus_latest.py --metrics power_total,energy_import
```

### Start ETL Scheduler (Runs every 30 minutes)
```bash
# Install scheduler as LaunchAgent (macOS)
python scripts/scheduler/install_scheduler.sh

# Or run manually
cd scripts/scheduler && python scheduler.py
```

## Troubleshooting

### "Could not reach InfluxDB"
1. Check `INFLUX_URL`, `INFLUX_TOKEN` are set
2. Verify your InfluxDB token has read access
3. Check `INFLUX_BUCKET` matches your bucket name

### "Backend fails to start"
1. Run `./start.sh` from project root
2. Check logs in `logs/backend.log`
3. Verify Python imports work: `python backend/main.py`

### "Frontend shows no data"
1. Check browser console for API errors
2. Verify backend is running on port 8081
3. Check `data/` folder has CSV files

## File Retention Policy

| Location | Retention |
|----------|-----------|
| `data/` | CSV files kept until manually cleared |
| `logs/` | Logs rotated weekly, keep 4 weeks |
| `paraquet_data/` | Archived raw data (keep until storage limit) |

## Project History

| Date | Event |
|------|-------|
| Feb 2026 | Initial FAIR algorithm implementation (Stage 2B) |
| Feb 25 2026 | Dashboard launch with health index tiers |
| Mar 2026 | ETL pipeline automation (30-min intervals) |
| Mar 2026 | Directory reorganization for maintainability |

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/core/risk_engine.py` | Health scoring engine (FAIR algorithm) |
| `backend/core/fair_health_scoring.py` | Per-AHU baseline scoring |
| `backend/core/influx_client.py` | InfluxDB query client |
| `scripts/etl/run_health_etl.py` | Health scoring ETL pipeline |
| `scripts/etl/run_prediction_etl.py` | Prediction ETL pipeline |
| `frontend/src/components/AhuHealthTrendDashboard.jsx` | Fleet dashboard component |
