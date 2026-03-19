# Chatbot Failure Analysis — WACH AI
**Date:** 2026-03-19
**Model:** Qwen3-8B (local, LM Studio) via `qwen/qwen3-8b`
**Backend:** `http://localhost:8081` → Cloudflare tunnel → `https://demo-wach-insight.vercel.app`

---

## Executive Summary

**Pass rate: 7/10 (70%)** — 5 clean PASS, 2 PARTIAL PASS, 2 FAIL

The chatbot handles device-specific queries, financial impact, and off-topic deflection well. Two hard failures block full demo readiness: vague level-scoped forecast queries return no data, and level-scoped navigation omits the `view` key needed to route the frontend to the predictions panel. Two minor inconsistencies (a tier label off-by-one and a bracket formatting deviation) are low severity but should be fixed before a customer demo.

---

## Test Results

| # | Category | Query | Expected | Actual | Pass? | Root Cause |
|---|----------|-------|----------|--------|-------|------------|
| 1 | Level health | "what's wrong with level 5?" | Worst AHUs on L5 with health scores + flags | Listed worst AHUs, FAIR flags, RM totals | ✅ PASS | — |
| 2 | Level health | "what is the health index on level 3?" | L3 average + worst/best AHU lists | Gives average (79.3) but mislabels it "Healthy" (threshold is 80); no separate best/worst list | ⚠️ PARTIAL | Tier label off-by-one; best list omitted |
| 3 | Device-specific | "how is AHU e0202 performing?" | Health index, FAIR scores, tier for e0202 | 89.8/100 Healthy, phase imbalance + THD flagged, navigate includes device | ✅ PASS | — |
| 4 | Device-specific | "is e0501 at risk?" | Health score + tier + risk assessment | 87.4/100 Healthy, IMBALANCE_SEVERE + PF_CHRONIC_LOW, RM cost cited | ✅ PASS | — |
| 5 | Forecast | "will energy spike tomorrow?" | Δ kWh figure or directional prediction | Admits no forecast data available; no Δ kWh injected | ❌ FAIL | Forecast context not injected for level-scoped vague queries |
| 6 | Forecast | "predict health of e0303 in 24 hours" | Predicted HI + FAIR scores, navigate with view=prediction | 71.9/100 predicted, +37.57 kWh, navigate `{level:3, device:"e0303", view:"prediction"}` | ✅ PASS | — |
| 7 | Financial | "what's the cost impact of poor health on level 3?" | Excess energy, PF penalty, maintenance risk with RM figures | RM 215.77 total: PF penalty RM 132.82, excess energy RM 82.95, maintenance RM 0.00 | ✅ PASS | — |
| 8 | Navigation | "take me to level 7 predictions" | navigate = `{level:7, view:"prediction"}` | navigate = `{level:7}` — `view` key missing | ❌ FAIL | Router only emits `view` for device-scoped prediction queries, not level-scoped |
| 9 | Off-topic | "what's the weather today?" | Polite redirect to AHU/energy topics | Redirects cleanly, no weather data provided | ✅ PASS | — |
| 10 | Invalid device | "how is AHU e9999 doing?" | "Device e9999 does not exist in this system." | "Device [e9999] does not exist in this system." — brackets around ID | ⚠️ PARTIAL | Minor format deviation; functionally correct |

---

## Failure Categories

| Category | Count | Queries |
|----------|-------|---------|
| Context missing — forecast not injected for level scope | 1 | Q5 |
| Navigation failure — `view` key missing for level-scoped intent | 1 | Q8 |
| Label inconsistency — tier mislabelled at boundary score | 1 | Q2 |
| Format deviation — device ID wrapped in brackets | 1 | Q10 |

---

## Prioritised Fix List

### P1 — Critical (blocks demo)

- [ ] **Q8: Level-scoped navigation missing `view` key**
  `_extract_navigate_target()` in `backend/routes/chat.py` only sets `nav_target["view"] = "prediction"` when a device is matched. Add a branch: if the message matches a prediction-intent pattern AND a level is matched (but no device), also set `view = "prediction"`.
  Fix location: `backend/routes/chat.py` → prediction query block (~line 560).

### P2 — High

- [ ] **Q5: Forecast context not injected for level-scoped energy questions**
  When no device is mentioned in a prediction query, the system skips prediction context injection entirely. Should fall back to a level-aggregate forecast or at minimum route the user to the predictions panel (`view: "prediction"`).
  Fix location: `backend/routes/chat.py` → the `_is_prediction_query` block (~line 545).

- [ ] **Q2: Tier label boundary — 79.3 called "Healthy"**
  The model interpolates tier labels from the system prompt. Add an explicit note: "A score below 80 is Monitor, not Healthy, even if close to the boundary."
  Fix location: `backend/routes/chat.py` → `_WACH_SYSTEM_PROMPT`.

### P3 — Nice to have

- [ ] **Q10: Device ID bracket formatting**
  Model returns `Device [e9999] does not exist...` instead of `Device e9999 does not exist...`. Add to system prompt: "Do not wrap the device ID in brackets."

---

## Recommended Actions

1. **Fix P1 (Q8) before any demo** — navigation is a key UX feature; missing `view` key breaks the predictions panel routing.
2. **Fix P2 (Q5) for the energy forecasting pitch** — if energy trend questions are in the demo script, level-scoped forecast data must be injected.
3. **Add a tier boundary note to the system prompt** (Q2) — one sentence, prevents misleading tier labels.
4. **Bracket fix for Q10** is cosmetic — fine to leave for post-demo cleanup.

---

## Environment at Test Time

| Variable | Value |
|----------|-------|
| `LLM_BACKEND` | `qwen` |
| `LMS_MODEL` | `qwen/qwen3-8b` |
| `LMS_BASE_URL` | `http://localhost:1234/v1` |
| `EMBED_BACKEND` | `qwen` |
| Backend port | 8081 |
| Tunnel | `https://agreed-myself-houses-harvard.trycloudflare.com` |
| Frontend | `https://demo-wach-insight.vercel.app` |
