# Chatbot Failure Analysis — WACH AI
**Date:** 2026-03-19
**Model:** Qwen (local, LM Studio) / fallback: Gemini 2.0 Flash
**Status:** Template — fill in actual results when LM Studio is running with a Qwen model loaded on port 1234.

---

## Executive Summary

> TODO: After running the 10 test queries below, summarise:
> - Overall pass rate (X/10)
> - Top 2–3 failure categories
> - Whether the chatbot is demo-ready

---

## Test Results

| # | Category | Query | Expected | Actual | Pass? | Root Cause |
|---|----------|-------|----------|--------|-------|------------|
| 1 | Level health | "what's wrong with level 5?" | Lists worst AHUs on L5 with health scores | — | — | — |
| 2 | Level health | "what is the health index on level 3?" | L3 average health + worst/best AHUs | — | — | — |
| 3 | Device-specific | "how is AHU e0202 performing?" | Health index, FAIR scores, tier for e0202 | — | — | — |
| 4 | Device-specific | "is e0501 at risk?" | Health score + tier for e0501 | — | — | — |
| 5 | Forecast | "will energy spike tomorrow?" | Prediction context injected, Δ kWh mentioned | — | — | — |
| 6 | Forecast | "predict health of e0303 in 24 hours" | Predicted HI + FAIR scores for e0303 at +24h | — | — | — |
| 7 | Financial | "what's the cost impact of poor health on level 3?" | Excess energy, PF penalty, maintenance risk totals | — | — | — |
| 8 | Navigation | "take me to level 7 predictions" | navigate field: {level: 7, view: "prediction"} | — | — | — |
| 9 | Off-topic | "what's the weather today?" | Polite redirect to AHU/energy topics | — | — | — |
| 10 | Invalid device | "how is AHU e9999 doing?" | "Device e9999 does not exist in this system." | — | — | — |

---

## Failure Categories

When filling in results, classify each failure by root cause:

1. **RAG miss** — Relevant docs exist in vector store but were not retrieved
2. **Hallucination** — Model invented data not present in the context
3. **Context missing** — Financial/health data was not injected into the system prompt
4. **Navigation failure** — `navigate` field wrong, missing, or pointing to wrong level/device
5. **Prompt confusion** — System prompt ambiguous or model misinterpreted instructions
6. **LM Studio issue** — Connection refused, model loading, or context window cutoff

---

## Prioritised Fix List

### P1 — Critical (blocks demo)

> TODO: List issues that cause wrong/missing responses for core use cases (health scores, device queries).

- [ ] TBD after testing

### P2 — High

> TODO: Issues that degrade UX but don't break the demo.

- [ ] TBD after testing

### P3 — Nice to have

> TODO: Polish items for after the demo.

- [ ] TBD after testing

---

## Recommended Actions

> TODO: After filling in the test results, add 3–5 actionable recommendations here.

### Common Qwen-specific issues to check:
- **Slow response** (>10s): Normal for local inference. Consider reducing `max_output_tokens` from 2048 to 512 for quicker replies.
- **Context window cutoff**: LM Studio default is often 4096 tokens. Increase to 8192+ in model settings if responses truncate.
- **`ConnectionRefusedError`**: LM Studio local server not started. Enable it in LM Studio → Local Server tab.
- **Empty reply**: Model still loading in LM Studio. Wait for model to fully initialise before sending requests.
- **Hallucinated AHU IDs**: Verify the system prompt constraint about valid device ID format is being respected.

---

## Environment at Test Time

| Variable | Value |
|----------|-------|
| `LLM_BACKEND` | `qwen` |
| `LMS_MODEL` | (fill in model name from LM Studio) |
| `LMS_BASE_URL` | `http://localhost:1234/v1` |
| `EMBED_BACKEND` | `qwen` |
| Backend port | 8081 |
| Frontend | `http://localhost:3000` or `https://demo-wach-insight.vercel.app` |
