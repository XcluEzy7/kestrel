---
id: KST-003
title: Add authenticated MCP server
status: To Do
assignee: []
created_date: '2026-09-10 06:16'
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
