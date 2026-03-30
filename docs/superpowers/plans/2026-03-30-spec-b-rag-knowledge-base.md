# Spec B — RAG Knowledge Base Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the chatbot's `search_docs` tool from a single AHU directory file to 10 domain knowledge documents covering AHU components, electrical health, FAIR scoring, Malaysian hospital standards, maintenance procedures, and TNB financials — plus a persona detection layer that shapes responses for general users, engineers, technicians, and financial managers.

**Architecture:** The RAG pipeline (ChromaDB, Qwen3 embedder, `search_docs` tool) already exists. This plan (1) writes 10 markdown documents to `backend/data/rag_docs/`, (2) adds a stateless `detect_persona()` function that infers user background from message keywords or an explicit frontend role selector, (3) injects a persona-specific block into the system prompt each turn, and (4) adds a role selector UI to the chat widget.

**Tech Stack:** Python 3.11, FastAPI, ChromaDB, sentence-transformers (Qwen3-Embedding-0.6B), React + TypeScript, Tailwind CSS, pytest

---

## Schema Note

`ChatRequest` is defined **locally in `backend/routes/chat.py`** (not in `schemas.py`). Add `persona` there. The V2 system prompt is also defined inline in `chat.py` as `_build_system_prompt()` — this plan moves it to `prompts.py` and adds persona injection.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/llm/persona_detector.py` | Stateless persona detection |
| Create | `backend/tests/test_persona_detector.py` | Persona detector unit tests |
| Modify | `backend/llm/prompts.py` | Add `PERSONA_BLOCKS` + `build_system_prompt(persona)` |
| Modify | `backend/routes/chat.py` | Add `persona` to `ChatRequest`, call detector + new prompt builder |
| Create | `backend/scripts/ingest_all_docs.py` | Batch ingest all `data/rag_docs/*.md` |
| Create | `backend/data/rag_docs/ahu_components_overview.md` | AHU component knowledge |
| Create | `backend/data/rag_docs/ahu_electrical_health.md` | Electrical health indicators |
| Create | `backend/data/rag_docs/fair_scoring_methodology.md` | FAIR health scoring |
| Create | `backend/data/rag_docs/malaysian_hospital_hvac_context.md` | MY standards + tropical climate |
| Create | `backend/data/rag_docs/hospital_ahu_environments.md` | Room-by-room requirements |
| Create | `backend/data/rag_docs/ahu_performance_benchmarks.md` | Normal operating ranges |
| Create | `backend/data/rag_docs/tnb_tariff_financial_guide.md` | TNB RP4 tariffs + PF penalty |
| Create | `backend/data/rag_docs/fault_diagnosis_guide.md` | Fault decision trees |
| Create | `backend/data/rag_docs/ahu_maintenance_guide.md` | PM schedules + procedures |
| Create | `backend/data/rag_docs/wach_system_guide.md` | WACH usage + escalation |
| Modify | `frontend/src/api/client.ts` | Add `persona?` to `sendChatMessage` |
| Modify | `frontend/src/components/chat/ChatWindow.tsx` | Persona state, pass to API |
| Modify | `frontend/src/components/chat/ChatInput.tsx` | Role selector UI |

---

## Task 1: Persona Detector (TDD)

**Files:**
- Create: `backend/llm/persona_detector.py`
- Create: `backend/tests/test_persona_detector.py`

- [ ] **Step 1.1: Write the failing tests**

```python
# backend/tests/test_persona_detector.py
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from llm.persona_detector import detect_persona


def test_financial_keywords():
    assert detect_persona("What is the ROI of fixing this? How much does the TNB penalty cost?") == "financial"


def test_technician_keywords():
    assert detect_persona("I need to replace the capacitor and inspect the belt tension") == "technician"


def test_technical_keywords():
    assert detect_persona("What does the THD reading mean and how does phase imbalance affect the FAIR score?") == "technical"


def test_general_default():
    assert detect_persona("Why is the machine not working?") == "general"


def test_stated_persona_overrides_all():
    assert detect_persona(
        "What is the ROI of fixing this? TNB penalty?",
        stated_persona="technician",
    ) == "technician"


def test_role_command():
    assert detect_persona("/role financial — what does the score mean?") == "financial"


def test_explicit_engineer():
    assert detect_persona("I'm an engineer, give me the technical breakdown") == "technical"


def test_explicit_technician():
    assert detect_persona("I'm a technician, how do I fix this?") == "technician"


def test_history_reinforces_financial():
    history = [
        {"role": "user", "content": "What is the ROI of this maintenance?"},
        {"role": "user", "content": "How does the TNB penalty affect our budget?"},
    ]
    assert detect_persona("Tell me more about the cost", history=history) == "financial"


def test_empty_message_defaults_general():
    assert detect_persona("") == "general"


def test_mixed_signals_financial_wins():
    # financial has more keywords
    assert detect_persona(
        "What is the cost, ROI, budget impact, TNB tariff, and RM penalty?"
    ) == "financial"
```

- [ ] **Step 1.2: Run tests — verify they fail**

```bash
cd backend && python -m pytest tests/test_persona_detector.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'llm.persona_detector'`

- [ ] **Step 1.3: Implement persona_detector.py**

```python
# backend/llm/persona_detector.py
"""
llm/persona_detector.py
───────────────────────
Stateless persona detection from message + history.
Returns: "general" | "technical" | "technician" | "financial"
"""
from __future__ import annotations
import re
from typing import Literal

Persona = Literal["general", "technical", "technician", "financial"]

_FINANCIAL = {
    "cost", "rm", "budget", "penalty", "roi", "savings", "expenditure",
    "tariff", "tnb", "payback", "bill", "money", "financial", "revenue",
    "ringgit", "sen", "charge", "rate", "expensive",
}
_TECHNICIAN = {
    "check", "replace", "inspect", "clean", "tighten", "fault", "repair",
    "capacitor", "belt", "coil", "filter", "reading", "measurement",
    "megger", "loto", "bearing", "winding", "contactor", "relay",
    "multimeter", "clamp", "torque", "resistor",
}
_TECHNICAL = {
    "thd", "harmonic", "power factor", "phase imbalance", "impedance",
    "pf_degradation", "energy_anomaly", "fair", "algorithm", "calculation",
    "analysis", "frequency", "reactive", "apparent", "rms", "kva",
    "kvar", "kwh", "ieee", "ashrae", "nema", "waveform",
}

_EXPLICIT: dict[str, re.Pattern] = {
    "financial": re.compile(
        r"\b(financial|facilities.manager|finance|cfo|accountant)\b"
        r"|i.?m.*(finance|financial|manager)",
        re.IGNORECASE,
    ),
    "technical": re.compile(
        r"\b(engineer|engineering|technical|biomedical|bme)\b"
        r"|technical (detail|breakdown|analysis)"
        r"|i.?m.*(engineer|technical)",
        re.IGNORECASE,
    ),
    "technician": re.compile(
        r"\b(technician|mechanic|maintenance (team|staff|person)|hands.on)\b"
        r"|i.?m.*(technician|mechanic)"
        r"|explain.*(step by step|procedure|how to fix)",
        re.IGNORECASE,
    ),
    "general": re.compile(
        r"\b(explain simply|simple terms|layman|non.technical|what does (it|this|that) mean)\b"
        r"|i.?m.*(not technical|just a|new to)",
        re.IGNORECASE,
    ),
}

_ROLE_CMD = re.compile(r"/role\s+(general|technical|technician|financial)", re.IGNORECASE)


def _score(text: str) -> dict[str, int]:
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    bigrams = set(re.findall(r"\b\w+ \w+\b", lower))
    tokens = words | bigrams
    return {
        "financial":  len(tokens & _FINANCIAL),
        "technician": len(tokens & _TECHNICIAN),
        "technical":  len(tokens & _TECHNICAL),
    }


def detect_persona(
    message: str,
    history: list[dict] | None = None,
    stated_persona: str | None = None,
) -> Persona:
    """
    Detect persona. Priority:
    1. stated_persona (from frontend role selector)
    2. /role command in message
    3. Explicit declaration regex in message
    4. Keyword scoring on message
    5. Rolling keyword scoring on last 3 history turns (half weight)
    6. Default: "general"
    """
    valid = {"general", "technical", "technician", "financial"}

    if stated_persona and stated_persona in valid:
        return stated_persona  # type: ignore[return-value]

    m = _ROLE_CMD.search(message)
    if m:
        return m.group(1).lower()  # type: ignore[return-value]

    for persona, pattern in _EXPLICIT.items():
        if pattern.search(message):
            return persona  # type: ignore[return-value]

    scores = _score(message)

    if history:
        for turn in history[-3:]:
            content = turn.get("content", "")
            if isinstance(content, str):
                h = _score(content)
                for k in scores:
                    scores[k] += h[k] // 2

    best = max(scores, key=lambda k: scores[k])
    others = max((v for k, v in scores.items() if k != best), default=0)
    if scores[best] >= 2 and scores[best] > others:
        return best  # type: ignore[return-value]

    return "general"
```

- [ ] **Step 1.4: Run tests — verify they pass**

```bash
cd backend && python -m pytest tests/test_persona_detector.py -v
```

Expected: `11 passed`

- [ ] **Step 1.5: Commit**

```bash
git add backend/llm/persona_detector.py backend/tests/test_persona_detector.py
git commit -m "feat(rag): add stateless persona detector with TDD"
```

---

## Task 2: System Prompt Persona Blocks

**Files:**
- Modify: `backend/llm/prompts.py`
- Modify: `backend/routes/chat.py`

The current V2 system prompt is defined as `_build_system_prompt()` inside `chat.py`. This task moves it to `prompts.py` and adds persona injection.

- [ ] **Step 2.1: Add PERSONA_BLOCKS and build_system_prompt to prompts.py**

Append the following to the END of `backend/llm/prompts.py` (after the existing `SYSTEM_PROMPT` variable — that variable is the V1 JSON parser prompt and is no longer used by V2, leave it in place):

```python
# ── V2 Chat System Prompt (agentic tool-use) ──────────────────────────────────

from config import get_building_name, get_department

PERSONA_BLOCKS: dict[str, str] = {
    "general": (
        "The user is not technical. Use plain language and everyday analogies. "
        "Avoid electrical jargon — if you must use a term, define it immediately. "
        "Focus on what matters practically: is it serious, does someone need to fix it, "
        "is it costing money? One clear action or conclusion per answer."
    ),
    "technical": (
        "The user is an engineer or technically fluent. Use precise terminology. "
        "Include numerical thresholds, component-level breakdowns, and scoring methodology "
        "where relevant. Reference standards (IEEE 519, ASHRAE 170, NEMA MG1) where appropriate. "
        "Show your reasoning when interpreting data."
    ),
    "technician": (
        "The user is a hands-on maintenance technician. Respond with step-by-step diagnostic "
        "and repair actions. Specify measurements to take (e.g., 'measure L1–L2 voltage at MCC'), "
        "tools required (clamp meter, Megger, multimeter), and LOTO safety steps. "
        "Keep language direct and procedural. Bullet points preferred."
    ),
    "financial": (
        "The user has a financial mindset. Lead with RM cost and penalty figures. "
        "Frame health scores as financial risk and cost-of-inaction. Reference TNB RP4 tariff "
        "implications (MV General RM0.2983/kWh, PF penalty 1.5%/0.01 below 0.85). "
        "Include payback periods and ROI where relevant. Skip electrical theory unless asked."
    ),
}


def build_system_prompt(persona: str = "general") -> str:
    building = get_building_name()
    department = get_department()
    persona_block = PERSONA_BLOCKS.get(persona, PERSONA_BLOCKS["general"])

    return f"""You are WACH AI, an AHU health assistant for {building} ({department}).

You monitor Air Handling Units (AHUs) across 11 building levels (Level 1–Level 11), totalling 121 AHUs.
Device IDs follow the format e[LEVEL][NN], e.g. e0101 (Level 1, unit 01) through e1108 (Level 11, unit 08).

## Health Scoring (FAIR)
Health Index: 0–100 scale.
- Healthy (80–100): Normal operation
- Monitor (60–79): Watch closely
- Maintenance (40–59): Schedule maintenance
- Critical (0–39): Immediate intervention required

FAIR component penalty weights:
- Energy Anomaly (15%): Unusual energy consumption
- Power Factor Degradation (25%): Poor reactive power management
- Phase Imbalance (25%): Unequal current across phases
- THD Drift (15%): Total Harmonic Distortion increase
- Overload (20%): Power demand exceeding rated capacity

Power quality targets: power factor >0.85, voltage THD <5% (IEEE 519), current unbalance <2% (NEMA MG-1).

Financial impact (TNB RP4, effective July 2025):
- Excess Energy Cost: kWh above baseline × RM0.2983/kWh (MV General tariff)
- Power Factor Penalty: 1.5% of bill per 0.01 below PF 0.85 (doubles to 3%/0.01 below PF 0.75)
- Capacity+Network Charge: RM89.27/kW/month — poor PF raises effective demand, increasing this charge

## Instructions
- Use the provided tools to retrieve data. Never guess device readings or fabricate values.
- Cite which devices and time ranges your data covers.
- If a tool returns no data, say so explicitly — do not invent numbers.
- Use markdown formatting. No emojis.
- Be concise and actionable. Use tables for comparisons.

## Response Style
{persona_block}
"""
```

- [ ] **Step 2.2: Update chat.py to use build_system_prompt**

In `backend/routes/chat.py`, replace the `_build_system_prompt` function and its usage:

Replace:
```python
from llm.client_factory import get_chat_client
from models.schemas import ChatHistoryItem
from config import get_building_name, get_department
from core.query_classifier import classify_query_complexity
from tools.tool_registry import TOOLS, dispatch_tool
```

With:
```python
from llm.client_factory import get_chat_client
from llm.persona_detector import detect_persona
from llm.prompts import build_system_prompt
from models.schemas import ChatHistoryItem
from core.query_classifier import classify_query_complexity
from tools.tool_registry import TOOLS, dispatch_tool
```

Replace the entire `ChatRequest` class:
```python
class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatHistoryItem]] = None
    context: Optional[dict] = None
    persona: Optional[str] = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        if len(v) > 1000:
            raise ValueError("message must be 1000 characters or fewer")
        return v
```

Delete the entire `_build_system_prompt` function (lines 54–89 in the current file).

Replace the `chat` endpoint body:
```python
@router.post("/chat")
async def chat(body: ChatRequest):
    history = body.history or []
    history_messages = _to_openai_messages(history)

    # 1. Detect persona from message + history + explicit field
    history_dicts = [{"role": m["role"], "content": m["content"]} for m in history_messages]
    persona = detect_persona(body.message, history=history_dicts, stated_persona=body.persona)

    # 2. Classify complexity → choose thinking mode
    thinking_mode = classify_query_complexity(body.message, history_messages)
    prefix = "/think " if thinking_mode == "think" else "/no_think "
    user_content = prefix + body.message

    # 3. Build messages list for tool loop
    messages = history_messages + [{"role": "user", "content": user_content}]

    # 4. Generate response using tool-augmented generation
    try:
        client = get_chat_client()
        reply = await client.generate_with_tools(
            system_prompt=build_system_prompt(persona),
            messages=messages,
            tools=TOOLS,
            tool_dispatcher=dispatch_tool,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    return {
        "reply": reply,
        "navigate": None,
        "thinking_mode": thinking_mode,
    }
```

- [ ] **Step 2.3: Run existing tests to verify nothing broke**

```bash
cd backend && python -m pytest tests/ -v --ignore=tests/test_csv_reader.py 2>&1 | tail -20
```

Expected: all previously passing tests still pass (test_tool_registry: 4 passed, test_persona_detector: 11 passed)

- [ ] **Step 2.4: Commit**

```bash
git add backend/llm/prompts.py backend/routes/chat.py
git commit -m "feat(rag): add persona blocks to prompts, wire detect_persona into chat route"
```

---

## Task 3: Ingest Script

**Files:**
- Create: `backend/scripts/ingest_all_docs.py`

- [ ] **Step 3.1: Create ingest_all_docs.py**

```python
# backend/scripts/ingest_all_docs.py
"""
scripts/ingest_all_docs.py
──────────────────────────
Batch-ingest all markdown files in data/rag_docs/ into ChromaDB.
Safe to re-run — hash-based dedup in rag/ingest.py skips already-indexed chunks.

Usage (from backend/):
    python -m scripts.ingest_all_docs
    python -m scripts.ingest_all_docs --persist-dir data/chroma --collection wach_docs
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def ingest_all(persist_dir: str, collection: str) -> None:
    from rag.ingest import ingest

    docs_dir = Path(__file__).parent.parent / "data" / "rag_docs"
    files = sorted(docs_dir.glob("*.md"))
    if not files:
        print(f"[ingest_all] No .md files found in {docs_dir}")
        sys.exit(1)

    total = 0
    for f in files:
        print(f"\n[ingest_all] Processing {f.name}...")
        try:
            count = await ingest(str(f), collection=collection, persist_dir=persist_dir)
            total += count
            print(f"[ingest_all] {f.name}: {count} chunks")
        except Exception as e:
            print(f"[ingest_all] ERROR on {f.name}: {e}")

    print(f"\n[ingest_all] Done. Total chunks ingested: {total}")
    if total < 50:
        print("[ingest_all] WARNING: fewer than 50 chunks — check documents exist and are non-empty")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest all RAG docs into ChromaDB")
    parser.add_argument("--persist-dir", default="data/chroma")
    parser.add_argument("--collection", default="wach_docs")
    args = parser.parse_args()
    asyncio.run(ingest_all(args.persist_dir, args.collection))
```

- [ ] **Step 3.2: Verify script is importable**

```bash
cd backend && python -c "import scripts.ingest_all_docs; print('OK')"
```

Expected: `OK`

- [ ] **Step 3.3: Commit**

```bash
git add backend/scripts/ingest_all_docs.py
git commit -m "feat(rag): add ingest_all_docs batch script"
```

---

## Task 4: RAG Documents — Batch 1 (Core Technical)

**Files:**
- Create: `backend/data/rag_docs/ahu_components_overview.md`
- Create: `backend/data/rag_docs/ahu_electrical_health.md`
- Create: `backend/data/rag_docs/fair_scoring_methodology.md`

- [ ] **Step 4.1: Write ahu_components_overview.md**

```bash
cat > backend/data/rag_docs/ahu_components_overview.md << 'DOCEOF'
```

Create `backend/data/rag_docs/ahu_components_overview.md` with the following content:

```markdown
# AHU Components Overview — Hospital Grade

## What is an Air Handling Unit?

An Air Handling Unit (AHU) conditions and distributes air throughout a building zone. In a hospital, AHUs control temperature, humidity, air changes per hour, filtration grade, and room pressure — all critical for infection control and patient safety.

## Air Filtration System

**Pre-filter (G4 / EU4)**
Coarse filter capturing large dust particles. First line of defence. High pressure drop indicates blockage — replace when ΔP across filter > 80–120 Pa. Typical replacement: monthly in hospital environments.

**Bag/Pocket Filter (F7 / EU7 or F9 / EU9)**
Medium efficiency filter. F7 captures particles ≥ 1 µm (70–80% efficiency). F9 captures particles ≥ 0.4 µm (95% efficiency). Used in wards and ICU. Replace when ΔP > design value or quarterly.

**HEPA Filter (H13 / H14)**
High Efficiency Particulate Air filter. H13: ≥ 99.95% efficiency at 0.3 µm. H14: ≥ 99.995%. Used in Operating Theatres, NICU, Pharmacy cleanrooms, Bone Marrow Transplant Unit. Replace annually or per pressure drop indication. Never clean — replace only.

**Filter pressure drop monitoring**: Rising ΔP = filter loading. Blocked filters force the fan to work harder, increasing motor current and energy consumption, and can contribute to belt slip and overload faults.

## Cooling and Heating Coils

**Cooling coil (chilled water or DX)**
Removes heat and dehumidifies supply air. In Malaysian hospitals, chilled water coils are most common (connected to central chiller plant). Fouling with dust, mould, or scale reduces heat transfer — causes supply air temperature to rise, increasing energy consumption and degrading indoor conditions.

Signs of coil fouling: rising supply air temperature at same chilled water valve position, increased energy anomaly score, visible dirt/scale on fin surfaces.

Maintenance: chemical wash (alkaline degreaser + acid rinse) annually or bi-annually depending on fouling rate.

**Heating coil (hot water or electric)**
Rarely used in Malaysian hospitals for re-heating (post-dehumidification). Present in Operating Theatre AHUs for precise temperature control. Failure mode: stuck valve (overheating or no heating), open circuit element.

## Fan and Motor Assembly

**Centrifugal fan / blower**
Moves air through the AHU. Types:
- Forward-curved blades: lower efficiency, common in smaller AHUs, sensitive to system resistance changes
- Backward-curved / backward-inclined: higher efficiency, used in larger units, more stable operating curve
- SWSI (Single Width Single Inlet): one side intake
- DWDI (Double Width Double Inlet): both sides intake, higher airflow

**Fan laws**: Airflow ∝ speed; static pressure ∝ speed²; power ∝ speed³. A 10% speed reduction via VFD = ~27% power reduction.

**Motor (induction motor)**
IE (International Efficiency) classes: IE1 (standard), IE2 (high), IE3 (premium), IE4 (super premium). Hospital AHUs should be IE2 minimum; IE3 preferred for continuous-duty motors. Nameplate data: kW, voltage (V), current (A = FLA), frequency (Hz), RPM, insulation class (F = 155°C, H = 180°C), service factor (SF 1.15 = can run 15% above nameplate continuously).

Motor failure modes: winding insulation failure (thermal aging, moisture), bearing failure (lack of lubrication, misalignment), rotor bar cracking (repeated starts, overload).

**Insulation resistance test (Megger test)**:
- Good: > 10 MΩ
- Marginal: 1–10 MΩ — monitor closely
- Poor: < 1 MΩ — motor winding suspect, investigate
- Critical: < 0.5 MΩ — do not energise, wind or replace

## Variable Frequency Drive (VFD)

Controls motor speed by varying supply frequency. Benefits: energy savings at part load, soft start (reduces inrush current), PF correction capability. Drawbacks: generates harmonic currents (3rd, 5th, 7th order) that increase THD — requires line reactor or output filter to mitigate.

VFD parameters relevant to WACH monitoring:
- Output frequency (Hz): corresponds to airflow
- Output current (A): motor loading
- DC bus voltage: check when VFD trips on overvoltage
- Fault codes: OC (overcurrent), OV (overvoltage), OH (overheating), PF (power failure)

Always install line reactor (3–5% impedance) on VFD input to reduce harmonic injection and improve input PF.

## Dampers and Actuators

**Fresh Air Damper (OAD)**: controls outdoor air intake. If jammed closed — CO2 rises, indoor air quality degrades. If jammed open — excessive load in tropical climate (high humidity ingress).

**Return Air Damper (RAD)**: controls recirculated air. Must be coordinated with OAD to maintain total airflow.

**Exhaust/Relief Damper**: releases excess building pressure.

**Bypass Damper**: diverts air around cooling coil in mild weather (rarely used in tropical Malaysia).

Actuator failures: seized (thermal bonding), loss of 24V signal, control board fault. Check actuator with manual override lever; measure control signal (0–10V or 4–20mA).

## Heat Recovery and Humidity Control

**Heat recovery wheel (enthalpy wheel)**: transfers heat AND moisture from exhaust to supply air. Reduces cooling load in tropical climates. Must be cleaned annually — blocked honeycomb reduces recovery efficiency. Failure: seized bearing, torn media.

**Humidifier**: rarely needed in Malaysian hospital supply air (tropical = high ambient humidity). Present in some Pharmacy cleanrooms or Sterile Supply Units that require tight RH control.

**Drain pan**: collects condensate from cooling coil. Must slope to drain connection. Standing water = Legionella risk. Chemical dosing (biocide) required. Check monthly.

## Belt, Pulley, and Bearing System

**V-belt drive**: transfers motor torque to fan shaft. Belt tension must be checked regularly — loose belt = slipping (motor runs hot, fan speed drops, vibration). Overtight belt = premature bearing failure.

Belt alignment: checked with straight-edge along pulley faces. Misalignment causes lateral belt wear, vibration, noise.

**Bearings**: motor front and rear bearings + fan shaft bearings. Lubricate per manufacturer schedule (typically quarterly for grease-nipple type). Over-greasing is as harmful as under-greasing. Signs of bearing failure: vibration, noise (rattling, grinding), heat.

## Sensors and BMS Integration

- **Supply air temperature sensor**: should read 12–15°C off-coil for hospital AHUs in Malaysia
- **Return air temperature sensor**: confirms space temperature
- **Relative humidity sensor**: for RH-controlled zones (OT, pharmacy)
- **Differential pressure sensor across filter**: monitors filter condition
- **Duct static pressure sensor**: used for VAV systems
- **CO2 / IAQ sensor**: demand-controlled ventilation
- **Current transducers (CT)**: non-invasive motor current monitoring — used by WACH FAIR scoring

BMS (Building Management System) provides remote start/stop, setpoint control, alarm monitoring, and trend logging. WACH reads electrical data from energy meters; BMS handles mechanical controls.

## Access Panels and Casing

Leaking access panel seals cause air bypass, reducing effective airflow to the space. Thermal bridging through casing raises condensation risk. Inspect panel gaskets during quarterly PM.
```

- [ ] **Step 4.2: Write ahu_electrical_health.md**

Create `backend/data/rag_docs/ahu_electrical_health.md` with the following content:

```markdown
# AHU Electrical Health Indicators

WACH monitors five electrical health indicators for each AHU. Together they form the FAIR health score (0–100). This document explains each indicator: what it measures, what causes it to degrade, what the thresholds mean, and why it matters.

## 1. Power Factor (PF)

**What it is**: Power Factor = Active Power (kW) ÷ Apparent Power (kVA). Ranges 0–1 (or 0–100%). A PF of 1.0 means all electrical power drawn is being converted to useful work. A PF of 0.75 means 25% of the current drawn is reactive — it does no useful work but still flows through cables, transformers, and switchgear.

**Why it matters**: Low PF means:
- Higher current for the same useful power → cable heating → accelerated insulation aging
- Higher kVA demand → larger TNB capacity + network charges
- TNB PF penalty surcharge (below 0.85 for supplies ≤ 132kV)
- Motor operates less efficiently → more heat generated

**Target**: ≥ 0.90 for hospital AHUs

**TNB threshold**: < 0.85 = penalty. Penalty = [(0.85 − PF)/0.01] × 1.5% of bill (for PF 0.75–0.85). Below 0.75: doubles to 3%/0.01.

**What causes low PF**:
- Induction motors running at part load (most common in hospitals — AHUs often oversized or running at reduced speed)
- Missing or undersized capacitor bank
- VFD not set to PF correction mode
- Failed capacitor bank (open-circuited capacitors)
- Addition of uncompensated inductive loads on same feeder

**How to correct**:
1. Inspect capacitor bank — test capacitance (should be within 5% of nameplate kVAR)
2. Check VFD PF settings
3. Install additional capacitors (fixed or automatic PF correction panel)
4. Check for open-circuited capacitors (one blown capacitor in a bank significantly reduces total correction)

## 2. Total Harmonic Distortion (THD)

**What it is**: THD measures the presence of harmonic currents (integer multiples of the fundamental 50 Hz frequency) as a percentage of the fundamental. THD-I = current THD; THD-V = voltage THD.

Common harmonic orders in AHU circuits:
- 5th harmonic (250 Hz): dominant in VFD-driven motors
- 7th harmonic (350 Hz): secondary VFD harmonic
- 3rd harmonic (150 Hz): from single-phase non-linear loads (lighting, UPS) on the same feeder

**Why it matters**:
- Harmonic currents cause additional heating in motor windings (I²R losses at higher frequencies)
- Reduces transformer efficiency and can cause transformer overheating
- Causes neutral conductor overloading (3rd harmonic circulates in neutral)
- Contributes to capacitor bank overloading and failure
- Can cause nuisance tripping of protective relays
- Degrades motor insulation lifespan

**Limits**: IEEE 519-2022 specifies THD-I < 5% at the point of common coupling (PCC) for most hospital supply systems.

**What causes high THD**:
- VFD without line reactor or harmonic filter (most common cause in hospital AHUs)
- Multiple VFDs on the same feeder without harmonic mitigation
- UPS systems (often in hospitals near critical equipment)
- Electronic ballasts, LED driver power supplies on the same circuits

**How to address**:
1. Install 3–5% impedance line reactor on VFD input (inexpensive, effective for 5th/7th harmonics)
2. Install passive harmonic filter (tuned to 5th/7th) for more severe cases
3. Separate VFD circuits from sensitive loads where possible
4. Measure THD at motor terminals vs. at MCC — if much higher at MCC, source is upstream

## 3. Phase Imbalance (Current Unbalance)

**What it is**: In a balanced three-phase system, currents in L1, L2, L3 are equal and 120° apart. Phase imbalance (current unbalance) is the maximum deviation from the average, expressed as a percentage.

NEMA MG1 standard: a 1% voltage unbalance causes approximately 6–10% current unbalance. Current unbalance > 5% requires motor derating.

**Why it matters**:
- Unequal currents produce unequal heating in motor windings → hot spots → accelerated insulation failure
- Negative sequence currents produce a counter-rotating magnetic field → braking torque → motor heats up further, runs less efficiently
- Reduces motor life significantly (each 10°C rise in winding temperature halves insulation life — Arrhenius rule)
- Can cause premature bearing failure due to shaft currents

**Target**: < 2% current unbalance

**What causes phase imbalance**:
- Unequal single-phase loads on the same three-phase feeder (most common in hospitals — medical equipment, lighting, sockets on different phases)
- Loose terminal connections at motor, contactor, or MCC (introduces resistance asymmetry)
- Blown fuse or open contact on one phase
- Deteriorated contactor contacts (unequal contact resistance)
- Motor winding fault (shorted turns in one phase)

**How to diagnose**:
1. Measure line voltages at MCC input: L1–L2, L2–L3, L1–L3. Voltage unbalance > 1%? → utility or supply problem
2. Balanced voltages but unbalanced currents → motor terminal or winding issue
3. Check contactor contacts visually — pitting, arcing marks
4. Measure each phase current with clamp meter — identify which phase is high or low
5. If one phase reads near-zero → open circuit (fuse, contactor contact, cable break)

## 4. THD Drift (thd_drift score)

In WACH, the `thd_drift` score tracks how much the THD has increased from the AHU's own baseline (not just whether it exceeds a fixed limit). A gradual drift upward over days or weeks often indicates a failing capacitor bank, deteriorating VFD filter, or new harmonic sources being added to the circuit.

Sudden THD spikes suggest load changes or equipment faults. Chronic upward drift suggests systematic degradation.

## 5. Overload (Overcurrent)

**What it is**: Overload occurs when the motor draws current above its Full Load Amperes (FLA) nameplate rating. WACH tracks whether measured current exceeds a calculated threshold based on the motor's rated current.

**Why it matters**:
- Thermal damage to motor windings (overtemperature)
- Trips thermal overload relay → unexpected AHU shutdown
- In hospital zones, unplanned AHU shutdown risks patient safety (OT, ICU, NICU)
- Frequent overload trips → motor insulation degradation → shorter motor life

**Causes of overload**:
- Clogged air filters (increased system resistance → fan works harder → motor draws more current)
- Fouled cooling coil (reduced airflow through the AHU)
- Belt slipping or misaligned (fan speed drops, motor compensates)
- VFD set to incorrect frequency (overspeeding motor)
- High ambient temperature in plant room (reduces motor cooling efficiency)
- Mechanical fault (seized bearing, jammed damper)

**How to address**:
1. Check filter ΔP — high ΔP → replace filters immediately
2. Check coil condition (visual, ΔT across coil)
3. Check belt tension and alignment
4. Measure motor terminal voltage (undervoltage causes overcurrent)
5. Check plant room temperature

## Relationship Between Indicators

Poor PF → higher currents → more heating → may trigger overload relay
High THD → additional copper losses → contributes to apparent overload
Phase imbalance → hot winding → accelerated insulation degradation → eventual motor failure
Energy anomaly often precedes and correlates with all of the above — it is the earliest warning signal.

WACH's FAIR scoring weights these to prioritise the most financially significant indicators (PF and phase imbalance at 25% weight each).
```

- [ ] **Step 4.3: Write fair_scoring_methodology.md**

Create `backend/data/rag_docs/fair_scoring_methodology.md` with the following content:

```markdown
# FAIR Health Scoring Methodology

WACH uses a proprietary scoring system called FAIR to express the electrical health of each AHU as a single number from 0 to 100. This document explains how it is calculated, what each component means, and how to interpret the results.

## What Does FAIR Stand For?

FAIR is a composite health index derived from five electrical performance indicators. The name reflects the goal: provide a Fair, Actionable, Interpretable Result for facility operators and engineers.

## The Five Component Scores

Each component is independently scored 0–100, where 100 = perfect health and 0 = severe degradation.

### 1. Energy Anomaly (weight: 15%)

Measures how much the AHU's current energy consumption deviates from its own rolling baseline. The baseline is calculated from the device's own historical patterns (same time of day, same weekday pattern).

- Score 100: energy consumption is normal, within expected range
- Score 50: energy is ~15–20% above baseline (e.g., clogged filters, fouled coil)
- Score 0: energy is severely elevated or has spiked anomalously

**Why it catches problems early**: energy anomaly often appears before PF or current imbalance degrades, because fouled coils and clogged filters increase the motor's mechanical load before it is reflected in electrical imbalance.

### 2. Power Factor Degradation (weight: 25%)

Measures how far the AHU's power factor has fallen below the target of ≥ 0.90.

- Score 100: PF ≥ 0.90
- Score 75: PF ~ 0.87 (approaching TNB penalty threshold)
- Score 50: PF ~ 0.85 (at TNB penalty threshold)
- Score 0: PF ≤ 0.70 (severe degradation, substantial TNB penalty)

Highest individual weight (25%) because poor PF has direct financial consequences via TNB penalty, and is the most actionable single-fix item (capacitor bank).

### 3. Phase Imbalance (weight: 25%)

Measures current unbalance across the three phases.

- Score 100: imbalance < 1%
- Score 75: imbalance ~ 2–3%
- Score 50: imbalance ~ 4–5% (NEMA MG1 action threshold)
- Score 0: imbalance > 10% (severe, motor damage risk)

High weight (25%) because phase imbalance directly degrades motor life and can cause thermal runaway in hospital AHUs running 24/7.

### 4. THD Drift (weight: 15%)

Measures how much the current THD has drifted upward from the device's own baseline.

- Score 100: THD-I at or below baseline (< 5%)
- Score 50: THD-I has drifted 3–5 percentage points above baseline
- Score 0: THD-I is severely elevated (> 15% or trending rapidly upward)

Lower weight (15%) because THD's direct operational impact on hospital AHUs is less immediate than PF or phase imbalance, but it is an early warning of harmonic source degradation.

### 5. Overload (weight: 20%)

Measures whether the motor is drawing current above its rated FLA.

- Score 100: current ≤ FLA × 1.00
- Score 75: current at FLA × 1.05 (5% above rated — normal service factor operation)
- Score 50: current at FLA × 1.10
- Score 0: current at FLA × 1.25 or thermal relay has tripped

Weight 20% — significant because overload leads directly to unplanned shutdown, which in ICU/OT environments is a patient safety event.

## Composite Health Index

```
health_index = (
    0.15 × energy_anomaly +
    0.25 × pf_degradation +
    0.25 × phase_imbalance +
    0.15 × thd_drift +
    0.20 × overload
)
```

Result: 0–100.

## Health Tiers

| Tier | Range | Meaning | Action |
|------|-------|---------|--------|
| Healthy | 80–100 | All indicators within normal range | Scheduled PM only |
| Monitor | 60–79 | One or more indicators showing early degradation | Investigate trend, consider early intervention |
| Maintenance | 40–59 | Clear degradation, performance impacted | Book work order within 1–2 weeks |
| Critical | 0–39 | Severe degradation, risk of failure | Immediate action required |

**Note on thresholds**: the Monitor range starts at 60, not 50. This is intentional — an AHU with a PF of 0.83 (close to TNB penalty threshold) will score in the Monitor range even if other components are healthy, prompting investigation before the penalty is incurred.

## Safety Flags

In addition to the composite score, WACH raises binary safety flags when individual components breach hard thresholds:

- `PF_CHRONIC_LOW`: PF < 0.82 sustained for > 24 hours
- `THD_CHRONIC_HIGH`: THD-I > 8% sustained for > 12 hours
- `PHASE_IMBALANCE_HIGH`: current unbalance > 5%
- `OVERLOAD_ACTIVE`: current > 110% FLA

Safety flags appear as alert badges on the dashboard and are returned in `search_docs` results. They trigger regardless of the composite score — an AHU can have a health_index of 72 (Monitor) but still carry a `PF_CHRONIC_LOW` flag.

## How to Read a Score in Practice

**health_index = 65, pf_degradation = 28**
→ Power factor is the dominant problem. The AHU is in Monitor tier. Address PF first (check capacitor bank). Other components are relatively healthy.

**health_index = 45, phase_imbalance = 30, overload = 50**
→ Maintenance tier. Phase imbalance and overload are both degraded. Check supply voltage balance, contactor contacts, and air filters immediately.

**health_index = 25, safety_flags = "PF_CHRONIC_LOW,OVERLOAD_ACTIVE"**
→ Critical. Both PF and overload are severe and have been sustained. Isolate AHU for inspection if patient safety allows. In OT or ICU: escalate to facilities engineer immediately.

## Temporal Behaviour

Scores are computed hourly by the ETL pipeline. A single bad reading does not immediately tank the score — the scoring uses a rolling window approach. However, chronic issues compound over time. An AHU that has been running at PF 0.80 for a week will have a lower accumulated penalty contribution than one that has been at 0.80 for a month.

This means: Monitor tier today → if not addressed → likely Maintenance tier within weeks for a trend issue. The dashboard's trend charts show this progression.
```

- [ ] **Step 4.4: Commit batch 1**

```bash
git add backend/data/rag_docs/ahu_components_overview.md \
        backend/data/rag_docs/ahu_electrical_health.md \
        backend/data/rag_docs/fair_scoring_methodology.md
git commit -m "docs(rag): add AHU components, electrical health, and FAIR scoring documents"
```

---

## Task 5: RAG Documents — Batch 2 (Malaysian Context)

**Files:**
- Create: `backend/data/rag_docs/malaysian_hospital_hvac_context.md`
- Create: `backend/data/rag_docs/hospital_ahu_environments.md`
- Create: `backend/data/rag_docs/ahu_performance_benchmarks.md`

- [ ] **Step 5.1: Write malaysian_hospital_hvac_context.md**

Create `backend/data/rag_docs/malaysian_hospital_hvac_context.md` with the following content:

```markdown
# Malaysian Hospital HVAC Context

## Regulatory Framework

### JKR (Jabatan Kerja Raya) Standards
JKR Standard Specification for Building Works 2025 (updated from 2020 edition) governs HVAC design and installation in Malaysian government buildings including public hospitals.

Key ACMV (Air Conditioning and Mechanical Ventilation) requirements:
- System maintenance, control, and monitoring per ANSI/ASHRAE Standard 111
- Redundancy requirements for critical zones (N+1 for OT, ICU, NICU AHUs)
- Energy efficiency targets aligned with MS 1525

### Ministry of Health (KKM) Standards
KKM Hospital Support Services Engineering specification sets HVAC requirements for each hospital department based on clinical risk classification.

KKM Ventilation Guidelines (2021, updated for airborne pathogen control) specifies:
- Minimum ACH rates by risk zone
- Pressure relationships between clinical zones
- Filter efficiency requirements by department
- Commissioning and maintenance verification requirements

### MS 1525:2014
Malaysian Standard — Code of Practice on Energy Efficiency and Use of Renewable Energy for Non-Residential Buildings.
- OTTV (Overall Thermal Transfer Value): ≤ 50 W/m² for building envelope
- RTTV (Roof Thermal Transfer Value): ≤ 25 W/m²
- Chiller plant COP targets: ≥ 4.5 for central chilled water systems
- Drives energy efficiency investments in hospital HVAC

### ASHRAE 170-2025
American Society of Heating, Refrigerating and Air-Conditioning Engineers Standard 170-2025 (Ventilation of Health Care Facilities) is the primary international reference applied in Malaysian hospitals alongside JKR/KKM requirements. Where JKR/KKM is more stringent (e.g., OT ACH), the local standard takes precedence.

Key 2025 updates over 170-2021: natural ventilation provisions, updated imaging room requirements, revised behavioural health spaces, updated construction-phase ventilation requirements.

## Tropical Climate Baseline

Malaysian hospitals (Peninsula Malaysia) design to:
- **Outdoor design conditions**: 33°C dry-bulb temperature (DBT) / 28°C wet-bulb temperature (WBT) — equivalent to approximately 85% relative humidity at peak conditions
- **Indoor setpoints (wards)**: 24°C / 55% RH
- **Indoor setpoints (OT)**: 18–24°C / 50–60% RH

**Critical implication**: Malaysia has no winter. AHUs run at near-full load year-round. There is no seasonal low-demand period that can be used for major overhauls without disrupting clinical operations. This makes condition monitoring (WACH scoring) especially important — you cannot rely on seasonal downtime to catch problems.

**High latent load**: tropical climate means dehumidification dominates the cooling load. Typically 40–50% of total cooling load is latent (moisture removal). A fouled cooling coil or reduced chilled water flow affects dehumidification before it visibly affects sensible temperature — RH rises, which increases infection risk in surgical environments.

**No-load period risk**: AHUs left off for >24 hours in tropical climate accumulate condensation, mould, and biological growth rapidly. WACH Critical tier AHUs in non-clinical zones should not simply be switched off — they require a controlled approach.

## Infection Control Pressure Relationships

Pressure relationships are maintained by carefully balancing supply and exhaust/return air volumes:

- **Positive pressure zones** (supply > exhaust): OT, clean rooms, ICU, NICU, Bone Marrow Transplant Unit, Pharmacy sterile manufacturing. Prevents contamination ingress from adjacent corridors.
- **Negative pressure zones** (exhaust > supply): Isolation rooms (airborne infections — TB, COVID, measles), airborne infection isolation rooms. Prevents contaminated air from escaping to corridor.
- **Neutral zones**: General wards, corridors, offices.

**Pressure cascade**: OT → Scrub → Sub-sterile → Corridor → Outside. Each zone must be positive relative to the next outward zone.

**AHU failure impact on pressure**: if an OT supply AHU trips, positive pressure is lost within minutes. Contamination risk is immediate. This is why OT AHUs require N+1 redundancy and WACH Critical alerts for OT-serving AHUs warrant immediate escalation.

## ACH Requirements by Department (JKR/KKM Malaysia)

| Department | Total ACH | Fresh Air ACH | Pressure |
|---|---|---|---|
| Operating Theatre | ≥ 25 | ≥ 15 | Positive |
| ICU / PICU / NICU | ≥ 12 | ≥ 2 | Positive |
| Airborne Infection Isolation | ≥ 12 | ≥ 2 | Negative |
| General Ward | ≥ 6 | ≥ 2 | Neutral |
| Emergency Department | ≥ 10 | ≥ 2 | Neutral |
| Pharmacy Cleanroom | ≥ 20 | ≥ 5 | Positive |
| Central Sterile Supply | ≥ 10 | ≥ 2 | Positive |
| Mortuary | ≥ 10 | 100% OA | Negative |

## Energy Intensity Context

Typical installed AHU motor sizes in Malaysian hospitals:
- Operating Theatre AHU: 15–25 kW (large volume, HEPA filtration, precise humidity control)
- ICU / PICU AHU: 7.5–15 kW
- General Ward AHU: 5–11 kW
- Pharmacy FAU: 3–7.5 kW
- Corridor / Common AHU: 2.2–5.5 kW

Hospitals are major electricity consumers. A 500-bed hospital in Malaysia typically consumes 8–15 GWh/year. HVAC accounts for approximately 50–60% of that — making AHU efficiency a primary energy management target.
```

- [ ] **Step 5.2: Write hospital_ahu_environments.md**

Create `backend/data/rag_docs/hospital_ahu_environments.md` with the following content:

```markdown
# Hospital AHU Environments — Room-by-Room Requirements

Each hospital department has specific AHU requirements driven by clinical function, infection control, and patient vulnerability. This document maps department types to their HVAC requirements and explains the consequences of AHU failure in each zone.

## Operating Theatre (OT)

**Temperature**: 18–24°C (surgeons often prefer 20–21°C; neonatal OT 26–28°C)
**Humidity**: 50–60% RH
**ACH**: ≥ 25 total (≥ 15 fresh air)
**Pressure**: Positive (+8 Pa minimum relative to scrub corridor)
**Filtration**: Pre-filter G4 → Bag filter F9 → HEPA H14 at supply terminal

Consequence of AHU failure: positive pressure lost → contamination risk → surgical site infection risk → must suspend operations. Requires N+1 redundant AHU. WACH Critical tier OT AHU = immediate escalation, do not wait for next shift.

AHU type: typically dedicated fresh air unit (FAU) + recirculation unit (ACU). The FAU handles OA conditioning; ACU handles filtration and fine temperature control. Both are monitored by WACH.

## Paediatric Intensive Care Unit (PICU) / Adult ICU / NICU

**Temperature**: 21–24°C (NICU: 24–26°C with incubator supplement)
**Humidity**: 50–60% RH
**ACH**: ≥ 12 total (≥ 2 fresh air)
**Pressure**: Positive
**Filtration**: G4 → F7 → F9

Consequence of failure: life-critical patients on ventilators and monitoring. Positive pressure loss risks healthcare-associated infection (HAI). WACH Critical in ICU/PICU/NICU = immediate call to on-call engineer.

## General Inpatient Ward (Levels 7–11 in WACH building)

**Temperature**: 22–25°C
**Humidity**: 50–65% RH
**ACH**: ≥ 6 total (≥ 2 fresh air)
**Pressure**: Neutral
**Filtration**: G4 → F7

Consequence of failure: patient discomfort, elevated infection risk, complaints. Not immediately life-threatening in most ward types, but paediatric patients are more vulnerable. WACH Maintenance tier = schedule work order within 1–2 weeks.

## Emergency Department

**Temperature**: 22–25°C
**Humidity**: 50–65% RH
**ACH**: ≥ 10 total (≥ 2 fresh air)
**Pressure**: Neutral (sub-waiting areas may be negative for respiratory triage)
**Filtration**: G4 → F7

High footfall, variable occupancy, long operating hours. Emergency AHU is exposed to outdoor air contaminants more than ward AHUs (patient entry/exit). Filter replacement frequency should be higher.

## Pharmacy Cleanroom / Sterile Compounding

**Temperature**: 20–22°C
**Humidity**: 40–60% RH (strict RH control for drug stability)
**ACH**: ≥ 20 total (≥ 5 fresh air)
**Pressure**: Positive (ISO Class 7 or 8)
**Filtration**: G4 → F9 → H13 (or H14 for ISO 5 critical zones)

Consequence of failure: sterile compounding products contaminated → batch rejection → drug supply disruption. Very high cost of failure.

## Central Sterile Supply Unit (CSSU)

**Temperature**: 20–23°C
**Humidity**: 40–55% RH
**ACH**: ≥ 10 total
**Pressure**: Positive (clean side), Negative (dirty/decontam side)
**Filtration**: G4 → F7 → F9

CSSU has two pressure zones: decontamination (negative) and clean packing/storage (positive). WACH monitors all AHUs serving this department. Failure in clean zone = reprocessed instruments contaminated.

## Bone Marrow Transplant Unit (BMTU) / Oncology

**Temperature**: 22–24°C
**Humidity**: 40–60% RH
**ACH**: ≥ 12 total
**Pressure**: Positive (+12 Pa or higher, more stringent than standard ICU)
**Filtration**: G4 → F9 → H14

Immuno-compromised patients. Aspergillus contamination (from construction dust, mould) can be fatal. HEPA filtration mandatory. WACH Critical = stop non-essential work in vicinity, check HEPA filter integrity.

## Airborne Infection Isolation Room

**Temperature**: 21–24°C
**Humidity**: 50–60% RH
**ACH**: ≥ 12 total
**Pressure**: Negative (−8 Pa relative to corridor)
**Filtration**: G4 → F9 (exhaust HEPA required before discharge to outside)

Used for TB, measles, COVID, other airborne-transmissible diseases. Negative pressure maintained by having slightly more exhaust than supply. WACH monitoring of these AHUs must flag any positive pressure reversal immediately.

## Level-Specific Zones in WACH Building

Based on the WACH building AHU mapping:
- **Level 1**: Emergency Department (e0110–e0117), Imaging (e0118, e0120, e0121), support services
- **Level 2**: Outpatient clinics, Child Development Centre, Pharmacy
- **Level 3**: Pathology, Dental, Paediatric Specialist Clinic
- **Level 4**: Inpatient Pharmacy, Bone Marrow Transplant, Maternity OT (e0413–e0416)
- **Level 5**: PICU (e0501, e0510), Adult ICU (e0505, e0507), HDU, OT complex (e0622)
- **Level 6**: Administration, CSSU (e0605, e0606, e0628), Library
- **Levels 7–11**: Inpatient wards (Obstetric, Gynaecology, Paediatric Medical, Neonatology, Paediatric Surgical)

AHU failure impact is highest in Level 5 (ICU/OT) and Level 4 (BMT/OT). Levels 7–11 are ward AHUs — lower immediate clinical risk but high patient volume.
```

- [ ] **Step 5.3: Write ahu_performance_benchmarks.md**

Create `backend/data/rag_docs/ahu_performance_benchmarks.md` with the following content:

```markdown
# AHU Performance Benchmarks — Malaysian Hospital Tropical Climate

These benchmarks define normal operating ranges for electrical health indicators in Malaysian hospital AHUs operating in a tropical climate (33°C / 85% RH outdoor conditions, continuous 24/7 operation). Use these to interpret WACH health scores.

## Electrical Health Benchmarks

| Parameter | Healthy | Monitor | Critical | Notes |
|---|---|---|---|---|
| Power Factor | ≥ 0.90 | 0.85–0.89 | < 0.85 | TNB penalty below 0.85 |
| Current Unbalance | < 2% | 2–5% | > 5% | NEMA MG1 action at 5% |
| THD-I (current) | < 5% | 5–8% | > 8% | IEEE 519 limit at 5% |
| Overload (vs FLA) | ≤ 100% | 100–110% | > 110% | Service factor 1.15 permits short-term 115% |

## Energy Intensity Benchmarks (by AHU class)

Operating Theatre AHU (15–25 kW motor):
- Normal daily energy: 280–420 kWh/day (running 24/7 at 70–80% load)
- Anomaly trigger: > 15% above rolling 7-day baseline

ICU/PICU AHU (7.5–15 kW motor):
- Normal daily energy: 130–240 kWh/day
- Anomaly trigger: > 15% above rolling 7-day baseline

General Ward AHU (5–11 kW motor):
- Normal daily energy: 90–180 kWh/day
- Anomaly trigger: > 20% above rolling 7-day baseline (wards have more occupancy variation)

## Motor Operating Temperature

| Condition | Temperature Rise | Status |
|---|---|---|
| Normal (IE2/IE3) | < 40°C above ambient | Healthy |
| Marginal | 40–60°C above ambient | Monitor |
| High — intervention needed | > 60°C above ambient | Critical |

Ambient in plant rooms: expect 30–40°C in Malaysian tropical climate. A motor with 60°C rise in a 38°C room = 98°C winding temperature — approaching insulation class F limit of 155°C but within safe range.

## Filter Pressure Drop Benchmarks

| Filter Type | Replace When ΔP > |
|---|---|
| Pre-filter G4 | 80–100 Pa |
| Bag filter F7 | 120–150 Pa |
| Bag filter F9 | 150–180 Pa |
| HEPA H13/H14 | 200–250 Pa (or per manufacturer) |

These are general guidelines. Actual replacement is triggered by either ΔP limit or time-based schedule (whichever comes first).

## Age-Based Degradation Expectations

AHU electrical health degrades with age even with regular maintenance:

- **0–5 years**: expect health_index 85–95 (well-maintained). PF 0.90+, THD < 5%.
- **5–10 years**: expect health_index 75–90. PF may drop to 0.87–0.89 if capacitor bank not serviced. THD slowly rises.
- **10–15 years**: expect health_index 60–80. PF degradation common. Phase imbalance events more frequent. Capacitor bank likely needs overhaul.
- **> 15 years**: variable. Motor rewinds may have been done with non-OEM wire → different resistance per phase → structural phase imbalance. WACH scores 50–75 expected even with good maintenance.

## Seasonal Variation

Malaysia has no distinct seasons, but:
- **Northeast monsoon (Nov–Feb)**: higher rainfall, slightly lower ambient temperatures (29–31°C) → minor improvement in AHU electrical health (motor runs cooler, lower latent load)
- **Dry periods (Jun–Sep)**: higher ambient temperatures (33–35°C) → higher motor temperature, slightly elevated overload risk
- **Post-Raya/holiday periods**: reduced building occupancy → AHUs may be operating well below design load → PF can temporarily improve (motors at light load with capacitor correction = risk of leading PF, but usually not severe)

## Benchmark Deviation Interpretation

**PF suddenly drops 0.05 in one reading**: likely capacitor bank fault or new inductive load added to feeder — investigate same day.

**THD gradually rises 2% over 2 weeks**: likely VFD output filter degradation or new harmonic source added — schedule inspection within 2 weeks.

**Phase imbalance spikes to 8% then returns to normal**: likely intermittent contactor contact or loose terminal — schedule inspection within 1 week.

**Energy anomaly +25% sustained for 3 days**: likely filter blockage (most common) or coil fouling — check filter ΔP immediately.

**All 5 component scores declining together**: systematic issue — check supply quality at MCC, check for building-wide load changes, check chilled water supply temperature (if CHW temp rises, AHU cooling output drops, motor works harder).
```

- [ ] **Step 5.4: Commit batch 2**

```bash
git add backend/data/rag_docs/malaysian_hospital_hvac_context.md \
        backend/data/rag_docs/hospital_ahu_environments.md \
        backend/data/rag_docs/ahu_performance_benchmarks.md
git commit -m "docs(rag): add Malaysian HVAC context, hospital environments, and benchmarks"
```

---

## Task 6: RAG Documents — Batch 3 (Operational Guides)

**Files:**
- Create: `backend/data/rag_docs/tnb_tariff_financial_guide.md`
- Create: `backend/data/rag_docs/fault_diagnosis_guide.md`
- Create: `backend/data/rag_docs/ahu_maintenance_guide.md`
- Create: `backend/data/rag_docs/wach_system_guide.md`

- [ ] **Step 6.1: Write tnb_tariff_financial_guide.md**

Create `backend/data/rag_docs/tnb_tariff_financial_guide.md` with the following content:

```markdown
# TNB Tariff and Financial Impact Guide

## TNB Tariff Structure — RP4 (Effective 1 July 2025)

Tenaga Nasional Berhad (TNB) overhauled its tariff structure under Regulatory Period 4 (RP4, 2025–2027). The key structural change: the old single Maximum Demand (MD) charge is replaced by two separate charges — Capacity Charge + Network Charge.

### Tariff Categories for Hospitals

Malaysian government hospitals are typically on Medium Voltage (MV) supply. Relevant tariffs:

**MV General Tariff (ex-Tariff C1 / E1)**
- Energy charge: RM 0.2983/kWh
- Capacity + Network charge: RM 89.27/kW/month
- No peak/off-peak differentiation
- Most common for hospitals without TOU metering

**MV Time-of-Use (TOU) Tariff (ex-Tariff C2 / E2)**
- Peak energy (Mon–Fri, 2 PM–10 PM): RM 0.3132/kWh
- Off-peak energy (all other times + weekends + public holidays): RM 0.2723/kWh
- Capacity + Network charge: RM 97.06/kW/month
- Available for hospitals with smart metering — allows energy shifting strategies

**High Voltage (HV) Tariff (ex-Tariff C3 / E3, 132kV and above)**
- Energy charge: RM 0.4303/kWh
- Capacity + Network charge: RM 31.21/kW/month
- Applies to very large hospital complexes with their own substation

### AFA (Automatic Fuel Adjustment)
Replaced ICPT from July 2025. Adjusted monthly by Energy Commission (ST) based on fuel prices and exchange rates. Added to or subtracted from energy charge.
- January 2026 AFA: −4.99 sen/kWh (discount)
- AFA adjusts monthly — check current month's AFA for exact billing calculations.

## Power Factor Penalty

TNB imposes a surcharge when monthly average PF falls below the minimum threshold.

**Threshold (for supplies ≤ 132kV)**: PF < 0.85
**Threshold (for supplies ≥ 132kV)**: PF < 0.90

### Penalty Formula

For PF between 0.75 and 0.85:
```
Penalty = [(0.85 − PF) / 0.01] × 1.5% × Monthly Bill
```

For PF below 0.75 (tiered — higher rate applies below 0.75):
```
Penalty = {[(0.85 − 0.75) / 0.01 × 1.5%] + [(0.75 − PF) / 0.01 × 3%]} × Monthly Bill
```

### Penalty Examples

| Monthly Average PF | Penalty Rate | On a RM 100,000 Bill |
|---|---|---|
| 0.88 | 0% | RM 0 |
| 0.85 | 0% | RM 0 (at threshold) |
| 0.84 | 1.5% | RM 1,500 |
| 0.82 | 4.5% | RM 4,500 |
| 0.78 | 10.5% | RM 10,500 |
| 0.75 | 15.0% | RM 15,000 |
| 0.72 | 24.0% | RM 24,000 |

### Fleet-Level Penalty Exposure Example

121 AHUs, MV TOU tariff (RM 0.30/kWh average), 200 kWh/day per AHU:
- Monthly fleet energy: ~726,000 kWh → bill ~RM 218,000
- If fleet average PF = 0.82 → penalty = 4.5% × RM 218,000 = **RM 9,810/month = RM 117,720/year**
- Fixing PF across 30 worst AHUs to ≥ 0.90 → eliminates this penalty

## Capacity + Network Charge Impact

The RM 89.27/kW charge (MV General) is applied to the maximum recorded demand in the billing month. Poor PF raises the apparent power (kVA) for the same useful power (kW), potentially increasing the peak demand recorded and thus the Capacity + Network charges.

Example: An AHU drawing 8 kW at PF 0.78 draws 8/0.78 = 10.26 kVA. At PF 0.92 it would draw 8.7 kVA. The difference in apparent power contributes to peak demand — particularly when many AHUs have poor PF simultaneously.

## ROI of Maintenance Actions

### Capacitor Bank Replacement (targets PF improvement)
- Typical cost per AHU: RM 2,000–5,000
- PF improvement: 0.78 → 0.90 (eliminates 10.5% penalty)
- On a RM 1,800/month bill per AHU: saves RM 189/month
- Payback: 11–27 months (from penalty savings alone, not counting reduced capacity charges and motor life extension)

### Filter Replacement (targets energy anomaly)
- G4 filter set: RM 30–80
- Bag filter set: RM 150–400
- Energy saving: 5–15% reduction in motor current if heavily blocked
- At RM 0.30/kWh and 10 kW AHU running 720 hr/month: RM 2,160/month energy cost; 10% saving = RM 216/month
- Payback: immediate (filter cost < 1 month savings)

### Coil Chemical Wash (targets energy anomaly + capacity)
- Cost: RM 500–1,500 per AHU
- Energy saving: 8–20% reduction (fouled coil forces motor to compensate)
- Payback: 1–6 months

### Motor Rewind or Replacement (targets phase imbalance + overload)
- Cost: RM 3,000–15,000 depending on kW
- Benefits: reduced phase imbalance, normal overload margin restored, often improved IE class
- Payback: 12–36 months (energy + penalty savings)

## Financial Framing of FAIR Tiers

| FAIR Tier | Score | Estimated Monthly Cost of Inaction (per AHU) |
|---|---|---|
| Healthy | 80–100 | RM 0–200 above optimal |
| Monitor | 60–79 | RM 200–800 (early PF penalty + energy drift) |
| Maintenance | 40–59 | RM 800–2,500 (PF penalty + energy + increased breakdown risk) |
| Critical | 0–39 | RM 2,500+ (full penalty + high breakdown risk + operational disruption cost) |

Note: figures are approximate per-AHU monthly estimates. A Critical AHU in OT that causes a surgical schedule cancellation adds tens of thousands in operational cost beyond the energy/penalty figures.
```

- [ ] **Step 6.2: Write fault_diagnosis_guide.md**

Create `backend/data/rag_docs/fault_diagnosis_guide.md` with the following content:

```markdown
# AHU Fault Diagnosis Guide

Step-by-step decision trees for diagnosing the four primary WACH fault types. Use these procedures to systematically identify the root cause before ordering parts or scheduling corrective maintenance.

## Safety First

Before any physical inspection or measurement:
1. Inform shift supervisor and Infection Control (if in clinical zone)
2. Obtain Permit-to-Work from Engineering Department
3. Apply Lockout-Tagout (LOTO) if disconnecting power — lock the MCC incomer, hang personal padlock, test for dead with voltage tester
4. For running measurements (current, voltage): use appropriate PPE — insulated gloves, face shield, Category III rated test equipment

---

## Fault 1: Low Power Factor (pf_degradation score low)

WACH flags: `PF_CHRONIC_LOW`, or pf_degradation component score < 50

**Step 1: Confirm the reading**
- Check WACH dashboard trend: is PF consistently low, or a single-point anomaly?
- Single-point anomaly → likely sensor/reading issue; monitor for 24h
- Consistent low PF (> 24h below 0.85) → proceed

**Step 2: Check capacitor bank**
- Locate capacitor bank (usually mounted in MCC panel or separate PF correction panel)
- Visual check: bulging, leaking, burnt smell → failed capacitor → replace bank
- Use capacitance tester: measure each capacitor, should be within ±5% of nameplate kVAR
- One failed capacitor in a 3-stage bank can reduce total correction by 30–50%

**Step 3: Check VFD settings (if VFD installed)**
- Access VFD keypad → navigate to output PF or reactive power monitoring
- Check if VFD has built-in PF correction settings → enable if available
- Check for output filter installed (line reactor) — if not present, harmonic current can interact with capacitor bank

**Step 4: Check motor condition**
- Power down AHU (LOTO)
- Megger test motor windings (phase-to-phase, phase-to-earth): should read > 10 MΩ
- Low insulation resistance → winding fault → motor requires rewind or replacement
- Check motor terminal connections — tight, clean, no corrosion

**Step 5: Check for added loads**
- Review electrical panel drawings for this circuit
- Confirm no additional inductive loads (transformers, other motors) added to same feeder recently

**Action thresholds**:
- PF 0.84–0.87: service capacitor bank, book for next scheduled maintenance window
- PF < 0.83: urgent — book within 1 week, TNB penalty accumulating
- PF < 0.75: immediate intervention — double-rate penalty, motor heating risk

---

## Fault 2: High THD (thd_drift score low)

WACH flags: `THD_CHRONIC_HIGH`, or thd_drift component score < 50

**Step 1: Confirm THD source — localise**
- Measure THD-I at motor terminals (clamp meter with THD function, or power analyser)
- Measure THD-V at MCC busbar
- If THD at motor >> THD at MCC: problem is local (VFD, motor winding)
- If THD at MCC is already high: upstream source or multiple AHUs contributing

**Step 2: Check VFD harmonic mitigation**
- Is a line reactor (3–5% impedance) installed on VFD input? If not: install one
- Is an output dV/dt filter or sine filter installed? Check condition
- VFD output filters degrade over time — inspect for physical damage, overheating marks

**Step 3: Check for new loads on feeder**
- Review recent electrical work in the zone: new UPS installed? New LED driver panels? New medical imaging equipment?
- Imaging equipment (CT scanners, MRI) are major harmonic sources — confirm they are on separate feeders

**Step 4: Measure THD spectrum**
- Use power quality analyser to identify dominant harmonic orders
- 5th harmonic dominant → VFD source
- 3rd harmonic dominant → single-phase non-linear loads (lighting, computers)
- Multiple orders present → mixed sources

**Step 5: Remediation options**
- Line reactor (input): cheapest, reduces 5th/7th by 50–70%, suitable for most AHU VFDs
- Passive harmonic filter: tuned notch filter, higher cost, very effective for 5th/7th
- Active harmonic filter: expensive, suitable for large complex harmonic sources

**Action thresholds**:
- THD-I 5–8%: install/check line reactor; monitor
- THD-I > 8%: urgent — install line reactor immediately, consult electrical engineer for harmonic filter assessment

---

## Fault 3: Phase Imbalance (phase_imbalance score low)

WACH flags: `PHASE_IMBALANCE_HIGH`, or phase_imbalance component score < 50

**Step 1: Measure supply voltages at MCC incomer**
Using a calibrated multimeter:
- Measure L1–L2, L2–L3, L1–L3 (phase-to-phase)
- Calculate voltage unbalance: (max deviation from average) / average × 100%
- Voltage unbalance > 1%? → utility supply problem or major single-phase load on feeder → report to TNB / internal electrical team

**Step 2: Balanced voltages but high current imbalance → local problem**

**Step 3: Check motor terminals**
- Power down, LOTO
- Inspect L1, L2, L3 terminals at motor terminal box: tight? Corrosion? Carbon deposits?
- Retorque to motor nameplate spec
- Clean with contact cleaner

**Step 4: Check contactor**
- Power down, LOTO
- Open MCC contactor for this AHU
- Inspect each contactor contact pair: equal wear? Pitting on only one phase? Unequal contact force?
- Light pitting: file smooth
- Heavy pitting: replace contactor

**Step 5: Check for single-phase loads**
- Identify all single-phase loads tapped off the same three-phase feeder
- Measure L1, L2, L3 load individually with clamp meter
- Redistribute single-phase loads to balance phases

**Step 6: Motor winding test**
- Measure winding resistance per phase (Ohm setting, low resistance measurement)
- L1–L2, L2–L3, L1–L3 winding resistance: should match within ±5% of each other
- Significant variation → shorted turns or open winding → motor requires rewinding or replacement

**Action thresholds**:
- Current imbalance 3–5%: check terminals and contactor; book inspection within 2 weeks
- Current imbalance > 5%: urgent — NEMA MG1 motor derating threshold exceeded; book within 1 week
- One phase reading near zero: open circuit — do not run motor, immediate LOTO, investigate

---

## Fault 4: Overload (overload score low)

WACH flags: `OVERLOAD_ACTIVE`, or overload component score < 60

**Step 1: Measure actual motor current**
Clamp meter on each phase at MCC output. Compare to nameplate FLA.
- Is it uniformly high across all three phases? → mechanical overload (filter, coil, belt)
- Is it high on one phase? → combined overload + phase imbalance → check both fault trees

**Step 2: Check air filters**
- Locate pre-filter and bag filter differential pressure gauges (if installed)
- Manual check: hold torch against filter — no light penetrating = extremely blocked
- Replace filters if ΔP > threshold — this is the most common cause of AHU overload in hospitals

**Step 3: Check cooling coil condition**
- With AHU running, measure air temperature before and after cooling coil (using pocket probe thermometer at access panels)
- Normal ΔT: 8–14°C across coil
- Reduced ΔT with same chilled water valve position → fouled coil → reduced airflow → motor works harder
- Book chemical coil wash

**Step 4: Check belt and drive**
- With AHU stopped, LOTO: manually rotate fan shaft — should turn freely
- Check belt tension (deflection method: press belt midspan, should deflect ~1% of belt length under light pressure)
- Slack belt = slipping → motor draws more current to maintain speed → overload
- Check belt for cracking, glazing (shiny surface = slipping)

**Step 5: Check ambient temperature**
- Measure plant room temperature
- Motor nameplate is rated at 40°C ambient (standard)
- If plant room > 45°C: motor needs derating by ~5–10% → effectively reduces overload threshold
- Check plant room ventilation — blocked louvres, failed ventilation fan?

**Step 6: Check VFD frequency setting**
- If VFD installed: confirm set frequency matches design (e.g., 48 Hz for reduced speed)
- If VFD set to 60 Hz on a 50 Hz motor design: motor overspeeds → overload

**Action thresholds**:
- Current 100–110% FLA: inspect filters and belt; book maintenance within 2 weeks
- Current > 110% FLA: urgent — overload relay may trip; filters/belt check same day
- Thermal relay has tripped and reset: investigation required before re-energising

---

## Energy Anomaly (energy_anomaly score low)

Not a direct electrical fault but an early warning of mechanical or electrical degradation.

**Step 1: Is it a sudden spike or gradual drift?**
- Sudden spike: mechanical fault (seized damper, belt break, bearing seizure) → immediate inspection
- Gradual rise over days/weeks: filter blockage (most common), coil fouling, refrigerant undercharge → scheduled inspection

**Step 2: Compare timing**
- Does anomaly correlate with a specific time of day? → occupancy change, specific equipment turning on
- Always high regardless of time? → persistent mechanical issue
- High on certain days? → check for related building events (maintenance shutdown of chilled water, power outages)

**Step 3: Cross-check with other scores**
- Energy anomaly high + overload high: filter or coil problem (mechanical load increase)
- Energy anomaly high + PF degrading: capacitor bank issue (more reactive current drawn)
- Energy anomaly high alone: early mechanical issue — inspect AHU before other scores degrade
```

- [ ] **Step 6.3: Write ahu_maintenance_guide.md**

Create `backend/data/rag_docs/ahu_maintenance_guide.md` with the following content:

```markdown
# AHU Maintenance Guide — Malaysian Hospital Standards

Preventive maintenance (PM) schedules and corrective procedures for hospital-grade AHUs in Malaysia. Based on JKR Standard Specification 2025, KKM Hospital Support Services guidelines, and manufacturer recommendations for tropical climate continuous-duty operation.

## Permit-to-Work and LOTO Procedure

Before ANY physical maintenance involving the AHU:
1. Submit Permit-to-Work (PTW) request to Engineering Department, minimum 24 hours notice for planned work
2. For clinical zones (OT, ICU, NICU): inform Ward Manager and Infection Control Officer — obtain their clearance
3. At the MCC: identify the correct incomer for the AHU. Confirm with single-line diagram.
4. Switch off MCCB/switch, then apply personal padlock to lockout device
5. Hang warning tag: "DO NOT ENERGISE — Maintenance in Progress — [Name] [Date]"
6. Use voltage tester to confirm dead on all three phases at motor terminal or panel output
7. Mechanical lockout: for belt drives, apply shaft lock or insert wooden block to prevent fan rotation

Reinstatement: reverse order. Remove all tools and personnel from AHU casing before energising. Do a no-load test (brief run) before handing back to operations.

## Preventive Maintenance Schedule

### Daily (BMS Operator / Dashboard Check — 5 minutes)
- Review WACH dashboard: any AHU in Critical tier? Any new safety flags?
- Check supply air temperature and humidity setpoints for critical zones (OT, ICU) on BMS
- Check BMS for active alarms — filter pressure alarms, supply temperature alarms
- Log any unusual readings

### Weekly (Mechanical Round — 30 minutes per zone)
- Visual inspection of pre-filter condition (through inspection window if available)
- Check condensate drain pan: no standing water, drain clear, no odour
- Check belt by touch/sound with AHU running (squealing = slipping; unusual vibration = alignment)
- Record motor current (clamp meter on each phase at MCC) and compare to last week
- Check plant room temperature; ensure louvres open and plant room exhaust fan running

### Monthly (30–60 minutes per AHU)
**Filters:**
- Replace pre-filter (G4) — in high-dust or high-occupancy zones, may need bi-weekly
- Clean filter frame housing (dry cloth, remove accumulated dust)

**Electrical:**
- Record three-phase currents (L1, L2, L3) with clamp meter
- Record power factor (if portable PF meter available)
- Inspect MCC panel for hot spots, discolouration, unusual odours (use thermal camera if available)

**Mechanical:**
- Check condensate drain pan and clean if necessary
- Inspect belt visually for cracking, glazing, fraying
- Check drain pump operation (if installed)
- Chemical dosing of drain pan (biocide per water treatment contractor schedule)

### Quarterly (2–4 hours per AHU) — Book with PTW
**Filters:**
- Replace bag filter (F7 or F9)
- Inspect filter frame for bypass gaps, torn seals — seal with filter tape if found
- Record pre/post filter pressure drop

**Motor:**
- Megger test: measure insulation resistance phase-to-phase and phase-to-earth
  - Test voltage: 500V DC for motors ≤ 1 kV
  - Minimum acceptable: 1 MΩ (warrants monitoring); > 10 MΩ is healthy
- Measure and record winding resistance per phase (Ω) — compare to baseline
- Lubricate bearings per manufacturer schedule (grease type and quantity as specified — do not over-grease)
- Check motor mounting bolts for tightness

**Drive:**
- Check belt tension (deflection method)
- Check pulley alignment with straight-edge
- Inspect pulleys for wear, groove damage
- Check all fasteners on fan bearing housing

**Coil:**
- Clean cooling coil fins with low-pressure compressed air (< 30 psi), blow from clean to dirty side
- Check coil fins for fin collapse (use fin comb to straighten if needed)
- Inspect coil drain pan for scale, algae — treat with biocide if present

**Capacitor bank:**
- Check for bulging, leaking, heat discolouration
- Measure capacitance of each unit (should be within ±5% of nameplate kVAR)

**Dampers:**
- Manually operate fresh air and return air damper actuators through full range
- Check actuator feedback signal matches BMS position reading
- Inspect damper blades for corrosion, damage

### Annual (4–8 hours per AHU) — Major Service, Book with PTW + Infection Control
**Filters:**
- Replace HEPA filter (H13/H14) in OT, ICU, Pharmacy, BMTU AHUs
- For HEPA replacement: wear full PPE (N95, gloves, coverall), double-bag used filters before disposal
- Conduct pressure test after HEPA installation to verify no bypass

**Coil chemical wash:**
- Chemical wash procedure:
  1. Isolate chilled water valve (closed), drain coil (open vent at top, drain at bottom)
  2. Apply alkaline degreaser (pH 10–12) to coil — spray from discharge face, let dwell 15 minutes
  3. Rinse with low-pressure water, collect runoff in drain pan
  4. Apply mild acid descaler (pH 3–5) if scale present — dwell 10 minutes
  5. Thorough rinse with clean water until neutral pH
  6. Blow dry with compressed air
  7. Open chilled water valve and check for leaks
- Note: do not use high-pressure wash (> 40 psi) — damages fins

**Electrical annual service:**
- Full VFD inspection: clean interior with dry compressed air, check terminal torque, record fault log, check/update firmware with manufacturer
- Replace motor thermal protection device per manufacturer schedule
- Motor winding resistance test (IR + winding resistance)

**Ductwork inspection:**
- Open access hatches in duct sections
- Inspect for cracks, disconnected joints (air leakage), microbial growth
- Report findings to Engineering Manager

**Commissioning verification:**
- Measure room pressure differential (for clinical zones)
- Measure actual ACH (using flow hood at supply diffusers and return grilles)
- Compare to design ACH — if > 15% short, investigate: blocked duct, incorrect fan speed, system leakage

## Triggering Corrective Maintenance from WACH Scores

| WACH Tier | Response Time | Action |
|---|---|---|
| Healthy (80–100) | Next scheduled PM | No corrective action needed |
| Monitor (60–79) | Within 2 weeks | Book inspection, identify root cause |
| Maintenance (40–59) | Within 1 week | Book corrective work order |
| Critical (0–39) — ward AHU | Within 24–48 hours | Prioritise above routine PM |
| Critical — OT/ICU/NICU AHU | Immediate | Call on-call engineer, do not wait for shift change |

## Post-Maintenance Verification

After any corrective maintenance, before handing back to operations:
1. Run AHU for minimum 15 minutes — check for unusual sounds, vibration
2. Measure and record three-phase currents → confirm within FLA
3. Note power factor reading if meter available
4. Check BMS confirms normal operation (temperatures, pressures normal)
5. Update maintenance log with: work done, parts replaced, before/after readings
6. If in clinical zone: inform Ward Manager that AHU is back in service, record in maintenance logbook
```

- [ ] **Step 6.4: Write wach_system_guide.md**

Create `backend/data/rag_docs/wach_system_guide.md` with the following content:

```markdown
# WACH AI System Guide

## What is WACH?

WACH (Ward Air Conditioning Health) Insight is a real-time monitoring and AI analytics platform for Air Handling Units (AHUs) in a Malaysian hospital. It continuously monitors 121 AHUs across 11 building levels, calculating hourly health scores and providing an AI chatbot for natural language queries.

## What WACH Monitors

- **121 AHUs** across Levels 1–11 of the hospital building
- **Electrical health**: power factor, current THD, phase imbalance, energy consumption, motor overload
- **FAIR health scores**: composite 0–100 score updated hourly, broken into 5 component scores
- **Safety flags**: binary alerts for chronic threshold breaches (PF_CHRONIC_LOW, THD_CHRONIC_HIGH, PHASE_IMBALANCE_HIGH, OVERLOAD_ACTIVE)
- **Financial impact**: estimated excess energy cost and TNB PF penalty exposure per level

## How to Use the Dashboard

**Site Summary (top of page)**
Shows building-wide health at a glance: tier distribution (how many AHUs are Healthy/Monitor/Maintenance/Critical), level heat map (click any level tile to jump to that floor's detail).

**Level Selector Bar (sticky)**
Click a level number (1–11) to view all AHUs on that floor.

**Dashboard Section**
Shows ranking of best/worst AHUs for the selected level, individual AHU health cards with sparklines, score breakdown for each FAIR component.

**Prediction Section**
Shows 24-hour health score forecasts for the selected level.

## How to Use the AI Chat

The chat widget (bottom-right corner) accepts natural language questions about any AHU, level, or the building as a whole.

**Questions it can answer well:**
- "What is the current health status of the building?" → queries all levels at once using the building summary tool
- "Which AHUs on Level 5 are worst?" → retrieves and ranks Level 5 AHUs
- "Why does e0501 have a low power factor score?" → retrieves PF data + searches documentation for explanation
- "What is the financial impact on Level 3?" → calculates estimated TNB penalty + energy cost for Level 3
- "What maintenance should I do for e0601?" → retrieves AHU health + recommends action based on dominant fault
- "How does FAIR scoring work?" → retrieves methodology documentation
- "What causes high THD?" → retrieves electrical health guide

**Questions it cannot answer:**
- Real-time maintenance team availability or work order status
- Spare parts inventory
- Contractor quotes or pricing
- Clinical decisions or medical advice
- Events before the health database coverage period

## Health Score Interpretation

| Score | Tier | Meaning | What to Do |
|---|---|---|---|
| 80–100 | Healthy | All indicators normal | Scheduled PM only |
| 60–79 | Monitor | One or more indicators showing early drift | Investigate, consider early intervention |
| 40–59 | Maintenance | Clear degradation, action needed | Book work order within 1–2 weeks |
| 0–39 | Critical | Severe degradation, failure risk | Act now |

**Important context for Clinical Zones:**
- An AHU in Critical tier serving Level 5 (ICU/PICU/OT) is a clinical safety concern — escalate to on-call engineer immediately
- The same score in Level 9 (paediatric ward) warrants urgent but not emergency response
- WACH does not know the clinical load — an ICU AHU at score 45 in the middle of the night with active patients requires faster response than one with the same score during a scheduled maintenance downtime

## Understanding the Five Component Scores

When an AHU has a low health_index, look at the component scores to identify the primary fault:

| Component | Score Low Means | Primary Fault | First Action |
|---|---|---|---|
| energy_anomaly | High energy vs baseline | Filters clogged / coil fouled | Check filter ΔP |
| pf_degradation | Low power factor | Capacitor bank fault / VFD issue | Test capacitor bank |
| phase_imbalance | Unequal phase currents | Loose terminals / contactor / supply issue | Check supply voltages, terminals |
| thd_drift | Rising current THD | VFD harmonic filter degrading | Check VFD line reactor |
| overload | Overcurrent | Filters / coil / belt / ambient temp | Check filters, belt, coil |

## Escalation Paths

**When to call on-call engineer (any hour):**
- Any AHU in Critical tier on Level 5 (PICU, ICU, OT), Level 4 (BMT, Maternity OT)
- Critical AHU + patient activity in zone confirmed with Ward Manager
- Multiple AHUs on same level dropping to Critical simultaneously (may indicate chiller or power supply event)

**When to book a work order (next business day):**
- AHU in Maintenance tier (40–59) in ward or support zone
- AHU in Monitor tier with safety flag raised (e.g., PF_CHRONIC_LOW)
- Energy anomaly sustained > 3 days

**When to monitor only:**
- Single AHU in Monitor tier (60–79) without safety flag
- Health score drop on hot day (> 35°C ambient) that recovers in cooler hours

## Data Coverage

WACH health data is stored in a DuckDB database updated hourly by the ETL pipeline. Coverage: from the point of system commissioning onwards. Typical queries can access up to 30 days of hourly data per request.

If an AHU shows no data: the energy meter for that device may be offline or not yet commissioned. This is different from a low health score — no data means WACH is blind to that AHU, not that it is healthy.
```

- [ ] **Step 6.5: Commit batch 3**

```bash
git add backend/data/rag_docs/tnb_tariff_financial_guide.md \
        backend/data/rag_docs/fault_diagnosis_guide.md \
        backend/data/rag_docs/ahu_maintenance_guide.md \
        backend/data/rag_docs/wach_system_guide.md
git commit -m "docs(rag): add TNB financial guide, fault diagnosis, maintenance guide, WACH system guide"
```

---

## Task 7: Ingest Documents and Verify

**Files:** None created — runs ingest pipeline on existing files

- [ ] **Step 7.1: Run ingest**

```bash
cd backend && python -m scripts.ingest_all_docs
```

Expected output (approximate):
```
[ingest_all] Processing ahu_components_overview.md...
[ingest_all] ahu_components_overview.md: 18 chunks
[ingest_all] Processing ahu_electrical_health.md...
[ingest_all] ahu_electrical_health.md: 14 chunks
...
[ingest_all] Done. Total chunks ingested: ~140–180
```

If output shows `WARNING: fewer than 50 chunks` → check that `data/rag_docs/` contains all 11 files (10 new + ahu_directory.md).

- [ ] **Step 7.2: Smoke-test search_docs tool**

```python
# Run from backend/ directory as a quick test
cd backend && python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from tools.health_tools import handle_search_docs

async def test():
    result = await handle_search_docs('TNB power factor penalty formula', k=3)
    print('Documents returned:', len(result['documents']))
    for i, doc in enumerate(result['documents']):
        print(f'--- chunk {i+1} ---')
        print(doc[:200])

asyncio.run(test())
"
```

Expected: 3 document chunks returned, at least one referencing TNB penalty formula, RM figures, or 0.85 threshold.

- [ ] **Step 7.3: Smoke-test persona detection**

```bash
cd backend && python3 -c "
from llm.persona_detector import detect_persona
tests = [
    ('What is the ROI of fixing this AHU? TNB penalty cost?', None, None, 'financial'),
    ('I need to replace the capacitor bank', None, None, 'technician'),
    ('Explain THD drift and phase imbalance interaction', None, None, 'technical'),
    ('Why is the machine not working?', None, None, 'general'),
    ('Tell me the cost', None, 'financial', 'financial'),
]
for msg, hist, stated, expected in tests:
    result = detect_persona(msg, hist, stated)
    status = 'OK' if result == expected else f'FAIL (got {result})'
    print(f'{status}: \"{msg[:50]}\"')
"
```

Expected: all lines print `OK`

- [ ] **Step 7.4: Commit**

```bash
git add -A  # no new tracked files, but chromadb may have updated data files in data/
# Note: data/chroma/ should be in .gitignore — only commit if new docs were added
git status  # confirm only .md files (already committed) or nothing new
git commit -m "feat(rag): ingest 10 domain knowledge documents into ChromaDB" --allow-empty
```

---

## Task 8: Frontend — API Client + Role Selector

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/chat/ChatWindow.tsx`
- Modify: `frontend/src/components/chat/ChatInput.tsx`

- [ ] **Step 8.1: Update sendChatMessage in client.ts**

In `frontend/src/api/client.ts`, replace the `sendChatMessage` function:

```typescript
/**
 * POST /api/chat — Chat widget messaging
 */
export async function sendChatMessage(
  message: string,
  options?: {
    level?: number;
    device?: string | null;
    financial_impact?: number | null;
    history?: Array<{ role: 'user' | 'model'; content: string }>;
    persona?: string | null;
  }
) {
  const { history, persona, ...context } = options ?? {};
  return apiFetch<{ reply: string; navigate?: NavigateTarget | null }>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      context,
      history: history ?? [],
      persona: persona ?? null,
    }),
  });
}
```

- [ ] **Step 8.2: Update ChatInput.tsx with role selector**

Replace the entire content of `frontend/src/components/chat/ChatInput.tsx`:

```tsx
import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

type Persona = 'general' | 'technical' | 'technician' | 'financial' | null;

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onPersonaChange: (persona: Persona) => void;
  selectedPersona: Persona;
}

const PERSONAS: { value: Persona; label: string }[] = [
  { value: 'general', label: 'General' },
  { value: 'technical', label: 'Engineer' },
  { value: 'technician', label: 'Technician' },
  { value: 'financial', label: 'Financial' },
];

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onPersonaChange,
  selectedPersona,
}) => {
  const [input, setInput] = useState('');
  const [showRoles, setShowRoles] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePersonaSelect = (p: Persona) => {
    onPersonaChange(p === selectedPersona ? null : p);
    setShowRoles(false);
  };

  return (
    <div className="bg-[#111820] border-t border-[#1E2A3A]">
      {showRoles && (
        <div className="flex gap-2 px-4 pt-2 pb-1 flex-wrap">
          {PERSONAS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => handlePersonaSelect(value)}
              className={`
                text-xs px-3 py-1 rounded-full border transition-colors
                ${selectedPersona === value
                  ? 'bg-[#00E5A0] text-[#0B0F14] border-[#00E5A0]'
                  : 'bg-transparent text-[#8A95A5] border-[#1E2A3A] hover:border-[#00E5A0] hover:text-[#00E5A0]'}
              `}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 px-4 py-3">
        <button
          onClick={() => setShowRoles((v) => !v)}
          title="Set your role"
          className={`
            w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center transition-colors
            ${selectedPersona
              ? 'bg-[#00E5A0] text-[#0B0F14]'
              : 'text-[#8A95A5] hover:text-[#00E5A0]'}
          `}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
          </svg>
        </button>

        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your AHUs…"
          className="
            flex-1 bg-transparent border-none outline-none
            text-[#E8ECF1] placeholder-[#8A95A5]
            text-sm
          "
        />

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleSend}
          disabled={!input.trim()}
          className="
            w-11 h-11 rounded-full flex-shrink-0
            bg-[#00E5A0] text-[#0B0F14]
            flex items-center justify-center
            disabled:opacity-30 disabled:cursor-not-allowed
          "
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </motion.button>
      </div>
    </div>
  );
};

export default ChatInput;
```

- [ ] **Step 8.3: Update ChatWindow.tsx — add persona state and wire up**

In `frontend/src/components/chat/ChatWindow.tsx`, make the following changes:

Add `persona` state after `isMinimized`:
```tsx
const [selectedPersona, setSelectedPersona] = useState<'general' | 'technical' | 'technician' | 'financial' | null>(null);
```

Update `handleSendMessage` to pass `persona`:
```tsx
const handleSendMessage = async (text: string) => {
  const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
  setMessages((prev) => [...prev, userMsg]);
  setIsTyping(true);

  const history = messages
    .slice(1)
    .map((m) => ({
      role: m.role === 'bot' ? ('model' as const) : ('user' as const),
      content: m.content,
    }));

  try {
    const { reply, navigate } = await sendChatMessage(text, {
      level: selectedLevel ?? undefined,
      device: selectedDevice ?? undefined,
      financial_impact: financialImpact ?? undefined,
      history,
      persona: selectedPersona,
    });
    setMessages((prev) => [
      ...prev,
      { id: (Date.now() + 1).toString(), role: 'bot', content: reply, navigate },
    ]);
  } catch {
    setMessages((prev) => [
      ...prev,
      {
        id: (Date.now() + 1).toString(),
        role: 'bot',
        content: 'Sorry, I had trouble connecting. Please try again in a moment.',
      },
    ]);
  } finally {
    setIsTyping(false);
  }
};
```

Add a persona confirmation bot message when user selects a role. In `handlePersonaChange`:
```tsx
const handlePersonaChange = (persona: 'general' | 'technical' | 'technician' | 'financial' | null) => {
  setSelectedPersona(persona);
  if (persona) {
    const labels: Record<string, string> = {
      general: 'general audience',
      technical: 'an engineering perspective',
      technician: 'a maintenance technician perspective',
      financial: 'a financial perspective',
    };
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'bot',
        content: `Got it — I'll explain things from ${labels[persona]}.`,
      },
    ]);
  }
};
```

Update the `ChatInput` usage in the JSX:
```tsx
<ChatInput
  onSendMessage={handleSendMessage}
  onPersonaChange={handlePersonaChange}
  selectedPersona={selectedPersona}
/>
```

- [ ] **Step 8.4: Build and verify no TypeScript errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: `✓ built in Xs` with no TypeScript errors.

- [ ] **Step 8.5: Commit**

```bash
git add frontend/src/api/client.ts \
        frontend/src/components/chat/ChatInput.tsx \
        frontend/src/components/chat/ChatWindow.tsx
git commit -m "feat(rag): add role selector UI and persona field to chat API"
```

---

## Task 9: Final Verification

- [ ] **Step 9.1: Run full backend test suite**

```bash
cd backend && python -m pytest tests/ -v --ignore=tests/test_csv_reader.py 2>&1 | tail -30
```

Expected: all tests pass. Key tests:
- `test_persona_detector.py`: 11 passed
- `test_tool_registry.py`: 4 passed (including `test_tools_list_has_six_entries`)

- [ ] **Step 9.2: Manual smoke test — persona adaptation**

Start backend:
```bash
cd backend && python -m uvicorn main:app --port 8081 --reload
```

Test financial persona via curl:
```bash
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Why is e0501 important to maintain?", "persona": "financial"}' \
  | python3 -m json.tool | grep -A3 '"reply"'
```

Expected: reply mentions RM figures, TNB penalty, cost of inaction rather than leading with technical electrical terms.

Test technician persona:
```bash
curl -X POST http://localhost:8081/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "e0501 has low power factor, what do I do?", "persona": "technician"}' \
  | python3 -m json.tool | grep -A3 '"reply"'
```

Expected: reply includes step-by-step instructions (check capacitor, measure with clamp meter, etc.)

- [ ] **Step 9.3: Commit final verification note**

```bash
git commit -m "feat(spec-b): RAG knowledge base and persona detection complete" --allow-empty
```

---

## Self-Review

**Spec coverage check:**
- ✅ 10 domain knowledge documents written and ingested
- ✅ Persona detection: auto-detect from keywords + history (persona_detector.py)
- ✅ Persona detection: explicit `/role` command support
- ✅ Persona detection: `stated_persona` from frontend role selector
- ✅ System prompt persona blocks: 4 personas × distinct instruction block
- ✅ Frontend role selector: gear/person icon → 4 pill buttons → persona confirmation message
- ✅ `persona` field in `ChatRequest` and passed through `sendChatMessage`
- ✅ Malaysian hospital standards (JKR 2025, KKM, MS 1525, ASHRAE 170-2025)
- ✅ TNB RP4 tariffs (effective July 2025): MV General RM0.2983/kWh, Capacity+Network RM89.27/kW, AFA mechanism
- ✅ PF penalty formula: tiered 1.5%/3% structure verified against official TNB source
- ✅ Tests: test_persona_detector.py covers all 11 cases

**No placeholders found.** All code steps contain complete, runnable code.
