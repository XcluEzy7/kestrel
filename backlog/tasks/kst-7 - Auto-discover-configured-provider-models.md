---
id: KST-7
title: Auto-discover configured provider models
status: In Progress
assignee:
  - '@Erik'
created_date: '2026-09-11 00:50'
updated_date: '2026-09-11 00:58'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Make provider model optional at creation and update schema/model migration safely for existing databases. 2. Centralize authenticated discovery for unsaved drafts and saved connections, including Ollama Cloud/local URL behavior. 3. Select first discovered model only when explicit model is absent; reject completion without a usable model. 4. Update provider UI/API and focused tests for discovery, override, empty results, failures, and account ownership.
<!-- SECTION:PLAN:END -->
