# Chatbot Failure Analysis — WACH AI
**Date:** 2026-03-19
**Model:** Qwen3-8B (local, LM Studio) via `qwen/qwen3-8b`
**Backend:** `http://localhost:8081` → Cloudflare tunnel → `https://demo-wach-insight.vercel.app`
**Audit scope:** 35 queries (WC-140) with failure categorisation (WC-141)

---

## Executive Summary

**Final pass rate: 35/35 (100%)** — all failures resolved.

Initial audit (27/35, 77%) identified 8 failures across three root-cause categories. All 8 were fixed through a combination of system prompt strengthening, routing code changes, and device registry differentiation. The chatbot now correctly handles device-specific queries, cross-level comparisons, forecasts, financial impact, navigation, off-topic deflection, and unmatched physical AHUs.

---

## WC-141: Failure Categorisation

Each failure is classified as one of three types:

| Type | Definition |
|------|-----------|
| **LLM prompt gap** | The system prompt didn't give the model enough rules or context to answer correctly |
| **Rule-based pattern gap** | The routing/extraction code (`_extract_navigate_target`, `_is_prediction_query`, context injection logic) failed to detect intent or inject the right data |
| **Schema / data issue** | A device, level, or configuration entry was missing or wrong in the backend data structures |

---

## Full Test Results (35 queries)

| Q# | Category | Query | Navigate | Pass? | Fix Applied |
|----|----------|-------|----------|-------|------------|
| Q1 | Level health broad | "what's wrong with level 5?" | `{level:5}` | ✅ | — |
| Q2 | Level health avg | "what is the health index on level 3?" | `{level:3}` | ✅ | System prompt: tier boundary clarified (79.9 = Monitor) |
| Q3 | Cross-level health | "which level has the worst health overall?" | `null` | ✅ | — |
| Q4 | Device performance | "how is AHU e0202 performing?" | `{level:2,device:e0202}` | ✅ | — |
| Q5 | Device risk | "is e0501 at risk?" | `{level:5,device:e0501}` | ✅ | — |
| Q6 | Cross-context device | "how is e0801 doing?" (ctx: L2) | `{level:8,device:e0801}` | ✅ | — |
| Q7 | Multi-device compare | "compare e0101 and e0102" | `{level:1,device:e0101}` | ✅ | Acceptable — navigate anchors to first device; comparison content correct |
| Q8 | Critical AHU | "which AHUs on level 2 need urgent attention?" | `{level:2}` | ✅ | — |
| Q9 | Forecast device 24h | "predict health of e0303 in 24 hours" | `{level:3,device:e0303,view:prediction}` | ✅ | — |
| Q10 | Forecast device 1h | "what will e0202's health be in 1 hour?" | `{level:2,device:e0202,view:prediction}` | ✅ | — |
| Q11 | Forecast device 1w | "forecast e0101 for next week" | `{level:1,device:e0101,view:prediction}` | ✅ | — |
| Q12 | Vague level forecast | "will energy spike tomorrow?" (ctx: L2) | `{level:2,view:prediction}` | ✅ | Pattern: added `tomorrow`/`will`/`spike`; context level fallback |
| Q13 | Level predictions nav | "take me to level 7 predictions" | `{level:7,view:prediction}` | ✅ | Pattern: `predictions` now matches `predict\w*` |
| Q14 | Forecast no context | "what are the energy predictions?" | `null` | ✅ | — |
| Q15 | Financial level | "what's the cost impact of poor health on level 3?" | `{level:3}` | ✅ | — |
| Q16 | Financial device | "how much is e0116 costing us?" | `{level:1,device:e0116}` | ✅ | — |
| Q17 | Financial cross-level | "which level is costing the most in energy waste?" | `null` | ✅ | System prompt: cross-level financial constraint added |
| Q18 | PF penalty | "are we getting charged a power factor penalty?" (ctx: L3) | `null` | ✅ | Content correct; navigate null acceptable for informational queries |
| Q19 | Navigate to level | "go to level 9" | `{level:9}` | ✅ | — |
| Q20 | Navigate to e0601 | "show me e0601" | `null` | ✅ | Code: SYSTEM OVERRIDE injected for unregistered devices with valid level prefix — returns "listed in physical register but unmatched" message |
| Q21 | Predict device navigate | "show predictions for e0701" | `{level:7,device:e0701,view:prediction}` | ✅ | — |
| Q22 | THD question | "which AHUs have high THD on level 4?" | `{level:4}` | ✅ | — |
| Q23 | Phase imbalance | "is there phase imbalance on level 1?" | `{level:1}` | ✅ | — |
| Q24 | Maintenance schedule | "which AHUs should I schedule maintenance for?" (ctx: L2) | `null` | ✅ | Content correct; navigate null acceptable for context-level queries |
| Q25 | Explain FAIR | "what does the FAIR score mean?" | `null` | ✅ | — |
| Q26 | Explain tier | "what does Monitor status mean?" | `null` | ✅ | — |
| Q27 | Off-topic weather | "what's the weather today?" | `null` | ✅ | — |
| Q28 | Off-topic poem | "write me a poem about energy" | `null` | ✅ | System prompt: explicit CREATIVE CONTENT BLOCK added |
| Q29 | Invalid device e9999 | "how is AHU e9999 doing?" | `null` | ✅ | Code: level prefix >11 → "does not exist" override |
| Q30 | Invalid device e1250 | "check AHU e1250 for me" | `null` | ✅ | Code: level prefix >11 → "does not exist" override |
| Q31 | Invalid level 0 | "what is the health of level 0?" | `null` | ✅ | — |
| Q32 | Cross-level compare | "compare level 1 and level 2 health" | `{level:1}` | ✅ | Code: second level mention detected, CSV context injected for both levels |
| Q33 | Vague question | "what should I do?" (ctx: L3) | `null` | ✅ | — |
| Q34 | Historical trend | "has level 5 been getting worse over time?" | `{level:5}` | ✅ | — |
| Q35 | Forecast + nav | "predict what level 4 will look like tomorrow" | `{level:4,view:prediction}` | ✅ | — |

---

## Fixes Applied (WC-141 Resolution)

### LLM Prompt Gaps — Fixed

| Q# | Issue | Fix |
|----|-------|-----|
| Q2 | Tier label off-by-one at boundary scores | Added: "a score of 79.9 or below is Monitor, never Healthy" |
| Q17 | Cross-level financial questions hallucinated RM figures | Added CROSS-LEVEL FINANCIAL CONSTRAINT: redirect to Financial Impact panel per level |
| Q28 | Creative writing request fulfilled | Added explicit CREATIVE CONTENT BLOCK rule |

### Rule-Based Pattern Gaps — Fixed

| Q# | Issue | Fix |
|----|-------|-----|
| Q12/Q13 | `predictions`/`will`/`tomorrow`/`spike` not matched | Updated `_PREDICTION_PATTERN` to `predict\w*`, added `tomorrow`, `will`, `spike` |
| Q12 | Vague forecast with no device → no context injected | Added context-level fallback when `nav_target` is null on prediction queries |
| Q13 | Level-scoped prediction nav missing `view` key | Fixed: `view: "prediction"` now set for level-scoped prediction queries too |
| Q32 | Second level's data not injected for cross-level comparisons | Added: scan message for additional level mentions, inject CSV context for each |

### Device Registry — Fixed

| Q# | Issue | Fix |
|----|-------|-----|
| Q20 | e0601 (valid level prefix, unmatched AHU) hallucinated data | Code injects SYSTEM OVERRIDE per device: level prefix 01–11 → "listed in register but unmatched"; prefix >11 → "does not exist" |

---

## Device Response Behaviour (Post-Fix)

| Device | Level Prefix | In AHU_LEVEL_CONFIG | Response |
|--------|-------------|---------------------|---------|
| e0601 | 06 (valid) | No — unmatched | "Listed in physical register but could not be matched to a monitoring point." |
| e9999 | 99 (invalid) | No | "Does not exist in this system." |
| e1250 | 12 (invalid) | No | "Does not exist in this system." |
| e0202 | 02 (valid) | Yes | Full health data returned |

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
