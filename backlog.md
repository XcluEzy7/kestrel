# Backlog

Kestrel uses this file as its project task ledger. Each item has a stable `KST-NNN` ID used in branch names, commit scopes, pull requests, and review evidence.

## Status values

- `ready`: approved and not started
- `in-progress`: active work
- `blocked`: waiting on a decision or external dependency
- `review`: implementation complete and under validation
- `done`: merged and verified

## Tasks

### KST-001: Add Shoo Google authentication and user data isolation

- Status: in-progress
- Depends on: none
- Branch: `feat/KST-001-shoo-auth`
- Goal: Require verified Shoo Google identity for private Kestrel data and bind every private record to its authenticated owner.
- Acceptance:
  - Backend verifies Shoo ID token signature, issuer, audience, and expiration.
  - Secure server session supports login, logout, expiration, and CSRF protection.
  - Profiles and private domain records resolve through authenticated ownership rather than trusted caller-supplied ownership.
  - Private API routes and application pages reject anonymous access.
  - Public routes are limited to login/auth flow, health, and required static files.
  - Personal analytics remain private.
  - Two-account isolation tests prove cross-user reads and writes fail.
  - Existing single-profile data receives a safe, documented ownership migration path.

### KST-002: Add user-configured OpenAI-compatible inference

- Status: ready
- Depends on: KST-001
- Branch: `feat/KST-002-openai-compatible`
- Goal: Let each authenticated user configure an OpenAI-compatible base URL and API key, auto-discover models, and select a default model. Include Ollama Cloud and supported Codex OAuth.
- Acceptance:
  - User can create, test, edit, disable, and delete an OpenAI-compatible connection.
  - Configuration accepts display name, provider type, base URL, bearer API key, and selected model.
  - Backend normalizes base URLs and discovers models from `GET {base_url}/models`.
  - Completion calls use `POST {base_url}/chat/completions` with selected model.
  - Ollama Cloud works at `https://ollama.com/v1` with `OLLAMA_API_KEY`; local Ollama still works without a key.
  - Credentials are encrypted at rest, redacted from every API response, and excluded from logs.
  - Hosted deployments block loopback, private-network, metadata-service, unsafe redirect, oversized-response, and unbounded-time SSRF paths.
  - Codex subscription OAuth ships only if research proves a supported OpenAI contract. Otherwise task records supported alternatives without borrowing CLI credentials, scraping tokens, or depending on undocumented credential extraction.
  - Provider contract, URL validation, model discovery, isolation, frontend, and migration tests pass.

### KST-003: Add authenticated MCP server

- Status: ready
- Depends on: KST-001
- Branch: `feat/KST-003-authenticated-mcp`
- Goal: Let local coding agents manage authenticated Kestrel data through a remote MCP endpoint.
- Acceptance:
  - Railway-hosted server exposes Streamable HTTP MCP.
  - User can create, list, and revoke scoped MCP tokens after Google login.
  - Tokens resolve account and profile server-side and never accept caller-selected ownership.
  - Tools cover upload/import, discovery, application pipeline, follow-ups, contacts, skills, learning paths, personal analytics, safe settings, and AI provider selection.
  - Read and write scopes are distinct; secrets never appear in tool output.
  - Upload limits, destructive-action safeguards, write audit records, schemas, and cross-user isolation tests pass.
  - Existing optional MCP packaging and local use remain functional or receive a documented migration path.

## Delivery

1. Validate and merge KST-001.
2. Rebase KST-002 and KST-003 on verified KST-001.
3. Validate and merge KST-002 and KST-003.
4. Run combined backend, frontend, security, migration, and MCP checks.
5. Push `main`, verify Railway deployment, then run authorized production smoke tests.
