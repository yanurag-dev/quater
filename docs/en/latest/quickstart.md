# Quickstart

Start with one object.

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

Run it:

```bash
uv run granian examples.basic_app:app --interface rsgi
```

Reload while editing:

```bash
uv run granian examples.basic_app:app --interface rsgi --reload
```

Request logs come from Granian:

```bash
uv run granian examples.basic_app:app --interface rsgi --access-log
```

## Generated Docs

Quater serves docs by default:

- `/docs` for Swagger UI.
- `/openapi.json` for OpenAPI.
- `/mcp/docs` for exposed MCP tools. It is empty until you expose a tool.

If you expose tools, pass `mcp_auth` when creating the app. Quater uses that
hook for MCP protocol requests and the MCP docs page.

Set a path to `None` to turn that page off:

```python
app = Quater(
    docs_path=None,
    openapi_path=None,
    mcp_docs_path=None,
)
```

If `docs_path` is enabled, `openapi_path` must also be enabled. Swagger UI needs
the JSON document to render anything useful.

## Binding

Path parameters come from route patterns:

```python
@app.get("/users/{id:int}")
async def get_user(id: int) -> dict[str, int]:
    return {"id": id}
```

Simple scalar parameters come from the query string:

```python
@app.get("/search")
async def search(q: str, page: int = 1) -> dict[str, object]:
    return {"q": q, "page": page}
```

Complex parameters come from the JSON body. `msgspec.Struct` is the best fit when
you care about speed and typed input.

```python
import msgspec


class UserIn(msgspec.Struct):
    name: str
    age: int


@app.post("/users")
async def create_user(user: UserIn) -> dict[str, object]:
    return {"name": user.name, "age": user.age}
```

## First MCP Tool

Expose a route as a tool with `tool=True`. Tool descriptions are required because
agents read them during `tools/list`.

```python
from quater import AuthContext, AuthRequest, Quater, Request


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    if ctx.headers.get("authorization") != "Bearer demo-token":
        return None
    return AuthContext(subject="demo-user")


app = Quater(mcp_auth=authenticate)


@app.get(
    "/users/{id:int}",
    tool=True,
    auth=authenticate,
    description="Fetch one user.",
)
async def get_user(id: int, request: Request) -> dict[str, object]:
    assert request.auth is not None
    return {"id": id, "subject": request.auth.subject}
```

`mcp_auth` protects the MCP endpoint itself. Route `auth=` protects the handler.
When both use the same function, Quater authenticates once for an MCP tool call.

## Responses

Handlers can return plain values or response objects:

- `dict`, `list`, dataclasses, and `msgspec.Struct` values become JSON.
- `str` becomes text.
- `bytes` becomes bytes.
- `None` becomes `204 No Content`.
- `Response` subclasses are returned directly.

## Adapters

RSGI is the primary path because it maps directly to Granian's fast Python
interface.

```bash
uv run granian examples.basic_app:app --interface rsgi
```

ASGI and WSGI use the same `Quater.handle()` core:

```bash
uv run granian examples.asgi_compat:app --interface asgi
uv run granian examples.wsgi_compat:app --interface wsgi
```

You can also pass the explicit adapter if a server wants it:

- `app.rsgi`
- `app.asgi`
- `app.wsgi`

WebSocket scopes are rejected for now. Quater does not expose a framework-level
WebSocket API in the MVP.
