# Quater

Quater is a typed Python API framework for APIs that humans use and agents can
safely operate.

The important bit is boring in the best way: HTTP calls and tool calls use the
same route, middleware, body parser, error handling, and response serialization.
Auth stays explicit. Normal HTTP routes use route-level `auth=...`; MCP uses
`mcp_auth` at the transport boundary, then optional route auth inside the tool
handler.

## Working On Quater

This repo uses `uv`.

```bash
uv sync --group dev
uv run pytest
uv run mypy src examples tests
uv run ruff check .
uv build
```

The documentation site uses VitePress:

```bash
npm install
npm run docs:dev
npm run docs:build
```

Release docs can be snapshotted before publishing:

```bash
npm run docs:snapshot -- 0.1
```

## Small App

```python
from quater import Quater, Request

app = Quater()


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/echo")
async def echo(request: Request) -> dict[str, object]:
    return {"received": await request.json()}
```

Run it with Granian on the RSGI path:

```bash
uv run granian examples.basic_app:app --interface rsgi
```

Use reload while building locally:

```bash
uv run granian examples.basic_app:app --interface rsgi --reload
```

Turn on request logs at the server:

```bash
uv run granian examples.basic_app:app --interface rsgi --access-log
```

ASGI and WSGI are there for compatibility:

```bash
uv run granian examples.asgi_compat:app --interface asgi
uv run granian examples.wsgi_compat:app --interface wsgi
```

## Docs Endpoints

These are on by default:

- `GET /docs` serves Swagger UI.
- `GET /openapi.json` serves the OpenAPI document.
- `GET /mcp/docs` shows the MCP tools you exposed.

OpenAPI docs are public unless you disable them. MCP docs use `mcp_auth` when
the app has one, which every tool-exposing app must have.

Move or disable them with paths:

```python
app = Quater(
    docs_path="/docs",
    openapi_path="/openapi.json",
    mcp_docs_path="/mcp/docs",
)

private_app = Quater(
    docs_path=None,
    openapi_path=None,
    mcp_docs_path=None,
)
```

## Handlers

Handlers are async functions. Quater binds path params, simple query params,
JSON body models, and `Request`.

```python
@app.get("/users/{id:int}")
async def get_user(id: int, include_email: bool = False) -> dict[str, object]:
    return {"id": id, "include_email": include_email}
```

Return plain Python values or response objects:

- `dict`, `list`, dataclasses, and `msgspec.Struct` values become JSON.
- `str` becomes text.
- `bytes` becomes bytes.
- `None` becomes `204 No Content`.
- `Response` subclasses are returned directly.

## Auth

Auth is per route. Public routes have no auth hook. Protected routes pass one to
the decorator. Returning `None` means `401 Unauthorized`.

```python
from quater import AuthContext, AuthRequest, Quater, Request

app = Quater()


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    if ctx.headers.get("authorization") != "Bearer demo-token":
        return None
    return AuthContext(subject="demo-user")


@app.get("/me", auth=authenticate)
async def me(request: Request) -> dict[str, str]:
    assert request.auth is not None
    return {"subject": request.auth.subject}
```

## MCP Tools

Routes are normal HTTP routes unless you opt in with `tool=True`.

If an app exposes even one tool, create it with `mcp_auth`. That hook protects
the MCP endpoint, the MCP docs page, tool discovery, and tool calls.

```python
app = Quater(
    mcp_docs_path="/mcp/docs",
    mcp_allowed_origins=["http://localhost:3000"],
    mcp_auth=authenticate,
)


@app.get(
    "/users/{id:int}",
    tool=True,
    auth=authenticate,
    description="Fetch one user by id.",
)
async def get_user(id: int, request: Request) -> dict[str, object]:
    assert request.auth is not None
    return {
        "id": id,
        "subject": request.auth.subject,
        "source": request.context.source,
        "tool": request.context.tool_name,
    }
```

Descriptions are required for tools. Use `description=` or a handler docstring.
Agents need real intent metadata. A name like `get_user` is not enough.

MCP lives at `POST /mcp`. The endpoint is fixed. There is no `mcp_path` option.

`mcp_auth` is checked on each HTTP request. `initialize` is not a login. Clients
must keep sending `Authorization: Bearer ...` for `initialize`, `tools/list`,
and every `tools/call`.

If `mcp_auth` and route `auth=` are the same function, Quater runs it once for a
tool call. If they are different functions, Quater runs both. Use that when the
MCP client token and route-level user or scope check are intentionally different.

HTTP calls see:

```python
request.context.source == "api"
request.context.tool_name is None
```

MCP `tools/call` calls see:

```python
request.context.source == "tool"
request.context.tool_name == "get_user"
```

Current MCP support: `initialize`, `notifications/initialized`, `tools/list`,
and `tools/call`.

Not in the MVP yet: SSE streaming, sessions, resumability, prompts, resources,
stdio, and server-to-client notifications.

## Public API

Common app code should import from `quater`:

```python
from quater import (
    AppConfig,
    AuthContext,
    AuthRequest,
    CORSConfig,
    Quater,
    Request,
    SignedCookieSigner,
    ToolAuditEvent,
)
```

The frozen surface is listed in
[docs/en/latest/api.md](docs/en/latest/api.md).

More detail:

- [Quickstart](docs/en/latest/quickstart.md)
- [Public API](docs/en/latest/api.md)
- [Security](docs/en/latest/security.md)
- [MCP](docs/en/latest/mcp.md)
