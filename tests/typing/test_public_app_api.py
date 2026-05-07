from __future__ import annotations

from typing import assert_type

from quater import App, AuthContext, AuthRequest
from quater.request import Request
from quater.response import Response
from quater.typing import Authenticate, LifespanHook


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    token = ctx.headers.get("authorization")
    if token is None:
        return None
    return AuthContext(subject=token)


app = App(auth=authenticate, allowed_hosts=["api.example.com"])


@app.on_startup
async def startup() -> None:
    return None


@app.on_shutdown
async def shutdown() -> None:
    return None


async def dispatch_contract() -> None:
    response = await app.handle(Request(method="GET", path="/missing"))
    assert_type(response, Response)


assert_type(app.auth, Authenticate | None)
assert_type(startup, LifespanHook)
assert_type(shutdown, LifespanHook)
assert_type(app.config.allowed_hosts, tuple[str, ...])
