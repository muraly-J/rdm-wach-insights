# RDMI — Jira Manual Input + Stakeholder Sprint-Plan Summary

**Date:** 2026-05-29
**For:** RDMI-007 (Jira setup) execution + RDMI-008 (scope sign-off) stakeholder send
**Companion files:**
- Import CSV: `docs/superpowers/notes/2026-05-29-rdm-insight-jira-import.csv` (76 rows: 1 epic + 63 base + 12 G-fix)
- Setup spec: `docs/superpowers/notes/2026-05-29-rdmi-007-jira-sprint-setup.md`
- Threat model: `docs/superpowers/notes/2026-05-29-rdmi-006-auth-tenancy-threat-model.md`

---

## Part A — Scope-Decision Brief (RDMI-008 meeting)

RDMI-008 is an **internal scope-decision meeting** — lock what goes in the MVP we eventually show clients, then build off it. Not an external send.

**Project:** RDM Insight — two-tenant building-intelligence platform (WACH + Cyberview).
**Timeline (P1 build):** 7 one-week sprints, **Jun 2 → Jul 17**, buffer week Jul 20–24. Target demo Jul 17.

### Phasing
- **Phase 1 — MVP base (what we build now):**
  - Dashboard: **high-level** KPIs + **low-level** deep-dive (multi-variable plotting).
  - Chatbot: queries the **respective site's DB**, answers both high-level and low-level questions.
  - Delivered across Plans A (foundation + auth/tenancy), B (WACH port + chat), C (Cyberview + admin + deploy).
- **Phase 2 — energy optimization algorithms.** Only feasible where data is collected.
- **Phase 3 — ML forecasting for predictive maintenance.**

**Phase 2 + 3 are WACH-only for now** — both need historical data, and Cyberview history isn't obtainable yet. Cyberview stays Phase-1-only until that changes.

**Client sequencing:** first client meeting is **WACH** (the deeper phases only work there today).

| Sprint | Dates | Goal | Pts |
|---|---|---|---|
| 1 — Plan A foundation | Jun 2–5 (4d, post-holiday) | Monorepo, Postgres schema, types | ~13 |
| 2 — Auth + tenancy | Jun 8–12 | JWT, sessions, tenant middleware, RBAC + 12 threat-model fixes | ~28.5 ⚠ |
| 3 — Plan A close | Jun 15–19 | `_default` adapter, dashboard routes, frontend shell, CI | ~18 |
| 4 — WACH port | Jun 22–26 | `wach` adapter, scoring port, Influx | ~20 |
| 5 — Chat + dashboard | Jun 29–Jul 3 | RAG, chat orchestrator/SSE, UI lift, DashboardPage | ~21 |
| 6 — Cyberview + admin | Jul 6–10 | Cyberview config, admin UI, knowledge upload | ~23 |
| 7 — E2E + deploy | Jul 13–17 | Playwright E2E, Railway/Vercel deploy, demo prep | ~16 |

**Security posture (from RDMI-006 threat model):** GO on app-layer tenant isolation for MVP (no Postgres RLS — engine-layer isolation via per-site Influx bucket + Chroma collection is structural). Conditional on 12 gating fixes (G1–G12) landing in Sprint 2; G10 router-conformance test gates merge to main.

**Decision needed at sign-off:**
1. **Lock MVP scope** — confirm Phase 1 (dashboard + chatbot, Plans A/B/C) in; Phase 2 (energy optimization) + Phase 3 (ML predictive maintenance) deferred, WACH-only when they land.
2. **Sprint 2 overload (~28.5 pts).** The 12 threat-model fixes add 10.5 pts on top of ~18 pts auth work. Need a rebalance call: defer which Sprint-2 tickets to Sprint 3? (Candidates that aren't on the demo path — TBD, no clean operator-override/audit-writer ticket exists in current backlog.)
3. **Solo-dev velocity is a guess.** Re-baseline after Sprint 1 actuals.

---

## Part B — Manual Jira Input (CSV can't do these)

Do **in this order** — sprints + epic must exist before the CSV import resolves.

### B1. Create project
- Projects → Create project → **Scrum** template (team-managed)
- Name: `RDM Insight`  |  Key: `RDMI`
- Default assignee: Jinendra Muraly
- Issue types: Epic, Task, Sub-task, Bug
- Workflow: Backlog → To Do → In Progress → In Review → Done

### B2. Create epic
- `RDMI-EPIC-1` — **Two-Tenant MVP**
- Labels: `mvp`, `rdm-insight`  |  Target end: 2026-07-24
- (Also a row in the CSV; create here first so Epic Link resolves on import.)

### B3. Create sprints (Backlog → Create sprint, set name + dates)
Names must match the CSV `Sprint` column **exactly**:

| Name | Start | End |
|---|---|---|
| Sprint 0 - Planning | May 26 | May 29 |
| Sprint 1 - Plan A foundation | Jun 2 | Jun 5 |
| Sprint 2 - Auth + tenancy | Jun 8 | Jun 12 |
| Sprint 3 - Plan A close | Jun 15 | Jun 19 |
| Sprint 4 - WACH port | Jun 22 | Jun 26 |
| Sprint 5 - Chat + dashboard | Jun 29 | Jul 3 |
| Sprint 6 - Cyberview + admin | Jul 6 | Jul 10 |
| Sprint 7 - E2E + deploy | Jul 13 | Jul 17 |

### B4. Configure board
- Columns: Backlog, To Do, In Progress, In Review, Done
- WIP limits: In Progress = 3, In Review = 3
- Swimlanes: by Epic
- Quick filters: `Sprint 1`, `Sprint 2`, `Blocked`, `Backend`, `Frontend`
- Card layout: show Story Points, Labels, Due Date

### B5. CSV import
- Path: Jira → Settings → System → External System Import → CSV
- File: `2026-05-29-rdm-insight-jira-import.csv`
- Field map:

| CSV column | Jira field |
|---|---|
| External ID | Issue Key (preserve) |
| Summary | Summary |
| Issue Type | Issue Type |
| Story Points | Story Points |
| Due Date | Due Date |
| Sprint | Sprint |
| Epic Link | Epic Link → `RDMI-EPIC-1` |
| Depends On | Linked Issues → `is blocked by` |
| Labels | Labels (semicolon-split) |
| Description | Description |

### B6. Post-import spot-check
- [ ] Issue count = **76** (1 epic + 75 tasks)
- [ ] RDMI-009 → Sprint 1  |  RDMI-044 → Sprint 5  |  RDMI-063 → Sprint 7
- [ ] RDMI-010 `is blocked by` RDMI-009
- [ ] RDMI-006a..006l all in Sprint 2, labeled `threat-model`
- [ ] Story-point sum per sprint matches Part A table

### B7. Open items (need a human decision — NOT done by import)
- [ ] **Sprint 2 rebalance** (~28.5 pts > ~22 target). Pick tickets to slip to Sprint 3.
- [ ] Verify G-fix dependency remap (006c/006d→RDMI-020 auth routes; 006g/j/k/l→RDMI-022 tenant middleware) — inferred from semantics, not the threat-model doc's literal (stale) numbering.
- [ ] Send Part A summary to stakeholders for RDMI-008 sign-off.
