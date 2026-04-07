#!/usr/bin/env bash
# docker/etl-entrypoint.sh
# ─────────────────────────
# ETL sidecar entrypoint.
#
# First-run (no sentinel):
#   1. Generate ward-specific RAG docs from ward_config.yml
#   2. Ingest all RAG docs into ChromaDB
#   3. Touch sentinel
#
# Subsequent runs (sentinel exists):
#   Skip init, go straight to supercronic.
#
# To force re-initialisation after updating ward_config.yml:
#   docker compose run etl rm /app/data/.migrated
#   docker compose restart etl
set -euo pipefail

SENTINEL="/app/data/.migrated"
CRON_FILE="/app/docker/etl.cron"

echo "[etl] Starting WACH ETL sidecar"

if [ ! -f "$SENTINEL" ]; then
    echo "[init] First-run detected — starting initialisation"

    echo "[init] Step 1/2 — Generating ward-specific RAG docs..."
    cd /app && python scripts/generate_ward_docs.py
    echo "[init] Ward docs generated."

    echo "[init] Step 2/2 — Ingesting RAG docs into ChromaDB..."
    cd /app/backend && python -m scripts.ingest_all_docs
    echo "[init] RAG ingest complete."

    touch "$SENTINEL"
    echo "[init] Sentinel written: $SENTINEL"
    echo "[init] Initialisation complete."
else
    echo "[init] Sentinel found — skipping initialisation."
fi

SCHEDULE="${ETL_SCHEDULE:-0 * * * *}"
echo "[cron] Starting supercronic with schedule: ${SCHEDULE}"

# Supercronic does not expand shell variables in cron files.
# Generate a resolved cron file with the literal schedule.
RESOLVED_CRON=$(mktemp)
echo "${SCHEDULE} cd /app && python -m scripts.etl.run_prediction_etl --level all" > "$RESOLVED_CRON"
echo "${SCHEDULE} cd /app && python -m scripts.etl.run_health_etl --level all --output-hourly" >> "$RESOLVED_CRON"

exec supercronic "$RESOLVED_CRON"
