# Quater Manual

This manual explains how Quater helps you build Python backends that people can
use through normal APIs and AI agents can operate through explicit tools and
actions.

## Prerequisites

You should know async Python, HTTP handlers, and basic type annotations. You do
not need prior MCP knowledge; the [MCP guide](/en/dev/mcp) starts with the
protocol model.

## The Short Version

Quater is for backends that need to serve people and services through normal
APIs, while also exposing selected views directly to AI agents and
MCP clients.

You declare a route, then opt it into the surfaces you want:

- HTTP by declaring the route.
- MCP by adding `tool=True`.
- CLI by adding `cli=True`.

That keeps application logic in one place instead of spreading it across API
routes, tool wrappers, scripts, and internal-only shortcuts.

Direct backend access does not mean broad backend access. Quater keeps each
surface behind its own boundary: `mcp_auth` protects MCP, `cli_auth` protects
CLI, and route `auth=` protects the handler itself.

Read [Why Quater Exists](/en/dev/why-quater) for the full problem statement
and design motivation.

### Non-goals

Quater does not ship an ORM, a template engine, a background worker, or a user
account system. It does not try to recreate Django/FastAPI/Flask. It also does not expose every
Starlette or ASGI primitive directly; ASGI and WSGI exist for compatibility.

### Who It Is For

Use Quater when you build API services where humans, agents, and MCP clients need
controlled access to the same backend operations. It fits teams that care about
typed handlers, generated schemas, explicit auth, AI-readable metadata,
operational safety, and low request overhead.


## How The Docs Are Organized

The docs are split by how a developer learns the framework:

- [Quickstart](/en/dev/quickstart) gets a working app running.
- [Why Quater Exists](/en/dev/why-quater) explains the problem behind the
  framework.
- Core concepts explain [routes](/en/dev/routes-handlers),
  [surfaces](/en/dev/surfaces), [auth](/en/dev/auth-model),
  [resources](/en/dev/resources), and
  [middleware](/en/dev/middleware-errors).
- Guides cover [MCP](/en/dev/mcp), [Actions and CLI](/en/dev/actions),
  [Testing](/en/dev/testing), [Deployment](/en/dev/deployment), and
  [Security](/en/dev/security).
- [Reference](/en/dev/reference/) gives exact signatures and defaults.
- Project notes cover [stability](/en/dev/stability),
  [release notes](/en/dev/changelog), and
  [known limitations](/en/dev/known-limitations).

Read the guides first when learning. Use the reference when you already know
which object or option you need.

## Request Lifecycle

Hosted HTTP, MCP, and remote CLI calls enter through the server adapter. Local
CLI imports your app and enters after the network layer.

```mermaid
flowchart TB
    in["request in\nframework"]
    adapter["server adapter\nframework: RSGI / ASGI / WSGI"]
    checks["request checks\nframework: host, body size, CORS, request id"]
    router["router\nframework: native route matcher"]
    before["before middleware\nyour code"]
    surface["surface check\nframework: HTTP, MCP, or CLI"]
    surface_auth["surface auth\nyour code: mcp_auth / cli_auth"]
    route_auth["route auth\nyour code: auth="]
    bind["bind parameters\nframework: path, query, body, resources"]
    handler["handler\nyour code"]
    after["after middleware\nyour code"]
    serialize["serialize\nframework: response or msgspec JSON"]
    out["response out\nframework"]

    in --> adapter --> checks --> router --> before --> surface
    surface -->|HTTP| route_auth
    surface -->|MCP or CLI| surface_auth --> route_auth
    route_auth --> bind --> handler --> after --> serialize --> out
```

Route groups do not add another router at request time. Quater flattens group
prefixes, middleware, auth, metadata, and resources when routes compile.

HTTP requests go from the route to route `auth=`. MCP and remote CLI requests
run their surface auth first, then the same route `auth=` if the route has one.

## One Handler, Three Surfaces

```python
from quater import AuthContext, AuthRequest, Quater, Request


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    if ctx.headers.get("authorization") != "Bearer demo-token":
        return None
    return AuthContext(subject="demo-user")


app = Quater(mcp_auth=authenticate, cli_auth=authenticate)


@app.get(
    "/orders/{order_id}",
    tool=True,
    cli=True,
    auth=authenticate,
    description="Fetch one order by id.",
)
async def get_order(order_id: str, request: Request) -> dict[str, object]:
    assert request.auth is not None
    return {
        "order_id": order_id,
        "subject": request.auth.subject,
        "source": request.context.source,
        "entrypoint": request.context.entrypoint,
    }
```

Expected HTTP output:

```json
{
  "order_id": "ord_1001",
  "subject": "demo-user",
  "source": "api",
  "entrypoint": "server"
}
```

Expected local CLI output:

```json
{
  "order_id": "ord_1001",
  "subject": "demo-user",
  "source": "cli",
  "entrypoint": "local"
}
```

The three surfaces converge on the same handler, but auth does not collapse:

```mermaid
flowchart LR
    api["HTTP caller"] --> api_auth["route auth="] --> handler["handler"]
    mcp["MCP caller"] --> mcp_auth["mcp_auth"] --> mcp_route["route auth="] --> handler
    cli["CLI caller"] --> cli_auth["cli_auth"] --> cli_route["route auth="] --> handler
```

## Reading Path

1. [Quickstart](/en/dev/quickstart): install Quater, run an app, call HTTP,
   MCP, and CLI.
2. [Why Quater Exists](/en/dev/why-quater): understand the human-and-agent
   backend model.
3. [Routes and Handlers](/en/dev/routes-handlers): learn how Quater maps
   calls to your code.
4. [HTTP, MCP, and CLI Surfaces](/en/dev/surfaces): understand the access
   paths.
5. [Auth Model](/en/dev/auth-model): review the layered auth rules.
6. [Resources and State](/en/dev/resources): add database sessions and other
   per-request values.
7. [MCP](/en/dev/mcp) and [Actions and CLI](/en/dev/actions): expose
   selected operations to agents and MCP clients.
8. [Security](/en/dev/security), [Deployment](/en/dev/deployment), and
   [Testing](/en/dev/testing): prepare real apps.
9. [Reference](/en/dev/reference/): look up signatures and exact defaults.

## What Can Go Wrong

`MCP tools require mcp_auth`
: Add `mcp_auth=...` to `Quater(...)` before declaring `tool=True` routes.

`CLI actions require cli_auth`
: Add `cli_auth=...` before declaring `cli=True` routes.

`needs_approval requires tool=True or cli=True`
: Use `needs_approval=True` only on routes exposed as MCP tools or CLI actions.

`Dynamic routes at the same position must use the same name and converter`
: Rename the conflicting path variable or split the route pattern.

## Known Limitations

See [Known Limitations](/en/dev/known-limitations) for the current pre-release
gaps, including WebSockets, built-in ORM support, background jobs, rate limiting,
MCP streaming, and OpenAPI depth.

## Also See

- [Quickstart](/en/dev/quickstart): build the first working app.
- [Why Quater Exists](/en/dev/why-quater): understand the problem Quater is
  built around.
- [Security](/en/dev/security): understand the auth boundaries shown above.
- [Reference](/en/dev/reference/): check exact signatures and defaults.
