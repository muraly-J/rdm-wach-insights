# Vercel Deployment Guide for WACH Insight

## Overview
This document describes the changes made to enable Vercel deployment for WACH Insight.

## Architecture

### Before
```
Frontend (Vercel) --> Cloudflare Tunnel --> Local Backend (port 8000)
```
- Required local server running
- Cloudflare tunnel URL changed on every restart
- API calls failed when tunnel was down

### After (Fixed)
```
Frontend + Backend (Both on Vercel) --> InfluxDB Cloud
```
- Fully hosted on Vercel
- No tunnel required
- Backend runs as serverless function

## Files Modified/Created

### 1. `api/index.py` (REPLACED)
**Issue**: Was a placeholder handler that returned static response.

**Fix**: Implemented full ASGI wrapper to bridge Vercel's Lambda event format with FastAPI:
- Converts incoming HTTP requests to ASGI scope
- Forwards requests to `backend/main.py`
- Properly handles headers, query params, and body
- Supports all HTTP methods (GET, POST, PUT, DELETE)

### 2. `backend/main.py` (UPDATED)
**Changes**:
- Added `IN_VERCEL` detection flag
- Skip query logger initialization in Vercel (read-only filesystem)
- Static files only mount when not in Vercel

### 3. `backend/middleware/query_logger.py` (UPDATED)
**Issue**: SQLite database write would fail on Vercel's read-only filesystem.

**Fix**:
- Detect Vercel environment via `VERCEL` env var
- Gracefully disable logging when not writable
- Log silently without crashing the request

### 4. `backend/routes/query.py` (FIXED)
**Issue**: HTTP status code 52 used instead of valid HTTP status code.

**Fix**: Changed `status_code=52` to `status_code=502`

### 5. `backend/routes/forecast.py` (UPDATED)
**Issue**: Model file paths hardcoded to incorrect location.

**Fix**:
- Dynamic path resolution that works in both local and Vercel
- Path goes up 3 levels from `backend/routes/forecast.py` to project root
- Multiple fallback paths for robustness

### 6. `backend/requirements.txt` (UPDATED)
**Added missing dependencies**:
- `joblib==1.3.2` (for XGBoost model loading)
- `xgboost==2.0.3` (for forecast models)

### 7. `vercel.json` (UPDATED)
**Changes**:
- Added version 2
- Added CORS headers for API routes
- Set Python version to 3.11
- Configured function maxDuration

### 8. `requirements.txt` (UPDATED)
**Added missing dependencies**:
- `joblib==1.3.2`
- `xgboost==2.0.3`

## Deployment Steps

### 1. Prepare Repository
```bash
# Ensure all changes are committed to dev branch
git add .
git commit -m "Fix Vercel deployment issues"
git push origin dev
```

### 2. Deploy via Vercel CLI
```bash
# Install Vercel CLI if not already installed
npm i -g vercel

# Deploy to production
vercel --prod
```

### 3. Set Environment Variables in Vercel
In the Vercel dashboard, add these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `INFLUX_URL` | InfluxDB cloud URL | `https://us-east-1-1.aws.cloud.influxdata.com` |
| `INFLUX_TOKEN` | API token with read access | `your-influx-token-here` |
| `INFLUX_ORG` | Your organization name | `wach` |
| `INFLUX_BUCKET` | Bucket name | `wach_bucket_3` |

**Optional (for LLM features)**:
| Variable | Description |
|----------|-------------|
| `ENABLE_LLM` | Set to "true" for AI query translation |
| `LMS_BASE_URL` | LM Studio URL (if using LLM) |

### 4. Deploy Model Files
The model files are already tracked in git at `paraquet_data/models/saved/`. Ensure they're committed:
```bash
git add paraquet_data/models/saved/*.pkl
git commit -m "Add forecast model files"
```

## API Endpoints Available

After deployment, the following endpoints will be available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check endpoint |
| `/api/query` | POST | Main query endpoint (natural language to InfluxDB) |
| `/api/forecast/{device_id}` | GET | 24-hour power forecast for devices |
| `/api/electrical-risk` | GET | Fleet-wide electrical risk assessment |
| `/api/electrical-risk/{ahu_id}` | GET | Single AHU risk details |
| `/api/electrical-risk/summary` | GET | Fleet summary with tier distribution |

## Troubleshooting

### Issue: "Model file not found"
**Solution**: Ensure `paraquet_data/models/saved/*.pkl` files are committed and deployed.

### Issue: "Could not reach InfluxDB"
**Solution**: Verify environment variables are set in Vercel dashboard:
- `INFLUX_URL`
- `INFLUX_TOKEN`
- `INFLUX_ORG`
- `INFLUX_BUCKET`

### Issue: "Query logging failed" (expected behavior)
**Explanation**: Query logging is automatically disabled in Vercel due to read-only filesystem. This is expected and does not affect API functionality.

### Issue: "Function timeout"
**Solution**: The maxDuration is set to 30 seconds. If queries take longer:
- Check InfluxDB connection
- Reduce time range in queries
- Contact administrator about increasing timeout

## Testing Deployment

After deployment, test the endpoints:

```bash
# Test health endpoint
curl https://your-app.vercel.app/api/health

# Test query endpoint (requires InfluxDB data)
curl -X POST https://your-app.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"user_query": "Show e0101 power last 7 days"}'

# Test forecast endpoint (requires model files)
curl https://your-app.vercel.app/api/forecast/e0202
```

## Files Not Changed

The following files were reviewed but did not require changes:

- `frontend/` - No changes needed (build output served via Vercel rewrites)
- `backend/core/risk_engine.py` - Already correctly implemented
- `backend/core/influx_client.py` - Only needed graceful env var handling

## Rollback Plan

If deployment issues occur:
```bash
# Deploy previous version from git
vercel --prod --prod
```

Or revert the changes on dev branch and redeploy.
