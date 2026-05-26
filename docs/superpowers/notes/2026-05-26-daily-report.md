# Daily Report — 2026-05-26 (Tue)

**Engineer:** Jin
**Branch:** `main`
**Sprint:** Week 0 — Planning & Alignment

## Summary

Completed all of Tuesday's scheduled work (spec walkthrough RDMI-001 + plan review RDMI-002), then pulled Thursday's three pre-Sprint-1 tickets (RDMI-003 / RDMI-004 / RDMI-005) forward and finished them today. Net effect: Week 0 is effectively closed two days early; Friday's two tickets (RDMI-006 threat-model review, RDMI-007 Jira setup) are the only items remaining before Sprint 1 starts Jun 2.

## Tickets completed today

| Ticket | Title | Pts | Status |
|---|---|---:|---|
| RDMI-001 | Spec walkthrough with stakeholders | 4 | ✅ done |
| RDMI-002 | Plans A/B/C engineering review | 5 | ✅ done |
| RDMI-003 | WACH source audit | 4 | ✅ done (pulled from Thu) |
| RDMI-004 | Extract WACH scoring formula | 3 | ✅ done (pulled from Thu) |
| RDMI-005 | Cyberview MQTT contract ADR | 3 | ✅ done (pulled from Thu) |

**Total points landed:** 19

## Artifacts produced

| Ticket | Path | What it is |
|---|---|---|
| RDMI-002 | `~/.claude/plans/reactive-wiggling-pixel.md` | Plan A/B/C walkthrough notes + scope amendments (UI/UX 3D layer, MQTT ingest reshaping, DuckDB-as-hot-layer architecture) |
| RDMI-003 | `docs/superpowers/notes/2026-05-28-wach-port-audit.md` | Portability matrix: 44 files across `backend/{core,rag,llm,models,routes}` classified LIFT / SEAM / CORE / LEAVE with target paths in `apps/api/` |
| RDMI-004 | `docs/superpowers/notes/2026-05-28-wach-scoring-formula.md` | Full FAIR scoring algorithm extracted from `core/fair_health_scoring.py` (1149 LOC). Weights, sensitivities, edge cases, 8 caveats, port acceptance checks. **Unblocks Plan B T2.** |
| RDMI-005 | `docs/superpowers/specs/2026-05-28-cyberview-mqtt-adr.md` | Topic schema + payload contract derived from 26 615-row 5-min snapshot. 9 open unknowns enumerated with verification method. Buffer DDL specified. Separate-scheduler rationale recorded. |

## Key decisions locked

1. **DuckDB as hot query layer; no Redis.** Influx is cold source; cron ETL writes to DuckDB; dashboard + chat read from DuckDB. Saved as memory: `~/.claude/projects/-Users-rdmasia-wach-insight/memory/project_rdm_insight_query_architecture.md`.
2. **Cyberview ingest is MVP-in-scope, not fixtures.** Separate `IngestRunner` from WACH, distinct DuckDB schema namespace (`cyberview_*` vs `wach_*`), distinct credentials, distinct schedule.
3. **3D UI layer added to Plan C.** Pre-rendered turntable sprites (36-frame WebP), no live WebGL. Two reference assets (AHU + chiller) ship in MVP. Adds ~3–5 days to Sprint 7.
4. **`orgs.theme_json` JSONB column** added to Plan A T6 migration to support per-tenant theming in Plan C.
5. **Plan totals after amendments:** Plan A = 28 tasks (+3 ingest), Plan B = 15 tasks (unchanged), Plan C = 18 tasks (+6 UI/UX). 61 tickets total, demo target ~Jul 21.

## Findings worth flagging

1. **PF load discount is defined but not wired** in `fair_health_scoring.py`. Constants `PF_DISCOUNT_THRESHOLD = 0.60` and `PF_DISCOUNT_FACTOR = 0.35` exist; the docstring references the discount; the code never applies it. Two options for the port — strict (replicate bug) or faithful (implement per docstring). **Needs Raj sign-off before Sprint 4 / Plan B T2.**
2. **`p95` named `p99` in some signal strings** — variable `historical_p99` actually holds p95. Rename during port.
3. **Cyberview snapshot shape:** 10-level MQTT topics, ~2 697 distinct topics in 5 min, 2 sites (`CoPlace3`, `Cyberview23`), uniform `{val, unit, ts}` JSON payload, `ts` is device-side epoch ms (not broker arrival).
4. **Cyberview broker access not yet established.** Action items 1–5 in the ADR are blocking A.27 discovery.

## Blockers carried forward

| # | Blocker | Owner | Needed by |
|---|---|---|---|
| 1 | Cyberview broker host/port/auth/network-path | Jin → Cyberview ops | Sprint 1 start (Jun 2) for A.27 |
| 2 | Cyberview historian DB confirm/deny | Jin → Cyberview ops | Sprint 2 (Jun 8) for A.28 |
| 3 | Raj sign-off on PF load discount port strategy | Jin → Raj | Sprint 4 start (Jun 22) for Plan B T2 |
| 4 | Scheduler choice: APScheduler in-process vs separate Railway worker | Jin (internal) | Sprint 1 start for A.26 |
| 5 | RDMI-004 ownership — formally assign Plan B T2 implementer | Jin → team | Sprint 4 start |

## Remaining Week 0 work

| Date | Ticket | Title | Pts |
|---|---|---|---:|
| Fri May 29 | RDMI-006 | Auth + tenancy threat-model review | 2 |
| Fri May 29 | RDMI-007 | Jira + sprint setup (epic, sprints, backlog import) | 2 |

After Friday, Week 0 closes and Sprint 1 starts Jun 2.

## Memory updates

- `project_rdm_insight_query_architecture.md` written (DuckDB hot layer, no Redis).
- `MEMORY.md` index updated with the architecture note.

## Tomorrow / next session

- If Cyberview ops have responded with broker creds, kick off A.27 discovery script work.
- Otherwise, pull RDMI-006 forward (threat-model review) — no external dependency.
- RDMI-007 (Jira setup) requires Jira access; do interactively when convenient.

---

## Index of all artifacts touched today

```
~/.claude/plans/reactive-wiggling-pixel.md                                    (RDMI-002)
~/.claude/projects/-Users-rdmasia-wach-insight/memory/MEMORY.md               (memory index)
~/.claude/projects/-Users-rdmasia-wach-insight/memory/
    project_rdm_insight_query_architecture.md                                 (new memory)
docs/superpowers/notes/2026-05-26-daily-report.md                             (this file)
docs/superpowers/notes/2026-05-28-wach-port-audit.md                          (RDMI-003)
docs/superpowers/notes/2026-05-28-wach-scoring-formula.md                     (RDMI-004)
docs/superpowers/specs/2026-05-28-cyberview-mqtt-adr.md                       (RDMI-005)
```
