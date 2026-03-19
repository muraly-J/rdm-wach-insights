# WACH Insight Backend - Docker Image
# ====================================
# Containerizes the FastAPI backend for electrical health analytics.
#
# Usage:
#   docker build -t wach-insight-backend .
#   docker run -d --name wach-backend -p 8000:8000 wach-insight-backend
#
# Environment Variables (required):
#   - INFLUX_URL     : InfluxDB server URL (e.g., http://localhost:8086)
#   - INFLUX_TOKEN   : InfluxDB API token
#   - INFLUX_ORG     : InfluxDB organization name (default: wach)
#   - INFLUX_BUCKET  : InfluxDB bucket name (default: wach_bucket_3)
#   - CORS_ORIGINS   : Allowed frontend origins (comma-separated)
#   - API_KEY        : Bearer token for API authentication

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Use backend/requirements.txt (root requirements.txt is incomplete)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend

# Copy data files required at startup
COPY data ./data

# paraquet_data holds optional model artifacts; create dir so imports don't fail
RUN mkdir -p paraquet_data

# Railway injects PORT — bind to it
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
