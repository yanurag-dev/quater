---
layout: home

hero:
  text: Backends for people, services, and AI agents.
  tagline: Build normal Python APIs, then expose selected backend operations directly to agents and operators without creating shadow code paths.
  actions:
    - theme: brand
      text: Start Building
      link: /en/latest/quickstart
    - theme: alt
      text: Public API
      link: /en/latest/api

features:
  - title: Built for the next caller
    details: Frontends still matter, but AI agents should not have to click through screens to do backend work safely.
  - title: One trusted operation
    details: Keep the real application logic in the route, then opt selected operations into MCP tools or CLI actions when they should be callable outside the UI.
  - title: Direct does not mean unsafe
    details: MCP and CLI have their own auth boundaries before route auth runs, with descriptions, schemas, audits, and approvals for sensitive actions.
  - title: Useful to humans too
    details: You still get normal HTTP APIs, OpenAPI, Swagger UI, typed binding, route groups, middleware, and an in-process test client.
  - title: Small request path
    details: "Quater uses Granian on RSGI, msgspec for JSON, and a native router to keep framework overhead low."
  - title: Docs by default
    details: OpenAPI, Swagger UI, and MCP tool docs are generated from the route metadata you already wrote.
---

## Start Here

Quater starts from a simple belief: AI agents need a better interface to
software than screens meant for humans. The answer is not to bypass your
backend. The answer is to expose the right backend operations directly, with
clear inputs and real safety boundaries.

This site documents Quater's current pre-release API. If you are evaluating the
framework, start with the [Quickstart](/en/latest/quickstart), then read the
[Manual](/en/latest/) to understand how HTTP, MCP, and CLI access fit together.

Prerequisites: Python 3.11 or newer, async Python basics, and enough HTTP
knowledge to read request and response examples.

## One Operation, Three Ways To Call It

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
    }
```

Run it:

```bash
uv add quater
quater dev main.py
```

Expected server output:

```text
[INFO] Starting granian
[INFO] Listening at: http://127.0.0.1:8000
```

Call it as HTTP:

```bash
curl -H "Authorization: Bearer demo-token" \
  http://127.0.0.1:8000/orders/ord_1001
```

Call it from the local CLI:

```bash
export QUATER_APP=main:app
export QUATER_TOKEN=demo-token
quater call get_order --order-id ord_1001
```

Call it as an MCP tool:

```bash
curl http://127.0.0.1:8000/mcp \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_order","arguments":{"order_id":"ord_1001"}}}'
```

All three calls reach the same handler. The `source` value tells you which
surface called it: `api`, `cli`, or `mcp`.


## Also See

- [Quickstart](/en/latest/quickstart): first working app.
- [Why Quater Exists](/en/latest/why-quater): the problem behind the framework.
- [HTTP, MCP, and CLI Surfaces](/en/latest/surfaces): how the three access paths
  fit together.
- [Public API](/en/latest/api): full public surface.
- [Deployment](/en/latest/deployment): production setup and checks.
