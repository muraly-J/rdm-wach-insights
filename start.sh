#!/bin/bash
# start.sh — builds the React frontend and starts Gunicorn
# Run from project root: bash start.sh
# For production use the LaunchAgent instead (com.wach.insight.plist)

set -e  # exit on any error

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT_DIR/venv"
FRONTEND="$PROJECT_DIR/frontend"

echo ""
echo "====================================="
echo "  WACH Insight — Production Start"
echo "====================================="

# 1. Build React frontend
echo ""
echo "[1/2] Building React frontend..."
cd "$FRONTEND"
npm install --silent
npm run build
echo "      ✅ Frontend built → frontend/dist/"

# 2. Start Gunicorn
echo ""
echo "[2/2] Starting Gunicorn..."
cd "$PROJECT_DIR"
source "$VENV/bin/activate"

exec gunicorn \
  -c gunicorn.conf.py \
  backend.main:app