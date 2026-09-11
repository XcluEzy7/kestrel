---
id: KST-8
title: Add mobile-native PWA shell
status: To Do
assignee: []
created_date: '2026-09-11 00:50'
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
