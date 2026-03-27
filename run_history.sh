#!/usr/bin/env bash
# run_history.sh — Run the history generator locally (Mac Studio)
#
# Mirrors the GitHub Actions history-generator.yml workflow but runs on this
# machine so it can use the local GPU / faster hardware and you can watch logs
# live in a terminal.
#
# Usage:
#   ./run_history.sh                          # all levels, both phases
#   ./run_history.sh --level 3                # single level
#   ./run_history.sh --dry-run                # dry run only
#   ./run_history.sh --skip-phase1            # skip prediction ETL, use existing predictions.csv
#   ./run_history.sh --resume                 # resume cancelled run (uses metric_cache + skips phase 1)
#   ./run_history.sh --devices e0101,e0102    # subset of devices
#   ./run_history.sh --batch-days 14          # smaller InfluxDB fetch windows
#   ./run_history.sh --no-commit              # skip the final git commit/push
#
# All flags are passed through to history_generator.py except --no-commit.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Load env vars ─────────────────────────────────────────────────────────────
if [[ -f .env ]]; then
    set -o allexport
    # shellcheck disable=SC1091
    source .env
    set +o allexport
    echo "[run_history] Loaded env vars from .env"
else
    echo "[run_history] ERROR: .env not found. Copy .env.example → .env and fill in values."
    exit 1
fi

export PYTHONUNBUFFERED=1
export INFLUX_SKIP_TLS="${INFLUX_SKIP_TLS:-true}"

# ── Parse flags ───────────────────────────────────────────────────────────────
LEVEL="all"
DRY_RUN=false
SKIP_PHASE1=false
RESUME=false
BATCH_DAYS=30
DEVICES=""
SIMULATE_TIMEOUT=""
NO_COMMIT=false
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --level)       LEVEL="$2"; shift 2 ;;
        --dry-run)     DRY_RUN=true; shift ;;
        --skip-phase1) SKIP_PHASE1=true; shift ;;
        --resume)      RESUME=true; SKIP_PHASE1=true; shift ;;
        --batch-days)  BATCH_DAYS="$2"; shift 2 ;;
        --devices)     DEVICES="$2"; shift 2 ;;
        --simulate-timeout-after-metrics) SIMULATE_TIMEOUT="$2"; shift 2 ;;
        --no-commit)   NO_COMMIT=true; shift ;;
        *) echo "[run_history] Unknown flag: $1"; exit 1 ;;
    esac
done

# Build shared args passed to every python invocation
BASE_ARGS=(--level "$LEVEL" --verbose --batch-days "$BATCH_DAYS")
[[ -n "$DEVICES" ]] && BASE_ARGS+=(--devices "$DEVICES")

echo ""
echo "=========================================="
echo " WACH History Generator — local run"
echo " Level:       $LEVEL"
echo " Dry run:     $DRY_RUN"
echo " Skip phase1: $SKIP_PHASE1"
echo " Resume:      $RESUME"
echo " Batch days:  $BATCH_DAYS"
[[ -n "$DEVICES" ]] && echo " Devices:     $DEVICES"
echo " Started:     $(date)"
echo "=========================================="
echo ""

# ── Dry run ───────────────────────────────────────────────────────────────────
if $DRY_RUN; then
    DRY_EXTRA=()
    $SKIP_PHASE1 && DRY_EXTRA+=(--skip-phase1)
    $RESUME      && DRY_EXTRA+=(--skip-phase1 --use-cache)
    python3 scripts/etl/history_generator.py --dry-run "${BASE_ARGS[@]}" "${DRY_EXTRA[@]}"
    echo ""
    echo "[run_history] Dry run complete."
    exit 0
fi

# ── Phase 1 — Prediction ETL ─────────────────────────────────────────────────
if ! $SKIP_PHASE1 && ! $RESUME; then
    echo "=========================================="
    echo " Phase 1: Prediction ETL — $(date)"
    echo "=========================================="
    python3 scripts/etl/history_generator.py --phase1-only "${BASE_ARGS[@]}"
    echo "[run_history] Phase 1 finished — $(date)"
    echo ""

    # Intermediate commit so predictions.csv is safe if Phase 2 is interrupted
    if ! $NO_COMMIT; then
        if ! git diff --quiet data/predictions.csv 2>/dev/null; then
            git add data/predictions.csv
            git commit -m "chore(data): save predictions after Phase 1 [skip ci]"
            git pull --rebase --autostash
            git push
            echo "[run_history] predictions.csv committed."
        else
            echo "[run_history] No changes to predictions.csv."
        fi
    fi
fi

# ── Phase 2 — Health Scoring ETL ─────────────────────────────────────────────
echo "=========================================="
echo " Phase 2: Health Scoring ETL — $(date)"
echo "=========================================="

PHASE2_ARGS=(--skip-phase1)
$RESUME && PHASE2_ARGS+=(--use-cache)
[[ -n "$SIMULATE_TIMEOUT" ]] && PHASE2_ARGS+=(--simulate-timeout-after-metrics "$SIMULATE_TIMEOUT")

python3 scripts/etl/history_generator.py "${BASE_ARGS[@]}" "${PHASE2_ARGS[@]}"
echo "[run_history] Phase 2 finished — $(date)"
echo ""

# ── Commit outputs ────────────────────────────────────────────────────────────
if ! $NO_COMMIT; then
    git pull --rebase --autostash
    git add data/predictions.csv data/health_all_levels.csv data/health_hourly.csv
    if ! git diff --staged --quiet; then
        git commit -m "chore(data): regenerate historical ETL outputs [skip ci]"
        git push
        echo "[run_history] CSVs committed and pushed."
    else
        echo "[run_history] No CSV changes to commit."
    fi
fi

echo ""
echo "=========================================="
echo " Done — $(date)"
echo "=========================================="
