# Security

Quater is secure by default. Security checks run before auth, routing, handlers,
and MCP tool lookup.

## Response Headers

Strict mode is the default and adds baseline headers to handler responses,
framework errors, auth failures, 404s, 405s, and MCP responses:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: same-origin`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` when the request scheme is HTTPS
- `Content-Security-Policy` when configured

Set `security="off"` only for controlled local or embedded use.

## Hosts And Proxies

Use `allowed_hosts` to reject unexpected Host headers:

```python
app = App(allowed_hosts=["api.example.com"])
```

Use `trusted_proxies` when Quater should honor forwarded host or scheme headers:

```python
app = App(
    allowed_hosts=["api.example.com"],
    trusted_proxies=["10.0.0.0/8"],
)
```

Forwarded headers are ignored unless the client IP matches a trusted proxy.

## Body Limits

`max_body_size` defaults to `2mb` and applies before JSON decoding:

```python
app = App(max_body_size="2mb")
```

If `Content-Length` is larger than the configured limit, Quater rejects the
request before reading the body stream.

## Auth

Quater intentionally does not provide a full user system. It provides one
central user-written auth hook:

```python
from quater import AuthContext, AuthRequest


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    token = ctx.headers.get("authorization")
    if token != "Bearer demo-token":
        return None
    return AuthContext(subject="demo-user")
```

When `auth` is configured, returning `None` rejects the request with `401`.
The same hook protects normal API calls and MCP calls.

`AuthRequest.context.source` is `"api"` for normal route calls and `"tool"` for
MCP `tools/call`.

## CORS And MCP Origins

Use `CORSConfig` for CORS response headers:

```python
from quater.cors import CORSConfig

app = App(
    cors=CORSConfig(
        allowed_origins=("https://app.example.com",),
        allow_credentials=True,
    )
)
```

MCP origin validation uses `mcp_allowed_origins` first. If that is empty and
CORS is configured, Quater uses the CORS allowed origins for MCP too.

```python
app = App(
    mcp_enabled=True,
    mcp_allowed_origins=["https://app.example.com"],
)
```

Invalid MCP origins are rejected before auth and before tool lookup.

## Signed Cookies

`SignedCookieSigner` signs small cookie values with HMAC and supports fallback
secrets for rotation:

```python
from quater.cookies import SignedCookieSigner

signer = SignedCookieSigner("new-secret", fallback_secrets=["old-secret"])
value = signer.sign("user_123")
subject = signer.verify(value)
```
