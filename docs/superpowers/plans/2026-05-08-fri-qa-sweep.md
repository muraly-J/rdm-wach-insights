# Fri QA Sweep #2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Light QA sweep across backend/frontend — lint, types, tests, deps, docs drift, dead code — producing prioritized backlog at `docs/audits/2026-05-04-qa-sweep.md` for following Monday triage.

**Architecture:** Sequential investigation tasks. Each task time-boxed ~2h, runs tooling, appends a section to the audit doc with findings + severity (blocker / soon / backlog). In-week fixes ONLY for blockers; everything else logged for Monday.

**Tech Stack:** ruff, mypy, tsc, eslint (if present), pytest, jest, pip, npm.

---

## File Structure

- Create: `docs/audits/2026-05-04-qa-sweep.md` — single audit output, one H2 per area.
- Modify: only when fixing in-week blockers (case-by-case, separate commits per fix).

Severity tags used in the audit doc:
- `[BLOCKER]` — fix this week (broken build, failing test on main, security-critical CVE)
- `[SOON]` — fix next sprint
- `[BACKLOG]` — Monday triage

---

### Task 1: Scaffold the audit doc

**Files:**
- Create: `docs/audits/2026-05-04-qa-sweep.md`

- [ ] **Step 1: Create audit doc with section skeleton**

```markdown
# QA Sweep #2 — 2026-05-04

**Date run:** 2026-05-08 (Fri)
**Author:** <fill>
**Branch / commit:** `<git rev-parse --short HEAD>`

Severity legend: `[BLOCKER]` fix in-week · `[SOON]` next sprint · `[BACKLOG]` Monday triage.

## 1. Lint / Format / Types
## 2. Tests & Coverage
## 3. Dependencies
## 4. Docs Drift
## 5. Dead Code
## 6. Summary & Monday Backlog
```

- [ ] **Step 2: Capture current commit**

Run: `git rev-parse --short HEAD`
Paste into header.

- [ ] **Step 3: Commit**

```bash
git add docs/audits/2026-05-04-qa-sweep.md
git commit -m "docs(audit): scaffold 2026-05-04 QA sweep #2"
```

---

### Task 2: Lint / format / types (~2h)

**Files:**
- Modify: `docs/audits/2026-05-04-qa-sweep.md` (section 1)

- [ ] **Step 1: Backend ruff**

Run: `cd backend && ruff check . 2>&1 | tee /tmp/ruff.txt; ruff check . --statistics`
Log: total issues, top 5 rules by count.

- [ ] **Step 2: Backend ruff format check**

Run: `cd backend && ruff format --check . 2>&1 | tee /tmp/ruff-fmt.txt`
Log: file count needing format.

- [ ] **Step 3: Backend mypy (best-effort)**

Run: `cd backend && mypy . --ignore-missing-imports --no-error-summary 2>&1 | tail -50; mypy . --ignore-missing-imports 2>&1 | grep -c "^.*error:"`
Note: no project mypy config exists. Run loose, log error count + 5 representative errors. Do NOT add a config in-week.

- [ ] **Step 4: Frontend tsc**

Run: `cd frontend && npx tsc --noEmit 2>&1 | tee /tmp/tsc.txt; echo "errors: $(grep -c 'error TS' /tmp/tsc.txt)"`
Log: error count + first 10 errors.

- [ ] **Step 5: Frontend lint**

Run: `cd frontend && (npx eslint 'src/**/*.{ts,tsx}' 2>&1 || true) | tee /tmp/eslint.txt`
Note: no `lint` script defined in `package.json`. Log eslint result OR record absence as `[BACKLOG] add lint script + eslint config`.

- [ ] **Step 6: Write findings into section 1**

For each tool: counts, top offenders (file paths), severity. Auto-fixable issues (`ruff check --fix`, `ruff format`) → tag `[SOON]` unless they break build → `[BLOCKER]`.

- [ ] **Step 7: Fix blockers only**

If any tool produces a *build-breaking* error (e.g., tsc errors that prevent `vite build`), fix in a separate commit. Otherwise log and move on.

- [ ] **Step 8: Commit**

```bash
git add docs/audits/2026-05-04-qa-sweep.md
git commit -m "docs(audit): QA sweep #2 — lint/types findings"
```

---

### Task 3: Tests & coverage (~2h)

**Files:**
- Modify: `docs/audits/2026-05-04-qa-sweep.md` (section 2)

- [ ] **Step 1: Backend tests + coverage**

Run: `cd backend && python -m pytest tests/ -v --cov=. --cov-report=term-missing 2>&1 | tee /tmp/pytest.txt; tail -40 /tmp/pytest.txt`
Log: pass/fail counts, total coverage %, modules <60% coverage.

- [ ] **Step 2: Highlight target-module coverage**

Grep `/tmp/pytest.txt` coverage table for these modules and record coverage %:
- `core/` (scoring, risk_engine)
- `routes/` (ticket router or whatever handles ticketing)
- `rag/`

Run: `grep -E '(core/|routes/|rag/)' /tmp/pytest.txt | grep -E '[0-9]+%'`

- [ ] **Step 3: Frontend tests + coverage**

Run: `cd frontend && npm test -- --coverage --watchAll=false 2>&1 | tee /tmp/jest.txt; tail -30 /tmp/jest.txt`
Log: pass/fail, statements/branches/functions/lines %.

- [ ] **Step 4: Write section 2**

Table per stack: tests run, passing, failing, coverage. Failing tests on main → `[BLOCKER]`. Coverage gaps on scoring / ticket router / RAG → `[BACKLOG]` with target % suggestion.

- [ ] **Step 5: Fix blockers only**

If any test fails on main, fix or revert offending commit. Separate commit.

- [ ] **Step 6: Commit**

```bash
git add docs/audits/2026-05-04-qa-sweep.md
git commit -m "docs(audit): QA sweep #2 — test/coverage findings"
```

---

### Task 4: Dependencies (~1h, security-critical only)

**Files:**
- Modify: `docs/audits/2026-05-04-qa-sweep.md` (section 3)

- [ ] **Step 1: Python outdated**

Run: `cd backend && pip list --outdated --format=columns 2>&1 | tee /tmp/pip-outdated.txt`
Log: count + list of major-version-behind packages only.

- [ ] **Step 2: Python audit (if available)**

Run: `cd backend && (pip-audit 2>&1 || pip install pip-audit && pip-audit 2>&1) | tee /tmp/pip-audit.txt | tail -50`
Log: any HIGH/CRITICAL CVEs.

- [ ] **Step 3: npm outdated**

Run: `cd frontend && npm outdated 2>&1 | tee /tmp/npm-outdated.txt; echo "exit=$?"`
Log: major-version-behind packages.

- [ ] **Step 4: npm audit**

Run: `cd frontend && npm audit --omit=dev 2>&1 | tee /tmp/npm-audit.txt; tail -20 /tmp/npm-audit.txt`
Log: high/critical only.

- [ ] **Step 5: Write section 3**

ONLY log:
- HIGH/CRITICAL CVEs → `[BLOCKER]` if reachable, `[SOON]` if dev-only
- Majors >2 versions behind → `[BACKLOG]`
Skip patch/minor noise.

- [ ] **Step 6: Patch CRITICAL CVEs in-week**

Only if a one-line bump fixes it AND tests still pass. Otherwise log.

- [ ] **Step 7: Commit**

```bash
git add docs/audits/2026-05-04-qa-sweep.md
git commit -m "docs(audit): QA sweep #2 — dependency findings"
```

---

### Task 5: Docs drift (~1h)

**Files:**
- Modify: `docs/audits/2026-05-04-qa-sweep.md` (section 4)

- [ ] **Step 1: Verify endpoints in API.md vs registered routes**

Run: `grep -E "include_router|@router\.(get|post|put|delete)" backend/main.py backend/routes/*.py | sort > /tmp/routes-actual.txt; grep -E "^(GET|POST|PUT|DELETE) " API.md | sort > /tmp/routes-doc.txt; diff /tmp/routes-doc.txt /tmp/routes-actual.txt | head -60`
Log: endpoints in code but not in API.md, and vice versa.

- [ ] **Step 2: Verify AHU level counts in CLAUDE.md and CONSTITUTION.md**

Run: `grep -A2 "AHU_LEVEL_CONFIG" backend/models/schemas.py | head -40; grep -E "L[0-9]+:" CLAUDE.md docs/CONSTITUTION.md`
Compare counts (CLAUDE.md says L1:21 L2:15 L3:16 L4:13 L5:12 L6:11 L7:4 L8:5 L9:8 L10:8 L11:8). Log mismatches.

- [ ] **Step 3: Verify ports**

Run: `grep -rE "(8081|3000|localhost)" CLAUDE.md docs/CONSTITUTION.md API.md README.md 2>/dev/null | head -20; grep -E "port|PORT" backend/config.py backend/main.py | head -10`
Log mismatches.

- [ ] **Step 4: Verify score convention is 0–100**

Run: `grep -rnE "(0-100|0–100|0..100|score.*100|/100)" docs/CONSTITUTION.md CLAUDE.md API.md backend/core/ | head -30`
Look for any lingering 0–10 or 0–1 references in docs. Log them.

- [ ] **Step 5: Write section 4**

Each drift item: what doc, what's wrong, correct value. Severity: `[SOON]` for doc-only fixes; `[BLOCKER]` only if drift is actively misleading new contributors (e.g., wrong port in setup instructions).

- [ ] **Step 6: Fix obvious one-liners in-week**

Pure typo / number drift in CLAUDE.md / API.md / CONSTITUTION.md — fix directly. Anything requiring rewrites → backlog.

- [ ] **Step 7: Commit**

```bash
git add docs/audits/2026-05-04-qa-sweep.md CLAUDE.md API.md docs/CONSTITUTION.md 2>/dev/null
git commit -m "docs(audit): QA sweep #2 — docs drift + trivial fixes"
```

---

### Task 6: Dead code (~1h)

**Files:**
- Modify: `docs/audits/2026-05-04-qa-sweep.md` (section 5)

- [ ] **Step 1: Frontend unused exports**

Run: `cd frontend && npx ts-prune 2>&1 | tee /tmp/ts-prune.txt | head -80; wc -l /tmp/ts-prune.txt`
(If `ts-prune` not installed, run via `npx --yes ts-prune`.) Log count + first 20 candidates.

- [ ] **Step 2: Backend unused imports / vars**

Run: `cd backend && ruff check --select F401,F841 . 2>&1 | tee /tmp/ruff-dead.txt | head -60`
Log count.

- [ ] **Step 3: Stale debug scripts**

Run: `ls -la scripts/debug/ 2>/dev/null; for f in scripts/debug/*; do echo "== $f =="; git log -1 --format="%cs %s" -- "$f"; done`
Log scripts not touched in >90 days.

- [ ] **Step 4: Orphan routes**

Run: `for f in backend/routes/*.py; do mod=$(basename "$f" .py); grep -q "$mod" backend/main.py || echo "ORPHAN: $f"; done`
Log routes not registered in `main.py`.

- [ ] **Step 5: Write section 5**

All dead-code findings → `[BACKLOG]` (deletions need review). Exception: orphan route files → `[SOON]` (confusing).

- [ ] **Step 6: Commit**

```bash
git add docs/audits/2026-05-04-qa-sweep.md
git commit -m "docs(audit): QA sweep #2 — dead code findings"
```

---

### Task 7: Summary & Monday backlog

**Files:**
- Modify: `docs/audits/2026-05-04-qa-sweep.md` (section 6)

- [ ] **Step 1: Write summary**

In section 6:
- Counts by severity across all sections (X blockers, Y soon, Z backlog)
- List of in-week fixes already committed (with commit SHAs — `git log --oneline | head -10`)
- Top 5 backlog items recommended for Monday triage, ranked by impact/effort

- [ ] **Step 2: Sanity check**

Run: `grep -c "BLOCKER\|SOON\|BACKLOG" docs/audits/2026-05-04-qa-sweep.md`
Confirm every finding has a severity tag.

- [ ] **Step 3: Commit**

```bash
git add docs/audits/2026-05-04-qa-sweep.md
git commit -m "docs(audit): QA sweep #2 — summary + Monday backlog"
```

- [ ] **Step 4: Push branch / open PR (optional)**

If user requests PR, push and open. Otherwise leave on local branch.

---

## Self-Review Notes

- Output file path matches user spec (`docs/audits/2026-05-04-qa-sweep.md`).
- Each area time-boxed; tasks 2–6 ≈ 2h, task 4 ≈ 1h (security-critical only per spec).
- Plan adapts to repo reality: no `lint` script in `frontend/package.json` → step records absence; no mypy config → run loose with `--ignore-missing-imports`.
- In-week fix policy explicit: blockers only.
- Severity tags consistent across all tasks.
