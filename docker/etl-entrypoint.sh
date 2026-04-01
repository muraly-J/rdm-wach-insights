#!/usr/bin/env bash
# docker/etl-entrypoint.sh
# ─────────────────────────
# ETL sidecar entrypoint.
#
# First-run (no sentinel):
#   1. Generate ward-specific RAG docs from ward_config.yml
#   2. Migrate health_hourly.csv → DuckDB (skipped if no CSV)
#   3. Ingest all RAG docs into ChromaDB
#   4. Touch sentinel
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

    echo "[init] Step 1/3 — Generating ward-specific RAG docs..."
    cd /app && python scripts/generate_ward_docs.py
    echo "[init] Ward docs generated."

    echo "[init] Step 2/3 — Migrating CSV to DuckDB (skipped if no CSV)..."
    cd /app && python -m scripts.etl.migrate_csv_to_duckdb || true
    echo "[init] Migration step complete."

    echo "[init] Step 3/3 — Ingesting RAG docs into ChromaDB..."
    cd /app/backend && python -m scripts.ingest_all_docs
    echo "[init] RAG ingest complete."

    touch "$SENTINEL"
    echo "[init] Sentinel written: $SENTINEL"
    echo "[init] Initialisation complete."
else
    echo "[init] Sentinel found — skipping initialisation."
fi

echo "[cron] Starting supercronic with schedule: ${ETL_SCHEDULE:-0 * * * *}"
exec supercronic "$CRON_FILE"
