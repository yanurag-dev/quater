# Public API

This is the surface Quater expects users to import for the first release.
Everything else can still move while the framework is pre-release.

Use top-level imports for normal app code:

```python
from quater import (
    AppConfig,
    AuthContext,
    AuthRequest,
    BytesResponse,
    CORSConfig,
    EmptyResponse,
    HTMLResponse,
    HTTPError,
    JSONResponse,
    Quater,
    RedirectResponse,
    Request,
    Response,
    SignedCookieSigner,
    StreamResponse,
    TextResponse,
    ToolAuditEvent,
)
```

## App

`Quater()` is the application object.

```python
app = Quater(
    allowed_hosts=["api.example.com"],
    max_body_size="2mb",
    docs_path="/docs",
    openapi_path="/openapi.json",
    mcp_docs_path="/mcp/docs",
    mcp_auth=authenticate,
)
```

The snippet assumes you already defined `authenticate`. For an app with no MCP
tools, omit `mcp_auth`.

Stable constructor options:

- `name`
- `config`
- `debug`
- `security`
- `allowed_hosts`
- `trusted_proxies`
- `max_body_size`
- `cors`
- `content_security_policy`
- `docs_path`
- `openapi_path`
- `mcp_docs_path`
- `mcp_allowed_origins`
- `mcp_auth`
- `mcp_audit`

The MCP JSON-RPC endpoint is always `/mcp`. There is no `mcp_path` option. If
an app exposes tools, `mcp_auth` is required.

## Routes

Route decorators are the main API:

```python
@app.get("/items/{id:int}")
async def get_item(id: int) -> dict[str, int]:
    return {"id": id}
```

Available decorators:

- `app.get`
- `app.post`
- `app.put`
- `app.patch`
- `app.delete`
- `app.route`

Stable decorator options:

- `name`
- `description`
- `tool`
- `auth`
- `metadata`
- `before`
- `after`
- `around`
- `exception_handlers`

`tool=True` exposes the route through MCP. Tool routes must have a useful
description, either through `description=` or the handler docstring. The app
must also be created with `mcp_auth`.

## Request And Context

Use `Request` when the handler needs headers, body access, auth, or the call
source.

```python
@app.get("/whoami")
async def whoami(request: Request) -> dict[str, object]:
    return {
        "source": request.context.source,
        "tool": request.context.tool_name,
    }
```

`request.context.source` is `"api"` for HTTP calls, `"mcp"` for MCP protocol
requests such as `initialize` and `tools/list`, and `"tool"` for MCP
`tools/call`.

## Auth

Auth hooks receive `AuthRequest` and return `AuthContext | None`.

```python
async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    if ctx.headers.get("authorization") != "Bearer demo-token":
        return None
    return AuthContext(subject="demo-user")
```

Attach the hook per route:

```python
@app.get("/me", auth=authenticate)
async def me(request: Request) -> dict[str, str]:
    assert request.auth is not None
    return {"subject": request.auth.subject}
```

For MCP tools, the same hook can also be passed as `mcp_auth`:

```python
app = Quater(mcp_auth=authenticate)
```

`mcp_auth` protects MCP protocol requests and `/mcp/docs`. Route `auth=` still
protects individual handlers. If both point to the same function, Quater runs it
once for an MCP tool call.

## Responses

Use response objects when you need explicit status, headers, content type, or
streaming:

```python
from quater import JSONResponse, StreamResponse, TextResponse
```

Plain return values still cover the common case:

- `dict` and `list` become JSON.
- `str` becomes `TextResponse`.
- `bytes` becomes `BytesResponse`.
- `None` becomes `204 No Content`.

## Config Helpers

`CORSConfig` is the public CORS helper:

```python
app = Quater(
    cors=CORSConfig(allowed_origins=("https://app.example.com",)),
)
```

`AppConfig` is useful when several app instances should share one base config:

```python
base = AppConfig(allowed_hosts=("api.example.com",))
app = Quater(config=base)
```

`SignedCookieSigner` signs small cookie values with HMAC:

```python
signer = SignedCookieSigner("new-secret", fallback_secrets=["old-secret"])
cookie_value = signer.sign("user_123")
```

## MCP Audit

Use `ToolAuditEvent` to type an audit hook:

```python
async def audit(event: ToolAuditEvent) -> None:
    print(event.tool_name, event.subject, event.success)


app = Quater(
    mcp_auth=authenticate,
    mcp_audit=audit,
)
```

Tool arguments are redacted before they reach the hook.

## Advanced Imports

These modules are public, but most apps do not need them:

- `quater.typing` for `Authenticate`, `LifespanHook`, and `RequestContext`.
- `quater.exceptions` for specific framework exceptions.
- `quater.adapters` when a server wants an explicit adapter object.

Do not import `quater._router`, `quater.docs.*`, or `quater.tools.registry` from
application code. Those are framework internals for now.
