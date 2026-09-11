---
id: KST-7
title: Auto-discover configured provider models
status: To Do
assignee: []
created_date: '2026-09-11 00:50'
labels:
  - feature
  - bug
dependencies: []
priority: high
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Allow OpenAI-compatible provider setup with base URL and API key alone. Discover models through the provider models endpoint, choose a usable default, and let users override it without requiring an exact model name during initial setup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Provider connection creation accepts omitted model and discovers a default when provider reports models
- [ ] #2 Draft frontend setup can discover models before save and displays selectable results
- [ ] #3 Completion and test paths use a discovered or explicitly selected model and return safe errors when none exists
- [ ] #4 Tests cover OpenAI-compatible, Ollama Cloud, local Ollama, account isolation, and provider failures
<!-- AC:END -->
