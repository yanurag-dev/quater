# Quickstart

Quater apps are built around one `Quater` object.

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

Run with Granian RSGI:

```bash
uv run granian examples.basic_app:app --interface rsgi
```

Use hot reload while building locally:

```bash
uv run granian examples.basic_app:app --interface rsgi --reload
```

RSGI is the primary path because it maps directly to Granian's fast Python
interface. ASGI and WSGI are compatibility paths that still call the same
`Quater.handle()` core.

```bash
uv run granian examples.asgi_compat:app --interface asgi
uv run granian examples.wsgi_compat:app --interface wsgi
```

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

Complex parameters come from the JSON body.

## Responses

Handlers can return plain values or response objects:

- `dict`, `list`, dataclasses, and `msgspec.Struct` values become JSON.
- `str` becomes text.
- `bytes` becomes bytes.
- `None` becomes `204 No Content`.
- `Response` subclasses are returned directly.

## Adapters

The `Quater` object is directly callable by Granian for every HTTP interface.
Adapter properties are also available when a server wants an explicit callable:

- `app.rsgi` for Granian RSGI.
- `app.asgi` for ASGI 3.0 compatibility and ASGI lifespan.
- `app.wsgi` for WSGI compatibility.

WebSocket transports are explicitly rejected for now. Quater does not expose a
framework-level WebSocket API in the MVP.
