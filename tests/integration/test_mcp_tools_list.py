from __future__ import annotations

import json

import pytest

from quater import App, Request


async def mcp_post(
    app: App,
    payload: dict[str, object],
) -> tuple[int, dict[str, object]]:
    response = await app.handle(
        Request(
            method="POST",
            path="/mcp",
            headers={"content-type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
        )
    )
    return response.status_code, json.loads(response.body)


def require_object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


@pytest.mark.asyncio
async def test_tools_list_exposes_only_tool_routes() -> None:
    app = App(mcp_enabled=True)

    @app.get("/internal")
    async def internal() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/users/{id:int}", tool=True)
    async def get_user(id: int) -> dict[str, int]:
        """Fetch one user."""
        return {"id": id}

    status, body = await mcp_post(
        app,
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )

    assert status == 200
    result = require_object(body["result"])
    assert result["tools"] == [
        {
            "name": "get_user",
            "description": "Fetch one user.",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
                "additionalProperties": False,
                "required": ["id"],
            },
        }
    ]


@pytest.mark.asyncio
async def test_mcp_path_is_not_available_until_enabled() -> None:
    response = await App().handle(
        Request(
            method="POST",
            path="/mcp",
            headers={"content-type": "application/json"},
            body=b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}',
        )
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mcp_get_returns_method_not_allowed_when_enabled() -> None:
    response = await App(mcp_enabled=True).handle(Request(method="GET", path="/mcp"))

    assert response.status_code == 405
    assert dict(response.headers)["allow"] == "POST"
