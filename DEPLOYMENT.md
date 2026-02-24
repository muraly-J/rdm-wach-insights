# Deployment Guide: WACH Insight

## Architecture Changes

### Before (Cloudflare Tunnel)
```
Frontend (Vercel) --> Cloudflare Tunnel --> Local Backend (FastAPI on port 8000)
```
- Required local server running with `gunicorn`
- Cloudflare tunnel URL changed on every restart
- API calls failed when tunnel was down

### After (Vercel Serverless)
```
Frontend + Backend (Both on Vercel) --> InfluxDB (Cloud)
```
- Fully hosted on Vercel
- No tunnel required
- Backend runs as serverless function

## Deployment Steps

### 1. Deploy Frontend
```bash
cd frontend
npm install
npm run build
```
The build output goes to `frontend/dist/`

### 2. Deploy Backend (Serverless)
Your backend is now configured to run as a Vercel serverless function.

#### Option A: Deploy via Vercel CLI
```bash
# Install Vercel CLI if not already installed
npm i -g vercel

# Deploy everything at once
vercel

# Or link to existing project
vercel --prod
```

#### Option B: Deploy via GitHub Integration
1. Push your code to GitHub
2. Connect your repo to Vercel dashboard
3. Add environment variables (see below)
4. Deploy

### 3. Environment Variables
Add these to your Vercel project settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `INFLUX_URL` | InfluxDB cloud URL | `https://us-east-1-1.aws.cloud.influxdata.com` |
| `INFLUX_TOKEN` | API token for InfluxDB | `your-influx-token-here` |
| `INFLUX_ORG` | Your organization name | `wach` |
| `INFLUX_BUCKET` | Bucket name | `wach_bucket_3` |

Optional (for LLM features in production):
| Variable | Description |
|----------|-------------|
| `ENABLE_LLM` | Set to `true` to enable AI translation |
| `LMS_BASE_URL` | LM Studio URL (only if using LLM) |

## Production Behavior

### Without LLM (Default)
- Queries use rule-based parsing
- Device IDs, metrics, and time ranges are extracted from text
- Works without any external LLM server

### With LLM (Optional)
Set `ENABLE_LLM=true` in Vercel environment variables:
- Queries are sent to LM Studio for translation
- Requires `LMS_BASE_URL` pointing to your LM Studio instance

## Troubleshooting

### "Model file not found" error
The forecast models are in `paraquet_data/models/saved/`. Make sure this directory is included when deploying:
```bash
# Check the models exist
ls -la paraquet_data/models/saved/
```

### "Could not reach InfluxDB" error
1. Check `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG` are set
2. Verify your InfluxDB token has read access to the bucket
3. Check `INFLUX_BUCKET` matches your actual bucket name

### "No assessments available" on Electrical Risk
1. Check InfluxDB has data for all devices
2. Verify device IDs match the pattern `e0101` through `e1108`

## Local Development

Run with gunicorn (without tunnel):
```bash
cd /Users/rdmasia/wach-insight
source venv/bin/activate
gunicorn -c gunicorn.conf.py backend.main:app
```

Run frontend dev server:
```bash
cd frontend
npm run dev
```

## Cloudflare Tunnel (Still Available)

The tunnel script still exists if you need it for local development:
```bash
# Start backend
./start.sh

# In separate terminal, start tunnel
./tunnel.sh
```

But for production deployment, the Cloudflare tunnel is no longer needed.
