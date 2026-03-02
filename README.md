# WACH Insight

Conversational AHU energy analytics for the WACH ward.

## Architecture

### Local Development
```
Frontend (localhost:3000) --> Backend API (localhost:8081) --> InfluxDB Cloud
```

### Deployment
For production deployment, run the backend on a server and update `CORS_ORIGIN` to allow requests from your domain.

## Features

- **Energy Analytics**: Time series charts and rankings for AHU metrics
- **Forecasting**: 24-hour power predictions for devices e0202, e0207, e0211
- **Electrical Risk Check**: Rule-based risk assessment for entire fleet
- **Preset Prompts**: Quick queries without LLM (rule-based fallback)

## Development

### Prerequisites
- Python 3.10+
- Node.js 18+

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

### Run Locally

```bash
# Terminal 1: Start backend
cd /Users/rdmasia/wach-insight
./start.sh

# Terminal 2: Start frontend
cd frontend
npm run dev
```

Open http://localhost:3000 in your browser.

## Environment Variables

### Required
| Variable | Description | Default |
|----------|-------------|---------|
| `INFLUX_URL` | InfluxDB cloud URL | (required) |
| `INFLUX_TOKEN` | API token with read access | (required) |
| `INFLUX_ORG` | Organization name | wach |
| `INFLUX_BUCKET` | Bucket name | wach_bucket_3 |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGIN` | Allowed origins for CORS | http://localhost:3000 |
| `ENABLE_LLM` | Set to "true" for AI query translation | false |
| `LMS_BASE_URL` | LM Studio URL (if ENABLE_LLM=true) | http://localhost:1234/v1 |

## Files

- `backend/main.py` - FastAPI backend
- `frontend/` - React + Vite frontend
- `DEPLOYMENT.md` - Detailed deployment guide
