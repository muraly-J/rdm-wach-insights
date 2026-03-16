#!/bin/bash
# scheduler.sh — Launch script for WACH Insight ETL Scheduler
#
# Usage:
#   bash scripts/scheduler.sh [--interval <minutes>] [--background]
#
# Options:
#   --interval <minutes>  Run interval (default: 30)
#   --background          Run in background with nohup
#
# Examples:
#   bash scripts/scheduler.sh                    # Run once (forever)
#   bash scripts/scheduler.sh --interval 60      # Every hour
#   bash scripts/scheduler.sh --background       # Run in background

set -e  # Exit on error

# Project directory
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPTS_DIR="${PROJECT_DIR}/scripts/scheduler"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"

# Default interval
INTERVAL=30

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --background|-b)
            BACKGROUND=true
            shift
            ;;
        -h|--help)
            echo "Usage: bash scripts/scheduler.sh [--interval <minutes>] [--background]"
            echo ""
            echo "Options:"
            echo "  --interval <minutes>  Run interval (default: 30)"
            echo "  --background, -b      Run in background with nohup"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Check if scheduler.py exists
if [[ ! -f "${SCRIPTS_DIR}/scheduler.py" ]]; then
    echo "[ERROR] scheduler.py not found at ${SCRIPTS_DIR}/scheduler.py"
    exit 1
fi

# Check if Python venv exists
if [[ ! -f "${VENV_PYTHON}" ]]; then
    echo "[ERROR] Python venv not found at ${PROJECT_DIR}/venv/bin/python"
    echo "Run: python -m venv venv"
    exit 1
fi

# Check if data directory exists
mkdir -p "${PROJECT_DIR}/data"
mkdir -p "${PROJECT_DIR}/logs"

echo "[INFO] WACH Insight ETL Scheduler"
echo "  Project: ${PROJECT_DIR}"
echo "  Interval: Every ${INTERVAL} minutes"
echo "  Background: $([ "${BACKGROUND}" = "true" ] && echo 'yes' || echo 'no')"
echo ""

# Change to project directory
cd "${PROJECT_DIR}"

# Activate virtual environment and run scheduler
if [[ "${BACKGROUND}" = "true" ]]; then
    # Run in background with nohup
    echo "[INFO] Starting scheduler in background..."
    
    # Create log file if it doesn't exist
    LOG_DIR="${PROJECT_DIR}/logs"
    mkdir -p "${LOG_DIR}"
    
    # Start scheduler in background
    nohup python scripts/scheduler/scheduler.py --interval "${INTERVAL}" >> "${LOG_DIR}/scheduler.log" 2>&1 &
    
    SCHEDULER_PID=$!
    echo "[OK] Scheduler started with PID: ${SCHEDULER_PID}"
    echo "  Logs: ${LOG_DIR}/scheduler.log"
    
    # Verify it started
    sleep 1
    if kill -0 "${SCHEDULER_PID}" 2>/dev/null; then
        echo "[OK] Scheduler process is running"
    else
        echo "[ERROR] Scheduler failed to start. Check logs."
        exit 1
    fi
else
    # Run in foreground
    echo "[INFO] Starting scheduler (Ctrl+C to stop)..."
    
    # Use exec to replace shell with python process
    exec python scripts/scheduler/scheduler.py --interval "${INTERVAL}"
fi
