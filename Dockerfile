# WACH Insight Backend - Docker Image
# ====================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic (PID-1 safe cron for containers)
ARG SUPERCRONIC_VERSION=0.2.29
RUN curl -fsSL \
    "https://github.com/aptible/supercronic/releases/download/v${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
    -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY data ./data

# Ward topology config — example always present as fallback
COPY ward_config.example.yml ./ward_config.example.yml

# ETL entrypoint scripts
COPY docker/ ./docker/
RUN chmod +x docker/etl-entrypoint.sh

RUN mkdir -p paraquet_data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
