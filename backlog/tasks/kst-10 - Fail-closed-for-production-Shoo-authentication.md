---
id: KST-10
title: Fail closed for production Shoo authentication
status: In Progress
assignee:
  - '@Erik'
created_date: '2026-09-23 07:22'
updated_date: '2026-09-23 07:23'
labels:
  - bug
  - security
dependencies: []
priority: high
type: bug
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A fresh container defaults SHOO_AUTH_ENABLED to false, causing private routes to accept anonymous requests and unscoped account data. Preserve explicitly chosen local unauthenticated development mode, but refuse an unsafe production startup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Production-style startup without enabled Shoo authentication fails closed before serving private routes
- [ ] #2 Anonymous requests cannot read another account’s profiles in production mode
- [ ] #3 Explicit local-development unauthenticated mode remains usable
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce anonymous cross-account exposure in a production-style configuration; inspect Settings validation, Docker defaults and private-route dependencies. 2. Add an explicit production mode in src/career_os/config.py and set it in Dockerfile; reject startup when Shoo auth is disabled, preserving local development configuration. 3. Strengthen existing tests/test_auth.py and account-scoping tests; prove rejected anonymous private access and local mode behavior. 4. Run targeted tests and configuration smoke; inspect security-sensitive diffs.
<!-- SECTION:PLAN:END -->
