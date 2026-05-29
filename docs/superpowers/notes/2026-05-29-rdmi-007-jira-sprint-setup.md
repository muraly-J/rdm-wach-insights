# RDMI-007 — Jira + Sprint Setup

**Date:** 2026-05-29
**Ticket:** RDMI-007 (2 pts)
**Owner:** Jinendra Muraly
**Output:** Jira project provisioned, epic created, sprints defined, backlog imported, board configured.
**Source of truth for backlog:** `docs/superpowers/notes/2026-05-25-rdm-insight-jira.csv` (63 rows) + G1–G12 deltas from RDMI-006 threat-model (see §6).

---

## 1. Project

| Field | Value |
|---|---|
| Project name | RDM Insight |
| Project key | **RDMI** |
| Project type | Scrum (team-managed) |
| Default assignee | Jinendra Muraly |
| Issue types | Epic, Task, Sub-task, Bug |
| Workflow | Backlog → To Do → In Progress → In Review → Done |

Create via: Jira → Projects → Create project → Scrum template → name `RDM Insight`, key `RDMI`.

---

## 2. Epic

| Key | Summary | Description |
|---|---|---|
| **RDMI-EPIC-1** | Two-Tenant MVP | Stand up multi-tenant building intelligence platform supporting WACH + Cyberview, with per-tenant dashboard, chat, auth, and isolation. Scope = Plans A/B/C; out-of-scope = MQTT ingest, anomaly, optimization, ML (Phase 2+). Spec: `docs/superpowers/specs/2026-05-25-rdm-insight-platform-design.md`. |

Labels: `mvp`, `rdm-insight`.
Target end: **2026-07-24** (end of Sprint 7).

---

## 3. Sprints

1-week cadence, Mon–Fri. Demo / retro Fri afternoon.

| Sprint | Name | Dates | Goal |
|---|---|---|---|
| Sprint 0 | Planning | May 26 – May 29 | Spec + plan review, threat-model, Jira setup, scope sign-off |
| Sprint 1 | Plan A foundation | **Jun 2 – Jun 5** (4d, post-holiday) | Monorepo, Postgres schema, settings, types package |
| Sprint 2 | Auth + tenancy | **Jun 8 – Jun 12** | JWT, sessions, tenant middleware, RBAC + G1–G12 gating fixes |
| Sprint 3 | Plan A close | **Jun 15 – Jun 19** | `_default` adapter, dashboard routes, frontend shell, CI |
| Sprint 4 | WACH port | **Jun 22 – Jun 26** | `wach` adapter, scoring port, Influx integration |
| Sprint 5 | Chat + dashboard | **Jun 29 – Jul 3** | RAG, chat orchestrator, SSE, `packages/ui` lift, DashboardPage wiring |
| Sprint 6 | Cyberview + admin | **Jul 6 – Jul 10** | Cyberview `_default` config, admin UI, knowledge upload |
| Sprint 7 | E2E + deploy | **Jul 13 – Jul 17** | Playwright E2E, Railway/Vercel deploy, observability stubs, demo prep |

Buffer week **Jul 20 – Jul 24** for slip / hardening / demo dry-run.

Create in Jira: Backlog → Create sprint → set name + start/end dates per row.

---

## 4. Board

**Columns:**

| Column | Maps to status |
|---|---|
| Backlog | Backlog |
| To Do | To Do |
| In Progress | In Progress |
| In Review | In Review |
| Done | Done |

**WIP limits:** In Progress = 3, In Review = 3 (solo dev — keep flow tight).

**Swimlanes:** by Epic (single epic for MVP — effectively one lane).

**Quick filters:** `Sprint 1`, `Sprint 2`, `Blocked`, `Backend`, `Frontend`.

**Card layout:** show Story Points, Labels, Due Date.

---

## 5. Backlog import

Import file: `docs/superpowers/notes/2026-05-25-rdm-insight-jira.csv` (63 rows, RDMI-001..RDMI-063).

**Path:** Jira → Settings → System → External System Import → CSV.

**Field map:**

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

**Pre-import checks:**
- Sprints (§3) exist in Jira before import (Sprint column matches by name).
- Epic `RDMI-EPIC-1` exists before import (Epic Link resolution).
- Project key `RDMI` matches External ID prefix.

**Post-import smoke:**
- Issue count = 63 + 1 epic.
- Spot-check RDMI-009 → Sprint 1, RDMI-044 → Sprint 5, RDMI-063 → Sprint 7.
- Spot-check `Depends On` → RDMI-010 blocked by RDMI-009.
- Verify Story Points sum per sprint (target: 12–18 pts/sprint for solo cadence).

---

## 6. Delta tickets — RDMI-006 threat-model gating fixes

From `2026-05-29-rdmi-006-auth-tenancy-threat-model.md` §6. Create in Jira **after** CSV import. All target **Sprint 2 (Jun 8–12)** since they ride alongside auth implementation (RDMI-016 sessions, RDMI-017 auth routes, RDMI-018 tenant middleware).

| Key | Summary | Pts | Sprint | Depends On | Description |
|---|---|---:|---|---|---|
| RDMI-006a | JWT: add `iss` + `aud` claims | 1 | Sprint 2 | RDMI-015 | Encode `iss="rdm-insight-api"`, `aud="rdm-insight-web"`; verify on decode. Update `test_jwt.py`. |
| RDMI-006b | JWT: `alg:none` regression test | 0.5 | Sprint 2 | RDMI-015 | Add explicit test asserting `decode_access_token` rejects unsigned tokens. |
| RDMI-006c | Refresh cookie: `secure=True` env-driven | 0.5 | Sprint 2 | RDMI-017 | Add `cookie_secure` setting (default `True`, dev override). |
| RDMI-006d | Refresh cookie: `samesite="strict"` | 0.5 | Sprint 2 | RDMI-017 | Tighten from `lax`. |
| RDMI-006e | Atomic `rotate_session` | 1 | Sprint 2 | RDMI-016 | Single transaction for DELETE+INSERT; add `commit=False` flag on `create_session`. |
| RDMI-006f | Refresh-token reuse detection | 2 | Sprint 2 | RDMI-016 | Track replaced-by hash; on reuse of a hash whose row is gone, log + alert. Full session-family revoke optional. Add migration. |
| RDMI-006g | Missing `X-Site-Id` → 403 (not 400) | 0.5 | Sprint 2 | RDMI-018 | Explicit `if site_id is None: raise HTTPException(403)` in tenant middleware. |
| RDMI-006h | Collapse `TenancyError` to single 403 response | 0.5 | Sprint 2 | RDMI-018 | Always return `{"detail":"forbidden"}` to client; keep distinct reasons in server logs. |
| RDMI-006i | Audit-log super-admin cross-org access | 1 | Sprint 2 | RDMI-018 | Append `audit_log` row with `action="super_admin_site_access"` when `is_super_admin=true` and accessed org ≠ user's own org context. |
| RDMI-006j | **Router conformance test** | 2 | Sprint 2 | RDMI-018 | New `tests/integration/test_router_conformance.py` walks `app.routes`, asserts every `/api/*` route declares `tenant_ctx` dep or is on explicit allow-list (`/healthz`, `/auth/*`, `/me/sites`). **CRITICAL — gates merge to main.** |
| RDMI-006k | Chat collection-isolation test (placeholder) | 0.5 | Sprint 2 | RDMI-018 | Create empty `tests/integration/test_chat_isolation.py`; real assertions land in Plan B (link to RDMI-044). |
| RDMI-006l | `X-Site-Id` flip cross-tenant test | 0.5 | Sprint 2 | RDMI-019 | Viewer-A sends `X-Site-Id: site-B` → must 403, not 500 or silent fallback. |

**Total added:** 10.5 pts to Sprint 2. Original Sprint 2 load (RDMI-015..023) ≈ 18 pts. Combined ≈ 28.5 pts — **over budget**.

**Mitigation:** move RDMI-022 (operator override endpoint) and RDMI-023 (audit-log writer) to Sprint 3 — they depend on tenant middleware but aren't on the demo path. Sprint 2 net ≈ 22 pts, tight but achievable since G fixes are mostly tiny.

---

## 7. Conventions

**Branch naming** (per CLAUDE.md): `feature/RDMI-NNN-short-desc`, `fix/RDMI-NNN-…`, etc. Issue key in branch unlocks Jira auto-linking.

**Commit format:** `<type>(scope): <RDMI-NNN> <desc>` e.g. `feat(auth): RDMI-016 add refresh-token rotation`.

**PR template:** include `Closes RDMI-NNN`; CI gate (`turbo lint test typecheck`) + router-conformance (post-RDMI-006j) before merge.

**Definition of Done:**
- Code + tests merged to `main`.
- CI green.
- Plan checkbox ticked in `docs/superpowers/plans/`.
- Ticket moved to Done in Jira.

---

## 8. Setup checklist

**Prep deliverables — DONE 2026-05-29** (see `2026-05-29-rdm-insight-jira-import.csv` + `2026-05-29-rdmi-jira-manual-input.md`):
- [x] Build import CSV: epic + 63 base tickets + 12 G-fix tickets (RDMI-006a..006l now in CSV, no longer manual).
- [x] Remap G-fix dependencies to real CSV keys (§6 doc numbering was stale).
- [x] Write manual-input guide (project, epic, sprints, board, import, spot-check steps).
- [x] Draft stakeholder sprint-plan summary for RDMI-008.

**Live Jira actions — human (per manual-input guide §B):**
- [ ] Create Jira project `RDMI` (§1 / B1).
- [ ] Create epic `RDMI-EPIC-1: Two-Tenant MVP` (§2 / B2).
- [ ] Create Sprints 0–7 with dates from §3 (B3).
- [ ] Configure board columns + WIP + quick filters (§4 / B4).
- [ ] CSV import 76 rows (§5 / B5).
- [ ] Spot-check post-import (§5 / B6).
- [ ] Send sprint plan link to stakeholders for RDMI-008 sign-off this afternoon.

**Open decision — NOT applied:**
- [ ] Sprint 2 over budget (~28.5 pts). §6 mitigation "move RDMI-022, RDMI-023 to Sprint 3" does NOT apply — those keys = tenant middleware + SiteAdapter here (RDMI-022 is a dep for 4 G-fixes). Needs a real rebalance call.

---

## 9. Risks

- **Solo-dev velocity unknown.** 18 pts/sprint is a guess. Re-baseline after Sprint 1 actuals.
- **No buffer in Sprint 2** after adding G fixes. If reuse-detection (RDMI-006f) blows up scope, downgrade to "log-only" and defer family-revoke to Phase 2.
- **Jun 2 holiday** in Sprint 1 — already accounted (4-day sprint, lower point target).
- **Dependencies in CSV** are best-effort; tighten as plans execute and real blockers surface.

---

## 10. Next

RDMI-008 (3 pts, this afternoon): MVP scope sign-off with stakeholders + Phase 2+ roadmap walkthrough. Bring this doc, the threat-model doc, and the platform spec.
