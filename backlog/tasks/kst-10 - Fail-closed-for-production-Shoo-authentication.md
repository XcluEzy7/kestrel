---
id: KST-10
title: Fail closed for production Shoo authentication
status: To Do
assignee: []
created_date: '2026-09-23 07:22'
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
