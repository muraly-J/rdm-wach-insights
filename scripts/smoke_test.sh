#!/usr/bin/env bash
# smoke_test.sh — Full local stack smoke test for WACH Insight on Mac Studio
# Usage: bash scripts/smoke_test.sh
# Prerequisites: backend running on :8081

set -euo pipefail

BASE="http://localhost:8081"
PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  local expect="$3"
  local out
  out=$(eval "$cmd" 2>&1) || true
  if echo "$out" | grep -qi "$expect"; then
    echo "✅  $name"
    PASS=$((PASS + 1))
  else
    echo "❌  $name"
    echo "    Expected to find: $expect"
    echo "    Got: $(echo "$out" | head -c 200)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== WACH Insight Local Smoke Test ==="
echo "Target: $BASE"
echo ""

# 1. Backend health check
check "GET /health" \
  "curl -sf --max-time 5 $BASE/health" \
  "ok"

# 2. Known good query — time series
check "POST /api/query (show power for e0101)" \
  "curl -sf --max-time 10 -X POST $BASE/api/query -H 'Content-Type: application/json' -d '{\"user_query\":\"show power for e0101\"}'" \
  "chart_type"

# 3. Level expansion → ranking (bar chart)
check "POST /api/query (top 5 power level 1 → bar)" \
  "curl -sf --max-time 10 -X POST $BASE/api/query -H 'Content-Type: application/json' -d '{\"user_query\":\"top 5 power level 1\"}'" \
  "bar"

# 4. Chat endpoint basic greeting
check "POST /api/chat (hello)" \
  "curl -sf --max-time 15 -X POST $BASE/api/chat -H 'Content-Type: application/json' -d '{\"message\":\"hello\",\"level\":1}'" \
  "reply"

# 5. Health index time series data
check "GET /api/level/1/health-index?range=last_7d" \
  "curl -sf --max-time 10 '$BASE/api/level/1/health-index?range=last_7d'" \
  "timestamp"

# 6. Unrecognised query → should return an error field, not silent garbage
check "POST /api/query (unrecognised → error returned)" \
  "curl -sf --max-time 10 -X POST $BASE/api/query -H 'Content-Type: application/json' -d '{\"user_query\":\"what is the weather\"}'" \
  "error"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
