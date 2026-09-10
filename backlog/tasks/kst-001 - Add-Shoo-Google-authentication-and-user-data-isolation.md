---
id: KST-001
title: Add Shoo Google authentication and user data isolation
status: In Progress
assignee:
  - '@erik'
created_date: '2026-09-10 06:16'
updated_date: '2026-09-10 20:37'
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
1. Map every profile-scoped model and route plus current auth middleware.
2. Add Shoo token verification, account ownership, session and CSRF controls with migrations.
3. Gate backend and frontend routes, preserving dedicated extension auth.
4. Add route-matrix, token, session, migration, frontend, and two-user isolation tests.
5. Run full checks, independent Terra review, repair until clean, then integrate directly to main.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation started in feat/KST-001-shoo-auth. Old hand-written backlog.md will be removed in favor of Backlog.md CLI records.

Deployment c1417bc7-6e14-4e9b-84a6-38444c15e545 reached SUCCESS without Railway configuration changes. Live /health returned 200 with database connected; anonymous private provider and MCP-token APIs returned 401. Live Settings screenshot captured MCP server tokens form with Read/Write scopes and expiry controls, but token fetch returned 401. Shoo login reached Google Email or phone prompt with no existing browser session, so authenticated separate-profile/provider proof remains unavailable. Docs routes still return 200 because SHOO_AUTH_ENABLED is absent/false in Railway variables; production auth must be enabled before AC4 live proof.

Production variables set via Railway CLI: SHOO_AUTH_ENABLED=true, SHOO_APP_ORIGIN=https://kestrel-production-2597.up.railway.app, SHOO_JWKS_URL=https://shoo.dev/.well-known/jwks.json, FRONTEND_URL=https://kestrel-production-2597.up.railway.app, SESSION_COOKIE_SECURE=true, MCP_RESOURCE_URL=https://kestrel-production-2597.up.railway.app/mcp/. Local-code deployment b7afbae6-d812-4cb3-9603-4fd534710408 succeeded after stale GitHub deployment 9405513c crashed on missing z9a0b1c2d3e4. /health=200 database connected; /api/auth/shoo/me reports auth_required=true; private APIs return 401. SHOO_CLAIM_LEGACY_DATA remains unset/false pending operator backup and explicit one-time ownership claim.
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
<!-- COMMENTS:END -->
