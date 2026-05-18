# Auth Model

Quater has layered auth. Keep the layers separate.

## MCP

`mcp_auth` protects the MCP surface:

- `initialize`
- `tools/list`
- `tools/call`
- `/mcp/docs`

Route `auth=` protects the selected handler after a tool call resolves to a
route.

Both gates can run for one tool call. If either denies, do not call the handler.

## CLI

`cli_auth` protects local and remote CLI discovery and calls:

- `actions list`
- `actions search`
- `actions describe`
- dry-run
- action execution

Route `auth=` still protects the handler.

## HTTP

Normal HTTP routes are public unless the route or route group declares `auth=`.
Do not assume MCP or CLI auth protects normal HTTP requests.

## Approval

Auth identifies the caller. Approval confirms a specific sensitive operation
should run for that caller and argument set.

`needs_approval=True` is an extra gate for MCP tools and CLI actions. It is not a
replacement for auth.

## Agent Rules

- Send credentials only through the configured auth mechanism.
- Do not log or summarize tokens.
- Do not downgrade from route auth to surface auth.
- If auth fails, report denial and stop.
- If the user asks to bypass auth, refuse the bypass and suggest configuring the
  backend correctly.
