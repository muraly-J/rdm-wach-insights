# WACH Insight — User Guide

WACH Insight is a web dashboard that monitors the electrical health of the Air Handling Units (AHUs) in your ward. It shows you which units are running well, which need attention, and lets you ask plain-language questions to get more detail.

---

## Opening the Dashboard

1. Open a web browser and navigate to the WACH Insight URL provided by your IT team.
2. If prompted, enter the access code or API key your administrator gave you.
3. You will land on the main dashboard. Use the level selector bar at the top to switch between building levels (1–11).

---

## Understanding the Health Scores

Each AHU receives a **FAIR Health Score** — a number from 0 to 100 that summarises how well the unit is running electrically. Higher is better.

| Score range | Tier | What it means |
|-------------|------|---------------|
| 80 – 100 | **Healthy** | Unit is running normally. No action needed. |
| 60 – 79 | **Monitor** | Minor deviation detected. Worth keeping an eye on. |
| 40 – 59 | **Maintenance** | Degraded performance. Schedule a maintenance visit. |
| 0 – 39 | **Critical** | Significant fault detected. Escalate to facilities. |

FAIR stands for the four electrical dimensions the score measures:

- **F — Frequency anomaly:** unusual variations in supply frequency
- **A — Amplitude anomaly:** energy consumption deviating from expected patterns
- **I — Imbalance:** voltage or current imbalance across the three phases
- **R — Resilience:** power factor and overload indicators

---

## Reading the Dashboard

**Top panel — Level summary:** Shows the average health score for all AHUs on the selected level, along with a trend line for the past 7 days.

**Ranking cards:** The five healthiest and five most in-need-of-attention AHUs on the level, updated every refresh.

**Safety flags:** Persistent electrical issues that have been active for more than 72 hours:
- *THD Critical* — total harmonic distortion consistently above safe limits
- *Severe Imbalance* — phase imbalance exceeding safety thresholds
- *Power Factor Low* — sustained low power factor (increases energy cost)
- *Overload Chronic* — recurring overload on the unit

---

## Using the Chatbot

Click the chat icon (bottom right) to open the assistant. You can type questions in plain English. The assistant understands four types of question:

### General questions
Ask about the dashboard, what scores mean, or what is happening overall.

> *"Which AHUs on level 3 need attention this week?"*  
> *"What does a health score of 45 mean for unit e0512?"*  
> *"Show me the health trend for the past month on level 7."*

### Technical questions
For engineers who want raw data and diagnostic detail.

> *"What is the THD reading for e0202 over the last 48 hours?"*  
> *"Show the power factor trend for all level 5 units in the last 30 days."*  
> *"Which units had energy anomalies above 0.05 this week?"*

### Maintenance questions
For technicians planning or following up on site visits.

> *"Which units on level 2 have had safety flags active for more than a week?"*  
> *"Give me a maintenance summary for e0311 — what issues have been recurring?"*  
> *"Are there any overload warnings on level 9 right now?"*

### Financial questions
For ward managers concerned with energy costs.

> *"What is the estimated excess energy cost from units in the Critical tier this month?"*  
> *"Which level has the highest power factor penalty charges?"*  
> *"Show the financial impact summary for the whole site."*

---

## When Something Looks Wrong

If a unit drops to **Critical** (score below 40) or a new safety flag appears, the dashboard highlights it in red. You do not need to act immediately on every amber flag, but a Critical score warrants escalation.

**Who to contact:**
- Facilities / BMS team: for units in the Critical tier or overload flags
- IT / WACH Insight administrator: if the dashboard itself is unavailable or showing errors
- Your ward manager: for financial impact questions or budget concern

If the dashboard shows an error message (e.g. "Service unavailable"), please note the time and contact your IT administrator.
