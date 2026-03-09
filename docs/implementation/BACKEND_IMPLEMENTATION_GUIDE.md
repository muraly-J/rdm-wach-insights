# WACH Insight Backend - Implementation Guide

> **Version:** 1.0.0  
> **Last Updated:** March 6, 2026  
> **Backend Type:** FastAPI (Python) - Electrical Health Analytics for AHU Fleet

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start-5-minutes)
2. [API Reference](#api-reference)
3. [Data Models & Schemas](#data-models--schemas)
4. [FAIR Health Scoring Explained](#fair-health-scoring-explained)
5. [Configuration Guide](#configuration-guide)
6. [Frontend Integration Examples](#frontend-integration-examples)

---

## Quick Start (5 minutes)

### Step 1: Build the Docker Image

On your machine (where backend will run):

```bash
# Navigate to project directory
cd /path/to/wach-insight

# Build Docker image
docker build -t wach-insight-backend .

# Verify image was created
docker images | grep wach-insight-backend
```

### Step 2: Create Environment File

```bash
# Copy example env file
cp .env.example .env

# Edit with your actual values
nano .env  # or vi, vim, VS Code, etc.
```

**Required values in `.env`:**

| Variable | Description | Example |
|----------|-------------|---------|
| `INFLUX_URL` | InfluxDB server URL | `http://localhost:8086` or cloud URL |
| `INFLUX_TOKEN` | API token for InfluxDB | Your actual InfluxDB token |
| `INFLUX_ORG` | Organization name | `wach` |
| `INFLUX_BUCKET` | Bucket containing AHU data | `wach_bucket_3` |
| `LMS_BASE_URL` | LM Studio server URL | `http://localhost:1234/v1` |
| `CORS_ORIGINS` | Frontend URLs allowed to call API | `http://localhost:3000` |

### Step 3: Run the Backend

```bash
# Start container in detached mode
docker run -d \
  --name wach-backend \
  -p 8000:8000 \
  --env-file .env \
  wach-insight-backend

# Check container is running
docker ps | grep wach-backend
```

### Step 4: Verify Backend is Working

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok"}
```

### Step 5: Make Your First API Call

```bash
# Query for health ranking of Level 1 devices
curl "http://localhost:8000/api/dashboard/ranking?level=1&range=last_30d"

# Expected response: JSON with best/worst AHUs
```

---

## API Reference

### Base URL
```
http://localhost:8000
```

When deploying to your machine, replace `localhost` with your server's IP address.

---

### Endpoint 1: Health Check

**Purpose:** Verify backend is running

```
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

---

### Endpoint 2: LLM Query (Main Interface)

**Purpose:** Natural language queries about AHU electrical data

```
POST /api/query
```

**Request Body:**
```json
{
  "user_query": "Show power consumption for e0101 last 7 days",
  "session_id": "optional-uuid-here"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_query` | string | Yes | Natural language question about AHUs |
| `session_id` | string (UUID) | No | Session tracking ID |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "What is the power consumption of e0101 over the last 24 hours?",
    "session_id": "abc-123-def"
  }'
```

**Response:**
```json
{
  "query_type": "time_series",
  "device_ids": ["e0101"],
  "metric": "power_total",
  "time_range": "last_24h",
  "structured_query": {
    "query_type": "time_series",
    "device_ids": ["e0101"],
    "metric": "power_total",
    "time_range": "last_24h"
  },
  "chart_data": {
    "data": [
      {"timestamp": "2026-03-05T14:00:00Z", "value": 120.5, "device_id": "e0101"},
      {"timestamp": "2026-03-05T14:05:00Z", "value": 121.2, "device_id": "e0101"},
      ...
    ],
    "chart_type": "line",
    "metric_label": "total active power (kW)",
    "time_range_label": "the past 24 hours"
  },
  "summary": "e0101 shows stable power consumption averaging 120.5 kW over the last day...",
  "csv_available": true
}
```

**Supported Natural Language Queries:**

| User Query | Translates To |
|------------|---------------|
| "Show power consumption for e0101 last 7 days" | Time series, metric: power_total |
| "Rank top 5 devices by energy today" | Ranking, metric: energy_import |
| "What's the health index for e0205?" | Time series, metric: health_index |
| "Show me devices with highest power factor" | Ranking, metric: power_factor_avg |

**Allowed Metrics:**

| Metric Name | Unit | Description |
|-------------|------|-------------|
| `power_total` | kW | Total active power across all phases |
| `energy_import` | kWh | Energy consumed from grid |
| `power_factor_avg` | (unitless) | Average power factor (-1 to 1) |
| `current_unbalance` | % | Current imbalance percentage |
| `volts_l1_thd` | % | Voltage THD Phase L1 |
| `current_l1_thd` | % | Current THD Phase L1 |
| `freq` | Hz | Supply frequency |

---

### Endpoint 3: Dashboard Ranking

**Purpose:** Get top 5 healthiest and top 5 at-risk AHUs for a specific level

```
GET /api/dashboard/ranking
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string/integer | No | `1` | Building level (1-11) |
| `range` | string | No | `last_30d` | Time range: `last_24h`, `last_7d`, `last_30d` |

**Response:**
```json
{
  "level": "1",
  "time_range": "last_30d",
  "snapshot_time": "2026-03-05T14:00:00+08:00",
  "best": [
    {
      "ahu_id": "e0105",
      "index": 94.2,
      "tier": "Healthy",
      "level": "Level 1"
    },
    {
      "ahu_id": "e0103",
      "index": 92.8,
      "tier": "Healthy",
      "level": "Level 1"
    },
    ...
  ],
  "worst": [
    {
      "ahu_id": "e0112",
      "index": 45.3,
      "tier": "Maintenance Soon",
      "level": "Level 1"
    },
    {
      "ahu_id": "e0107",
      "index": 38.9,
      "tier": "Critical",
      "level": "Level 1"
    },
    ...
  ]
}
```

**Health Tier Definitions:**

| Tier | Health Index Range | Action Required |
|------|-------------------|-----------------|
| **Healthy** | 80-100 | No action needed |
| **Monitor** | 60-79 | Watch for degradation |
| **Maintenance Soon** | 40-59 | Schedule maintenance |
| **Critical** | 0-39 | Immediate attention required |

---

### Endpoint 4: Dashboard Trend

**Purpose:** Get time-series health index data for all AHUs on a level

```
GET /api/dashboard/trend
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string/integer | No | `1` | Building level (1-11) |
| `range` | string | No | `7d` | Time range: `24h`, `7d`, `30d` |

**Response (Simplified):**
```json
{
  "level": "1",
  "range": "7d",
  "ahus": ["e0101", "e0102", ..., "e0121"],
  "series": [
    {
      "timestamp": "2026-03-05T14:00:00+08:00",
      "ahu_id": "e0101",
      "health_index": 94.2,
      "energy_anomaly": 0.05,
      "pf_degradation": 0.12,
      "phase_imbalance": 0.08,
      "thd_drift": 0.15,
      "overload": 0.22
    },
    ...
  ],
  "latest_snapshot": {
    "e0101": 94.2,
    "e0102": 87.5,
    ...
  }
}
```

**Chart Data Structure:**

The `series` array contains one entry per AHU per timestamp. For time-series charts:

- **X-axis:** `timestamp`
- **Y-axis:** `health_index` (or any component: `energy_anomaly`, `pf_degradation`, etc.)
- **Series:** Each AHU is a separate line

**Component Scores (0-1 range, higher = worse):**

| Score | Description | Threshold |
|-------|-------------|-----------|
| `energy_anomaly` | Energy consumption deviation from baseline | 0.10+值得关注 |
| `pf_degradation` | Power factor degradation | 0.15+值得关注 |
| `phase_imbalance` | Current/voltage imbalance between phases | 0.10+值得关注 |
| `thd_drift` | Total Harmonic Distortion drift | 0.15+值得关注 |
| `overload` | Operating near historical maximum | 0.20+值得关注 |

---

### Endpoint 5: Dashboard Summary

**Purpose:** Generate LLM-powered analytical summaries for health metrics

```
GET /api/dashboard/summary
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string/integer | No | `1` | Building level (1-11) |
| `range` | string | No | `7d` | Time range: `24h`, `7d`, `30d` |
| `ahu_id` | string | No | None | Optional specific AHU for per-device analysis |

**Response:**
```json
{
  "level": "1",
  "range": "7d",
  "ahu_id": null,
  "summaries": {
    "health_index": {
      "title": "Health Index",
      "summary": "Level 1 shows an overall healthy trend with 67% of devices in the Healthy tier..."
    },
    "energy_anomaly": {
      "title": "Energy Anomaly",
      "summary": "Energy consumption patterns remain stable with minor deviations detected in e0112..."
    },
    "pf_degradation": {
      "title": "Power Factor Degradation",
      "summary": "Power factor metrics show stable performance across the fleet..."
    },
    "phase_imbalance": {
      "title": "Phase Imbalance",
      "summary": "Phase imbalance levels are within acceptable thresholds..."
    },
    "thd_drift": {
      "title": "THD Drift",
      "summary": "Total Harmonic Distortion remains stable across monitoring period..."
    },
    "overload": {
      "title": "Overload",
      "summary": "No significant overload events detected in the monitored period..."
    }
  }
}
```

---

## Data Models & Schemas

### AHU Level Mapping

| Level | Device Count | ID Range | Department |
|-------|--------------|----------|------------|
| 1 | 21 | e0101-e0121 | Women & Child Ward L1 |
| 2 | 15 | e0201-e0218 | Orthopaedic Ward L1 |
| 3 | 16 | e0210-e0423 | ENT L1 |
| 4 | 13 | e0401-e0419 | Ophthalmology |
| 5 | 12 | e0501-e0622 | Paediatrics |
| 6 | 10 | e0601-e0628 | Maternity |
| 7 | 4 | e0701-e0704 | ICU Level 1 |
| 8 | 5 | e0801-e0805 | ICU Level 2 |
| 9 | 8 | e0901-e0908 | ICU Level 3 |
| 10 | 8 | e1001-e1008 | Theatre |
| 11 | 8 | e1101-e1108 | Laboratory |

**Device ID Format:** `e{level}{unit}`
- Example: `e0105` = Level 1, Unit 5
- Example: `e0712` = Level 7, Unit 12

---

### Allowed Metrics Reference

**Power Metrics:**
| Metric | Unit | Description |
|--------|------|-------------|
| `power_total` | kW | Total active power across all phases |
| `power_l1` | kW | Active power Phase L1 |
| `power_l2` | kW | Active power Phase L2 |
| `power_l3` | kW | Active power Phase L3 |
| `apparent_power_total` | kVA | Total apparent power |
| `reactive_power_total` | kVAR | Total reactive power |

**Energy Metrics:**
| Metric | Unit | Description |
|--------|------|-------------|
| `energy_import` | kWh | Energy consumed from grid |
| `energy_export` | kWh | Energy sent to grid |
| `reactive_energy_import` | kVARh | Reactive energy consumed |

**Current Metrics:**
| Metric | Unit | Description |
|--------|------|-------------|
| `current_avg` | A | Average current across phases |
| `current_l1` | A | Current Phase L1 |
| `current_unbalance` | % | Current unbalance percentage |

**Voltage Metrics:**
| Metric | Unit | Description |
|--------|------|-------------|
| `volts_l_n_avg` | V | Phase-to-neutral voltage average |
| `volts_l1_n` | V | Phase L1 to neutral voltage |
| `volts_unbalance` | % | Voltage unbalance percentage |

**Power Quality Metrics:**
| Metric | Unit | Description |
|--------|------|-------------|
| `power_factor_avg` | (unitless) | Power factor (-1 to 1, target >0.85) |
| `power_factor_l1` | (unitless) | Power factor Phase L1 |
| `current_l1_thd` | % | Current THD Phase L1 |
| `volts_l1_thd` | % | Voltage THD Phase L1 |

**Other:**
| Metric | Unit | Description |
|--------|------|-------------|
| `freq` | Hz | Supply frequency (target: 50Hz) |
| `digital_input_1_and_2` | - | Binary status inputs |

---

## FAIR Health Scoring Explained

### What is FAIR?

**FAIR** = **F**airness through **A**bsolute and **I**nterrelative scoring

A rule-based health scoring system for AHU electrical equipment.

---

### The Problem With Absolute Scoring

| AHU | Average Power | Normal PF |
|-----|---------------|-----------|
| e0101 (small AHU) | 0.67 kW | 0.35 |
| e0105 (large AHU) | 35 kW | 0.74 |

**Absolute threshold approach FAILS:**
- Applying "PF > 0.85" to both would label e0101 as permanently broken
- Even though e0101 is behaving normally for its class

---

### The FAIR Solution: Per-AHU Baselines

**Each AHU is scored against its OWN historical baseline.**

The question isn't: "Is this device good?"  
The question is: "Is this device behaving differently than usual?"

---

### Health Index Formula

```
Health Index = 100 - (weighted_penalty × 100)

Where weighted_penalty = 
    energy_anomaly     × 0.15
  + power_factor       × 0.25
  + phase_imbalance    × 0.25
  + thd_drift          × 0.15
  + overload           × 0.20
```

**Note:** All component scores are in range [0, 1], where:
- `0` = perfect (no penalty)
- `1` = worst case (full penalty)

---

### Component Score Details

#### 1. Energy Anomaly (weight: 0.15)

**What it measures:** Deviation from expected energy consumption

**Calculation:**
```
Z-score = (current_delta_kwh - historical_median) / robust_std
Score = sigmoid(Z-score × sensitivity)
```

**Use case:** Detect unusual energy consumption patterns

---

#### 2. Power Factor Degradation (weight: 0.25)

**What it measures:** Decline in power factor over time

**Calculation:**
```
Z-score = (current_pf - historical_median_pf) / robust_std_pf
Score = sigmoid(Z-score × sensitivity)

If current_power < 60% of own median power:
    Apply load discount (score reduced by 65%)
```

**Use case:** Detect capacitor bank issues, underloaded equipment

---

#### 3. Phase Imbalance (weight: 0.25)

**What it measures:** Current/voltage imbalance between phases

**Calculation:**
```
Z-score = (current_unbalance - historical_median) / robust_std
Score = sigmoid(Z-score × sensitivity)
```

**Thresholds:**
- Normal: < 2% imbalance
- Warning: 2-5% imbalance
- Critical: > 5% imbalance

---

#### 4. THD Drift (weight: 0.15)

**What it measures:** Total Harmonic Distortion trends

**Calculation:**
```
THD_24h_mean = 24-hour rolling mean of THD values
Z-score = (current_thd - historical_median_thd) / robust_std_thd
Score = sigmoid(Z-score × sensitivity)
```

**IEEE 519 Standards:**
- Limited THD: < 5%
- Critical THD: > 5%

---

#### 5. Overload (weight: 0.20)

**What it measures:** Operating near historical maximum

**Calculation:**
```
Normal = p95 ceiling for this AHU
Score = sigmoid((current_power / normal) × sensitivity)
```

**Use case:** Detect equipment running beyond safe limits

---

### Health Tier Distribution

| Tier | Range | Color | Recommended Action |
|------|-------|-------|-------------------|
| Healthy | 80-100 | 🟢 Green | No action needed |
| Monitor | 60-79 | 🟡 Yellow | Watch for degradation |
| Maintenance Soon | 40-59 | 🟠 Orange | Schedule maintenance within 2 weeks |
| Critical | 0-39 | 🔴 Red | Immediate attention required |

---

## Configuration Guide

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INFLUX_URL` | Yes | - | InfluxDB server URL |
| `INFLUX_TOKEN` | Yes | - | API token for InfluxDB |
| `INFLUX_ORG` | No | `wach` | Organization name |
| `INFLUX_BUCKET` | No | `wach_bucket_3` | Bucket name |
| `LMS_BASE_URL` | Yes | - | LM Studio server URL |
| `LMS_MODEL` | No | `qwen/qwen3-coder-next` | Model name |
| `LMS_API_KEY` | No | `lm-studio` | API key placeholder |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Allowed origins (comma-separated) |
| `DEBUG` | No | `false` | Enable debug mode |

---

### Example: InfluxDB Cloud Configuration

```env
INFLUX_URL=https://us-east-1-1.aws.cloud2.influxdata.com
INFLUX_TOKEN=inflx_token_abc123xyz789def456ghi012
INFLUX_ORG=wach
INFLUX_BUCKET=wach_bucket_3
```

**How to get these from InfluxDB Cloud:**
1. Log into https://cloud.influxdata.com
2. Navigate to **Load Data** → **API Tokens**
3. Copy your token
4. Note your organization and bucket names

---

### Example: LM Studio Configuration

```env
# If LM Studio running on same machine:
LMS_BASE_URL=http://localhost:1234/v1

# If LM Studio running on different machine:
LMS_BASE_URL=http://192.168.1.50:1234/v1

LMS_MODEL=qwen/qwen3-coder-next
LMS_API_KEY=lm-studio
```

**How to configure LM Studio:**
1. Download LM Studio from https://lmstudio.ai
2. Load a model (e.g., `qwen/qwen3-coder-next`)
3. Start the local server on port 1234
4. Backend will connect to this local LLM

---

### Example: Multiple Frontend Origins

```env
# Local development:
CORS_ORIGINS=http://localhost:3000

# Development on same network:
CORS_ORGINS=http://localhost:3000,http://192.168.1.100:3000

# Production:
CORS_ORIGINS=http://localhost:3000,http://wach-insight.com
```

---

## Frontend Integration Examples

### JavaScript (Fetch API)

```javascript
// api.js
const API_BASE = 'http://localhost:8000'; // Replace with your backend URL

// Query LLM
async function queryLLM(question) {
  try {
    const response = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: question,
        session_id: crypto.randomUUID()
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail?.error || 'Query failed');
    }
    
    return data;
  } catch (error) {
    console.error('Query error:', error);
    throw error;
  }
}

// Get dashboard ranking
async function getDashboardRanking(level, range = 'last_30d') {
  const url = `${API_BASE}/api/dashboard/ranking?level=${level}&range=${range}`;
  
  try {
    const response = await fetch(url);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch ranking');
    }
    
    return data;
  } catch (error) {
    console.error('Ranking error:', error);
    throw error;
  }
}

// Get dashboard trend
async function getDashboardTrend(level, range = '7d') {
  const url = `${API_BASE}/api/dashboard/trend?level=${level}&range=${range}`;
  
  try {
    const response = await fetch(url);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch trend');
    }
    
    return data;
  } catch (error) {
    console.error('Trend error:', error);
    throw error;
  }
}

// Get dashboard summary
async function getDashboardSummary(level, range = '7d') {
  const url = `${API_BASE}/api/dashboard/summary?level=${level}&range=${range}`;
  
  try {
    const response = await fetch(url);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch summary');
    }
    
    return data;
  } catch (error) {
    console.error('Summary error:', error);
    throw error;
  }
}

// Example usage
async function example() {
  // Query LLM
  const queryResult = await queryLLM('Show power consumption for e0101 last 7 days');
  console.log(queryResult.chart_data);
  
  // Get ranking
  const ranking = await getDashboardRanking(1, 'last_30d');
  console.log('Best:', ranking.best);
  console.log('Worst:', ranking.worst);
  
  // Get trend data
  const trend = await getDashboardTrend(1, '7d');
  console.log('Series:', trend.series);
  
  // Get summaries
  const summary = await getDashboardSummary(1, '7d');
  console.log('Summaries:', Object.keys(summary.summaries));
}
```

---

### TypeScript Interfaces

```typescript
// types.ts

export interface ChartDataPoint {
  timestamp: string;
  value: number;
  device_id?: string;
}

export interface ChartPayload {
  data: ChartDataPoint[];
  chart_type: 'line' | 'bar';
  metric_label: string;
  time_range_label: string;
}

export interface QueryResponse {
  query_type: 'time_series' | 'ranking';
  device_ids: string[];
  metric: string;
  time_range: string;
  structured_query: Record<string, unknown>;
  chart_data: ChartPayload;
  summary: string;
  csv_available?: boolean;
}

export interface RiskScore {
  score: number;
  severity: string;
  confidence: string;
  signal: string;
}

export interface SingleAHURiskAssessment {
  ahu_id: string;
  timestamp: string;
  health_index: number;
  health_tier: string;
  energy: {
    forecast_24h_kwh?: number;
    normal_range_kwh?: number[];
    deviation_probability_pct?: number;
    trend_7d: string;
  };
  risk_scores: {
    power_factor?: RiskScore & { confidence: 'High' };
    phase_imbalance?: RiskScore & {
      confidence: 'Moderate';
      root_cause_uncertainty?: string;
    };
    thd_drift?: RiskScore & { confidence: 'High' };
    overload?: RiskScore & {
      confidence: 'Moderate';
      seasonal_caveat?: string;
    };
  };
  data_quality: {
    missing_data_pct: number;
    days_since_last_valid_reading: number;
    model_source: string;
    model_confidence_flag: string;
  };
}

export interface FleetRankingResponse {
  level: string;
  time_range: string;
  snapshot_time?: string;
  best: Array<{
    ahu_id: string;
    index: number;
    tier: string;
    level: string;
  }>;
  worst: Array<{
    ahu_id: string;
    index: number;
    tier: string;
    level: string;
  }>;
}

export interface TrendResponse {
  level: string;
  range: string;
  ahus: string[];
  series: Array<{
    timestamp: string;
    ahu_id: string;
    health_index: number;
    energy_anomaly: number;
    pf_degradation: number;
    phase_imbalance: number;
    thd_drift: number;
    overload: number;
  }>;
  latest_snapshot: Record<string, number>;
}

export interface SummaryResponse {
  level: string;
  range: string;
  ahu_id?: string;
  summaries: Record<string, {
    title: string;
    summary: string;
  }>;
}
```

---

### React Component Example

```jsx
// Dashboard.jsx
import { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000'; // Your backend URL

export default function Dashboard() {
  const [level, setLevel] = useState('1');
  const [timeRange, setTimeRange] = useState('last_30d');
  const [ranking, setRanking] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchRanking = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/dashboard/ranking?level=${level}&range=${timeRange}`
      );
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch ranking');
      }
      
      setRanking(data);
    } catch (error) {
      console.error('Fetch error:', error);
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRanking();
  }, [level, timeRange]);

  return (
    <div className="dashboard">
      <h1>Electrical Health Dashboard</h1>
      
      {/* Controls */}
      <div className="controls">
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
        >
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'].map(l => (
            <option key={l} value={l}>Level {l}</option>
          ))}
        </select>

        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
        >
          <option value="last_24h">Last 24 hours</option>
          <option value="last_7d">Last 7 days</option>
          <option value="last_30d">Last 30 days</option>
        </select>

        <button onClick={fetchRanking} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Results */}
      {ranking && (
        <div className="results">
          {/* Best Units */}
          <section>
            <h2>🏆 Healthiest AHUs</h2>
            {ranking.best.map((unit, i) => (
              <div key={unit.ahu_id} className="health-card healthy">
                <span>#{i + 1}</span>
                <strong>{unit.ahu_id}</strong>
                <span>Health: {unit.index.toFixed(1)}</span>
              </div>
            ))}
          </section>

          {/* Worst Units */}
          <section>
            <h2>⚠️ Needs Attention</h2>
            {ranking.worst.map((unit, i) => (
              <div key={unit.ahu_id} className="health-card critical">
                <span>#{ranking.worst.length - i}</span>
                <strong>{unit.ahu_id}</strong>
                <span>Health: {unit.index.toFixed(1)}</span>
              </div>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}
```

---

### Error Handling Patterns

```javascript
// Handle common errors

async function safeQuery(backendUrl, userQuery) {
  try {
    const response = await fetch(`${backendUrl}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_query: userQuery })
    });

    const data = await response.json();

    if (!response.ok) {
      // Rate limit exceeded
      if (response.status === 429) {
        throw new Error(
          'Too many requests. Please wait a moment before trying again.'
        );
      }

      // Invalid query (injection detected)
      if (response.status === 400) {
        throw new Error(
          `${data.detail?.error} \nSuggestion: ${data.detail?.suggestion}`
        );
      }

      // Parse error
      if (response.status === 422) {
        throw new Error(
          `${data.detail?.error} \nSuggestion: ${data.detail?.suggestion}`
        );
      }

      // Backend error
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return data;

  } catch (error) {
    console.error('Backend query failed:', error);
    
    // Network error
    if (!navigator.onLine) {
      alert('No internet connection. Please check your network.');
    } else if (error.message.includes('Failed to fetch')) {
      alert(`Cannot connect to backend at ${backendUrl}\n` +
            'Is the Docker container running?\n' +
            'Run: docker ps | grep wach-backend');
    } else {
      alert(error.message);
    }
    
    throw error;
  }
}
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs wach-backend
```

**Common issues:**

| Error | Solution |
|-------|----------|
| `FileNotFoundError: [Errno 2] No such file or directory` | Check `.env` values for InfluxDB/LLM URLs |
| `ConnectionRefusedError` | Verify InfluxDB and LM Studio are running and accessible |
| `Permission denied` | Check Docker has read access to `.env` file |

---

### API Returns 502 Bad Gateway

**Cause:** Backend can't reach InfluxDB or LM Studio

**Check connectivity:**
```bash
# Test InfluxDB
curl -v http://your-influx-url:8086/api/v2/ping

# Test LM Studio
curl -v http://localhost:1234/v1/models
```

---

### CORS Error in Browser

**Error:** `Access to fetch...has been blocked by CORS policy`

**Solution:** Update `CORS_ORIGINS` in `.env`:

```env
# Allow all origins (development only)
CORS_ORIGINS=*

# Or add specific origin
CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

Then restart container:
```bash
docker stop wach-backend
docker run -d --name wach-backend \
  -p 8000:8000 \
  --env-file .env \
  wach-insight-backend
```

---

### Queries Returning Empty Data

**Check:**
1. InfluxDB bucket has data
2. Device IDs in queries match actual devices (`e0101`-`e1108`)
3. Time range matches available data

**Verify device exists:**
```bash
curl "http://localhost:8000/api/dashboard/ranking?level=1&range=last_30d"
```

If this fails with "No devices found", the device IDs in InfluxDB don't match expected format.

---

## API Response Formats (Complete Reference)

### Health Endpoint
```json
{"status":"ok"}
```

---

### Query Response (Time Series)
```json
{
  "query_type": "time_series",
  "device_ids": ["e0101"],
  "metric": "power_total",
  "time_range": "last_24h",
  "structured_query": { ... },
  "chart_data": {
    "data": [
      {"timestamp": "2026-03-05T14:00:00Z", "value": 120.5, "device_id": "e0101"},
      ...
    ],
    "chart_type": "line",
    "metric_label": "total active power (kW)",
    "time_range_label": "the past 24 hours"
  },
  "summary": "...",
  "csv_available": true
}
```

---

### Ranking Response
```json
{
  "level": "1",
  "time_range": "last_30d",
  "snapshot_time": "2026-03-05T14:00:00+08:00",
  "best": [
    {"ahu_id": "e0105", "index": 94.2, "tier": "Healthy", "level": "Level 1"},
    ...
  ],
  "worst": [
    {"ahu_id": "e0112", "index": 45.3, "tier": "Maintenance Soon", "level": "Level 1"},
    ...
  ]
}
```

---

### Trend Response
```json
{
  "level": "1",
  "range": "7d",
  "ahus": ["e0101", "e0102", ...],
  "series": [
    {
      "timestamp": "2026-03-05T14:00:00+08:00",
      "ahu_id": "e0101",
      "health_index": 94.2,
      "energy_anomaly": 0.05,
      "pf_degradation": 0.12,
      "phase_imbalance": 0.08,
      "thd_drift": 0.15,
      "overload": 0.22
    },
    ...
  ],
  "latest_snapshot": {
    "e0101": 94.2,
    ...
  }
}
```

---

### Summary Response
```json
{
  "level": "1",
  "range": "7d",
  "ahu_id": null,
  "summaries": {
    "health_index": {
      "title": "Health Index",
      "summary": "..."
    },
    "energy_anomaly": {
      "title": "Energy Anomaly",
      "summary": "..."
    },
    ...
  }
}
```

---

## Rate Limiting

- **Max requests:** 20 per minute per IP
- **Response when exceeded:** HTTP 429 with retry-after message

---

## Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

---

## Support

For questions or issues:

1. Check error logs: `docker logs wach-backend`
2. Verify `.env` configuration
3. Test endpoints with curl
4. Check InfluxDB and LM Studio are accessible

---

**End of Guide**
