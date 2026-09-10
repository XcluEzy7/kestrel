---
id: KST-002
title: Add user-configured OpenAI-compatible inference
status: To Do
assignee: []
created_date: '2026-09-10 06:16'
labels: []
dependencies:
  - KST-001
references:
  - 'https://docs.ollama.com/cloud'
  - 'https://docs.ollama.com/api/authentication'
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let each authenticated user configure an OpenAI-compatible base URL and bearer API key, auto-discover account models, and select a default model. Include Ollama Cloud and supported-contract-gated Codex OAuth.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 User can create, test, edit, disable, and delete an OpenAI-compatible connection
- [ ] #2 Configuration accepts display name, provider type, base URL, bearer API key, and selected model
- [ ] #3 Backend normalizes base URLs and discovers models from GET {base_url}/models
- [ ] #4 Completion calls use POST {base_url}/chat/completions with selected model
- [ ] #5 Ollama Cloud works at https://ollama.com/v1 with an API key and local Ollama still works without a key
- [ ] #6 Credentials are encrypted at rest, redacted from API responses, and excluded from logs
- [ ] #7 Hosted deployments block loopback, private-network, metadata-service, unsafe redirect, oversized-response, and unbounded-time SSRF paths
- [ ] #8 Codex subscription OAuth ships only when research proves a supported OpenAI contract; no borrowed CLI credentials, token scraping, or undocumented credential extraction
- [ ] #9 Provider contract, URL validation, model discovery, isolation, frontend, and migration tests pass
<!-- AC:END -->
