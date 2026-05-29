# RDMI-006 — Auth + Tenancy Threat-Model Review

**Date:** 2026-05-29
**Ticket:** RDMI-006 (2 pts)
**Scope:** RDM Insight MVP (two-tenant: WACH + Cyberview)
**Spec under review:** `docs/superpowers/specs/2026-05-25-rdm-insight-platform-design.md` §6
**Code refs:** `docs/superpowers/plans/2026-05-25-rdm-insight-plan-a-foundation.md` Tasks 8–17
**Reviewer:** Jinendra Muraly
**Decision:** **GO — app-layer isolation acceptable for MVP** with the gating fixes in §6 landed before Sprint 1 close (Jun 5).

---

## 1. Threat model scope

In scope:
- JWT access-token claim shape and trust boundary.
- Refresh-token lifecycle (issue, rotate, revoke, storage).
- Cross-tenant 403 surface (every `/api/*` route).
- App-layer isolation vs Postgres RLS for MVP guarantee: **"Cyberview can never see WACH data."**

Out of scope (deferred to later phases):
- SSO / MFA / password reset (spec §2 non-goals).
- Per-row RLS in Postgres (Phase 3+, see §5).
- MQTT ingress auth (Phase 2).
- DoS / rate-limit / WAF.
- Secrets rotation playbook (covered by infra hardening ticket later).

Adversary classes:
- **A1** — Logged-in tenant user (WACH viewer) probing for cross-tenant access.
- **A2** — Unauthenticated attacker with intercepted access token (XSS, log spill).
- **A3** — Unauthenticated attacker with intercepted refresh cookie (network MITM, malicious browser extension).
- **A4** — Insider with read-only DB access (Neon dashboard) — out-of-scope for MVP control but noted in §7.

---

## 2. JWT claim shape — review

### Current shape (Plan A Task 9, `core/auth/jwt.py` + `routes/auth.py::_claims_for_user`)

```json
{
  "sub": "<user uuid>",
  "email": "viewer.wach@example.com",
  "is_super_admin": false,
  "org_memberships":  [{"org_id": "<uuid>", "role": "org_admin"}],
  "site_memberships": [{"site_id": "<uuid>", "role": "site_viewer"}],
  "iat": 1717000000,
  "exp": 1717000900
}
```

Algorithm: **HS256**, shared `JWT_SECRET`. TTL: **900s** (15 min). No `kid`, `iss`, `aud`, `jti`.

### Findings

| # | Finding | Severity | Action |
|---|---------|----------|--------|
| J1 | No `iss` / `aud` claim. A token minted for another HS256 service sharing the secret would validate here. Not exploitable today (single service) but cheap insurance. | Low | **FIX** — add `iss: "rdm-insight-api"`, `aud: "rdm-insight-web"`, verify on decode. |
| J2 | No `jti`. Cannot revoke a leaked access token before `exp`. With 15-min TTL the blast radius is bounded; live revocation is a Phase 2 problem. | Low | **ACCEPT** — 15-min TTL is the mitigation. Revisit when sessions get longer. |
| J3 | `org_memberships` and `site_memberships` embedded in the token. **Permission changes don't take effect for up to 15 min.** Acceptable for MVP (memberships rarely change; super-admin provisions manually). | Medium-info | **ACCEPT + document** — note in admin UI: "membership changes propagate on next refresh, up to 15 min." |
| J4 | `email` in payload. PII in a token that may land in browser console / Sentry. Not catastrophic; `sub` alone would do. | Low | **ACCEPT** — `email` is already in DB; trade-off favors UX (shows in header without extra fetch). |
| J5 | No `kid` → secret rotation requires invalidating all live tokens (15-min window). For MVP, acceptable; document the rotation procedure (set new secret, accept 15-min auth gap, all users re-login). | Low | **DOCUMENT** in `docs/runbooks/`. |
| J6 | **Auth decision relies on token claims, not a fresh DB lookup.** A user whose membership is revoked keeps access until token expires. The actual authorization check (`resolve_tenant_ctx`) re-reads memberships from DB on every request — so this is **already mitigated by construction**. Verified in `core/tenancy/service.py`. | — | **No action.** Confirms the design is correct. |
| J7 | Confirm `decode_access_token` rejects `alg: none` and asymmetric algs. PyJWT 2.x with `algorithms=["HS256"]` does. Verified. | — | **No action**, but add a regression test asserting `alg: none` rejection. |

### Recommended claim shape (post-fix)

```json
{
  "iss": "rdm-insight-api",
  "aud": "rdm-insight-web",
  "sub": "<user uuid>",
  "email": "…",
  "is_super_admin": false,
  "org_memberships":  [...],
  "site_memberships": [...],
  "iat": ..., "exp": ...
}
```

Decoder: `pyjwt.decode(t, secret, algorithms=["HS256"], audience="rdm-insight-web", issuer="rdm-insight-api")`.

---

## 3. Refresh-token rotation — review

### Current design (Plan A Task 12, `core/auth/sessions.py`; Task 13 cookie config)

- 48-byte URL-safe random → SHA-256 → `sessions.refresh_hash` (DB column, indexed).
- Cookie: `rdm_refresh`, `max_age = 30d`, **`httponly=True, secure=False, samesite="lax", path="/auth"`**.
- `rotate_session` deletes the old row and inserts a new row in the same transaction (one round-trip semantically; verify atomicity in §6).
- `find_session_by_refresh` rejects expired rows.

### Findings

| # | Finding | Severity | Action |
|---|---------|----------|--------|
| R1 | **`secure=False` in cookie.** Refresh token transmitted over plain HTTP is exposed to passive MITM. Plan code is dev-default but must flip in prod. | **High** | **FIX before deploy** — env-driven `secure=True` for any non-localhost origin. Add `settings.cookie_secure: bool = True` and override in dev. |
| R2 | `samesite="lax"` lets the cookie ride GET top-level navigations from third-party origins. Refresh route is POST, so CSRF risk is bounded — but tighten to `strict` since web app is single-origin (Vercel domain). | Medium | **FIX** — `samesite="strict"`. |
| R3 | `path="/auth"` is good (cookie not sent to `/api/*`). Keep. | — | Keep. |
| R4 | **No reuse detection.** If `rotate_session` deletes the old row then a replay of the old refresh returns 401 — **but we lose the signal that a token was leaked**. Per OAuth 2.1 refresh-token-rotation guidance, a reuse attempt should **kill the entire session family**. | Medium | **FIX (small)** — on `find_session_by_refresh` miss for a token whose hash *was previously seen* (track via a short-TTL `revoked_hashes` table or a `replaced_by` column on `sessions`), revoke all sessions for that user. Defer the full impl if time-boxed; minimum bar for MVP is logging the event. |
| R5 | Refresh hash is SHA-256 (unsalted). Acceptable: input is 48 bytes of CSPRNG entropy (~256 bits), so rainbow tables / brute force are infeasible. | — | **No action.** |
| R6 | `rotate_session` does `DELETE` + `INSERT` across two `commit`s in the helper (`delete` then call `create_session` which itself commits). Two transactions = a crash window where the user loses their refresh entirely. Low impact (user re-logs in), but trivial to fix. | Low | **FIX** — wrap in a single transaction; `create_session` should accept an optional `commit=False` flag. |
| R7 | No idle-timeout. 30-day absolute TTL only. A user who logs in once and walks away keeps a valid refresh for 30 days. Acceptable for MVP (single-operator workstation pattern); revisit when first real tenant onboards. | Low | **ACCEPT.** |
| R8 | No `user_agent` / IP binding. A stolen cookie used from another machine works. Binding to UA is fragile (UA changes break sessions); IP binding breaks mobile. **Accept** for MVP; rely on `secure + httponly + samesite=strict + short access TTL + rotation + reuse-detection`. | — | **ACCEPT** with documented rationale. |
| R9 | `revoke_session` deletes by hash. Logout works. But there is no **"log out everywhere"** affordance (delete all `sessions` for a user). Useful when a password is suspected leaked. | Low | **ADD** small admin endpoint `POST /auth/revoke-all` for self; super-admin variant out of scope. |

---

## 4. Cross-tenant 403 surface — review

### Current design (spec §6, Plan A Task 15)

Two middlewares per `/api/*` request:

1. `auth_middleware` → `request.state.user`.
2. `tenant_middleware` → reads `X-Site-Id` header → `resolve_tenant_ctx(user, site_id)` → `request.state.tenant_ctx`, else **403**.

Route handlers depend on `Depends(require_role(...))` which returns the `tenant_ctx`. Every data-access function takes `tenant_ctx` as first arg.

### Findings

| # | Finding | Severity | Action |
|---|---------|----------|--------|
| C1 | **Whole guarantee rests on every route depending on `get_tenant_ctx` / `require_role`.** A new route that forgets the dependency is a silent cross-tenant leak (not a 500). | **Critical** | **CONTROLS NEEDED**: (a) cross-tenant parametric test suite (already specified in §10) covering *every* route in `app.routes` — assert 403 for foreign user. (b) lint rule / unit test that walks `app.routes` and asserts every router under `/api` declares a `tenant_ctx` dependency or is explicitly allow-listed (`/healthz`, `/auth/*`, `/me/sites`). I'll call this the **"router conformance test"**; add it as a Plan A acceptance criterion. |
| C2 | `X-Site-Id` header as the tenant selector is **trust-on-client-input**. That is fine *because* `resolve_tenant_ctx` re-validates membership against DB. Worth a regression test: viewer-A sends `X-Site-Id: <site-B>` → 403 (not 500, not silent fall-through to "first site"). | Low | **TEST** — add to `test_cross_tenant_isolation.py`. |
| C3 | Missing-header behavior must be **403, not 400**, and certainly not "default to first membership." Confirm middleware. | Medium | **FIX/CONFIRM** in middleware — explicit `if site_id is None: raise HTTPException(403, "site context required")`. |
| C4 | **Chat collection isolation.** `ChromaDB collection = f"site:{site_id}"`. The `site_id` comes from `tenant_ctx` not from request body — verify. If any chat path takes `site_id` from the message payload it can be flipped. | High | **AUDIT** Plan B chat orchestrator before merge — RAG `collection` must derive from `tenant_ctx.site_id` only. Add a chat-specific cross-tenant test: WACH user asks "what's on Cyberview's level 1" → response must not contain Cyberview-collection content (assert by seeding a uniquely-tagged doc). |
| C5 | **Influx bucket isolation.** Each adapter receives `site.influx_bucket` via `tenant_ctx → site` lookup. Same trust path as C4. Same control: test that a viewer's Flux query for site_b never reaches `bucket-b`. | High | **TEST** via adapter unit test with a mock Influx client capturing the bucket arg. |
| C6 | Super-admin path: `is_super_admin` flag short-circuits to `role="super_admin"` for any site. Correct for spec, but means a compromised super-admin account = total breach. **Reduce blast radius**: require super-admin to be a separate account (not their day-to-day viewer account), and audit-log every super-admin cross-org access. | Medium | **FIX** — add `audit_log` entry on super-admin tenant resolution with `action="super_admin_site_access"`. Operational: super-admin accounts are flagged in seed and not used for routine work. |
| C7 | `org_admin` role currently only on `org_memberships`; no route gates on `org_admin` yet in Plan A. When admin routes ship (Plan B/C), `require_role("org_admin")` must reject org-admins from *other* orgs even if `X-Site-Id` points at their org. Confirm `resolve_tenant_ctx` ordering does this — it does (`OrgMembership.user_id == user.id, OrgMembership.org_id == site.org_id`). | — | **No action**, regression test in C1 suite covers it. |
| C8 | List endpoints. Spec says "no global list-all-devices." Enforce by code review — flag any route that doesn't take a `site_id` and returns multi-entity data. The conformance test (C1) catches this structurally. | — | Covered by C1. |
| C9 | Error message leakage. Both "unknown site" and "forbidden" currently raise `TenancyError` with distinct messages. Reduce to a single response shape (`403 forbidden`) so attackers cannot enumerate site IDs by status/message differences. | Low | **FIX** in `tenant_middleware` translation layer — always return `403 {"detail": "forbidden"}` regardless of underlying `TenancyError` reason. Keep distinct reasons in server logs. |
| C10 | Background jobs. Plan A has none; Plan B introduces chat orchestrator (request-scoped, fine). Phase 2 ingestion must carry explicit `site_id` in every job payload — flag in MQTT design before that phase starts. | — | **Document** as Phase 2 entry criterion. |

---

## 5. App-layer isolation vs Postgres RLS — decision

### Recap

Spec §5: "Application-layer enforcement only — no Postgres RLS for MVP. Consistency comes from every route depending on the same middleware-injected `tenant_ctx`."

### Pros of app-layer (current plan)

- Single code path; easier to reason about during a 2-tenant demo.
- No per-request `SET LOCAL app.current_tenant` ceremony or connection-pool gotchas.
- Adapter dispatch already enforces the boundary at the engine level (Influx bucket, Chroma collection) — Postgres rows are a small surface (orgs, sites, users, sessions, audit_log) and most queries are admin-side.
- Plan B has a `cross_tenant_isolation` test suite as a structural backstop.

### Cons / risks

- **One missing `Depends(get_tenant_ctx)` = silent leak.** Mitigation: conformance test (C1). With it, the leak surface collapses to "a route added without running tests" which CI catches.
- A misconfigured ORM query (`select(Device).all()` with no `where(site_id=...)`) leaks across tenants. **Mitigation:** Postgres holds *no telemetry*. All time-series data is in per-site Influx buckets. The only multi-tenant tables in Postgres are admin metadata (`sites`, `users`, `memberships`) — and those queries are either single-row (by id) or super-admin-only. The "leaky ORM query" risk is low for MVP because there is no per-tenant *data* in Postgres.
- A Neon dashboard reader (insider, A4) sees all tenants' rows. RLS would not stop them either (they'd `SET ROLE` past it). Mitigation is access control on Neon, not RLS.

### Decision

**APP-LAYER ISOLATION IS ACCEPTABLE FOR MVP** subject to:

1. **Router conformance test (C1) lands in Plan A** — non-negotiable. Without it, the "Cyberview can't see WACH" guarantee is aspirational.
2. **Cross-tenant integration test suite (Plan A §10 + chat-specific case from C4) is green in CI** as a merge gate.
3. **Chat collection (C4) and Influx bucket (C5) tests** prove the engine-layer isolation, not just the route layer.
4. **Re-evaluate when adding a multi-tenant *telemetry* table to Postgres** (e.g., if alerts get persisted in Postgres). At that point, RLS becomes the cheap belt-and-braces; revisit in Phase 3 alongside the anomaly engine.

RLS is **not free**: it complicates migrations (`ALTER TABLE … ENABLE ROW LEVEL SECURITY`, per-table policies), forces `SET LOCAL app.current_tenant_id` on every connection checkout (easy to miss with async pool), and the super-admin escape hatch (`BYPASSRLS` role) is itself a footgun. Pay that cost when the telemetry surface in Postgres justifies it.

---

## 6. Gating fixes before Sprint 1 close (Jun 5)

Bundle of small, scoped changes. Add to Plan A backlog as new tickets or fold into existing Task 13 / Task 15.

| Tag | Change | Where | Effort |
|-----|--------|-------|--------|
| **G1** | Add `iss` + `aud` to JWT encode/decode (J1). | `core/auth/jwt.py`, `core/settings.py` | 30 min |
| **G2** | Add `alg: none` rejection regression test (J7). | `tests/unit/test_jwt.py` | 10 min |
| **G3** | `cookie_secure` env flag; default `True`, dev override `False` (R1). | `core/settings.py`, `routes/auth.py::_refresh_cookie` | 20 min |
| **G4** | `samesite="strict"` on refresh cookie (R2). | same | 5 min |
| **G5** | Atomic `rotate_session` (R6). | `core/auth/sessions.py` | 30 min |
| **G6** | Reuse-detection logging — log on `find_session_by_refresh` miss for a hash present in a new `revoked_hashes` table OR `sessions.replaced_by_id` column; full session-family revoke optional for MVP but log + alert at minimum (R4). | `core/auth/sessions.py`, migration | 1–2 h |
| **G7** | Missing-`X-Site-Id` returns 403 not 400 (C3). | `core/tenancy/middleware.py` | 10 min |
| **G8** | Collapse `TenancyError` variants to single 403 response (C9). | `core/tenancy/middleware.py` | 10 min |
| **G9** | Audit-log every super-admin site access (C6). | `core/tenancy/service.py` or middleware | 30 min |
| **G10** | **Router conformance test**: walks `app.routes`, asserts every `/api/*` route has a `tenant_ctx` dependency or is in an explicit allow-list (C1). | `tests/integration/test_router_conformance.py` | 1 h |
| **G11** | Chat collection-isolation regression test (C4) — placeholder file in Plan A, real assertions land with Plan B chat. | `tests/integration/test_chat_isolation.py` | 30 min Plan A + 30 min Plan B |
| **G12** | Cross-tenant `X-Site-Id` flip test: viewer-A sends `X-Site-Id: site-B` → 403 (C2). | `tests/integration/test_cross_tenant_isolation.py` | 15 min |

Total ≈ **half a day** of engineering, all inside Plan A scope.

---

## 7. Items deferred (tracked, not blocking MVP)

- **Postgres RLS** — revisit when a multi-tenant table holds tenant *data* (alerts, overrides) rather than admin metadata. Phase 3.
- **JWT `kid` + key rotation runbook.** Document the brute-force rotation procedure (set new secret, accept 15-min auth gap) in `docs/runbooks/` before first paying tenant.
- **MFA / SSO.** Spec §2 non-goals. Likely path is Clerk via Vercel Marketplace when first paying tenant onboards.
- **Rate-limiting on `/auth/login`.** Add when public. For MVP (super-admin provisioned accounts, internal demo), accept.
- **Insider (A4) controls.** Neon access policy + audit, not an app-layer concern.
- **Background job tenant carrying** (C10) — Phase 2 MQTT ingestion entry criterion.

---

## 8. Sign-off

**Decision:** **GO** for app-layer isolation MVP, conditional on G1–G12 landing by end of Sprint 1 (Jun 5).
**"Cyberview can't see WACH" guarantee** is supported by:
  - Per-site Influx bucket (engine boundary, structural).
  - Per-site Chroma collection (engine boundary, structural).
  - `tenant_ctx` re-resolves memberships from DB on every request (no stale-token bypass).
  - Cross-tenant + router-conformance test suites (structural CI backstop).

**Next:** fold G1–G12 into Plan A tasks (or open as RDMI-006a..l), confirm with stakeholders in RDMI-008 scope sign-off later today.
