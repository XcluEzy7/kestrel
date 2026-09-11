---
id: KST-6
title: Add controlled debug authentication access
status: In Progress
assignee:
  - '@Erik'
created_date: '2026-09-11 00:50'
updated_date: '2026-09-11 00:58'
labels:
  - feature
  - security
dependencies: []
priority: high
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide explicit opt-in access for frontend debugging through the deployed app without weakening default Shoo authentication. Debug access must fail closed unless configured, require a secret, create only a dedicated debug account/profile, and expose clear non-production warnings.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Default configuration keeps Shoo authentication unchanged and debug access unavailable
- [ ] #2 Configured debug access requires a secret and establishes a normal server session with CSRF protection
- [ ] #3 Debug account/profile ownership remains isolated from other accounts
- [ ] #4 Tests cover disabled, invalid-secret, successful-login, and session-bound behavior
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add explicit DEBUG_AUTH_ENABLED and secret settings with fail-closed production defaults. 2. Add token-checked debug login endpoint that creates standard Account/AuthSession cookies and CSRF token for a dedicated stable debug identity. 3. Add frontend debug-login affordance and warning only when backend advertises debug mode. 4. Add focused API tests for disabled, invalid, successful, CSRF, and account isolation paths.
<!-- SECTION:PLAN:END -->
