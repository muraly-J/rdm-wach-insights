# Mon — Scoring Standardization Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an authoritative matrix of every score producer/consumer in WACH Insight, plus a ranked fix list to bring all scoring to the canonical convention **0–100, high = good** at the API boundary.

**Architecture:** Audit-only task. No production code changes. Pure read-only sweep of backend producers, ETL writers, API responders, and frontend renderers. Output is a single markdown matrix file consumed by Tuesday's fix work.

**Tech Stack:** Python 3.11 (FastAPI backend), TypeScript/React (frontend), grep/ripgrep, manual code reading. No tests written today (audit, not implementation).

**Canonical convention to enforce going forward:**
- Scale: **0–100** (integer or 1-decimal float)
- Direction: **high = good** (100 = healthy, 0 = critical)
- Conversion site: **ETL ingest only** — no scale/direction math in routes or frontend

---

## File Structure

**Created today (audit deliverable):**
- `docs/audits/2026-05-04-scoring-audit.md` — matrix + canonical convention + ranked fix list

**Read-only references (do NOT edit today):**
- `backend/core/fair_health_scoring.py`
- `backend/core/healthdb.py`
- `backend/core/risk_engine.py`
- `backend/routes/health_scores.py`
- `backend/routes/dashboard.py`
- `scripts/etl/**`
- `scripts/generate/**`
- `frontend/src/components/dashboard/HealthIndexChart.tsx`
- `frontend/src/components/dashboard/ScoreCard.tsx` (locate exact path during Task 2)
- `frontend/src/components/dashboard/CombinedScoresChart.tsx`
- `frontend/src/components/dashboard/derivation/*`

---

### Task 1: Scaffold the audit document

**Files:**
- Create: `docs/audits/2026-05-04-scoring-audit.md`

- [ ] **Step 1: Create directory if missing**

```bash
mkdir -p docs/audits
```

- [ ] **Step 2: Write skeleton file**

Write this exact content to `docs/audits/2026-05-04-scoring-audit.md`:

```markdown
# Scoring Standardization Audit — 2026-05-04

## Canonical Convention

- **Scale:** 0–100
- **Direction:** high = good (100 = healthy, 0 = critical)
- **Conversion site:** ETL ingest only — routes and frontend pass through unchanged

## Producer Matrix

| File | Symbol (function/class) | Score(s) emitted | Scale | Direction | Notes |
|------|-------------------------|------------------|-------|-----------|-------|

## ETL Matrix

| File | Symbol | Reads from | Writes to | Scale at write | Direction at write | Notes |
|------|--------|------------|-----------|----------------|--------------------|-------|

## API Matrix

| Route | Handler | Field name(s) | Scale at response | Direction at response | Notes |
|-------|---------|---------------|-------------------|-----------------------|-------|

## Frontend Matrix

| File | Component | Field consumed | Expected scale | Expected direction | Math done in component? | Notes |
|------|-----------|----------------|----------------|--------------------|-------------------------|-------|

## Mismatches

(Filled during Task 6.)

## Ranked Fix List

(Filled during Task 7.)
```

- [ ] **Step 3: Commit scaffold**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs: scaffold scoring standardization audit"
```

---

### Task 2: Locate frontend score-rendering components

**Files:**
- Modify: `docs/audits/2026-05-04-scoring-audit.md` (Frontend Matrix section)

- [ ] **Step 1: Find ScoreCard exact path**

Run:
```bash
fd -t f 'ScoreCard' frontend/src
```
Expected: at least one `.tsx` file. Record the path.

- [ ] **Step 2: List all derivation components**

Run:
```bash
ls frontend/src/components/dashboard/derivation/
```
Expected: list of `.tsx` files. Record each.

- [ ] **Step 3: Find any other component that consumes a score field**

Run:
```bash
rg -l --type ts --type tsx 'health[_-]?index|fairScore|score' frontend/src/components/
```
Expected: list of files. Cross-reference against components already in scope; add new ones to a working list.

- [ ] **Step 4: Append the discovered file list to the audit doc as comments under Frontend Matrix**

Add a `<!-- Files in scope: ... -->` HTML comment listing every frontend file you'll inspect. Don't fill rows yet.

- [ ] **Step 5: Commit**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs(audit): record frontend files in scope for scoring audit"
```

---

### Task 3: Fill Producer Matrix (backend score generation)

**Files:**
- Read: `backend/core/fair_health_scoring.py`, `backend/core/healthdb.py`, `backend/core/risk_engine.py`
- Modify: `docs/audits/2026-05-04-scoring-audit.md` (Producer Matrix section)

- [ ] **Step 1: Read `backend/core/fair_health_scoring.py` end-to-end**

Read the entire file. For every function/class that returns a score, note:
- Symbol name
- Which score(s) it emits (F, A, I, R, health_index, other)
- Return scale (inspect literals, clamps, multipliers — `* 100`, `min(1.0, ...)`, etc.)
- Return direction (look for inversions like `1 - x`, `100 - score`)

- [ ] **Step 2: Read `backend/core/healthdb.py` for score persistence/derivation**

Look for any function that computes or transforms a score before storage. Record same fields.

- [ ] **Step 3: Read `backend/core/risk_engine.py`**

Same approach. Note any risk→score conversion.

- [ ] **Step 4: Append a row to Producer Matrix per symbol**

Example row:
```markdown
| backend/core/fair_health_scoring.py | calculate_fairness | fairness | 0–1 | high=good | clamps via min(1.0, max(0.0, x)) |
```
Use `?` in any cell where the answer is unclear after reading; flag it in Notes.

- [ ] **Step 5: Commit**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs(audit): fill producer matrix from backend/core score modules"
```

---

### Task 4: Fill ETL Matrix (scripts that write scores)

**Files:**
- Read: `scripts/etl/**/*.py`, `scripts/generate/**/*.py`
- Modify: `docs/audits/2026-05-04-scoring-audit.md` (ETL Matrix section)

- [ ] **Step 1: Enumerate ETL files that touch scores**

Run:
```bash
rg -l 'fair|health_index|score' scripts/etl scripts/generate
```
Expected: list of Python files. Record.

- [ ] **Step 2: For each file, read score-writing block**

Identify the call site that writes to InfluxDB or HealthDB. Record:
- Source field (raw input)
- Destination field (stored name)
- Scale at write (e.g. `score * 100` → 0–100, or raw `score` → 0–1)
- Direction at write (any `1 - x` or `invert` flag?)

- [ ] **Step 3: Append a row per write site to ETL Matrix**

Example:
```markdown
| scripts/etl/run_health_etl.py | _write_fair_scores | calculate_fairness() output | InfluxDB measurement `fair_score` field `f` | 0–1 | high=good (post commit 0dbb31c inversion) | |
```

- [ ] **Step 4: Commit**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs(audit): fill ETL matrix for score write sites"
```

---

### Task 5: Fill API Matrix and Frontend Matrix

**Files:**
- Read: `backend/routes/health_scores.py`, `backend/routes/dashboard.py`, every frontend file recorded in Task 2
- Modify: `docs/audits/2026-05-04-scoring-audit.md` (API Matrix + Frontend Matrix sections)

- [ ] **Step 1: Read `backend/routes/health_scores.py` and `backend/routes/dashboard.py`**

For each route handler that returns score-bearing JSON, record:
- Route path
- Response field name(s) carrying scores
- Scale at response (does the handler multiply, clamp, invert?)
- Direction at response

Append rows to API Matrix.

- [ ] **Step 2: For each frontend file in scope, read the score-rendering JSX**

For every component that displays a score, record:
- Component name
- Field consumed (from API)
- Expected scale (look for `* 100`, `.toFixed`, axis domain, `max={100}`)
- Expected direction (look for color thresholds — `score < 30 ? 'red' : ...` implies high=good)
- Whether the component does scale/direction math itself (any `1 - score`, `100 - score`, `score * 100`)

Append rows to Frontend Matrix.

- [ ] **Step 3: Commit**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs(audit): fill API and frontend matrices for score consumers"
```

---

### Task 6: Cross-reference matrices and list mismatches

**Files:**
- Modify: `docs/audits/2026-05-04-scoring-audit.md` (Mismatches section)

- [ ] **Step 1: Walk each producer→ETL→API→frontend chain**

Group rows by score (fairness, F, A, I, R, health_index, etc.). For each chain, check:
- Same scale at every hop?
- Same direction at every hop?
- Frontend doing math the API should own?
- Two consumers expecting different scales for the same field?

- [ ] **Step 2: Record each mismatch as a numbered entry**

Format:
```markdown
### Mismatch 1 — Health index scale drift
- Where: `backend/routes/health_scores.py` returns `health_index` on 0–1; `frontend/src/components/dashboard/HealthIndexChart.tsx` multiplies by 100 in render
- Convention violation: math at consumer instead of API boundary
- Severity: medium (display correct, but two source-of-truth scales)
```

Severity scale: **high** (wrong number shown), **medium** (correct display, convention violated), **low** (cosmetic / naming).

- [ ] **Step 3: Commit**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs(audit): catalog scoring scale and direction mismatches"
```

---

### Task 7: Produce ranked fix list

**Files:**
- Modify: `docs/audits/2026-05-04-scoring-audit.md` (Ranked Fix List section)

- [ ] **Step 1: Sort mismatches**

Sort by severity (high → low). Within same severity, sort by blast radius (number of consumers affected, descending).

- [ ] **Step 2: For each mismatch, write a fix entry**

Format:
```markdown
1. **[HIGH] Normalize `/api/health-scores` `health_index` to 0–100**
   - File: `backend/routes/health_scores.py:<line>`
   - Change: multiply by 100 before serializing; remove the `* 100` in `HealthIndexChart.tsx`
   - Tests to update: `backend/tests/test_health_scores.py`
   - Estimated effort: 30 min
   - Blocks: HealthIndexChart, CombinedScoresChart, ScoreCard
```

Include estimated effort (15 min / 30 min / 1 h / half-day) and blockers list per item. This list is consumed Tuesday morning.

- [ ] **Step 3: Add a "Tuesday AM batch" header before the top items the engineer should land first**

Mark the cutoff between "Tuesday AM (must-fix to unblock metric inventory)" and "Tuesday PM or later".

- [ ] **Step 4: Commit**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs(audit): rank scoring fixes for Tuesday AM batch"
```

---

### Task 8: Final pass and verification

**Files:**
- Modify (only if gaps found): `docs/audits/2026-05-04-scoring-audit.md`

- [ ] **Step 1: Re-read the audit doc top to bottom**

Check:
- Every matrix has rows (no empty tables)
- No `?` cells without a Notes explanation
- Every Mismatch has a corresponding Fix List entry (or an explicit "deferred — not blocking" note)
- Canonical convention block at top matches every fix entry direction

- [ ] **Step 2: Cross-check producer count vs ETL count**

Run:
```bash
rg -c 'def ' backend/core/fair_health_scoring.py backend/core/healthdb.py backend/core/risk_engine.py
```
Compare with Producer Matrix row count. If a function emits a score but isn't in the matrix, add it.

- [ ] **Step 3: Verify no production code changed today**

Run:
```bash
git log --since="2026-05-04 00:00" --name-only | grep -vE 'docs/audits|^$|^commit |^Author|^Date|^ '
```
Expected: empty (only audit doc commits today).

- [ ] **Step 4: Final commit if any gaps were filled**

```bash
git add docs/audits/2026-05-04-scoring-audit.md
git commit -m "docs(audit): close gaps from final-pass review"
```

If no changes needed, skip this step.

---

## Verification (end of Mon)

- [ ] `docs/audits/2026-05-04-scoring-audit.md` exists and committed.
- [ ] Producer Matrix has ≥1 row per score-emitting function found in the three core modules.
- [ ] ETL Matrix has ≥1 row per file returned by `rg -l 'fair|health_index|score' scripts/etl scripts/generate`.
- [ ] API Matrix covers every route in `backend/routes/health_scores.py` and `backend/routes/dashboard.py` that returns a score field.
- [ ] Frontend Matrix covers `HealthIndexChart`, `ScoreCard`, `CombinedScoresChart`, and every file under `components/dashboard/derivation/`.
- [ ] Mismatches section is non-empty OR includes an explicit "no mismatches found" note with reasoning.
- [ ] Ranked Fix List has a clear "Tuesday AM batch" cutoff.
- [ ] Zero production code (backend/, frontend/, scripts/) was modified today.

---

## Out of Scope Today

- Applying fixes (Tuesday AM).
- Touching tests (Tuesday).
- Metric inventory of 46 power-meter fields (Tuesday PM).
- Frontend grey-state work (Thursday).
