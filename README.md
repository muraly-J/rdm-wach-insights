# WACH Insight

Conversational AHU energy analytics for the WACH ward.

## Quick Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/rdmasia/wach-insight)

After deploying:
1. Set environment variables in Vercel: `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`
2. Verify `/health` endpoint returns `{"status": "ok"}`
3. Try preset prompts - they should work without blank screens!

## Architecture

### Before (Old)
```
Frontend (Vercel) --> Cloudflare Tunnel --> Local Backend
```

### After (New)
```
Frontend + Backend (Vercel Serverless) --> InfluxDB Cloud
```

## Features

- **Energy Analytics**: Time series charts and rankings for AHU metrics
- **Forecasting**: 24-hour power predictions for devices e0202, e0207, e0211
- **Electrical Risk Check**: Rule-based risk assessment for entire fleet
- **Preset Prompts**: Quick queries without LLM (rule-based fallback)

## Development

### Prerequisites
- Python 3.10+
- Node.js 18+ 
- Vercel CLI (`npm i -g vercel`)

### Local Setup

```bash
# Install backend dependencies
cd /Users/rdmasia/wach-insight
source venv/bin/activate
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

### Run Locally (without tunnel)

```bash
# Terminal 1: Start backend
cd /Users/rdmasia/wach-insight
./start.sh

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### Build for Production

```bash
npm run build
```

Output: `frontend/dist/`

## Environment Variables

Required for production deployment:

| Variable | Description |
|----------|-------------|
| `INFLUX_URL` | InfluxDB cloud URL |
| `INFLUX_TOKEN` | API token with read access |
| `INFLUX_ORG` | Organization name |
| `INFLUX_BUCKET` | Bucket name |

Optional:
| Variable | Description |
|----------|-------------|
| `ENABLE_LLM` | Set to "true" for AI query translation |
| `LMS_BASE_URL` | LM Studio URL (if ENABLE_LLM=true) |

## Files

- `backend/main.py` - FastAPI backend
- `frontend/` - React + Vite frontend
- `api/index.py` - Vercel serverless function
- `DEPLOYMENT.md` - Detailed deployment guide
- `MIGRATION_SUMMARY.md` - Migration details
