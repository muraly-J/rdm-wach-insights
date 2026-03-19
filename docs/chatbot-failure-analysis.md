# Chatbot Failure Analysis — WACH AI
**Date:** 2026-03-19
**Model:** Qwen3-8B (local, LM Studio) via `qwen/qwen3-8b`
**Backend:** `http://localhost:8081` → Cloudflare tunnel → `https://demo-wach-insight.vercel.app`
**Audit scope:** 35 queries (WC-140) with failure categorisation (WC-141)

---

## Executive Summary

**Pass rate: 27/35 (77%)** — 27 PASS, 8 FAIL

The chatbot handles device-specific queries, financial impact, health score explanations, forecasts, navigation, and off-topic deflection reliably. Eight failures fall into three root-cause categories (WC-141). Most are fixable with small rule-based or prompt changes. One is a data bug (Q20: valid device incorrectly reported as non-existent).

---

## WC-141: Failure Categorisation

Each failure is classified as one of three types:

| Type | Definition |
|------|-----------|
| **LLM prompt gap** | The system prompt doesn't give the model enough rules or context to answer correctly |
| **Rule-based pattern gap** | The routing/extraction code (`_extract_navigate_target`, `_is_prediction_query`, context injection logic) failed to detect intent or inject the right data |
| **Schema / data issue** | A device, level, or configuration entry is missing or wrong in the backend data structures |

---

## Full Test Results (35 queries)

| Q# | Category | Query | Navigate | Pass? | Failure Type | Root Cause |
|----|----------|-------|----------|-------|-------------|------------|
| Q1 | Level health broad | "what's wrong with level 5?" | `{level:5}` | ✅ | — | — |
| Q2 | Level health avg | "what is the health index on level 3?" | `{level:3}` | ❌ | LLM prompt gap | No explicit instruction to show worst/best AHU lists; reply thin |
| Q3 | Cross-level health | "which level has the worst health overall?" | `null` | ✅ | — | — |
| Q4 | Device performance | "how is AHU e0202 performing?" | `{level:2,device:e0202}` | ✅ | — | — |
| Q5 | Device risk | "is e0501 at risk?" | `{level:5,device:e0501}` | ✅ | — | — |
| Q6 | Cross-context device | "how is e0801 doing?" (ctx: L2) | `{level:8,device:e0801}` | ✅ | — | — |
| Q7 | Multi-device compare | "compare e0101 and e0102" | `{level:1,device:e0101}` | ❌ | Rule-based pattern gap | `_extract_navigate_target` returns first device match only; e0102 absent |
| Q8 | Critical AHU | "which AHUs on level 2 need urgent attention?" | `{level:2}` | ✅ | — | — |
| Q9 | Forecast device 24h | "predict health of e0303 in 24 hours" | `{level:3,device:e0303,view:prediction}` | ✅ | — | — |
| Q10 | Forecast device 1h | "what will e0202's health be in 1 hour?" | `{level:2,device:e0202,view:prediction}` | ✅ | — | — |
| Q11 | Forecast device 1w | "forecast e0101 for next week" | `{level:1,device:e0101,view:prediction}` | ✅ | — | — |
| Q12 | Vague level forecast | "will energy spike tomorrow?" (ctx: L2) | `{level:2,view:prediction}` | ✅ | — | — |
| Q13 | Level predictions nav | "take me to level 7 predictions" | `{level:7,view:prediction}` | ✅ | — | — |
| Q14 | Forecast no context | "what are the energy predictions?" | `null` | ✅ | — | — |
| Q15 | Financial level | "what's the cost impact of poor health on level 3?" | `{level:3}` | ✅ | — | — |
| Q16 | Financial device | "how much is e0116 costing us?" | `{level:1,device:e0116}` | ✅ | — | — |
| Q17 | Financial cross-level | "which level is costing the most in energy waste?" | `null` | ❌ | LLM prompt gap | No instruction to redirect to financial panel; bot fully deflects |
| Q18 | PF penalty | "are we getting charged a power factor penalty?" (ctx: L3) | `null` | ❌ | Rule-based pattern gap | Level number not in message text; `_extract_navigate_target` returns null despite context |
| Q19 | Navigate to level | "go to level 9" | `{level:9}` | ✅ | — | — |
| Q20 | Navigate to device e0601 | "show me e0601" | `null` | ❌ | Schema / data issue | e0601 not found in `AHU_LEVEL_CONFIG` device_ids for Level 6; model applies invalid-device rule |
| Q21 | Predict device navigate | "show predictions for e0701" | `{level:7,device:e0701,view:prediction}` | ✅ | — | — |
| Q22 | THD question | "which AHUs have high THD on level 4?" | `{level:4}` | ✅ | — | — |
| Q23 | Phase imbalance | "is there phase imbalance on level 1?" | `{level:1}` | ✅ | — | — |
| Q24 | Maintenance schedule | "which AHUs should I schedule maintenance for?" (ctx: L2) | `null` | ❌ | Rule-based pattern gap | Content correct; navigate null because no level number appears in message text |
| Q25 | Explain FAIR | "what does the FAIR score mean?" | `null` | ✅ | — | — |
| Q26 | Explain tier | "what does Monitor status mean?" | `null` | ✅ | — | — |
| Q27 | Off-topic weather | "what's the weather today?" | `null` | ✅ | — | — |
| Q28 | Off-topic poem | "write me a poem about energy" | `null` | ❌ | LLM prompt gap | System prompt says redirect "outside your domain" but bot treats energy poem as in-domain |
| Q29 | Invalid device e9999 | "how is AHU e9999 doing?" | `null` | ✅ | — | — |
| Q30 | Invalid device e1250 | "check AHU e1250 for me" | `null` | ✅ | — | — |
| Q31 | Invalid level 0 | "what is the health of level 0?" | `null` | ✅ | — | — |
| Q32 | Cross-level compare | "compare level 1 and level 2 health" | `{level:1}` | ❌ | Rule-based pattern gap | Only nav_target level's data injected; second level treated as unavailable |
| Q33 | Vague question | "what should I do?" (ctx: L3) | `null` | ✅ | — | — |
| Q34 | Historical trend | "has level 5 been getting worse over time?" | `{level:5}` | ✅ | — | — |
| Q35 | Forecast + nav | "predict what level 4 will look like tomorrow" | `{level:4,view:prediction}` | ✅ | — | — |

---

## Failures by Category (WC-141)

### LLM Prompt Gap (3 failures)

These require changes to `_WACH_SYSTEM_PROMPT` in `backend/routes/chat.py`.

| Q# | Issue | Fix |
|----|-------|-----|
| Q2 | Level health response omits worst/best AHU lists | Add instruction: "When answering a level health question, always list the 3 worst and 3 best AHUs with their scores and tier" |
| Q17 | Cross-level financial question causes full deflection | Add instruction: "If asked which level costs the most and you lack the data, tell the user to open the Financial Impact panel for each level" |
| Q28 | Creative writing request fulfilled instead of redirected | Tighten the redirect rule: "Do not write poems, stories, or any creative content. Any request that is not a question about AHU health, energy, or building systems should be redirected." |

### Rule-Based Pattern Gap (4 failures)

These require code changes in `backend/routes/chat.py`.

| Q# | Issue | Fix location |
|----|-------|-------------|
| Q7 | Multi-device compare: navigate anchors to first device only | `_extract_navigate_target` — return both devices when two device IDs appear in same message |
| Q18 | Informational query about current context level emits null navigate | After building the response, if no nav_target was set but context has a level, emit `{"level": ctx_level}` as navigate |
| Q24 | Same as Q18 — maintenance query about current level emits null navigate | Same fix as Q18 |
| Q32 | Cross-level compare: second level's data not injected | When `_extract_navigate_target` returns a level and a second level number appears in the message, fetch and inject context for both |

### Schema / Data Issue (1 failure)

| Q# | Issue | Fix |
|----|-------|-----|
| Q20 | e0601 (valid Level 6 device) reported as non-existent | Check `AHU_LEVEL_CONFIG` in `backend/models/schemas.py` — verify all Level 6 device IDs are listed. If e0601 is missing, add it. |

---

## Prioritised Fix List

### P1 — Critical (breaks demo)

- [ ] **Q20: e0601 device lookup failure** — Valid device incorrectly blocked. Check `AHU_LEVEL_CONFIG` Level 6 entries.
- [ ] **Q28: Poem / creative writing** — Tighten system prompt redirect rule to explicitly exclude creative content.

### P2 — High (degrades UX)

- [ ] **Q18 + Q24: Missing navigate on context-aware informational replies** — Emit `{"level": ctx_level}` from context when no explicit navigate was set but the answer is clearly about the current level.
- [ ] **Q32: Cross-level comparison injects only one level's data** — Detect second level mention and inject its live + CSV context.
- [ ] **Q2: Level health responses are thin** — Add explicit instruction to include worst/best AHU list in level health answers.

### P3 — Nice to have

- [ ] **Q7: Multi-device compare navigate** — Include both devices in navigate (or at minimum both level references).
- [ ] **Q17: Cross-level financial deflection** — Add redirect instruction to financial panel when data is missing.

---

## Recommended Actions

1. **Fix Q20 first** — open `backend/models/schemas.py`, find `AHU_LEVEL_CONFIG`, and verify Level 6 device IDs are complete.
2. **Fix Q18/Q24 together** — single code change: emit context level as navigate fallback for informational queries.
3. **Fix Q28** — one line addition to the system prompt.
4. **Fix Q2** — one sentence addition to the system prompt about level health response format.
5. **Q32 (cross-level)** is a more involved code change — tackle after the quick wins above.

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
