from __future__ import annotations

from quater import AuthContext, AuthRequest, Quater, Request
from quater.tools.audit import ToolAuditEvent


async def authenticate(ctx: AuthRequest) -> AuthContext | None:
    token = ctx.headers.get("authorization")
    if token != "Bearer demo-token":
        return None
    return AuthContext(
        subject="demo-user",
        metadata={"source": ctx.context.source},
    )


async def audit_tool_call(event: ToolAuditEvent) -> None:
    return None


app = Quater(
    mcp_enabled=True,
    mcp_allowed_origins=["http://localhost:3000"],
    mcp_audit=audit_tool_call,
)


@app.get("/profile", auth=authenticate)
async def profile(request: Request) -> dict[str, object]:
    assert request.auth is not None
    return {
        "subject": request.auth.subject,
        "source": request.context.source,
    }


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
