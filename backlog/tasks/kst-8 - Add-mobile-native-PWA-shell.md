---
id: KST-8
title: Add mobile-native PWA shell
status: In Progress
assignee:
  - '@Erik'
created_date: '2026-09-11 00:50'
updated_date: '2026-09-11 00:58'
labels:
  - feature
  - frontend
dependencies: []
priority: high
type: feature
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make Kestrel installable and usable as a mobile-first PWA while preserving desktop behavior. Add install metadata, offline asset shell, and responsive navigation suitable for narrow screens.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Built frontend includes valid manifest metadata, theme colors, and standalone display configuration
- [ ] #2 Production frontend registers a service worker that caches the app shell without caching private API responses
- [ ] #3 Navigation works at 375px without horizontal overflow and exposes accessible mobile controls
- [ ] #4 Tests or smoke checks cover manifest registration and responsive navigation behavior
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add manifest and icons through Vite public assets with standalone metadata and theme colors. 2. Register a minimal production-only service worker that caches same-origin app-shell assets and never API responses. 3. Refactor Layout navigation into accessible mobile menu with responsive sizing and no horizontal overflow at 375px. 4. Add focused frontend tests and build smoke checks.
<!-- SECTION:PLAN:END -->
