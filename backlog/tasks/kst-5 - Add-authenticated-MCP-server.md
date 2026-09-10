---
id: KST-5
title: Add authenticated MCP server
status: In Progress
assignee: []
created_date: '2026-09-10 21:49'
updated_date: '2026-09-10 23:22'
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
- [ ] #1 Railway-hosted server exposes Streamable HTTP MCP
- [ ] #2 User can create, list, and revoke scoped MCP tokens after Google login
- [ ] #3 Tokens resolve account and profile server-side and never accept caller-selected ownership
- [ ] #4 Tools cover upload/import, discovery, application pipeline, follow-ups, contacts, skills, learning paths, personal analytics, safe settings, and AI provider selection
- [ ] #5 Read and write scopes are distinct and secrets never appear in tool output
- [ ] #6 Upload limits, destructive-action safeguards, write audit records, schemas, and cross-user isolation tests pass
- [ ] #7 Existing optional MCP packaging and local use remain functional or have a documented migration path
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Independent MCP security audit passed: token verification, account/profile ownership, scopes, secret redaction, confirmation gates, audit records, transport auth, and SSRF boundary checks verified. Removed caller-supplied search_profile_id from MCP discovery tools.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-10 23:22
---
[judge] PASS @ 92ac826. Verifier ownership/scopes/redaction/confirm/audit verified independently (mcp_server.py:105-164,185-219). FOLLOW-UPs: (1) mcp_server.py:348,363 — contact linkedin_url lacks http/https scheme check unlike create_application:1075 (stored self-XSS on click); (2) mcp_server.py:525-570 + csv_import.py:155-163 — CSV import writes raw status without is_valid_transition; (3) shoo_auth.py:155-181 — no rate limit/cap on token minting; (4) mcp_server.py:262-293,707-735 — ilike search wildcard injection (own-account scope only); (5) main.py — no CSP/security headers (defense-in-depth). None crosses account boundary.
---
<!-- COMMENTS:END -->
