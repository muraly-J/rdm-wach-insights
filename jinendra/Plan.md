# WACH Insight — Project Plan
**Duration**: Mon Mar 2 → Tue Mar 31, 2026
**Working days**: 22
**Team**: Jinendra + Ambika

---

## Deliverables

### Jinendra
1. **Perfect Chatbot** — Significantly improved NLP accuracy, edge case handling, better chart output (single-turn, no multi-turn required)
2. **Math-formula predictions** (1h / 6h / 12h / 24h) for ALL 112+ AHUs on delta kWh, with a visualization overlaying last week's actuals + yesterday's actuals + prediction
3. **Perfect rule-based health index** — Fix all 5 component formulas AND make scoring live for all 11 levels via automated ETL (not static CSVs)

### Ambika
1. **Data feasibility report** — Is ~4 months of InfluxDB data (Nov 2025 → Feb 2026) sufficient to train ML models for each of the 5 health scores?
2. **Research report** — Architecture recommendations, embedding strategy, model selection, training approach for each of the 5 scores
3. **Working prototype OR scaffolded framework** — Prototype models if data has enough anomaly diversity; fully scaffolded, ready-to-train ML pipeline + live logging infrastructure if not

---

## Settled Decisions

### Prediction Formula
**Weighted Seasonal Average:**
```
ŷ(t) = 0.50 × E(t − 24h)    ← same hour yesterday
     + 0.30 × E(t − 168h)   ← same hour last week
     + 0.20 × E(t − 336h)   ← same hour 2 weeks ago

Δ kWh = E_actual(t) − ŷ(t)
```
- Weights are decay-ordered (yesterday matters most)
- Transparent and stakeholder-verifiable
- AHUs with < 2 weeks of hourly history are flagged as `insufficient_history`

### Health Index Pipeline
Automated ETL → CSV architecture:
```
InfluxDB (hourly)
    ↓  [scheduled ETL job, every 30 min]
Health formula engine (fair_health_scoring.py)
    ↓
Append → health_all_levels.csv (or per-level CSVs)
    ↓
Frontend reads CSV on page load (static, instant)
```

| Stage | Target |
|-------|--------|
| ETL pipeline runtime (all 112+ AHUs, all 11 levels) | < 45 seconds |
| ETL run frequency | Every 30 minutes |
| Data staleness (worst case) | 30 minutes |
| Frontend CSV load + render | < 3 seconds |
| User-perceived experience | Instant (reads cached CSV) |

### Ambika's ML Approach
The central question for Week 1: **does the data contain enough real anomaly diversity (healthy + unhealthy AHU behaviour) to train supervised ML?**

- **Branch A (Go)**: Proceed to prototype ML models in XGBoost
- **Branch B (No-Go)**: Build logging infrastructure + ML framework scaffold so training can begin the moment enough labelled data accumulates

Regardless of branch, the **logging infrastructure is built and goes live in Week 2**. Every rule-based flag automatically logs:
- The event (component, score, tier, timestamp)
- Full metric snapshot at flag time
- A reference window to the 24–48h of raw InfluxDB data *leading up to* the flag (the "run-up"), which is what teaches future models early detection

---

## Jinendra — Day-by-Day Plan

### Week 1 (Mar 2–6) — Health Index Audit + ETL Architecture

**Mon Mar 2**
- Read `fair_health_scoring.py` end-to-end, document every formula, threshold, and edge case
- Pull sample data from 2–3 AHUs per level, run all 5 scoring functions, record anomalies
- Deliverable: Written audit of formula weaknesses

**Tue Mar 3**
- Test scoring across a broader sample (AHUs from all 11 levels)
- Identify: bimodal distribution edge cases, missing metric handling, AHUs scoring nonsensically
- Deliverable: Issue table per formula

**Wed Mar 4**
- Fix Energy Anomaly and Overload formulas (thresholds, guards for missing data, minimum history requirements)
- Design ETL pipeline architecture: what does one pipeline run look like? Which InfluxDB queries? What does the output CSV schema look like?

**Thu Mar 5**
- Fix Power Factor Degradation, Phase Imbalance, and THD Drift formulas
- Settle prediction formula implementation details: how to handle AHU with < 2 weeks history? How to fetch exactly `t−24h`, `t−168h`, `t−336h` hourly slots?

**Fri Mar 6**
- Write unit tests for all 5 fixed formulas using known-good and known-bad synthetic data
- Deliverable: All formula fixes committed, tested
- **4pm meeting** (see Meeting Plans section)

---

### Week 2 (Mar 9–13) — ETL Pipeline + Prediction Backend

**Mon Mar 9**
- Build the ETL pipeline script: `scripts/run_health_etl.py`
  - Fetch latest hourly data for all AHUs across all 11 levels from InfluxDB
  - Run all 5 scoring functions per AHU
  - Output: append one row per AHU per hour to `health_all_levels.csv`
  - Include: `timestamp, ahu_id, level, health_index, energy_anomaly, pf_degradation, phase_imbalance, thd_drift, overload, tier, safety_flags`

**Tue Mar 10**
- Test ETL pipeline end-to-end on Level 1 (22 AHUs)
- Measure runtime: is it within the 45s target?
- Fix batching issues: one InfluxDB call per level (not per AHU) to avoid N+1 queries

**Wed Mar 11**
- Implement prediction formula: `scripts/run_prediction_etl.py` or add to main ETL
  - For each AHU: fetch `E(t−24h)`, `E(t−168h)`, `E(t−336h)` from InfluxDB
  - Compute `ŷ(t)` and `Δ kWh`
  - Output: `predictions.csv` with `timestamp, ahu_id, predicted_kwh, yesterday_kwh, last_week_kwh, two_weeks_kwh, delta_kwh`

**Thu Mar 12**
- Test prediction ETL across all AHUs
- Handle edge cases: AHU with < 2 weeks history → `insufficient_history` flag; missing hourly slot → use nearest valid reading
- Verify `Δ kWh` feeds back correctly into `score_energy_anomaly()` as the primary signal

**Fri Mar 13**
- Automate both ETL pipelines (scheduler — cron job or lightweight loop), run every 30 minutes
- Deliverable: Both ETL pipelines running automatically, generating fresh CSVs every 30 min
- **4pm meeting** (see Meeting Plans section)

---

### Week 3 (Mar 16–20) — Frontend: Prediction Viz + Health Dashboard Upgrade

**Mon Mar 16**
- Upgrade `AhuHealthTrendDashboard.jsx` to read from the new all-levels CSV (not just Level 1)
- Add level selector so user can browse Levels 1–11
- Data loads from pre-generated CSV, instant render

**Tue Mar 17**
- Build the prediction visualization component
- Chart: three overlaid lines — **Last Week** (grey), **Yesterday** (blue), **Prediction** (green dashed)
- X-axis: time-of-day; Y-axis: kWh; four horizon markers highlighted (1h, 6h, 12h, 24h ahead)
- AHU selector + horizon toggle in UI

**Wed Mar 18**
- Wire prediction chart to `predictions.csv`
- Display `Δ kWh` prominently: "Predicted +12 kWh above normal" or "−8 kWh below baseline"
- Make prediction chart accessible from chatbot: "predict energy for e0202 for next 6 hours"
- Integrate `Δ kWh` into energy anomaly scoring: `score_energy_anomaly()` uses prediction delta as primary signal

**Thu Mar 19**
- Chatbot audit: run 30+ test queries, record every failure
- Categorise: LLM prompt gap vs. rule-based pattern gap vs. schema validation issue
- Deliverable: Chatbot failure analysis with prioritised fix list

**Fri Mar 20**
- Improve LLM prompt in `prompts.py`: add examples for health index queries, prediction queries, level-wide queries; tighten JSON schema instructions
- Test improved prompt against all known failure cases
- **4pm meeting** (see Meeting Plans section)

---

### Week 4 (Mar 23–27) — Chatbot + End-to-End Integration

**Mon Mar 23**
- Improve rule-based pattern matching in `translator.py`
- Add patterns for: health index queries, prediction queries, "show Level 3", THD/phase imbalance natural language variants, multi-AHU queries

**Tue Mar 24**
- Improve chart selection logic (line vs. bar vs. prediction chart)
- Better error messages when query cannot be understood
- Handle partial matches: "power Level 1" → bar chart of all Level 1 AHUs' power

**Wed Mar 25**
- Full end-to-end test: ETL → CSV → dashboard + chatbot together
- Test scenario: user asks health question → dashboard shows live data → prediction chart accessible → energy anomaly reflects prediction delta
- Document integration bugs

**Thu Mar 26**
- Fix all integration bugs
- Performance audit: is ETL pipeline completing in < 45s? If not, optimise InfluxDB queries
- Run ETL on live clock and verify 30-min freshness is maintained

**Fri Mar 27**
- Demo dry run: walk through all three deliverables as if presenting to stakeholders
- Polish: loading states, error messages, empty states in frontend
- Deliverable: All three deliverables feature-complete
- **4pm meeting** (see Meeting Plans section)

---

### Week 5 (Mar 30–31) — Final Polish + Delivery

**Mon Mar 30**
- Final bug fixes
- Code comments: prediction formula documented in plain English inside the code so any engineer can verify the math
- ETL logging: ensure pipeline writes a log entry each run (timestamp, AHUs processed, errors if any)

**Tue Mar 31**
- Demo / delivery
- Buffer for last-minute issues
- **Checkpoint**: Chatbot ✅ | Predictions (all AHUs) ✅ | Health Index (all 11 levels, live ETL) ✅

---

## Ambika — Day-by-Day Plan

### Week 1 (Mar 2–6) — Data Assessment: Anomaly Diversity Check

**Mon Mar 2**
- Pull all available data from InfluxDB: all AHUs, all 80 metrics, Nov 2025 → present
- Build a data availability matrix: which AHUs have complete data, which have gaps, which metrics are sparsely recorded
- Deliverable: Coverage heatmap (AHU × metric × date)

**Tue Mar 3**
- Run rule-based health scores against all available data
- Count: how many AHU-hours are flagged as unhealthy (score > 0.5) for each of the 5 components?
- **Diversity check**: if < 5% of AHU-hours are flagged across any component, supervised ML is impractical for that component right now

**Wed Mar 4**
- Stationarity tests (ADF/KPSS) on key metrics per AHU
- Distribution analysis: do metrics show meaningful variance over 4 months, or are they flat and stable?
- Document: which metrics show enough variation to be informative for ML?

**Thu Mar 5**
- Write the **Go/No-Go assessment** per score component:
  - Energy Anomaly → Go / No-Go
  - PF Degradation → Go / No-Go
  - Phase Imbalance → Go / No-Go
  - THD Drift → Go / No-Go
  - Overload → Go / No-Go
- Recommendation: which components are ML-ready now vs. need more operational data first?

**Fri Mar 6**
- Deliverable: **Data Feasibility Report** (final)
  - Coverage stats, anomaly diversity findings, Go/No-Go per component, risks
  - Recommendation: "Proceed with ML for X components now; defer Y and Z pending 3–6 months of rule-based logging"
- **4pm meeting** (see Meeting Plans section)

---

### Week 2 (Mar 9–13) — Logging Schema Design + ML Framework Setup

**Mon Mar 9**
- Design the **ML-ready logging schema** — the most critical output if data is insufficient
- Every time rule-based system flags an event, the log captures:
  ```
  event_id, ahu_id, timestamp_flagged,
  component_flagged (energy/pf/imbalance/thd/overload),
  rule_score_at_flag, tier_at_flag,
  run_up_window_start (e.g., 24h before flag),
  raw_metrics_at_flag: {power_total, power_factor, unbalance_pct, thd_24h, delta_kwh, ...},
  manually_reviewed: bool,
  confirmed_label: true_positive | false_positive | true_negative | false_negative | unreviewed
  ```
- The `run_up_window_start` is critical: 24–48h of data *before* the flag is what teaches early detection

**Tue Mar 10**
- Implement logging infrastructure in backend:
  - New SQLite table: `anomaly_events` (extend `query_logs.db` or separate)
  - Hook into `fair_health_scoring.py`: when a score crosses threshold, write an event log
  - Include full metric snapshot at flag time + InfluxDB reference for future raw data retrieval

**Wed Mar 11**
- Literature review: ML for electrical anomaly detection in commercial HVAC/power systems
  - Key approaches: XGBoost on engineered features, LSTM autoencoders, Isolation Forest (one-class)
  - Focus on what works with < 6 months data + sparse labels
- AHU embedding strategy: how to encode per-device identity in a way that generalises

**Thu Mar 12**
- Design the ML architecture (for when data is ready):
  - **Input**: rolling window (last 24h at hourly resolution) of relevant metrics + AHU embedding
  - **AHU Embedding**: learnable vector per AHU ID (lookup table, dim=16 or 32)
  - **Model**: XGBoost on flattened features — fast and interpretable
  - **Per-component models**: 5 separate XGBoost models, each with same architecture but different target
  - **Output**: anomaly score (0–1), comparable to rule-based score
  - **Training strategy**: time-based split (train Nov–Jan, validate Feb, test held-out AHUs)
  - **Minimum data to trigger training**: 200 labelled events per component per class

**Fri Mar 13**
- Deliverable: **Technical Architecture Document**
  - Logging schema spec, ML model architecture per component, training pipeline design
  - Data requirements to trigger ML training
  - Feature engineering plan: which features feed each model
- **4pm meeting** (see Meeting Plans section)

---

### Week 3 (Mar 16–20) — Prototype or Framework Build

#### Branch A — Data is sufficient for at least 1–2 components (Go)

**Mon–Wed Mar 16–18**
- Set up training pipeline: data loader → feature engineering → XGBoost training → evaluation
- Train Energy Anomaly model (most likely to have data)
- Evaluate: MAE vs. rule-based score on held-out data; agreement rate on flagged events

**Thu–Fri Mar 19–20**
- Train second model (whichever component has next most data)
- Error analysis: where does the model disagree with rule-based? Genuine insight or noise?

#### Branch B — Data is insufficient for all components (No-Go on training)

**Mon–Wed Mar 16–18**
- Build full training pipeline scaffold (framework only, no training yet):
  - Data loader from SQLite event log + InfluxDB raw data fetch
  - Feature engineering functions (lag, rolling stats, AHU embedding lookup)
  - XGBoost training wrapper with cross-validation
  - Evaluation harness (precision/recall/F1 vs. rule-based labels)
- Pipeline is ready to run the moment enough labelled data arrives

**Thu–Fri Mar 19–20**
- Simulate training on synthetic/augmented data to verify pipeline runs end-to-end without errors
- Document: "Run `train.py --component energy_anomaly --min_events 200` once log has enough data"

**Fri Mar 20** — **4pm meeting** (see Meeting Plans section)

---

### Week 4 (Mar 23–27) — Expand + Evaluate

#### Branch A
- **Mon–Thu**: Train remaining components where data allows; scaffold No-Go components
- **Fri**: Full evaluation: ML health index vs. rule-based health index side-by-side

#### Branch B
- **Mon–Tue**: Integrate logging with live ETL (every rule-based run writes to event log automatically)
- **Wed–Thu**: Build monitoring view: "X events logged so far, Y confirmed TP, Z FP" — so Jinendra can track label accumulation
- **Fri**: End-to-end dry run: simulate a flagged event → event logged → data retrievable → features computable

**Fri Mar 27** — **4pm meeting** (see Meeting Plans section)

---

### Week 5 (Mar 30–31) — Final Report + Handoff

**Mon Mar 30**
- Write **Comprehensive Research Report**:
  - Data feasibility findings (with evidence)
  - Go/No-Go per component (and why)
  - Logging schema and how it feeds future ML
  - Architecture decisions and rationale
  - Branch A: model results, metrics, comparison vs. rule-based, limitations
  - Branch B: what data needs to accumulate before training, estimated timeline
  - Recommendation: when to trigger ML training in production

**Tue Mar 31**
- Deliver: report + logging infrastructure (live) + prototype or scaffolded pipeline
- Walk Jinendra through findings and next-step triggers
- **Checkpoint**: Feasibility report ✅ | Logging infrastructure live ✅ | ML prototype or ready-to-train framework ✅

---

## Summary Table

| Week | Jinendra | Ambika |
|------|----------|--------|
| **W1** Mar 2–6 | Health index audit + formula fixes + ETL architecture | Data profiling + anomaly diversity check + Go/No-Go assessment |
| **W2** Mar 9–13 | Build ETL pipeline (health + predictions), automate at 30 min | Logging schema design + implementation + ML architecture doc |
| **W3** Mar 16–20 | Frontend: all-levels dashboard + prediction chart | Prototype training (Branch A) OR full ML framework scaffold (Branch B) |
| **W4** Mar 23–27 | Chatbot improvements + end-to-end integration testing | Expand models / live logging integration + monitoring view |
| **W5** Mar 30–31 | Final polish, demo, delivery | Final research report + handoff |

---

## Friday Meeting Plans

**Standing format**: 4pm, every Friday. Covers both workstreams. Tone: confident, evidence-backed, one step ahead of concerns. Open with what's done, close with what's next. Never raise a concern without also saying what you're doing about it.

---

### Meeting 1 — Fri Mar 6

**Theme: "We've diagnosed the system and locked in our approach"**

**What to show**
- The written audit of `fair_health_scoring.py` — show before/after on 2–3 specific formulas that were wrong or fragile (e.g. "the THD score was treating a bimodal AHU the same as a flat one — that's fixed")
- Ambika's data feasibility Go/No-Go table — one clear doc, per-component verdict
- The prediction formula written out plainly: `ŷ = 0.5 × Yesterday + 0.3 × LastWeek + 0.2 × TwoWeeksAgo`, with a worked example on one AHU

**What to tell them**
- "We spent this week auditing what we have before building anything new. We found and fixed specific issues in the health scoring formulas and settled on a transparent, mathematically verifiable prediction approach."
- "Ambika has assessed whether our 4 months of data supports ML. [State the Go/No-Go result honestly.] Based on that, she's moving into [prototype work / building the logging infrastructure that creates our ML dataset over time]."
- "Next week: the automated pipeline goes live — health scores refreshed every 30 minutes for all 112 AHUs across all 11 levels."

**How to raise concerns**
- If most Go/No-Go results are No-Go: *"The data shows AHUs have been performing well since installation — which is good news operationally, but it means we don't yet have enough fault examples to train ML models. Ambika is instead building the logging system now, so every future flag automatically builds our training dataset. The rule-based system delivers value immediately while the ML dataset matures."*
- If formula fixes revealed scoring was significantly off: *"Some of our existing health scores were producing misleading results for certain AHU types. We've corrected this — so the scores going forward will be more reliable, but they may look different from what was shown before. I'd rather fix it now than show stakeholders a number we can't fully stand behind."*

**Questions to ask**
- "Are there specific levels or AHUs your team is most concerned about right now? That helps us prioritise our testing."
- "Is 30-minute data refresh acceptable for the dashboard, or is there a specific freshness requirement from your side?"
- "Is there a preference for how health scores are labelled in the UI — e.g. 'Healthy / Monitor / Maintenance Soon / Critical' vs. a numerical score?"

---

### Meeting 2 — Fri Mar 13

**Theme: "The engine is running — live health data for all 11 levels"**

**What to show**
- **Live demo** (or terminal run): show the ETL pipeline executing and generating the CSV with fresh health scores
- Open the CSV — show rows for multiple AHUs across multiple levels, point out `health_index`, `tier`, and component score columns
- Ambika's ML architecture document — one-page summary of what the ML system will look like and what data it needs before training begins

**What to tell them**
- "The automated pipeline is live. Every 30 minutes it pulls the latest data from InfluxDB, runs all five health formulas across all 112+ AHUs, and writes fresh health scores to a file the dashboard reads from. Data is never more than 30 minutes old."
- "The prediction system backend is also built — for every AHU, we can now compute expected energy consumption for the next 1, 6, 12, and 24 hours using a mathematically transparent formula. We'll be wiring this into the frontend next week."
- "Ambika has designed and implemented the logging system. From this point forward, every time the health system flags an AHU, the event and the surrounding electrical data are automatically recorded. This is the foundation of our future ML dataset."

**How to raise concerns**
- If ETL is running slower than 45 seconds: *"The pipeline is processing all AHUs but currently takes around X seconds. We're optimising the InfluxDB queries to batch by level rather than by device — we expect to bring this within target by next week. It doesn't affect the user experience since the dashboard reads from a pre-generated file."*
- If any level has sparse/missing data from InfluxDB: *"Level X has some gaps in the InfluxDB data — some AHUs are missing metric readings intermittently. We're flagging those AHUs in the output rather than silently dropping them. We may want to investigate the metering on those units."*

**Questions to ask**
- "When we present the health dashboard, should the default view show all AHUs or a specific level? Knowing the typical audience helps us design the first screen."
- "Is there anyone on the facilities or maintenance side who should review what gets flagged as 'Maintenance Soon' or 'Critical' before we go live? We want to avoid false alarms causing unnecessary callouts."
- "Are there any new AHUs being added to the system in the next few months we should plan for?"

---

### Meeting 3 — Fri Mar 20

**Theme: "The dashboard is live and predictions are visible — here's what stakeholders will see"**

**What to show**
- **Full live demo of the health dashboard**: navigate through multiple levels, show health index trend charts for different AHUs, demonstrate tier colour coding, show component breakdown scores
- **Prediction chart**: pull up one AHU, show three overlaid lines (last week grey, yesterday blue, prediction green dashed), point to the delta — "this AHU is predicted to use 14 kWh more than its normal pattern today"
- **Chatbot before vs. after**: show a query that used to fail or give a wrong answer, then show it working correctly now

**What to tell them**
- "The dashboard now shows live, auto-refreshed health data for all 11 levels. Any team member can open it and immediately see which AHUs need attention without knowing anything about the underlying data."
- "The prediction chart is live. For any AHU, you can see how its expected energy consumption compares to yesterday and last week, and see the model's forward prediction. This is what feeds the energy anomaly score — if an AHU deviates significantly from prediction, it gets flagged automatically."
- "The chatbot is significantly improved — it now handles [list 3–4 specific query types it couldn't handle before], and we've tightened query understanding for electrical metrics."
- "Ambika has [state Branch A or B outcome clearly]."

**How to raise concerns**
- If there's an AHU or level showing unexpected health scores: *"We noticed Level X, AHU e0X0X is consistently scoring in the 'Monitor' tier. We're not raising this as a critical alert yet, but I'd recommend someone from the maintenance side takes a look at it. Here's the specific metric that's elevated."*
- If chatbot improvements are still in progress: *"The core chatbot improvements are done. There are a few query types we're still polishing — specifically [X and Y] — but they're on track for next week's delivery. The most-used queries are all working correctly."*

**Questions to ask**
- "When you show this to non-technical stakeholders, is the terminology clear? 'Phase Imbalance' and 'THD Drift' might need plain-language tooltips — do you want us to add those?"
- "Is there a specific AHU or scenario you'd like to demo to your superiors on March 31st? We can make sure it's polished for that."
- "For the prediction chart — is it more useful to show this per AHU on demand, or should there be a summary view showing which AHUs have the biggest predicted deviations today?"

---

### Meeting 4 — Fri Mar 27

**Theme: "Delivery is 2 working days away — here is the complete picture"**

**What to show**
- **Full polished walkthrough of all three deliverables** as if this were the actual March 31 delivery:
  1. Chatbot: run 3–4 queries that showcase the improvement (health index query, prediction query, level-wide query, electrical metric query)
  2. Prediction chart: show delta kWh for a real AHU, explain what the number means in plain English
  3. Health dashboard: all 11 levels, live data, correct tiers, component breakdown
- **Ambika's research report** (or draft): hand over the document, give a 2-minute verbal summary of findings and recommendations

**What to tell them**
- "All three deliverables are feature-complete as of today. The next two days are for final testing, documentation, and making sure everything is stable for delivery on March 31st."
- "The health scoring system is now live across all 112+ AHUs. The prediction engine is running. The chatbot handles a significantly broader range of queries with much higher accuracy."
- "Ambika's report concludes [state key finding]. The logging system she built means every rule-based flag from this point forward is automatically building our ML training dataset. We'll revisit ML model training in Q3 once enough labelled events have accumulated."
- "What you're seeing today is what gets delivered on Tuesday."

**How to raise concerns**
- If any final bugs remain: *"There are two known issues we're resolving this weekend: [X] and [Y]. Neither affects the core functionality — they're [describe severity honestly]. They'll be fixed before Tuesday's delivery."*
- If the ML branch outcome is No-Go and that might surprise them: *"I want to set expectations on the ML piece clearly. Ambika's assessment shows that 4 months of post-installation data doesn't yet have enough anomaly events to train reliable ML models — which actually means the AHUs are performing well. The rule-based system delivers full value now, and the logging infrastructure means we'll accumulate labelled training data automatically from here. We'll have a genuine ML dataset to work with in a few months."*

**Questions to ask**
- "Is there anything you'd like added or adjusted before Tuesday's delivery? This is the last checkpoint."
- "Who is the audience for the March 31 delivery — just your team, or will other stakeholders be present? That affects how we pitch the demo."
- "After delivery, what's the process for raising bugs or issues? Should we plan for a support window in April?"
- "Looking ahead — what's the next milestone after this? Knowing that helps us think about what to build on top of this foundation."

---

## Quick-Reference Card

| | Show | Tell | Concern framing | Ask |
|---|---|---|---|---|
| **Mar 6** | Audit doc, formula fixes, Go/No-Go table, prediction formula | Foundation week done, pipeline design locked | Insufficient anomaly data → logging strategy | Priority AHUs? Freshness requirements? Label preferences? |
| **Mar 13** | Live ETL run, CSV output, ML arch doc | Pipeline live all 11 levels, logging live | ETL slow? InfluxDB gaps? | Default dashboard view? Maintenance team review process? New AHUs? |
| **Mar 20** | Dashboard, prediction chart, chatbot before/after | Dashboard live, predictions visible, chatbot improved | Unexpected AHU flags, in-progress queries | Plain-language labels? Mar 31 demo scenario? Summary view? |
| **Mar 27** | Full delivery walkthrough, Ambika's report | Feature-complete, 2 days to delivery | Final bugs (with severity), ML No-Go expectation setting | Last change requests? Delivery audience? Post-delivery support? |
