from __future__ import annotations

import json

import pytest

from quater import Quater, Request
from quater.tools.audit import ToolAuditEvent
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
async def test_successful_tool_call_emits_sanitized_audit_event() -> None:
    events: list[ToolAuditEvent] = []

    async def audit(event: ToolAuditEvent) -> None:
        events.append(event)

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        return AuthContext(subject="user_1")

    app = Quater(mcp_enabled=True, mcp_audit=audit)

    @app.get(
        "/users/{id:int}",
        tool=True,
        auth=authenticate,
        description="Fetch one user.",
    )
    async def get_user(id: int) -> dict[str, int]:
        return {"id": id}

    response = await app.handle(
        Request(method="POST", path="/mcp", body=mcp_body("get_user", {"id": 7}))
    )

    assert response.status_code == 200
    assert len(events) == 1
    assert events[0].tool_name == "get_user"
    assert events[0].subject == "user_1"
    assert events[0].success is True
    assert events[0].arguments == {"id": "<redacted>"}
    assert events[0].duration_ms >= 0


@pytest.mark.asyncio
async def test_failed_tool_call_emits_failure_audit_event() -> None:
    events: list[ToolAuditEvent] = []

    async def audit(event: ToolAuditEvent) -> None:
        events.append(event)

    app = Quater(mcp_enabled=True, mcp_audit=audit)

    @app.get("/boom", tool=True, description="Raise a handler error.")
    async def boom() -> dict[str, bool]:
        raise RuntimeError("boom")

    response = await app.handle(
        Request(method="POST", path="/mcp", body=mcp_body("boom", {}))
    )
    body = json.loads(response.body)

    assert body["result"]["isError"] is True
    assert len(events) == 1
    assert events[0].tool_name == "boom"
    assert events[0].success is False
