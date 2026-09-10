# Kestrel MCP Server

MCP server that exposes Kestrel job search tools for Claude Code. Works from any directory.

Hosted deployments expose authenticated Streamable HTTP MCP at `/mcp`. Create a
scoped token after Shoo login with `POST /api/auth/shoo/mcp-tokens`, then send
`Authorization: Bearer <token>` to the hosted endpoint. Token secret appears
only in create response; list responses contain prefix and metadata only.

Local stdio packaging remains supported below. It is intentionally separate from
hosted MCP and continues using `KESTREL_API_KEY` as a Bearer token plus configured local profile.
To migrate an agent to hosted MCP, set `KESTREL_MCP_URL=https://your-host/mcp` and
`KESTREL_MCP_TOKEN=<scoped token>`. Hosted mode derives profile/account ownership
from token claims; `KESTREL_PROFILE_ID` is ignored for hosted calls. Remove those
two variables to keep local REST-over-stdio mode.

## Tools

| Tool | Description |
|------|-------------|
| `list_pipeline` | List applications with optional status/search filters |
| `pipeline_stats` | Pipeline statistics (counts by status, trends) |
| `score_job` | Score a job description against user profile |
| `discover_jobs` | Run job discovery sweep across sources |
| `run_discovery` | Hosted account-owned discovery execution |
| `create_skill`, `update_skill` | Mutate account-owned skills |
| `create_learning_resource`, `update_learning_resource` | Manage learning paths |
| `select_provider`, `update_provider_connection` | Select or update account-owned AI provider |

## Setup

Add to `~/.claude/mcp.json` (global) or project `.mcp.json`:

```json
{
  "mcpServers": {
    "kestrel": {
      "command": "/path/to/kestrel/.venv/bin/python",
      "args": ["tools/kestrel-mcp/server.py"],
      "cwd": "/path/to/kestrel",
      "env": {
        "KESTREL_URL": "http://localhost:8100",
        "KESTREL_PROFILE_ID": "1"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KESTREL_URL` | `http://localhost:8100` | Base URL of running Kestrel instance |
| `KESTREL_PROFILE_ID` | `1` | Profile ID to scope operations |
| `KESTREL_API_KEY` | (empty) | Bearer token if auth is enabled |
| `KESTREL_MCP_URL` | (empty) | Hosted Streamable HTTP MCP endpoint; enables hosted mode |
| `KESTREL_MCP_TOKEN` | (empty) | Scoped hosted MCP token (keep secret) |

## Requirements

- Running Kestrel backend instance
- `mcp` Python SDK (`pip install mcp`)
- `httpx` (`pip install httpx`)
