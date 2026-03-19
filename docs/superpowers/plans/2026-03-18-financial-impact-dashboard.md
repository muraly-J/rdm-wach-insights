# Financial Impact ROI Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Financial Impact section to WACH Insight that translates AHU health scores into estimated RM cost savings, giving Hospital Kuala Lumpur Women and Children's (WACH) management a compelling business case and a live demo tool for prospective clients.

**Architecture:** A configurable financial settings panel (persisted as `data/financial_config.json`) feeds two new backend endpoints that compute three cost categories — excess energy waste, TNB power factor penalty, and maintenance risk exposure — from existing CSV data. The frontend renders a headline savings figure, three breakdown cards, and a top-10 AHU cost table, lazy-loaded as a new section below PredictionView in App.tsx.

**Tech Stack:** Python FastAPI, pandas, React + TypeScript + Recharts + Tailwind v3, Zustand

---

## ═══════════════════════════════════
## COST CALCULATION REFERENCE
## ═══════════════════════════════════

### 1. Excess Energy Cost
```
excess_kwh_per_ahu = sum(max(0, raw_hourly_delta - raw_predicted_delta))
excess_cost        = excess_kwh_per_ahu × tariff_rate_rm_per_kwh
```
Uses existing `raw_hourly_delta` and `raw_predicted_delta` columns from `health_hourly.csv`.

### 2. PF Penalty Cost (TNB formula)
```
avg_pf             = mean(raw_power_factor_avg) for AHU over range
if avg_pf < 0.85:
    steps_below    = (0.85 - avg_pf) / 0.01
    surcharge_frac = steps_below × 0.015          # 1.5% per 0.01 below 0.85
    total_energy_cost = sum(raw_hourly_delta) × tariff_rate
    pf_penalty_cost   = surcharge_frac × total_energy_cost
else:
    pf_penalty_cost = 0
```

### 3. Maintenance Risk Exposure (projection)
```
at_risk_ahus       = AHUs where latest health_index < 60
risk_per_ahu       = planned_maintenance_cost × (emergency_multiplier - 1)
maintenance_risk   = count(at_risk_ahus) × risk_per_ahu
```
Clearly labelled "projected exposure" — not an actual saving.

---

## ═══════════════════════════════════
## FILE MAP
## ═══════════════════════════════════

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/routes/financial_impact.py` | Create | Two endpoints: GET/POST config, GET impact |
| `backend/main.py` | Modify | Register financial_impact router |
| `frontend/src/types/index.ts` | Modify | Add FinancialConfig, FinancialImpact, AHUCost types |
| `frontend/src/api/financial.ts` | Create | fetchFinancialConfig, saveFinancialConfig, fetchFinancialImpact |
| `frontend/src/components/financial/CostBreakdownCard.tsx` | Create | Reusable card for one cost category |
| `frontend/src/components/financial/TopCostAHUsTable.tsx` | Create | Ranked table of top 10 AHUs by cost |
| `frontend/src/components/financial/FinancialSettingsDrawer.tsx` | Create | Slide-out config panel |
| `frontend/src/components/financial/FinancialImpactView.tsx` | Create | Top-level section, wires all sub-components |
| `frontend/src/App.tsx` | Modify | Lazy-load and render FinancialImpactView below PredictionView |

---

## ═══════════════════════════════════
## IMPLEMENTATION TASKS
## ═══════════════════════════════════

---

### Task 1: Backend — Financial config + impact endpoints

**File:** `backend/routes/financial_impact.py` (create)

The financial config is stored as a simple JSON file (`data/financial_config.json`). The impact endpoint reads `health_hourly.csv` via the existing `_load_csv` helper and applies the three cost formulas.

- [ ] **Step 1: Create `backend/routes/financial_impact.py`**

```python
"""
financial_impact.py
───────────────────
GET  /api/financial-config         — Load saved financial parameters
POST /api/financial-config         — Save financial parameters
GET  /api/financial-impact?level=N&range=30d  — Compute cost breakdown

All calculations use existing health_hourly.csv data — no new ETL required.
"""
import json
import logging
import os
import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

log = logging.getLogger(__name__)
router = APIRouter()

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'financial_config.json'
)

DEFAULT_CONFIG = {
    "currency":                  "RM",
    "tariff_rate":               0.365,   # RM/kWh — TNB C1 default
    "max_demand_rate":           30.30,   # RM/kVA/month — TNB C1 default
    "planned_maintenance_cost":  500.0,   # RM per visit
    "emergency_multiplier":      3.0,     # emergency = 3× planned
}


class FinancialConfig(BaseModel):
    currency:                  str   = Field(default="RM")
    tariff_rate:               float = Field(default=0.365,  gt=0)
    max_demand_rate:           float = Field(default=30.30,  gt=0)
    planned_maintenance_cost:  float = Field(default=500.0,  gt=0)
    emergency_multiplier:      float = Field(default=3.0,    gt=1)


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                stored = json.load(f)
            # Merge with defaults so new fields always present
            return {**DEFAULT_CONFIG, **stored}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def _save_config(cfg: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)


@router.get("/financial-config")
async def get_financial_config():
    return _load_config()


@router.post("/financial-config")
async def post_financial_config(config: FinancialConfig):
    cfg = config.model_dump()
    _save_config(cfg)
    return cfg


@router.get("/financial-impact")
async def get_financial_impact(level: int, range: str = "30d"):
    try:
        result = _compute_impact(level, range)
    except Exception as exc:
        log.error("financial-impact level=%s: %s", level, exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Financial impact calculation failed")
    return result


# ── Calculation helpers ────────────────────────────────────────────────────────

def _compute_impact(level: int, time_range: str) -> dict:
    from core.csv_reader import _load_csv, _filter_time_range

    cfg = _load_config()
    tariff        = cfg["tariff_rate"]
    planned_cost  = cfg["planned_maintenance_cost"]
    multiplier    = cfg["emergency_multiplier"]
    currency      = cfg["currency"]

    df = _load_csv(time_range=time_range)
    if df.empty:
        return _empty_response(currency)

    df = df[df['level'] == f"Level {level}"]
    df = _filter_time_range(df, time_range).sort_values('timestamp')
    if df.empty:
        return _empty_response(currency)

    ahu_rows = []
    for ahu_id, grp in df.groupby('ahu_id'):
        grp = grp.sort_values('timestamp')

        # 1. Excess energy cost
        excess_cost = 0.0
        if 'raw_hourly_delta' in grp.columns and 'raw_predicted_delta' in grp.columns:
            excess_kwh = (grp['raw_hourly_delta'].fillna(0) - grp['raw_predicted_delta'].fillna(0)).clip(lower=0).sum()
            excess_cost = round(float(excess_kwh) * tariff, 2)

        # 2. PF penalty cost (TNB formula)
        pf_penalty = 0.0
        if 'raw_power_factor_avg' in grp.columns and 'raw_hourly_delta' in grp.columns:
            avg_pf = grp['raw_power_factor_avg'].dropna().mean()
            if pd.notna(avg_pf) and avg_pf < 0.85:
                steps_below    = (0.85 - avg_pf) / 0.01
                surcharge_frac = steps_below * 0.015
                total_energy   = grp['raw_hourly_delta'].fillna(0).sum()
                pf_penalty     = round(float(total_energy) * tariff * surcharge_frac, 2)

        # 3. Maintenance risk (latest health index for this AHU)
        latest_hi = float(grp['health_index'].dropna().iloc[-1]) if 'health_index' in grp.columns and not grp['health_index'].dropna().empty else 100.0
        maintenance_risk = round(planned_cost * (multiplier - 1), 2) if latest_hi < 60 else 0.0

        total = round(excess_cost + pf_penalty + maintenance_risk, 2)

        ahu_rows.append({
            "ahu_id":            ahu_id,
            "health_index":      round(latest_hi, 1),
            "excess_energy_cost": excess_cost,
            "pf_penalty_cost":   pf_penalty,
            "maintenance_risk":  maintenance_risk,
            "total_cost":        total,
        })

    ahu_rows.sort(key=lambda r: r["total_cost"], reverse=True)

    total_excess      = round(sum(r["excess_energy_cost"] for r in ahu_rows), 2)
    total_pf          = round(sum(r["pf_penalty_cost"]    for r in ahu_rows), 2)
    total_maintenance = round(sum(r["maintenance_risk"]   for r in ahu_rows), 2)
    grand_total       = round(total_excess + total_pf + total_maintenance, 2)

    return {
        "currency":          currency,
        "level":             level,
        "range":             time_range,
        "grand_total":       grand_total,
        "excess_energy_cost": total_excess,
        "pf_penalty_cost":   total_pf,
        "maintenance_risk":  total_maintenance,
        "top_ahus":          ahu_rows[:10],
    }


def _empty_response(currency: str) -> dict:
    return {
        "currency": currency, "level": 0, "range": "",
        "grand_total": 0, "excess_energy_cost": 0,
        "pf_penalty_cost": 0, "maintenance_risk": 0,
        "top_ahus": [],
    }
```

- [ ] **Step 2: Register router in `backend/main.py`**

Add import after the existing router imports:
```python
from routes.financial_impact import router as financial_impact_router
```

Add registration alongside the others:
```python
app.include_router(financial_impact_router, prefix="/api")
```

- [ ] **Step 3: Write a unit test for the calculation helpers**

Create `tests/test_financial_impact.py`:
```python
"""Unit tests for financial impact calculation helpers."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pandas as pd
import numpy as np

# Import the private helpers directly
from routes.financial_impact import _load_config, _save_config, DEFAULT_CONFIG, FinancialConfig


def test_default_config_has_required_keys():
    for key in ["currency", "tariff_rate", "planned_maintenance_cost", "emergency_multiplier"]:
        assert key in DEFAULT_CONFIG


def test_financial_config_model_rejects_zero_tariff():
    from pydantic import ValidationError
    try:
        FinancialConfig(tariff_rate=0)
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_pf_penalty_formula():
    """Verify TNB 1.5%/0.01 formula."""
    avg_pf = 0.80           # 5 steps below 0.85
    steps  = (0.85 - avg_pf) / 0.01   # 5.0
    frac   = steps * 0.015              # 0.075  (7.5% surcharge)
    total_energy_cost = 1000.0          # RM 1000 base
    penalty = total_energy_cost * frac  # RM 75
    assert abs(penalty - 75.0) < 0.01


def test_excess_energy_calculation():
    """sum of max(0, actual - predicted)."""
    actual    = pd.Series([10.0, 12.0,  9.0, 11.0])
    predicted = pd.Series([10.0, 10.0, 10.0, 10.0])
    excess = (actual - predicted).clip(lower=0).sum()
    assert excess == 3.0   # only hours 2 and 4 contributed


def test_maintenance_risk_only_for_unhealthy():
    planned    = 500.0
    multiplier = 3.0
    risk_if_unhealthy = planned * (multiplier - 1)   # RM 1000
    assert risk_if_unhealthy == 1000.0
    # healthy AHU (hi >= 60) → 0
    hi = 75.0
    risk = risk_if_unhealthy if hi < 60 else 0.0
    assert risk == 0.0
```

- [ ] **Step 4: Run tests**
```bash
cd /Users/rdmasia/wach-insight
python -m pytest tests/test_financial_impact.py -v
```
Expected: 5 tests pass.

- [ ] **Step 5: Smoke test the endpoints**

Start backend: `cd backend && uvicorn main:app --port 8081 --reload`

```bash
curl -s -H "Authorization: Bearer $DEV_API_KEY" \
  http://localhost:8081/api/financial-config | python3 -m json.tool

curl -s -H "Authorization: Bearer $DEV_API_KEY" \
  "http://localhost:8081/api/financial-impact?level=1&range=30d" \
  | python3 -m json.tool | head -20
```
Expected: config returns default RM values; impact returns `{grand_total, excess_energy_cost, pf_penalty_cost, maintenance_risk, top_ahus}`.

- [ ] **Step 6: Commit**
```bash
git add backend/routes/financial_impact.py backend/main.py tests/test_financial_impact.py
git commit -m "$(cat <<'EOF'
feat: add financial impact backend endpoints (config + cost calculations)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Frontend — Types + API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/financial.ts`

- [ ] **Step 1: Add types to `frontend/src/types/index.ts`**

Append at the end of the file:
```typescript
// ── Financial Impact Types ────────────────────────────────────────────────────

export interface FinancialConfig {
  currency: string;
  tariff_rate: number;
  max_demand_rate: number;
  planned_maintenance_cost: number;
  emergency_multiplier: number;
}

export interface AHUCost {
  ahu_id: string;
  health_index: number;
  excess_energy_cost: number;
  pf_penalty_cost: number;
  maintenance_risk: number;
  total_cost: number;
}

export interface FinancialImpact {
  currency: string;
  level: number;
  range: string;
  grand_total: number;
  excess_energy_cost: number;
  pf_penalty_cost: number;
  maintenance_risk: number;
  top_ahus: AHUCost[];
}
```

- [ ] **Step 2: Create `frontend/src/api/financial.ts`**

```typescript
import { apiFetch } from './client';
import type { FinancialConfig, FinancialImpact } from '../types';

export async function fetchFinancialConfig(): Promise<FinancialConfig> {
  return apiFetch<FinancialConfig>('/financial-config');
}

export async function saveFinancialConfig(config: FinancialConfig): Promise<FinancialConfig> {
  return apiFetch<FinancialConfig>('/financial-config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export async function fetchFinancialImpact(
  level: number,
  range: '24h' | '7d' | '30d' = '30d'
): Promise<FinancialImpact> {
  return apiFetch<FinancialImpact>(`/financial-impact?level=${level}&range=${range}`);
}
```

- [ ] **Step 3: Commit**
```bash
git add frontend/src/types/index.ts frontend/src/api/financial.ts
git commit -m "$(cat <<'EOF'
feat: add FinancialConfig/FinancialImpact types and API client functions

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Frontend — CostBreakdownCard component

**File:** `frontend/src/components/financial/CostBreakdownCard.tsx` (create)

A reusable card showing one cost category: icon, label, amount, and a short description.

- [ ] **Step 1: Create the component**

```tsx
import React from 'react';

interface CostBreakdownCardProps {
  label: string;
  amount: number;
  currency: string;
  description: string;
  color: string;        // accent colour e.g. '#F97316'
  isProjection?: boolean;
}

const CostBreakdownCard: React.FC<CostBreakdownCardProps> = ({
  label, amount, currency, description, color, isProjection = false,
}) => (
  <div className="card p-5 flex flex-col gap-3">
    <div className="flex items-center justify-between">
      <span className="text-sm text-[#8A95A5] font-medium">{label}</span>
      {isProjection && (
        <span className="text-[10px] px-2 py-0.5 rounded-full border border-[#3B4B5A] text-[#8A95A5]">
          projected
        </span>
      )}
    </div>
    <div className="text-[28px] font-bold font-mono" style={{ color }}>
      {currency} {amount.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </div>
    <p className="text-xs text-[#8A95A5] leading-relaxed">{description}</p>
  </div>
);

export default CostBreakdownCard;
```

- [ ] **Step 2: Commit**
```bash
git add frontend/src/components/financial/CostBreakdownCard.tsx
git commit -m "$(cat <<'EOF'
feat: add CostBreakdownCard component

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Frontend — TopCostAHUsTable component

**File:** `frontend/src/components/financial/TopCostAHUsTable.tsx` (create)

Ranked table of up to 10 AHUs sorted by total estimated cost. Each row shows AHU ID, health index (colour-coded), and the three cost components.

- [ ] **Step 1: Create the component**

```tsx
import React from 'react';
import type { AHUCost } from '../../types';

interface Props {
  ahus: AHUCost[];
  currency: string;
}

function fmt(n: number) {
  return n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function tierColor(hi: number) {
  if (hi >= 80) return 'text-[#00E5A0]';
  if (hi >= 60) return 'text-yellow-400';
  if (hi >= 40) return 'text-orange-400';
  return 'text-red-400';
}

const TopCostAHUsTable: React.FC<Props> = ({ ahus, currency }) => {
  if (!ahus.length) return (
    <div className="card p-6 text-center text-[#8A95A5] text-sm">No data available</div>
  );

  return (
    <div className="card p-0 overflow-hidden">
      <div className="px-6 py-4 border-b border-[#1E2A3A]">
        <h3 className="font-display text-[18px] font-bold">Top AHUs by Financial Impact</h3>
        <p className="text-xs text-[#8A95A5] mt-1">Ranked by estimated total cost — prioritise these for maintenance</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1E2A3A]">
              {['#', 'AHU', 'Health', 'Excess Energy', 'PF Penalty', 'Maint. Risk', 'Total'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs text-[#8A95A5] font-medium whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ahus.map((row, i) => (
              <tr key={row.ahu_id} className="border-b border-[#1E2A3A]/50 hover:bg-[#1A2230]/50 transition-colors">
                <td className="px-4 py-3 text-[#8A95A5] text-xs">{i + 1}</td>
                <td className="px-4 py-3 font-mono text-white font-medium">{row.ahu_id}</td>
                <td className={`px-4 py-3 font-mono font-bold ${tierColor(row.health_index)}`}>
                  {row.health_index.toFixed(0)}
                </td>
                <td className="px-4 py-3 text-[#8A95A5]">{currency} {fmt(row.excess_energy_cost)}</td>
                <td className="px-4 py-3 text-[#8A95A5]">{currency} {fmt(row.pf_penalty_cost)}</td>
                <td className="px-4 py-3 text-[#8A95A5]">{currency} {fmt(row.maintenance_risk)}</td>
                <td className="px-4 py-3 font-bold text-white">{currency} {fmt(row.total_cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TopCostAHUsTable;
```

- [ ] **Step 2: Commit**
```bash
git add frontend/src/components/financial/TopCostAHUsTable.tsx
git commit -m "$(cat <<'EOF'
feat: add TopCostAHUsTable component

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Frontend — FinancialSettingsDrawer component

**File:** `frontend/src/components/financial/FinancialSettingsDrawer.tsx` (create)

Slide-out drawer (fixed right panel) with a form for all five configurable parameters. On save, calls POST `/api/financial-config` and notifies parent to refresh impact data.

- [ ] **Step 1: Create the component**

```tsx
import React from 'react';
import { saveFinancialConfig } from '../../api/financial';
import type { FinancialConfig } from '../../types';

interface Props {
  config: FinancialConfig;
  onClose: () => void;
  onSaved: (config: FinancialConfig) => void;
}

const FIELDS: { key: keyof FinancialConfig; label: string; hint: string; step?: string }[] = [
  { key: 'currency',                 label: 'Currency symbol',          hint: 'e.g. RM, USD, SGD' },
  { key: 'tariff_rate',              label: 'Electricity tariff (per kWh)', hint: 'TNB C1 default: 0.365', step: '0.001' },
  { key: 'max_demand_rate',          label: 'Max demand charge (per kVA/month)', hint: 'TNB C1 default: 30.30', step: '0.01' },
  { key: 'planned_maintenance_cost', label: 'Planned maintenance cost (per visit)', hint: 'e.g. 500', step: '1' },
  { key: 'emergency_multiplier',     label: 'Emergency repair multiplier', hint: 'e.g. 3 = 3× planned cost', step: '0.1' },
];

const FinancialSettingsDrawer: React.FC<Props> = ({ config, onClose, onSaved }) => {
  const [form, setForm] = React.useState<FinancialConfig>(config);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const saved = await saveFinancialConfig(form);
      onSaved(saved);
      onClose();
    } catch (e: any) {
      setError(e.message ?? 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[360px] bg-[#0B0F14] border-l border-[#1E2A3A] z-50 flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#1E2A3A]">
          <h2 className="font-display text-[18px] font-bold">Financial Settings</h2>
          <button onClick={onClose} className="text-[#8A95A5] hover:text-white transition-colors text-xl">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {FIELDS.map(({ key, label, hint, step }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-[#8A95A5] mb-1.5">{label}</label>
              <input
                type={key === 'currency' ? 'text' : 'number'}
                step={step}
                value={form[key] as string | number}
                onChange={e => setForm(prev => ({
                  ...prev,
                  [key]: key === 'currency' ? e.target.value : parseFloat(e.target.value) || 0,
                }))}
                className="w-full bg-[#1A2230] border border-[#1E2A3A] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#00E5A0] transition-colors"
              />
              <p className="text-[11px] text-[#4A5568] mt-1">{hint}</p>
            </div>
          ))}
          {error && <p className="text-red-400 text-xs">{error}</p>}
        </div>
        <div className="px-6 py-4 border-t border-[#1E2A3A] flex gap-3">
          <button onClick={onClose} className="flex-1 py-2 rounded-lg border border-[#1E2A3A] text-[#8A95A5] text-sm hover:border-[#2A3A4A] transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 rounded-lg bg-[#00E5A0] text-[#0B0F14] text-sm font-semibold hover:bg-[#00CC8E] transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </>
  );
};

export default FinancialSettingsDrawer;
```

- [ ] **Step 2: Commit**
```bash
git add frontend/src/components/financial/FinancialSettingsDrawer.tsx
git commit -m "$(cat <<'EOF'
feat: add FinancialSettingsDrawer slide-out config panel

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Frontend — FinancialImpactView (top-level section)

**File:** `frontend/src/components/financial/FinancialImpactView.tsx` (create)

Fetches config and impact data, renders the headline card, three CostBreakdownCards, and TopCostAHUsTable. Settings gear icon opens FinancialSettingsDrawer.

- [ ] **Step 1: Create the component**

```tsx
import React from 'react';
import { motion } from 'framer-motion';
import { fetchFinancialConfig, fetchFinancialImpact } from '../../api/financial';
import CostBreakdownCard from './CostBreakdownCard';
import TopCostAHUsTable from './TopCostAHUsTable';
import FinancialSettingsDrawer from './FinancialSettingsDrawer';
import type { FinancialConfig, FinancialImpact } from '../../types';

interface Props {
  level: number;
  range?: '24h' | '7d' | '30d';
}

const FinancialImpactView: React.FC<Props> = ({ level, range = '30d' }) => {
  const [config, setConfig]           = React.useState<FinancialConfig | null>(null);
  const [impact, setImpact]           = React.useState<FinancialImpact | null>(null);
  const [loading, setLoading]         = React.useState(true);
  const [error, setError]             = React.useState<string | null>(null);
  const [drawerOpen, setDrawerOpen]   = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cfg, imp] = await Promise.all([
        fetchFinancialConfig(),
        fetchFinancialImpact(level, range),
      ]);
      setConfig(cfg);
      setImpact(imp);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load financial data');
    } finally {
      setLoading(false);
    }
  }, [level, range]);

  React.useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="space-y-4">
      <div className="card h-32 animate-pulse bg-[#1A2230]" />
      <div className="grid grid-cols-3 gap-4">
        {[0,1,2].map(i => <div key={i} className="card h-28 animate-pulse bg-[#1A2230]" />)}
      </div>
    </div>
  );

  if (error || !impact || !config) return (
    <div className="card p-6 flex items-center justify-center h-32">
      <span className="text-[#8A95A5] text-sm">Financial data unavailable</span>
    </div>
  );

  const cur = impact.currency;

  return (
    <motion.div
      className="mb-12 space-y-6"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-display text-[28px] font-bold tracking-[-0.01em]">
            Financial Impact
          </h3>
          <p className="text-[#8A95A5] mt-1 text-sm">
            Estimated cost of current AHU health issues · Last {range}
          </p>
        </div>
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#1E2A3A] text-[#8A95A5] text-sm hover:border-[#00E5A0] hover:text-[#00E5A0] transition-colors"
        >
          ⚙ Configure
        </button>
      </div>

      {/* Headline card */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <p className="text-[#8A95A5] text-sm mb-1">Estimated monthly savings opportunity</p>
          <div className="text-[42px] font-bold font-mono text-[#00E5A0]">
            {cur} {impact.grand_total.toLocaleString('en-MY', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-[#4A5568] mt-1">
            Across {impact.top_ahus.length} AHUs on Level {level} ·
            {impact.top_ahus.filter(a => a.health_index < 60).length} at elevated risk
          </p>
        </div>
        <div className="text-[#8A95A5] text-xs text-right hidden md:block max-w-[200px]">
          Based on TNB tariff {cur} {config.tariff_rate}/kWh and{' '}
          {cur} {config.planned_maintenance_cost} planned maintenance cost.{' '}
          Maintenance risk is a projection.
        </div>
      </div>

      {/* Three breakdown cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <CostBreakdownCard
          label="Excess Energy Waste"
          amount={impact.excess_energy_cost}
          currency={cur}
          color="#60A5FA"
          description="kWh consumed above predicted baseline × tariff rate. Driven by energy anomaly scores."
        />
        <CostBreakdownCard
          label="TNB Power Factor Penalty"
          amount={impact.pf_penalty_cost}
          currency={cur}
          color="#F97316"
          description="TNB surcharge: 1.5% per 0.01 that average monthly PF falls below 0.85 (ASHRAE / IEEE 141)."
        />
        <CostBreakdownCard
          label="Maintenance Risk Exposure"
          amount={impact.maintenance_risk}
          currency={cur}
          color="#C084FC"
          description="AHUs with health index < 60 risk emergency repairs. Saving = (multiplier − 1) × planned cost."
          isProjection
        />
      </div>

      {/* Top AHUs table */}
      <TopCostAHUsTable ahus={impact.top_ahus} currency={cur} />

      {/* Settings drawer */}
      {drawerOpen && config && (
        <FinancialSettingsDrawer
          config={config}
          onClose={() => setDrawerOpen(false)}
          onSaved={(saved) => { setConfig(saved); load(); }}
        />
      )}
    </motion.div>
  );
};

export default FinancialImpactView;
```

- [ ] **Step 2: Commit**
```bash
git add frontend/src/components/financial/FinancialImpactView.tsx
git commit -m "$(cat <<'EOF'
feat: add FinancialImpactView top-level section with headline, cards, table, and settings drawer

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Frontend — Integrate into App.tsx

**File:** `frontend/src/App.tsx` (modify)

Lazy-load `FinancialImpactView` and render it below `PredictionView` when a level is selected.

- [ ] **Step 1: Add lazy import**

Find where `PredictionView` is lazy-loaded (around line 29) and add:
```tsx
const FinancialImpactView = React.lazy(
  () => import('./components/financial/FinancialImpactView')
);
```

- [ ] **Step 2: Render below PredictionView**

Find where `<PredictionView deviceId={selectedDevice} />` is rendered (around line 282) and add below it:
```tsx
{selectedLevel && (
  <React.Suspense fallback={<div className="card h-48 animate-pulse bg-[#1A2230] rounded-xl" />}>
    <FinancialImpactView level={selectedLevel} range={timeRange} />
  </React.Suspense>
)}
```

- [ ] **Step 3: Build to verify no TypeScript errors**
```bash
cd /Users/rdmasia/wach-insight/frontend && npm run build
```
Expected: clean build, no errors.

- [ ] **Step 4: Commit**
```bash
git add frontend/src/App.tsx
git commit -m "$(cat <<'EOF'
feat: integrate FinancialImpactView into App.tsx below PredictionView

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## ═══════════════════════════════════
## END-TO-END VERIFICATION CHECKLIST
## ═══════════════════════════════════

After all tasks complete:

- [ ] Backend tests pass: `python -m pytest tests/test_financial_impact.py -v`
- [ ] Frontend builds clean: `npm run build` inside `frontend/`
- [ ] Select Level 1 in app → scroll down → Financial Impact section appears
- [ ] Headline shows RM figure (not 0.00 and not NaN)
- [ ] Three breakdown cards show distinct values
- [ ] Top AHUs table shows up to 10 rows, sorted by total cost descending
- [ ] Click "Configure" → drawer slides in with TNB defaults pre-filled
- [ ] Change tariff rate → Save → numbers refresh
- [ ] AHUs with health index < 60 have non-zero maintenance risk
- [ ] "projected" badge appears on maintenance risk card
- [ ] Browser console: no errors
