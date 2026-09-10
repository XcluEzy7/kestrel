# Kestrel MCP Server

MCP server that exposes Kestrel job search tools for Claude Code. Works from any directory.

Hosted deployments expose authenticated Streamable HTTP MCP at `/mcp`. Create a
scoped token after Shoo login with `POST /api/auth/shoo/mcp-tokens`, then send
`Authorization: Bearer <token>` to the hosted endpoint. Token secret appears
only in create response; list responses contain prefix and metadata only.

Local stdio packaging remains supported below. It is intentionally separate from
hosted MCP and continues using `KESTREL_API_KEY` as a Bearer token plus configured local profile.

## Tools

| Tool | Description |
|------|-------------|
| `list_pipeline` | List applications with optional status/search filters |
| `pipeline_stats` | Pipeline statistics (counts by status, trends) |
| `score_job` | Score a job description against user profile |
| `discover_jobs` | Run job discovery sweep across sources |

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

## Requirements

- Running Kestrel backend instance
- `mcp` Python SDK (`pip install mcp`)
- `httpx` (`pip install httpx`)
