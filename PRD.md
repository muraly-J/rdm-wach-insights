WACH Insight – Press Release
============================

**Kuala Lumpur Malaysia – February 18 2026** – **WACH Insight** launches today, giving
non-technical hospital stakeholders a radically simpler way to understand AHU electrical
performance in the Women and Child Ward at Hospital KL, delivering clear visual answers in
seconds instead of technician callouts.

WACH Insight allows users to ask simple questions like *“Show e0101 power consumption for the
last 7 days”* or *“Rank the top 10 devices by average power this month”* and instantly receive
a time-series chart, plain-English summary, and downloadable data. Built on secure
infrastructure and powered by a local enterprise LLM, the system translates natural language
into safe structured queries against InfluxDB—ensuring reliable and controlled access to
operational data.

> *“This removes the bottleneck of technical intermediaries. Our stakeholders can finally
explore performance insights themselves.”*
> — Project Lead

WACH Insight is currently focused on AHUs within the WACH ward and supports predefined time
ranges with structured, easy-to-understand outputs. Future updates will incorporate predictive
anomaly detection to further enhance operational awareness.

---

Frequently Asked Questions
--------------------------

**Q1: Who is WACH Insight for?**
A1: Non-technical hospital administrators and facilities staff who need quick visibility into
AHU electrical performance without relying on technicians.

**Q2: What problem does it solve?**
A2: Eliminates dependency on technical staff for generating electrical performance reports,
visualizations, and summaries from InfluxDB data.

**Q3: How does it work?**
A3: User types or speaks a question. The local LLM converts the request into a *validated
structured query*, which middleware routes to InfluxDB. Outputs include charts, summaries, and
CSV exports.

**Q4: What devices are supported?**
A4: AHUs in the WACH ward with device IDs from `e0101` to `e1108`. Invalid IDs return a
helpful error (e.g., *“I couldn’t find e9999 — it’s outside the WACH ward.”*).

**Q5: What time ranges are supported?**
A5: Last 24 hours • Last 7 days • Last 30 days • All time
> *Note: “All time” queries are automatically capped at 6 months to preserve performance.*

**Q6: What metrics are available in MVP?**
A6:
- `power_total` • `energy_import` • `power_factor_avg` • `current_avg`
- `volts_l_n_avg` • `apparent_power_total` • `power_demand` • `reactive_power_total`

**Q7: Does it perform anomaly detection?**
A7: Not in the current version. WACH Insight provides *descriptive* analytics only. Predictive
features are planned for future releases.

**Q8: How is it different?**
A8: It combines conversational AI with strict guardrails and templated outputs — ensuring
enterprise-safe analytics, not open-ended AI speculation.

**Q9: How is it accessed?**
A9: Via a secure cloud-hosted web application. Authentication (RBAC) is out of scope for MVP;
access uses browser session isolation.

---

Product Requirements Document – WACH Insight
============================================

0 Executive Summary
-------------------

WACH Insight is a secure web-based conversational analytics tool that enables non-technical
hospital stakeholders to retrieve AHU electrical performance insights from InfluxDB using
natural language — returning structured charts, plain-English summaries, and downloadable
data.

---

1 Narrative
-----------

A hospital administrator in WACH needs to understand why energy costs are rising. Normally,
they email a technician, wait a day, and receive a static spreadsheet they barely understand.

They try navigating raw dashboards but get lost in device IDs like `e0101` and cryptic
electrical fields.

Then they open WACH Insight.

They type: *“Rank top 5 devices by energy this month.”*

Within seconds, a bar chart appears — clearly labeled `e0108` at the top. A summary explains:
*“e0108 consumed 420 kWh — 22% more than the next highest device.”* A CSV is ready to
download.

No calls. No waiting. No confusion.
Operational insight becomes self-serve.

---

2 Vision & Scope
----------------

WACH Insight provides safe, conversational access to *descriptive* AHU electrical analytics
for the **WACH ward only**.

- **In scope:**
  – Natural language query translation (text & voice)
  – Predefined time ranges (`last_24h`, `last_7d`, `last_30d`, `all_time`)
  – Line charts for time series, bar charts for rankings
  – Plain-English summary generation + CSV export
  – Device existence validation (`e0101–e1108`)
  – Browser-based speech-to-text input

- **Out of scope:**
  – Anomaly detection
  – Root cause analysis
  – Custom date ranges (e.g., “March 5–12”)
  – Devices outside WACH ward
  – Native mobile apps
  – Multi-ward support

> [BRACKETED NOTE: Clearer than original “out of scope” list — now organized by user-facing
vs. technical exclusions.]

---

3 Goals
-------

### Business Goals
| Category | Goal Statement | Success Metric |
|---------|----------------|----------------|
| Adoption | 80% of WACH admin queries handled without technician involvement | ≥80% reduction
in routine data requests |
| Engagement | Average session includes at least one completed query | ≥1 successful query per
session |
| Efficiency | Reduce technician reporting time | 50% reduction in manual report generation
time |

### User Goals
| Category | Goal Statement | Success Metric |
|---------|----------------|----------------|
| Speed | First insight generated quickly | <10 seconds response time |
| Clarity | User understands output without assistance | ≥90% positive feedback in pilot
survey |
| Accuracy | Correct device and metric retrieval | 100% schema-validated queries |

**Why these metrics matter:**
Adoption proves business value. Speed builds trust. Accuracy prevents credibility loss.
Clarity ensures independence from technical intermediaries.

### Non-Goals
– No predictive modeling in MVP
– No conversational memory across sessions *(but session-local memory allowed, e.g., remember
last-selected device)*
– No free-text data manipulation or chart customization

---

4 Personas & Key Stories
------------------------

- **Hospital Administrator**
  *“I want to ask simple questions about AHU energy use so I can make informed operational
decisions without calling technicians.”*

- **Facilities Supervisor**
  *“I need quick comparative performance checks without navigating complex dashboards.”*

> [BRACKETED NOTE: Added second persona + stronger “I want…” phrasing to reflect user need.]

---

5 Use-Case Matrix
-----------------

| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| UC-1 | View device power over time | Returns line chart + summary paragraph + CSV download |
| UC-2 | Rank top devices by metric | Returns bar chart + summary paragraph + CSV download |
| UC-3 | Query invalid device ID | Returns polite error: *“I couldn’t find [device]. Valid
IDs: e0101–e1108.”* |
| UC-4 | Ask for anomaly reasoning | Returns: *“Anomaly detection isn’t available yet — this
view shows descriptive data only.”* |
| UC-5 | Voice query with background noise | Falls back to typed input or shows *“Could you
type that?”* if ASR confidence < 80% |

---

6 Functional Requirements
-------------------------

### FR-1 Natural Language Interface
1. Accept text input via chatbox
2. Accept browser speech-to-text (Web Speech API); fallback to typed input if confidence < 80%

3. Display real-time placeholder hints: *e.g., “Try: ‘Show power for e0105 last 7 days’”*

### FR-2 Query Translation Engine
1. Local LLM converts natural language into a **structured query object** with fields:
   ```json
   {
     "device_id": "e1234",
     "metric": "energy_import",
     "time_range": "last_7d"
   }
   ```
2. *Only* predefined metrics and time ranges are allowed
3. If confidence < 90% or fields missing → trigger fallback UI (see UC-5)
4. Log rejected/ambiguous queries to `query_logs` for analysis

### FR-3 Middleware Safety Layer
1. Validate device ID against `devices.devices` table (cached for performance)
2. Validate metric against `metrics_metadata.allowed_in_mvp = true`
3. Reject unsupported time ranges with message: *“We support last 24h, 7d, 30d, or all time.”*

4. Cap “all time” queries at 6 months — warn user: *“Showing last 180 days due to size.”*

### FR-4 Visualization Engine
1. Line chart for time-series queries (with smooth interpolation)
2. Bar chart for ranking/top-N queries
3. Exportable CSV with same column order as DB: `timestamp, device_id, metric_name, value`

### FR-5 Structured Response Template
1. Always return chart (mandatory)
2. Always return summary paragraph: *“Device X consumed Y [unit]. That’s [Z]% more than device
W.”*
3. Always provide CSV download button (`download.csv`)

---

7 Non-Functional Requirements
-----------------------------

| Requirement | Details |
|------------|---------|
| Response time | <10 seconds for 95% of queries (<15s max for capped “all time”) |
| Security | AES-256 encryption in transit & at rest; no direct LLM→InfluxDB access |
| Availability | 99% uptime target ( excludes scheduled maintenance ) |
| Logging | All queries logged to `query_logs` with structured fields for auditing/debugging |

---

8 High-Level UX Flow
--------------------

1. User opens web app → sees banner:
   *“Ask about power, energy, or demand for WACH ward AHUs (e0101–e1108). Try: ‘Show power for
e0105 last 7 days’”*
2. User types or speaks query
3. LLM generates structured query
4. Middleware validates device + metric + time range
5. InfluxDB queried (with caching for repeated queries)
6. Response rendered: Chart → Summary → CSV download

> [BRACKETED NOTE: Integrated fallback + prompt hints directly into UX flow.]

---

9 Database Schema
-----------------

### `devices`
- `device_id` (text)
- `ward` (e.g., "WACH")
- `device_type` (e.g., "AHU")
- `exists_flag` (boolean) — for soft-deleted devices

### `metrics_metadata`
- `metric_name` (primary key)
- `unit` (e.g., “kW”, “kWh”)
- `description`
- `allowed_in_mvp` (boolean) — e.g., `"power_total": true`, `"vibration": false`

### `query_logs`
- `session_id` (UUID)
- `timestamp` (UTC)
- `user_query` (raw text)
- `structured_query` (JSON blob)
- `status` (`success`, `rejected_no_device`, `rejected_bad_metric`, `partial`)
- `fallback_used` (boolean)

> InfluxDB remains the time-series store. Linkage:
- `devices` validates allowed AHUs
- `metrics_metadata` enforces whitelist
- `query_logs` enables iterative improvement (e.g., retrain on rejected queries)

---

10 Build Notes
--------------

| Priority | Feature | Notes |
|---------|---------|-------|
| **P0** | Chat interface (text + voice fallback) | Use React + simple ASR wrapper |
| **P0** | Local LLM structured query generator | Use distilled LLaMA-3 or Mistral (off-cloud)
|
| **P0** | Middleware validation layer | JSON schema + whitelist enforcement |
| **P0** | InfluxDB connector | Use Flux queries for efficiency; limit `TOP 10` for ranking |
| **P0** | Line/bar chart rendering | Use Plotly (lightweight, exportable to CSV) |
| **P1** | CSV export | Include timestamp + device_id + metric in columns |
| **P1** | Voice input | Browser-native; graceful degradation if unsupported |
| **P2** | Authentication layer | Deferred to v1.1; MVP uses session-only access |

---

11 Out of Scope
---------------

– Predictive anomaly detection
– Root cause analysis
– Custom date ranges
– Natural language causal reasoning (*e.g., “Why did power spike?”*)
– Cross-device correlation

---

Appendix A: Sample Queries & Fallback Behavior
=============================================

| User Query | Expected Response if Valid | Expected Response if Ambiguous / Invalid |
|------------|----------------------------|------------------------------------------|
| *“Show power for e0105 last 7 days”* | Line chart + summary: *“Average power over e0105 is
2.3 kW”* + CSV | — |
| *“Rank devices with highest energy this month”* | Bar chart (top N) + summary: *“e0108 leads
at 420 kWh”* | — |
| *“Show power for e9999 last week”* | Error: *“e9999 doesn’t exist in WACH. Valid IDs:
e0101–e1108”* | — |
| *“What’s the most energy used?”* | Prompt + summary: *“e0108 consumed 420 kWh (top
device)”*<br>*Device ID auto-inferred from top result* | If multiple devices: *“Could you
specify a date range or device?”* |
| *“Why did power spike on March 5?”* | *“I can show the data — but I don’t yet explain *why*.
Anomaly analysis is coming soon.”* | Adds link to Roadmap if feedback received ≥3 times |

---

WACH Insight
A safer, simpler way to turn electrical data into decisions.
