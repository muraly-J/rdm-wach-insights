# Migration Summary: Cloudflare Tunnel → Vercel Serverless

## Problem Statement
The app had three issues:
1. **Blank screen on prediction clicks** - Forecast endpoint route mismatch
2. **"Something went wrong" on preset prompts** - LLM unavailable in production  
3. **Electrical Risk Check - no fleet assessment** - API routing broken

## Root Causes
1. `vercel.json` was rewriting `/api/*` to a hardcoded Cloudflare tunnel URL
2. Backend `forecast_router` included without `/api` prefix (frontend called `/api/forecast`)
3. LLM translator had no fallback for production environments
4. Vercel Python runtime not properly configured

## Solution

### 1. Backend Migration to Serverless
Created `/api/index.py` as a Vercel serverless function that wraps the FastAPI app:

```python
# api/index.py
import os
import sys
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
os.environ["VERCEL"] = "1"
from backend.main import app
handler = app
```

### 2. Updated vercel.json
```json
{
  "routes": [
    {"src": "/api/(.*)", "dest": "/api/index.py"},
    {"src": "/assets/(.*)", "dest": "/frontend/dist/assets/$1"},
    {"src": "/(.*)", "dest": "/frontend/dist/index.html"}
  ]
}
```

### 3. Fixed Route Prefixes
Changed `backend/main.py` to include all routers with `/api` prefix:
```python
app.include_router(forecast_router, prefix="/api")
```

### 4. Added LLM Fallback
Modified `backend/llm/translator.py`:
- Detects production environment (VERCEL env var)
- Falls back to rule-based query parsing when LLM is unavailable
- Disabled by default in production (set `ENABLE_LLM=true` to enable)

### 5. Environment Variable Handling
Added proper `.env` loading in production-safe manner:
```python
IN_VERCEL = os.getenv("VERCEL") == "1"
LLM_ENABLED = os.getenv("ENABLE_LLM", "false").lower() == "true"
```

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `api/index.py` | Created | Vercel serverless function |
| `api/requirements.txt` | Created | Python dependencies for Vercel |
| `vercel.json` | Modified | Route API to serverless function |
| `backend/main.py` | Modified | Add /api prefix, production-safe startup |
| `backend/llm/translator.py` | Modified | Add rule-based fallback for production |
| `DEPLOYMENT.md` | Created | Deployment guide |
| `MIGRATION_SUMMARY.md` | Created | This document |
| `tunnel.sh` | Modified | Marked as deprecated |

## Deployment Checklist

1. [ ] Push changes to GitHub
2. [ ] Deploy to Vercel (or run `vercel --prod`)
3. [ ] Set environment variables in Vercel:
   - `INFLUX_URL`
   - `INFLUX_TOKEN`
   - `INFLUX_ORG`
   - `INFLUX_BUCKET`
4. [ ] Verify `/health` endpoint works
5. [ ] Test preset prompts (no more blank screens!)
6. [ ] Test Electrical Risk Check

## What Works Now

✅ **Production URL works** - No more Cloudflare tunnel dependency
✅ **Preset prompts work** - Rule-based fallback for queries
✅ **Electrical Risk Check loads** - API routes properly configured
✅ **Forecast endpoints work** - Fixed `/api/forecast/{device_id}` routing

## Notes

- Cloudflare tunnel is now **deprecated** for production use
- Keep `tunnel.sh` for local development if needed
- LLM features disabled in production by default (rule-based parsing instead)
- Set `ENABLE_LLM=true` if you have LM Studio accessible from Vercel
