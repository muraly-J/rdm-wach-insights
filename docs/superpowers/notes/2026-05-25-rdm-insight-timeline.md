# RDM Insight — Revised Timeline (May 26 → Jul 17 2026)

## Week 0 — Planning & Alignment (Tue May 26, Thu May 28, Fri May 29)

| Date | Ticket | Title | Pts | Notes |
|------|--------|-------|-----|-------|
| Tue May 26 | RDMI-001 | Spec walkthrough with stakeholders | 3 | Walk through `2026-05-25-rdm-insight-platform-design.md`. Capture pushback on scope, MVP definition, tenancy model. |
| Tue May 26 | RDMI-002 | Plans A/B/C engineering review | 3 | Walk through each plan, validate task granularity, identify missing tasks, confirm async cascade + N+1 + scoring-guard fixes are clear. |
| Thu May 28 | RDMI-003 | WACH source audit — what ports cleanly | 4 | Walk `$WACH/backend/{core,rag,llm,models,routes}`. List files that lift verbatim, files that need an interface seam, files to leave behind. Output: portability matrix in `docs/superpowers/notes/2026-05-28-wach-port-audit.md`. |
| Thu May 28 | RDMI-004 | Extract WACH scoring formula (spike, unblocks RDMI-035) | 3 | Find the real `compute_health_score` (or equivalent) in `$WACH/backend/core/`. Document inputs, weights, edge cases. Save as `docs/superpowers/notes/2026-05-28-wach-scoring-formula.md` so RDMI-035 can paste it in without re-deriving. |
| Thu May 28 | RDMI-005 | Cyberview MQTT middleware contract spike | 3 | Document the topic schema, payload shape, auth model of the existing Cyberview MQTT middleware. Decide: ingest now (Phase 2 pull-in) or stay on fixtures for MVP demo. Output: short ADR. |
| Fri May 29 | RDMI-006 | Auth + tenancy threat-model review | 2 | Walk JWT claim shape, refresh-token rotation, cross-tenant 403 surface. Identify anything missing for a "Cyberview can't see WACH" guarantee. Confirm app-layer isolation is acceptable vs. RLS for MVP. |
| Fri May 29 | RDMI-007 | Jira + sprint setup | 2 | Create epic `RDMI-EPIC-1: Two-Tenant MVP`. Create sprints (1-week cadence: Sprint 1 = Jun 2–5, Sprint 2 = Jun 8–12, ...). Add board columns. Import RDMI-009..RDMI-063 as backlog. |
| Fri May 29 | RDMI-008 | MVP scope sign-off + Phase 2+ roadmap presentation | 3 | Final go/no-go on MVP scope with stakeholders. Walk Phase 2 (MQTT) / 3 (anomaly) / 4 (optimization) / 5 (ML) roadmap. Lock scope. |

**Planning week deliverables:**

- WACH port audit matrix (RDMI-003)
- WACH scoring formula extracted to a note (RDMI-004) — unblocks the scoring port in execution
- Cyberview MQTT contract ADR (RDMI-005)
- Jira board ready, all execution tickets imported, Sprint 1 planned

---

## Sprint 1 — Plan A Foundation Start (Jun 2 → Jun 5)

| Date | Ticket | Title | Tasks (Plan A) | Pts | Depends |
|------|--------|-------|----------------|-----|---------|
| Tue Jun 2 | RDMI-009 | Bootstrap monorepo + docker infra | A.1, A.2 | 3 | RDMI-008 |
| Tue Jun 2 | RDMI-010 | Scaffold `apps/api` FastAPI + `/healthz` | A.3 | 2 | RDMI-009 |
| Thu Jun 4 | RDMI-011 | Scaffold `apps/web` Vite/React/Zustand | A.4 | 2 | RDMI-009 |
| Thu Jun 4 | RDMI-012 | Create `packages/types` shared types | A.5 | 1 | RDMI-009 |
| Fri Jun 5 | RDMI-013 | Postgres initial migration (indexes + role CHECKs) | A.6 | 3 | RDMI-010 |
| Fri Jun 5 | RDMI-014 | SQLAlchemy ORM models + async session | A.7 | 2 | RDMI-013 |

---

## Sprint 2 — Auth + Tenancy (Jun 8 → Jun 12)

| Date | Ticket | Title | Tasks | Pts | Depends |
|------|--------|-------|-------|-----|---------|
| Mon Jun 8 | RDMI-015 | Argon2 password hashing (TDD) | A.8 | 1 | RDMI-014 |
| Mon Jun 8 | RDMI-016 | JWT encode/decode (TDD) | A.9 | 2 | RDMI-014 |
| Mon Jun 8 | RDMI-017 | Pytest fixtures (db, app, seeded users) | A.10 | 2 | RDMI-015, RDMI-016 |
| Tue Jun 9 | RDMI-018 | `resolve_tenant_ctx` service (TDD) | A.11 | 3 | RDMI-017 |
| Tue Jun 9 | RDMI-019 | Session/refresh rotation (TDD) | A.12 | 2 | RDMI-017 |
| Wed Jun 10 | RDMI-020 | Auth routes login/refresh/logout (TDD) | A.13 | 4 | RDMI-019 |
| Thu Jun 11 | RDMI-021 | `get_current_user` dependency | A.14 | 1 | RDMI-016 |
| Thu Jun 11 | RDMI-022 | Tenant middleware + `require_role` (TDD) | A.15 | 3 | RDMI-018, RDMI-021 |
| Fri Jun 12 | RDMI-023 | `SiteAdapter` Protocol + DTOs (async) | A.16 | 2 | RDMI-018 |

---

## Sprint 3 — Default Adapter + Dashboard + Plan A Close (Jun 15 → Jun 19)

| Date | Ticket | Title | Tasks | Pts | Depends |
|------|--------|-------|-------|-----|---------|
| Mon Jun 15 | RDMI-024 | `_default` adapter stub (async) | A.17 | 2 | RDMI-023 |
| Mon Jun 15 | RDMI-025 | Adapter dispatch + UnknownAdapter (TDD) | A.18 | 1 | RDMI-024 |
| Mon Jun 15 | RDMI-026 | Dashboard routes through adapter (TDD) | A.19 | 3 | RDMI-022, RDMI-025 |
| Tue Jun 16 | RDMI-027 | Cross-tenant 403 parameterized suite | A.20 | 2 | RDMI-026 |
| Tue Jun 16 | RDMI-028 | Local-dev seed (incl. operator user) | A.21 | 2 | RDMI-014 |
| Wed Jun 17 | RDMI-029 | Frontend auth store + API client | A.22 | 2 | RDMI-020 |
| Wed Jun 17 | RDMI-030 | Login page + protected shell + stub dashboard | A.23 | 3 | RDMI-029 |
| Thu Jun 18 | RDMI-031 | Frontend Jest + login smoke | A.24 | 1 | RDMI-030 |
| Thu Jun 18 | RDMI-032 | CI workflow (api + web) | A.25 | 2 | RDMI-027, RDMI-031 |
| Fri Jun 19 | RDMI-033 | Plan A integration review + walkthrough | — | 2 | RDMI-032 |

---

## Sprint 4 — Plan B: WACH Port (Jun 22 → Jun 26)

| Date | Ticket | Title | Tasks (Plan B) | Pts | Depends |
|------|--------|-------|----------------|-----|---------|
| Mon Jun 22 | RDMI-034 | Port `AHU_LEVEL_CONFIG` + e\d{4} validation | B.1 | 2 | RDMI-033 |
| Mon Jun 22 | RDMI-035 | Port scoring engine (uses RDMI-004 note) | B.2 | 3 | RDMI-004, RDMI-034 |
| Tue Jun 23 | RDMI-036 | CI grep guard for scoring placeholder | B.2 step 7 | 1 | RDMI-035 |
| Tue Jun 23 | RDMI-037 | Influx wrapper async + `query_all_device_scores` | B.3 | 3 | RDMI-034 |
| Wed Jun 24 | RDMI-038 | RAG client (site-scoped Chroma) | B.4 | 2 | RDMI-033 |
| Wed Jun 24 | RDMI-039 | Qwen LM Studio async client | B.5 | 3 | RDMI-033 |
| Thu Jun 25 | RDMI-040 | `WachAdapter` + protocol conformance suite | B.6 | 4 | RDMI-035, RDMI-037, RDMI-038 |
| Fri Jun 26 | RDMI-041 | WACH dashboard integration test (mocked Influx) | B.7 | 2 | RDMI-040 |
| Fri Jun 26 | RDMI-042 | Chat prompt builder (TDD) | B.8 | 2 | — |

---

## Sprint 5 — Chat + Frontend Dashboard (Jun 29 → Jul 3)

| Date | Ticket | Title | Tasks | Pts | Depends |
|------|--------|-------|-------|-----|---------|
| Mon Jun 29 | RDMI-043 | Rule-based fallback (`ENABLE_LLM=false`) | B.9 | 2 | RDMI-042 |
| Mon Jun 29 | RDMI-044 | Chat orchestrator + SSE route (TDD) | B.10 | 4 | RDMI-039, RDMI-042, RDMI-043 |
| Tue Jun 30 | RDMI-045 | Chat RAG-isolation test | B.11 | 1 | RDMI-044 |
| Tue Jun 30 | RDMI-046 | `packages/ui` — lift WACH components | B.12 | 4 | RDMI-033 |
| Wed Jul 1 | RDMI-047 | DashboardPage wired to `/api/dashboard/*` | B.13 | 3 | RDMI-046 |
| Thu Jul 2 | RDMI-048 | Chat panel SSE + history forwarding | B.14 | 3 | RDMI-044, RDMI-047 |
| Thu Jul 2 | RDMI-049 | Seed update — WACH site → `wach` adapter | B.15 | 1 | RDMI-040 |
| Fri Jul 3 | RDMI-050 | Plan B WACH dry-run + bug-bash | — | 3 | RDMI-048, RDMI-049 |

---

## Sprint 6 — Plan C: Cyberview + Admin (Jul 6 → Jul 10)

| Date | Ticket | Title | Tasks (Plan C) | Pts | Depends |
|------|--------|-------|----------------|-----|---------|
| Mon Jul 6 | RDMI-051 | Generic Influx aggregator for `_default` | C.1 | 4 | RDMI-050 |
| Mon Jul 6 | RDMI-052 | Cyberview seed from `scripts/research` | C.2 | 3 | RDMI-051 |
| Tue Jul 7 | RDMI-053 | Admin routes — orgs/sites/users CRUD (TDD) | C.3 | 4 | RDMI-050 |
| Wed Jul 8 | RDMI-054 | Knowledge upload + chunk/embed (TDD) | C.4 | 4 | RDMI-038, RDMI-053 |
| Thu Jul 9 | RDMI-055 | `/me/sites` + index.css defaults + ThemeProvider + Gate + SiteSwitcher | C.5 | 4 | RDMI-053 |
| Fri Jul 10 | RDMI-056 | Frontend admin pages (Orgs/Sites/Users/Knowledge) | C.6 | 4 | RDMI-053, RDMI-054, RDMI-055 |

---

## Sprint 7 — E2E, Deploy, Sign-Off (Jul 13 → Jul 17)

| Date | Ticket | Title | Tasks | Pts | Depends |
|------|--------|-------|-------|-----|---------|
| Mon Jul 13 | RDMI-057 | Playwright E2E suite (4 scenarios) | C.7 | 4 | RDMI-056 |
| Tue Jul 14 | RDMI-058 | E2E CI workflow (nightly + PR) | C.8 | 2 | RDMI-057 |
| Wed Jul 15 | RDMI-059 | Vercel deploy config (`vercel.json`) | C.9 | 2 | RDMI-056 |
| Wed Jul 15 | RDMI-060 | Railway service config + Dockerfile | C.10 | 2 | RDMI-056 |
| Thu Jul 16 | RDMI-061 | Adapter author guide docs | C.11 | 1 | RDMI-040, RDMI-051 |
| Thu Jul 16 | RDMI-062 | MVP acceptance test (spec §8 four scenarios) | C.12 | 2 | RDMI-058, RDMI-059, RDMI-060 |
| Fri Jul 17 | RDMI-063 | Stakeholder demo + retro + Phase 2 brainstorm | — | 3 | RDMI-062 |

---

## Summary

**Totals:** 63 tickets (8 planning + 55 execution), ~140 points over 35 working days. Avg 4 pts/day with built-in slack each week.

**Critical-path callouts:**

- RDMI-004 (scoring formula extraction in planning week) directly unblocks RDMI-035 in Sprint 4. If RDMI-004 reveals the formula is more complex than expected, escalate before Sprint 4 starts.
- RDMI-005 (MQTT spike) is information-gathering only; doesn't gate any execution ticket. Output feeds Phase 2 planning.
