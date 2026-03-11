# WACH Insight

Conversational AHU energy analytics for the WACH ward.

## Security Features

- **HTTPS Enforcement**: InfluxDB connections must use HTTPS in production
- **API Authentication**: All `/api` endpoints require a valid API key
- **Rate Limiting**: Default 20 requests per minute (configurable)
- **Input Validation**: Device IDs and metrics are strictly validated
- **Flux Query Sanitization**: Regex injection prevented via escaping
- **CORS Hardening**: Restricted origins, methods, and headers

See `docs/security/SECURITY_AUDIT_2026.md` for complete security audit details.

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

### Required (Security)
| Variable | Description | Example |
|----------|-------------|---------|
| `INFLUX_URL` | InfluxDB URL (HTTP for localhost, HTTPS for production) | http://localhost:8086 or https://cloud.influxdata.com |
| `INFLUX_TOKEN` | API token with read access | inflx_token_abc123... |
| `API_KEY` | API key for /api authentication | prod_api_key_xyz789 |

### Optional (Security)
| Variable | Description | Default |
|----------|-------------|---------|
| `DEV_API_KEY` | Development-only API key | dev-key-change-in-production |
| `CORS_ORIGINS` | Comma-separated allowed origins | http://localhost:3000 |
| `RATE_LIMIT_REQUESTS` | Max requests per window | 20 |
| `RATE_LIMIT_WINDOW` | Rate limit window (seconds) | 60 |

### InfluxDB Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `INFLUX_ORG` | Organization name | wach |
| `INFLUX_BUCKET` | Bucket name | wach_bucket_3 |

### LLM Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_LLM` | Set to "true" for AI query translation | false |
| `LMS_BASE_URL` | LM Studio URL (if ENABLE_LLM=true) | http://localhost:1234/v1 |
| `LMS_MODEL` | Model name in LM Studio | qwen/qwen3-coder-next |
| `LMS_API_KEY` | LLM API key (if required) | lm-studio |

### Required for Production
```
INFLUX_URL=https://your-influxdb-host.cloud.influxdata.com
INFLUX_TOKEN=secure-token-from-cloud
API_KEY=generate-strong-random-string

# For local development, you can use HTTP:
INFLUX_URL=http://localhost:8086
```

## Files

- `backend/main.py` - FastAPI backend
- `frontend/` - React + Vite frontend
- `DEPLOYMENT.md` - Detailed deployment guide
