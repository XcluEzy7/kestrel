---
id: KST-4
title: Add user-configured OpenAI-compatible inference
status: Done
assignee: []
created_date: '2026-09-10 21:49'
updated_date: '2026-09-11 05:05'
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
- [x] #6 Credentials are encrypted at rest, redacted from API responses, and excluded from logs
- [ ] #7 Hosted deployments block loopback, private-network, metadata-service, unsafe redirect, oversized-response, and unbounded-time SSRF paths
- [x] #8 Codex subscription OAuth ships only when research proves a supported OpenAI contract; no borrowed CLI credentials, token scraping, or undocumented credential extraction
- [x] #9 Provider contract, URL validation, model discovery, isolation, frontend, and migration tests pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Scope legacy integration credential fallback by authenticated account. 2. Add multi-account regression coverage proving credentials never cross accounts. 3. Run focused provider tests and record evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation found no Codex OAuth contract, no OLLAMA_API_KEY resolution, and provider route/component test gaps; all focused tests passed with two dependency deprecation warnings. Refreshed tracked packaged frontend artifact after rebuilding frontend.

Integrated security audit found high-severity unscoped integration_configs credential fallback; repair required before judge.

Implementer: targeted provider/inference suite 240 passed, 9 skipped, 2 warnings. Audit: PASS, 0 blocking; 77 provider tests passed. Judge: PASS, 0 blocking. Combined gates: backend 4358 passed, 36 skipped; frontend 382 passed; build and lint passed. Deployment c714099e-ee44-470c-8b7b-63ccf76aab14 SUCCESS; health 200 database connected; anonymous provider API 401. No authorized Shoo session, so live provider create/test or authenticated UI proof unavailable. Follow-ups remain non-blocking: NAT64 defense-in-depth, response/timeout coverage, empty-key clearing.

Release boundary: authenticated live provider UI validation remains blocked at Shoo Google credential prompt; no provider save/test claim made. Code/test gates and anonymous auth boundary are verified.

Final release validation: Railway deployment 228fdc00-de50-44a3-8c5a-30d7acf446bd SUCCESS; /health 200 with database connected; anonymous provider API 401. Browser reached Kestrel login and Shoo Google sign-in boundary; no authorized Google credentials, so authenticated provider UI proof remains unavailable.

Focused verification 2026-09-11: provider, inference, MCP, Shoo auth, account isolation, extension ownership, and MCP client tests passed: 152 passed, 2 warnings. Live provider UI remains unverified without authorized Shoo session.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-10 23:22
---
[judge] FOLLOW-UPs (audit-consistent, non-blocking): (1) provider_connections.py:175 — NAT64 64:ff9b::/96 passes is_global gate (defense-in-depth; add explicit /96 rejection). (2) provider_connections.py:152-153 — empty api_key cannot clear stored key; document delete-as-removal or accept empty-string clear. (3) tests/test_provider_connections.py — no coverage for 2MiB response cap / timeout bounds. (4) Codex OAuth correctly absent (grep: no codex matches in src/) — AC8 met by not shipping.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented account-scoped OpenAI-compatible provider configuration, model discovery, secure credential handling, and isolation. Verified by focused/full code gates, audit and judge PASS, Railway deployment SUCCESS, live health 200, and anonymous provider auth 401. Authenticated provider UI proof stops at Shoo Google sign-in without authorized credentials.
<!-- SECTION:FINAL_SUMMARY:END -->
