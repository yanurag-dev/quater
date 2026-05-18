---
name: quater-apps
description: Operate applications built with Quater. Use when an agent needs to discover or call Quater MCP tools, Quater CLI actions, remote Quater actions, or HTTP endpoints; configure bearer-token access; use dry-run and approval flows; inspect tool/action schemas; or safely operate a deployed Quater application.
---

# Quater Apps

Use this skill to operate an existing Quater application. Quater apps can expose one
handler through HTTP, MCP tools, and CLI actions, but each surface is opt-in.
Discover the exposed surface before calling anything.

If the current agent does not support skills, treat this file and the linked
references as project instructions.

## Live Docs

Use the bundled references for the immediate operating rules. Use the live
Quater docs when you need the full explanation or exact framework behavior:

- Overview: https://quater.devilsautumn.com/en/latest/
- MCP tools: https://quater.devilsautumn.com/en/latest/mcp
- CLI actions: https://quater.devilsautumn.com/en/latest/actions
- Auth model: https://quater.devilsautumn.com/en/latest/auth-model
- Security: https://quater.devilsautumn.com/en/latest/security
- Deployment: https://quater.devilsautumn.com/en/latest/deployment

## Operating Workflow

1. Identify the available access path: MCP URL, remote CLI name, local
   `QUATER_APP`, or direct HTTP API.
2. Discover tools or actions before calling them. Never invent names or
   arguments.
3. Describe the selected tool or action before use when the command is
   available.
4. Use dry-run before mutating CLI actions.
5. Require approval tokens for `needs_approval` operations. Do not fake or guess
   approval tokens.
6. Send auth on every request or command that needs it. Never print tokens,
   cookies, or authorization headers.
7. Report safe errors clearly. Do not recommend weakening auth or disabling
   production checks.

## Choose The Surface

- **MCP**: use when an MCP URL is available or the user asks an AI agent to call
  Quater tools. Read `references/mcp.md`.
- **CLI actions**: use when the `quater` CLI is available, when a remote is
  configured, or when the user asks for operational commands. Read
  `references/cli-actions.md`.
- **HTTP**: use when the user gives normal API docs, a route URL, or an endpoint
  that is not exposed as MCP/CLI.

Prefer MCP or CLI actions over clicking through a frontend. Prefer HTTP when the
operation is a file upload, because Quater keeps `File` parameters HTTP-only in
this release.

## Safety Defaults

- Treat route descriptions and schemas as the source of truth.
- Do not pass framework internals such as `request`, `auth`, `state`, resources,
  or database sessions as tool/action arguments.
- Do not retry non-idempotent operations after timeouts unless the user confirms
  it is safe.
- Do not persist credentials in skill files, notes, examples, or command
  history.
- Do not call destructive actions without an explicit user request and, when
  required, a valid approval token.

For more detail, read `references/auth.md` and `references/safety.md`.

## Common Errors

- `401 Unauthorized`: the surface auth or route auth denied the call.
- `approval_required`: ask the user or approval system for a token for that
  exact action and argument hash.
- `Unknown tool` or `Unknown CLI action`: rediscover tools/actions and check the
  route was exposed with `tool=True` or `cli=True`.
- `Routes with File parameters cannot be exposed as MCP tools or CLI actions`:
  use HTTP for the upload route.
