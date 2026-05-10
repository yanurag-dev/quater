from __future__ import annotations

import json

import pytest

from quater import Quater, Request
from quater.typing import AuthContext, AuthRequest


def mcp_body(name: str, arguments: dict[str, object]) -> bytes:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    ).encode("utf-8")


@pytest.mark.asyncio
async def test_mcp_uses_same_auth_denial_policy_as_http() -> None:
    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        return None

    app = Quater()

    @app.get(
        "/private",
        tool=True,
        auth=authenticate,
        description="Read private data.",
    )
    async def private() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(method="POST", path="/mcp", body=mcp_body("private", {}))
    )

    assert response.status_code == 401
    assert response.body == b"Unauthorized"


@pytest.mark.asyncio
async def test_auth_hook_sees_tool_source_for_tools_call() -> None:
    seen: list[tuple[str, str | None]] = []

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        seen.append((ctx.context.source, ctx.context.tool_name))
        return AuthContext(subject="user_1")

    app = Quater()

    @app.get("/me", tool=True, auth=authenticate, description="Read current user.")
    async def me(request: Request) -> dict[str, object]:
        assert request.auth is not None
        return {
            "subject": request.auth.subject,
            "source": request.context.source,
            "tool": request.context.tool_name,
        }

    response = await app.handle(
        Request(method="POST", path="/mcp", body=mcp_body("me", {}))
    )
    body = json.loads(response.body)

    assert seen == [("tool", "me")]
    assert body["result"]["content"][0]["text"] == (
        '{"subject":"user_1","source":"tool","tool":"me"}'
    )


@pytest.mark.asyncio
async def test_invalid_mcp_origin_rejects_before_auth_and_handler() -> None:
    auth_calls = 0
    handler_calls = 0

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        nonlocal auth_calls
        auth_calls += 1
        return AuthContext(subject="user_1")

    app = Quater(mcp_allowed_origins=["https://app.example.com"])

    @app.get(
        "/private",
        tool=True,
        auth=authenticate,
        description="Read private data.",
    )
    async def private() -> dict[str, bool]:
        nonlocal handler_calls
        handler_calls += 1
        return {"ok": True}

    response = await app.handle(
        Request(
            method="POST",
            path="/mcp",
            headers={"origin": "https://evil.example.com"},
            body=mcp_body("private", {}),
        )
    )

    assert response.status_code == 400
    assert response.body == b"Invalid MCP Origin"
    assert auth_calls == 0
    assert handler_calls == 0


@pytest.mark.asyncio
async def test_valid_mcp_origin_can_use_cors_origin_policy() -> None:
    from quater.cors import CORSConfig

    app = Quater(cors=CORSConfig(allowed_origins=("https://app.example.com",)))

    @app.get("/ping", tool=True, description="Check tool connectivity.")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(
            method="POST",
            path="/mcp",
            headers={"origin": "https://app.example.com"},
            body=mcp_body("ping", {}),
        )
    )

    assert response.status_code == 200
    assert dict(response.headers)["access-control-allow-origin"] == (
        "https://app.example.com"
    )
