# MCP

Quater exposes selected routes as MCP tools through the same app that serves
normal HTTP APIs.

## Enable MCP

```python
from quater import Quater

app = Quater(
    mcp_enabled=True,
    mcp_allowed_origins=["http://localhost:3000"],
)
```

The endpoint defaults to `/mcp`.

## Expose A Tool

Routes are not tools unless they opt in and define a description:

```python
@app.get("/users/{id:int}", tool=True, description="Fetch one user by id.")
async def get_user(id: int) -> dict[str, int]:
    return {"id": id}
```

If `description=` is not set, Quater uses the handler docstring. Tool routes
without either one fail when the route is registered.

The route still works as a normal API:

```text
GET /users/123
```

It also appears in MCP discovery:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

Tool calls use JSON-RPC:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_user",
    "arguments": {"id": 123}
  }
}
```

## Request Context

The same handler can be reached through HTTP or MCP. Use
`request.context.source` to distinguish the current invocation:

```python
@app.get("/users/{id:int}", tool=True, description="Fetch one user by id.")
async def get_user(id: int, request: Request) -> dict[str, object]:
    return {
        "id": id,
        "source": request.context.source,
        "tool": request.context.tool_name,
    }
```

Normal HTTP calls use:

```python
request.context.source == "api"
request.context.tool_name is None
```

MCP tool calls use:

```python
request.context.source == "tool"
request.context.tool_name == "get_user"
```

## Auth

MCP tool calls use the auth hook attached to the underlying route. A protected
HTTP route stays protected when exposed as a tool, and a public route stays
public.

```python
@app.get(
    "/users/{id:int}",
    tool=True,
    auth=authenticate,
    description="Fetch one protected user by id.",
)
async def get_user(id: int, request: Request) -> dict[str, object]:
    assert request.auth is not None
    return {"id": id, "subject": request.auth.subject}
```

## Input Schemas

Quater generates `inputSchema` from path parameters, query parameters, and one
JSON body parameter. Required fields follow the handler signature and body model.

## Auditing

Pass `mcp_audit` to receive sanitized tool-call events:

```python
from quater.tools.audit import ToolAuditEvent


async def audit(event: ToolAuditEvent) -> None:
    print(event.tool_name, event.subject, event.success)


app = Quater(mcp_enabled=True, mcp_audit=audit)
```

Arguments are redacted before they reach the audit hook.

## Implemented Now

- `POST /mcp`
- JSON-RPC request/response
- `tools/list`
- `tools/call`
- auth parity with HTTP
- origin validation
- audit hook support

## Deferred

- SSE streaming
- resumability
- sessions
- server-to-client notifications
- prompts
- resources
- stdio transport
- full MCP SDK adapter
