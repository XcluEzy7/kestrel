---
id: KST-001
title: Add Shoo Google authentication and user data isolation
status: In Progress
assignee:
  - '@erik'
created_date: '2026-09-10 06:16'
updated_date: '2026-09-10 23:22'
labels: []
dependencies: []
references:
  - 'https://docs.shoo.dev/docs/server-verification'
modified_files:
  - src/career_os/config.py
  - src/career_os/main.py
  - src/career_os/middleware.py
  - src/career_os/dependencies.py
  - src/career_os/api/shoo_auth.py
  - src/career_os/services/auth.py
  - src/career_os/models/auth.py
  - src/career_os/models/models.py
  - src/career_os/models/__init__.py
  - src/career_os/api/profiles.py
  - src/career_os/api/batch.py
  - src/career_os/api/extension.py
  - src/career_os/services/extension_pairing.py
  - src/career_os/cli/extension.py
  - src/career_os/_alembic/versions/x6y7z8a9b0c1_add_shoo_auth_ownership.py
  - frontend/src/App.tsx
  - frontend/src/main.tsx
  - frontend/src/api/auth.ts
  - frontend/src/api/client.ts
  - frontend/src/api/applications.ts
  - frontend/src/api/contacts.ts
  - frontend/src/api/onboarding.ts
  - frontend/src/components/AuthGuard.tsx
  - frontend/src/pages/LoginPage.tsx
  - tests/test_shoo_auth.py
  - tests/test_extension_auth_ownership.py
  - frontend/src/__tests__/AuthGuard.test.tsx
  - frontend/src/__tests__/client.test.ts
  - docs/reference/shoo-auth-migration.md
  - .env.example
  - pyproject.toml
  - uv.lock
  - frontend/package.json
  - frontend/package-lock.json
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Require verified Shoo Google identity for private Kestrel data and bind every private record to its authenticated owner. Existing Railway data must migrate without silent data loss.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Backend verifies Shoo ID token signature, issuer, audience, expiration, and stable pairwise_sub
- [ ] #2 Secure server session supports login, logout, expiration, HttpOnly Secure SameSite cookies, and CSRF protection
- [ ] #3 Profiles and private records resolve through authenticated ownership instead of trusted caller-supplied ownership
- [ ] #4 Private API routes and application pages reject anonymous access; public routes are limited to login/auth flow, health, and required static assets
- [ ] #5 Personal analytics remain private
- [ ] #6 Dedicated browser-extension authentication remains isolated and cannot cross users
- [ ] #7 Two-account tests prove cross-user reads and writes fail
- [ ] #8 Existing single-profile data has a safe documented ownership migration path
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Bound SPA catch-all file serving to frontend directory using normalized containment. 2. Add regression coverage for encoded parent traversal. 3. Run focused startup/security tests and record evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation started in feat/KST-001-shoo-auth. Old hand-written backlog.md will be removed in favor of Backlog.md CLI records.

Deployment c1417bc7-6e14-4e9b-84a6-38444c15e545 reached SUCCESS without Railway configuration changes. Live /health returned 200 with database connected; anonymous private provider and MCP-token APIs returned 401. Live Settings screenshot captured MCP server tokens form with Read/Write scopes and expiry controls, but token fetch returned 401. Shoo login reached Google Email or phone prompt with no existing browser session, so authenticated separate-profile/provider proof remains unavailable. Docs routes still return 200 because SHOO_AUTH_ENABLED is absent/false in Railway variables; production auth must be enabled before AC4 live proof.

Production variables set via Railway CLI: SHOO_AUTH_ENABLED=true, SHOO_APP_ORIGIN=https://kestrel-production-2597.up.railway.app, SHOO_JWKS_URL=https://shoo.dev/.well-known/jwks.json, FRONTEND_URL=https://kestrel-production-2597.up.railway.app, SESSION_COOKIE_SECURE=true, MCP_RESOURCE_URL=https://kestrel-production-2597.up.railway.app/mcp/. Local-code deployment b7afbae6-d812-4cb3-9603-4fd534710408 succeeded after stale GitHub deployment 9405513c crashed on missing z9a0b1c2d3e4. /health=200 database connected; /api/auth/shoo/me reports auth_required=true; private APIs return 401. SHOO_CLAIM_LEGACY_DATA remains unset/false pending operator backup and explicit one-time ownership claim.

Investigated reported redirect loop: useShooAuth default autoHandleCallback redirected from /auth/callback before LoginPage submitted the ID token to /api/auth/shoo/login, so Kestrel never received a server session. Patched LoginPage to own callback completion, retain a validated same-origin return route, then exchange the token with Kestrel before navigation; added regression coverage.

Committed callback repair as 50b5c76 and deployed local code to Railway deployment ececf06d-2979-492e-9fcb-b419888a1d85; deployment reached SUCCESS. Frontend callback regression test and npm build pass. Live health check pending final browser login attempt.

Railway deployment ececf06d served stale frontend asset index-CscV4BTt.js despite local repair bundle index-fEq-KDzG.js; .dockerignore excludes frontend/dist, proving build context used stale source. Re-deployed current local source directly as 839dedb8-e362-4362-b9d3-91c1a47f1e83; status SUCCESS. Live bundle verification follows.

Independent judge found and verified blocking stale-token race; repaired in f1ccd1b by suppressing token submission while callback URL contains code/state, and strengthened test with stale localStorage identity plus exactly-one login POST. Focused test, full frontend test suite (382 passed), build, and lint pass. Deployed local source as 86e558f8-00b4-4624-afe0-dbdcb74302eb; status SUCCESS.

Integrated security audit found critical unauthenticated SPA path traversal; repair required before judge.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @atomic
created: 2026-09-10 06:26
---
2026-09-10 continuation started. Contract re-read with `backlog task view KST-001 --plain`. Preserved prior uncommitted auth draft; no files overwritten. Initial state: modified config.py, main.py, models/models.py; new api/shoo_auth.py, dependencies.py, models/auth.py, services/auth.py. Repository intent and route/profile ownership inventory in progress.
---

author: @atomic
created: 2026-09-10 06:49
---
Intent and architecture inventory complete. Official Shoo docs confirm ES256/P-256, issuer `https://shoo.dev`, JWKS `https://shoo.dev/.well-known/jwks.json`, audience `origin:` plus configured app origin, expiration verification, and stable origin-scoped `pairwise_sub`; browser claims remain untrusted. Draft gaps confirmed: undeclared JWT dependency, no JWKS cache, no CSRF enforcement, private routers not gated, caller profile IDs still authoritative, extension token unbound to account, no migration, no frontend guard/client, no tests. origin/main equals HEAD before feature work. No open GitHub issues or PRs.
---

author: @atomic
created: 2026-09-10 07:23
---
Implementation slice complete. Added verified Shoo ES256/JWKS login, hashed expiring server sessions, secure HttpOnly/SameSite cookies, CSRF guard, account/profile ownership gate, account-filtered profile list/create, account-owned async batch handles, account-bound dedicated extension tokens, explicit legacy ownership claim flag/migration guide, frontend Shoo login and fail-closed route guard, runtime profile selection, same-origin cookie/CSRF fetch layer, and tests. Focused evidence: backend 80 passed; migration packaging 13 passed; Ruff clean/format clean; frontend build passed; focused Vitest 4 passed; focused ESLint passed. Full deterministic stage still pending.
---

author: @atomic
created: 2026-09-10 07:25
---
Implementation stage committed as `3445e372` (`feat(KST-001): add Shoo account authentication`) with non-empty body. Working tree contains no source changes after commit. No push, merge, rebase, or PR performed. Next stage: deterministic full checks, then later Terra implementation/security review.
---

author: @atomic
created: 2026-09-10 19:52
---
Deployment evidence: health 200, private APIs 401, MCP controls visible, Shoo authenticated browser proof blocked at Google credential prompt. Release remains conditional.
---

author: @ShooCallbackJudge
created: 2026-09-10 21:16
---
[judge] BLOCKING frontend/src/pages/LoginPage.tsx:58-64 — Race: on /auth/callback mount with a stale shoo_identity token in localStorage, the hook init effect (@shoojs/react dist/index.js: setIdentity(client.getIdentity())) surfaces the old token in the same commit in which effect 1 starts finishSignIn; effect 2 has no callback-awareness, so it immediately POSTs the STALE token to /api/auth/shoo/login concurrently with the in-flight callback exchange. Interleavings: stale 401 → catch's clearIdentity() can run after refreshIdentity() already read the fresh token, wiping it from localStorage and state so the new token is never submitted; callbackHandled.current (line 45) blocks auto-retry → user sees spurious "Sign-in could not be verified" and must repeat the full Shoo redirect. If the stale token is still valid, a duplicate server session and duplicate navigation are created. Fix: gate effect 2 on callback completion (in-flight flag set in effect 1, cleared after finishSignIn settles) so token submission happens only after the callback exchange, while preserving the no-callback silent re-login path (parseCallback() === null).
---

author: @ShooCallbackJudge
created: 2026-09-10 21:16
---
[judge] FOLLOW-UP frontend/src/__tests__/LoginPage.test.tsx:24-32 — The useShooAuth mock diverges from the installed package contract (frontend/node_modules/@shoojs/react/dist/index.js): real hook returns claims/sessionState and initializes identity via client.getIdentity(); real refreshIdentity is async with no args and does NOT throw on failure. The mock hard-codes refreshIdentity to force identity.token, so the test asserts only the happy path and cannot fail on any effect-2 failure/clearIdentity interleave. Rework the mock to mirror the real return shape + init from getIdentity, then add tests for the stale-token race and failure clearing.
---

author: @ShooCallbackJudge
created: 2026-09-10 21:16
---
[judge] FOLLOW-UP frontend/src/pages/LoginPage.tsx:47,62 — useEffect dependency arrays use whole function refs (refreshIdentity/clearIdentity) while the code path only depends on the option objects captured at mount; acceptable today but brittle. Also line 47 sessionStorage.getItem is read without normalization: safeReturnTo re-validates, so a poisoned stored value falls back safely — no security issue, noting for clarity only.
---

created: 2026-09-10 23:22
---
[judge] PASS — combined review @ 92ac826. No blocking. Verified: token verification (services/auth.py:33-58 ES256/kid/iss/aud/pairwise_sub), session+CSRF+expiry (services/auth.py:60-95), ownership gate+CSRF body scan (dependencies.py:33-52,84-95), 30 routers under _private_dependencies (main.py:292-325), SPA containment (main.py:373-385 + test_kestrel_start.py regression), extension account binding (api/extension.py:80-93, tests/test_extension_auth_ownership.py), linear migration chain w5→x6y7z8a9b0c1→y7z8a9b0c1d2→z8a9b0c1d2e3→z9a0b1c2d3e4. FOLLOW-UP (new): src/career_os/api/shoo_auth.py:155-181,203-211 — POST/DELETE /api/auth/shoo/mcp-tokens skip csrf_valid (router mounted without _private_dependencies and _browser_account checks session only); SameSite=lax mitigates cross-site POST and DELETE is preflight-blocked, so no exploitable hole, but add csrf_valid for parity with logout/authorize_private_request.
---
<!-- COMMENTS:END -->
