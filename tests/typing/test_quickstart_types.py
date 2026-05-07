from __future__ import annotations

from typing import Literal, assert_type

from quater import App, AuthContext, AuthRequest, Request, Response


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    token = ctx.headers.get("authorization")
    if token != "Bearer demo-token":
        return None
    return AuthContext(subject="demo-user")


app = App(
    auth=authenticate,
    mcp_enabled=True,
    mcp_allowed_origins=["http://localhost:3000"],
)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/users/{id:int}", tool=True)
async def get_user(id: int, request: Request) -> dict[str, object]:
    assert_type(id, int)
    assert_type(request.context.source, Literal["api", "tool"])
    return {
        "id": id,
        "source": request.context.source,
        "tool": request.context.tool_name,
    }


async def dispatch_contract() -> None:
    response = await app.handle(Request(method="GET", path="/health"))
    assert_type(response, Response)
