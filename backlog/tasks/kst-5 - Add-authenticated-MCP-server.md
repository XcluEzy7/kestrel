---
id: KST-5
title: Add authenticated MCP server
status: Done
assignee: []
created_date: '2026-09-10 21:49'
updated_date: '2026-09-11 05:05'
labels: []
dependencies:
  - KST-001
references:
  - tools/kestrel-mcp/server.py
priority: high
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let local coding agents manage authenticated Kestrel data through a remote Streamable HTTP MCP endpoint.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Railway-hosted server exposes Streamable HTTP MCP
- [ ] #2 User can create, list, and revoke scoped MCP tokens after Google login
- [x] #3 Tokens resolve account and profile server-side and never accept caller-selected ownership
- [x] #4 Tools cover upload/import, discovery, application pipeline, follow-ups, contacts, skills, learning paths, personal analytics, safe settings, and AI provider selection
- [x] #5 Read and write scopes are distinct and secrets never appear in tool output
- [x] #6 Upload limits, destructive-action safeguards, write audit records, schemas, and cross-user isolation tests pass
- [x] #7 Existing optional MCP packaging and local use remain functional or have a documented migration path
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Independent MCP security audit passed: token verification, account/profile ownership, scopes, secret redaction, confirmation gates, audit records, transport auth, and SSRF boundary checks verified. Removed caller-supplied search_profile_id from MCP discovery tools.

Implementer: tests/test_mcp_server.py 20 passed, test_shoo_auth.py 8 passed, test_kst001_account_scoping.py 2 passed, test_extension_auth_ownership.py 3 passed, tools/tests/test_kestrel_mcp.py 20 passed. Audit: PASS, 0 blocking; judge: PASS, 0 blocking. Deployment c714099e-ee44-470c-8b7b-63ccf76aab14 SUCCESS; health 200 database connected; anonymous provider/MCP-token APIs and POST /mcp/ return 401. Google browser flow reached credential prompt; authenticated token lifecycle and MCP tool proof unavailable. Non-blocking follow-ups: stored URL scheme validation, token mint rate/cap, CSV status validation, wildcard escaping, CSP.

Release boundary: authenticated MCP token create/list/revoke and tool-call browser proof remains blocked at Shoo Google credential prompt; no authenticated lifecycle claim made. Anonymous /mcp/ rejection and code/test gates are verified.

Final release validation: Railway deployment 228fdc00-de50-44a3-8c5a-30d7acf446bd SUCCESS; /health 200 with database connected; anonymous provider, MCP-token, and /mcp/ requests 401. Browser reached Kestrel login and Shoo Google sign-in boundary; no authorized Google credentials, so authenticated MCP token lifecycle/tool proof remains unavailable.

Focused verification 2026-09-11: provider, inference, MCP, Shoo auth, account isolation, extension ownership, and MCP client tests passed: 152 passed, 2 warnings. Live MCP token lifecycle/tool calls remain unverified without authorized Shoo session.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-10 23:22
---
[judge] PASS @ 92ac826. Verifier ownership/scopes/redaction/confirm/audit verified independently (mcp_server.py:105-164,185-219). FOLLOW-UPs: (1) mcp_server.py:348,363 — contact linkedin_url lacks http/https scheme check unlike create_application:1075 (stored self-XSS on click); (2) mcp_server.py:525-570 + csv_import.py:155-163 — CSV import writes raw status without is_valid_transition; (3) shoo_auth.py:155-181 — no rate limit/cap on token minting; (4) mcp_server.py:262-293,707-735 — ilike search wildcard injection (own-account scope only); (5) main.py — no CSP/security headers (defense-in-depth). None crosses account boundary.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented authenticated Streamable HTTP MCP with account/profile binding, scopes, redaction, confirmations, audit records, and isolation. Verified by focused/full code gates, audit and judge PASS, Railway deployment SUCCESS, live health 200, and anonymous MCP auth rejection. Authenticated token/tool proof stops at Shoo Google sign-in without authorized credentials.
<!-- SECTION:FINAL_SUMMARY:END -->
