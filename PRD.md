WACH Insight – Press Release
============================

**Kuala Lumpur Malaysia – February 18 2026** – **WACH Insight** launches today giving non-technical hospital stakeholders a radically simpler way to understand AHU electrical performance in the Women and Child Ward at Hospital KL, delivering clear visual answers in seconds instead of technician callouts.

WACH Insight allows users to ask simple questions like “Show e0101 power consumption for the last 7 days” or “Rank the top 10 devices by average power this month” and instantly receive a time-series chart, a plain-English summary, and downloadable data. Built on secure infrastructure and powered by a local enterprise LLM, the system translates natural language into safe structured queries against InfluxDB, ensuring reliable and controlled access to operational data.

“This removes the bottleneck of technical intermediaries. Our stakeholders can finally explore performance insights themselves,” said Project Lead.

WACH Insight is currently focused on AHUs within the WACH ward and supports predefined time ranges with structured, easy-to-understand outputs. Future updates will incorporate predictive anomaly detection to further enhance operational awareness.

Frequently Asked Questions
--------------------------

**Q1 Who is WACH Insight for**A1 Non-technical hospital administrators and stakeholders who need quick visibility into AHU electrical performance without relying on technicians.

**Q2 What problem does it solve**A2 It removes the dependency on technical staff for generating electrical performance reports, visualizations, and summaries from InfluxDB data.

**Q3 How does it work**A3 A user types or speaks a question. The LLM converts the request into a structured safe query. Middleware validates and executes the query in InfluxDB and returns a chart, summary, and downloadable CSV.

**Q4 What devices are supported**A4 AHUs in the WACH ward with device IDs ranging from e0101 to e1108. If a device ID does not exist, the system informs the user.

**Q5 What time ranges are supported**A5 Last 24 hours Last 7 days Last 30 days All time.

**Q6 What metrics are available in MVP**A6 • power\_total • energy\_import • power\_factor\_avg • current\_avg • volts\_l\_n\_avg • apparent\_power\_total • power\_demand • reactive\_power\_total

**Q7 Does it perform anomaly detection**A7 Not in the current version. The system provides descriptive analytics only. Predictive anomaly features are planned for a future release.

**Q8 How is it different**A8 It combines conversational AI with strict query guardrails and templated outputs, ensuring reliable enterprise-safe analytics rather than open-ended AI speculation.

**Q9 How is it accessed**A9 Via a secure cloud-hosted web application with future authentication and role-based access controls.

Product Requirements Document – WACH Insight
============================================

0 Executive Summary
-------------------

WACH Insight is a secure web-based conversational analytics tool that enables non-technical hospital stakeholders to retrieve AHU electrical performance insights from InfluxDB using natural language, returning structured charts, summaries, and downloadable data.

1 Narrative
-----------

A hospital administrator in WACH needs to understand why energy costs are rising. Normally, they email a technician, wait a day, and receive a static spreadsheet they barely understand.

They try navigating raw dashboards but get lost in device IDs like e0101 and cryptic electrical fields.

Then they open WACH Insight.

They type, “Rank the top 10 devices by average power for the past 30 days.”

Within seconds, a clean bar chart appears. A short summary explains which AHUs consume the most power. A CSV is ready for download.

No calls. No waiting. No confusion.

Operational insight becomes self-serve.

2 Vision & Scope
----------------

WACH Insight provides safe, conversational access to descriptive AHU electrical analytics for the WACH ward only.

• **In scope:**– Natural language query translation– Predefined time range filtering– Line charts for time series– Bar charts for ranking queries– Summary paragraph generation– CSV download– Device existence validation– Browser-based voice input

• **Out of scope:**– Anomaly detection– Root cause analysis– Custom date ranges– Devices outside WACH– Native mobile apps– Multi-ward support

3 Goals
-------

### Business Goals

CategoryGoal statementSuccess metricAdoption80% of WACH admin queries handled without technician involvement≥80% reduction in routine data requestsEngagementAverage session includes at least one completed query≥1 successful query per sessionEfficiencyReduce technician reporting time50% reduction in manual report generation time

### User Goals

CategoryGoal statementSuccess metricSpeedFirst insight generated quickly<10 seconds response timeClarityUser understands output without assistance90% positive feedback in pilot surveyAccuracyCorrect device and metric retrieval100% schema-validated queries

### Non-Goals

– No predictive modeling in MVP– No conversational memory across sessions– No free-text data manipulation

**Why these metrics matter:**Adoption proves business value. Speed builds trust. Accuracy prevents loss of credibility. Clarity ensures non-technical users can operate independently without fallback to technicians.

4 Personas & Key Stories
------------------------

• **Hospital Administrator** – Needs quick operational insight without technical knowledge.• **Facilities Supervisor** – Wants quick comparative performance checks without dashboard navigation.

> “As a hospital administrator, I want to ask simple questions about AHU energy use so that I can make informed operational decisions without calling technicians.”

5 Use-Case Matrix
-----------------

IDUser StoryAcceptance CriteriaUC-1View device power over timeReturns line chart + summary + CSVUC-2Rank top devices by metricReturns bar chart + summary + CSVUC-3Query invalid device IDReturns polite error messageUC-4Ask for anomaly reasoningReturns restriction message

6 Functional Requirements
-------------------------

### FR-1 Natural Language Interface

1.  Accept text input from chatbox.
    
2.  Accept browser speech-to-text input.
    

### FR-2 Query Translation Engine

1.  LLM converts natural language to structured query object.
    
2.  Only predefined metrics allowed.
    
3.  Only predefined time ranges allowed.
    

### FR-3 Middleware Safety Layer

1.  Validate device ID within allowed WACH list.
    
2.  Validate metric against whitelist.
    
3.  Reject unsupported requests.
    

### FR-4 Visualization Engine

1.  Line chart for time series queries.
    
2.  Bar chart for ranking queries.
    
3.  Export CSV functionality.
    

### FR-5 Structured Response Template

1.  Always return chart.
    
2.  Always return summary paragraph.
    
3.  Always return CSV option.
    

7 Non-Functional Requirements
-----------------------------

– Response time under 10 seconds– Secure cloud hosting– Encrypted API communication– No direct LLM access to database– 99% uptime target– Strict schema validation

8 High-Level UX Flow
--------------------

1.  User opens web app.
    
2.  Instruction banner explains supported query types and time ranges.
    
3.  User types or speaks query.
    
4.  LLM generates structured query.
    
5.  Middleware validates.
    
6.  InfluxDB queried.
    
7.  Chart rendered in main output area.
    
8.  Summary paragraph displayed below chart.
    
9.  CSV download button enabled.
    

9 Database Schema
-----------------

### Database 1 devices

– device\_id– ward– device\_type– exists\_flag

### Database 2 metrics\_metadata

– metric\_name– unit– description– allowed\_in\_mvp

### Database 3 query\_logs

– session\_id– timestamp– user\_query– structured\_query– execution\_status

InfluxDB remains the time-series store containing electrical metrics per device ID.

**Linkage:**devices validates allowed AHUs.metrics\_metadata enforces metric whitelist.query\_logs supports auditing and debugging.

10 Build Notes
--------------

PriorityFeatureP0Chat interfaceP0LLM structured query generatorP0Middleware validation layerP0InfluxDB connectorP0Line and bar chart renderingP1CSV exportP1Voice inputP2Authentication layer

11 Out of Scope
---------------

– Predictive anomaly detection– Multi-ward expansion– Advanced analytics– Natural language causal reasoning– Cross-device correlation

Commentary
==========

This is a strong, tightly scoped MVP with real operational value and clear guardrails. The biggest risk is LLM query reliability and schema drift if InfluxDB changes. Another risk is user expectation creep toward anomaly reasoning before the model is integrated. You should prototype the structured query format early to test edge cases. I’d also strongly recommend logging every rejected query for iterative improvement.