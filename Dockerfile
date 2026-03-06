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
#   - LMS_BASE_URL   : LM Studio server URL (for LLM queries)
#   - CORS_ORIGINS   : Allowed frontend origins (comma-separated, default: http://localhost:3000)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend ./backend

# Copy data directory (for health score CSVs and metadata)
COPY data ./data

# Copy paraquet_data (for forecast models if any)
COPY paraquet_data ./paraquet_data

# Copy environment example (for reference)
COPY .env.example* ./

# Expose backend port
EXPOSE 8000

# Run the backend server
# --host 0.0.0.0 allows connections from outside Docker network
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
