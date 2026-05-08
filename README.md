# Quater

Quater is a typed Python API framework for APIs that humans use and agents can
safely operate.

It keeps one application pipeline for normal HTTP routes and MCP tools:
security, auth, middleware, routing, handler binding, serialization, and error
handling all run through the same core.

## Install For Development

Use `uv` for local development:

```bash
uv sync --group dev
uv run pytest
uv run mypy src examples tests
uv run ruff check .
uv build
```

## Quickstart

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

Run the RSGI fast path with Granian:

```bash
uv run granian examples.basic_app:app --interface rsgi
```

Compatibility adapters are available for ASGI and WSGI:

```bash
uv run granian examples.asgi_compat:app --interface asgi
uv run granian examples.wsgi_compat:app --interface wsgi
```

## Route Handlers

Handlers are async functions. Quater binds path params, simple query params,
JSON body models, and `Request` automatically.

```python
@app.get("/users/{id:int}")
async def get_user(id: int, include_email: bool = False) -> dict[str, object]:
    return {"id": id, "include_email": include_email}
```

Common return values become responses:

- `dict`, `list`, dataclasses, and `msgspec.Struct` values become JSON.
- `str` becomes a text response.
- `bytes` becomes a byte response.
- `None` becomes an empty `204` response.
- `Response` subclasses are returned as-is.

## Auth

Auth is configured per route. A public route has no auth hook; a protected route
passes an auth hook to the route decorator. Returning `None` produces
`401 Unauthorized`.

```python
from quater import Quater, AuthContext, AuthRequest, Request


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    token = ctx.headers.get("authorization")
    if token != "Bearer demo-token":
        return None
    return AuthContext(subject="demo-user")


app = Quater()


@app.get("/me", auth=authenticate)
async def me(request: Request) -> dict[str, str]:
    assert request.auth is not None
    return {"subject": request.auth.subject}
```

## Access Logs

Quater leaves request access logging to the server, matching how FastAPI gets
request lines from Uvicorn rather than from FastAPI itself. With Granian, enable
server access logs explicitly:

```bash
uv run granian examples.basic_app:app --interface rsgi --access-log
```

## MCP Tools

Routes are normal APIs by default. A route becomes visible to MCP only when
registered with `tool=True`. Tool routes must define a description, either with
`description=` or a handler docstring, so `tools/list` gives agents useful
intent metadata.

```python
@app.get(
    "/users/{id:int}",
    tool=True,
    auth=authenticate,
    description="Fetch one user by id.",
)
async def get_user(id: int, request: Request) -> dict[str, object]:
    return {
        "id": id,
        "source": request.context.source,
        "tool": request.context.tool_name,
    }
```

Normal HTTP calls see:

```python
request.context.source == "api"
request.context.tool_name is None
```

MCP `tools/call` calls see:

```python
request.context.source == "tool"
request.context.tool_name == "get_user"
```

Enable MCP with:

```python
app = Quater(
    mcp_enabled=True,
    mcp_allowed_origins=["http://localhost:3000"],
)
```

MVP MCP support includes `POST /mcp`, JSON-RPC `tools/list`, and JSON-RPC
`tools/call`. Tool calls execute the auth hook attached to the underlying route.
SSE streaming, resumability, sessions, prompts, resources, stdio, and
server-to-client notifications are intentionally deferred.

More detail lives in `docs/quickstart.md`, `docs/security.md`, and `docs/mcp.md`.
