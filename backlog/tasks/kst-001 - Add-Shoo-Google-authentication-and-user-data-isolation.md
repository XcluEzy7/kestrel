---
id: KST-001
title: Add Shoo Google authentication and user data isolation
status: In Progress
assignee:
  - '@erik'
created_date: '2026-09-10 06:16'
updated_date: '2026-09-10 06:17'
labels: []
dependencies: []
references:
  - 'https://docs.shoo.dev/docs/server-verification'
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
<!-- SECTION:NOTES:END -->
