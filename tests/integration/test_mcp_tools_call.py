from __future__ import annotations

import json
from collections.abc import Callable
from typing import cast

import msgspec
import pytest

from quater import AuthContext, AuthRequest, Quater, Request


async def allow_mcp_auth(ctx: AuthRequest) -> AuthContext | None:
    return AuthContext(subject="mcp")


class CreateUser(msgspec.Struct):
    name: str
    age: int


async def mcp_call(
    app: Quater,
    *,
    name: str,
    arguments: dict[str, object],
    request_id: int = 1,
) -> tuple[int, dict[str, object]]:
    response = await app.handle(
        Request(
            method="POST",
            path="/mcp",
            headers={
                "authorization": "Bearer mcp",
                "content-type": "application/json",
            },
            body=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                }
            ).encode("utf-8"),
        )
    )
    return response.status_code, json.loads(response.body)


def require_object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def require_object_list(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    assert all(isinstance(item, dict) for item in value)
    return value


@pytest.mark.asyncio
async def test_tools_call_invokes_handler_with_tool_request_context() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/users/{id:int}", tool=True, description="Fetch one user.")
    async def get_user(id: int, request: Request) -> dict[str, object]:
        assert request.context.source == "tool"
        assert request.context.tool_name == "get_user"
        assert request.auth is not None
        return {
            "id": id,
            "source": request.context.source,
            "subject": request.auth.subject,
        }

    status, body = await mcp_call(app, name="get_user", arguments={"id": 7})

    assert status == 200
    assert body["result"] == {
        "content": [
            {"type": "text", "text": '{"id":7,"source":"tool","subject":"mcp"}'},
        ],
        "isError": False,
    }


@pytest.mark.asyncio
async def test_tools_call_reuses_cached_json_rpc_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Quater(mcp_auth=allow_mcp_auth)
    original_decode = cast(Callable[..., object], msgspec.json.decode)
    decode_calls = 0

    def decode_json(*args: object, **kwargs: object) -> object:
        nonlocal decode_calls
        decode_calls += 1
        return original_decode(*args, **kwargs)

    monkeypatch.setattr(msgspec.json, "decode", decode_json)

    @app.get("/users/{id:int}", tool=True, description="Fetch one user.")
    async def get_user(id: int) -> dict[str, object]:
        return {"id": id}

    status, body = await mcp_call(app, name="get_user", arguments={"id": 7})

    assert status == 200
    result = require_object(body["result"])
    assert result["isError"] is False
    assert decode_calls == 1


@pytest.mark.asyncio
async def test_normal_api_call_keeps_api_request_context() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/users/{id:int}", tool=True, description="Fetch one user.")
    async def get_user(id: int, request: Request) -> dict[str, object]:
        return {"id": id, "source": request.context.source}

    response = await app.handle(Request(method="GET", path="/users/7"))

    assert response.body == b'{"id":7,"source":"api"}'


@pytest.mark.asyncio
async def test_tools_call_escapes_rendered_request_path_parameters() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/files/{name}", tool=True, description="Fetch one file.")
    async def get_file(name: str, request: Request) -> dict[str, str]:
        return {"name": name, "path": request.path}

    status, body = await mcp_call(
        app,
        name="get_file",
        arguments={"name": "reports/2026 draft"},
    )

    assert status == 200
    result = require_object(body["result"])
    content = require_object_list(result["content"])
    assert (
        content[0]["text"]
        == '{"name":"reports/2026 draft","path":"/files/reports%2F2026%20draft"}'
    )
    assert result["isError"] is False


@pytest.mark.asyncio
async def test_tools_call_binds_body_model_from_arguments() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.post("/users", tool=True, description="Create one user.")
    async def create_user(user: CreateUser) -> dict[str, object]:
        return {"name": user.name, "age": user.age}

    status, body = await mcp_call(
        app,
        name="create_user",
        arguments={"user": {"name": "Ada", "age": 37}},
    )

    assert status == 200
    result = require_object(body["result"])
    content = require_object_list(result["content"])
    assert content[0]["text"] == '{"name":"Ada","age":37}'
    assert result["isError"] is False


@pytest.mark.asyncio
async def test_unknown_tool_returns_json_rpc_error() -> None:
    status, body = await mcp_call(
        Quater(),
        name="missing",
        arguments={},
    )

    assert status == 200
    assert body["error"] == {"code": -32602, "message": "Unknown tool"}


@pytest.mark.asyncio
async def test_invalid_tool_arguments_do_not_call_handler() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)
    calls = 0

    @app.get("/users/{id:int}", tool=True, description="Fetch one user.")
    async def get_user(id: int) -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"id": id}

    status, body = await mcp_call(app, name="get_user", arguments={"id": "broken"})

    assert status == 200
    assert body["error"] == {"code": -32602, "message": "Invalid path argument: id"}
    assert calls == 0


@pytest.mark.asyncio
async def test_handler_error_becomes_tool_result_error() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/boom", tool=True, description="Raise a handler error.")
    async def boom() -> dict[str, bool]:
        raise RuntimeError("database token leaked")

    status, body = await mcp_call(app, name="boom", arguments={})

    assert status == 200
    assert body["result"] == {
        "content": [{"type": "text", "text": "Tool call failed"}],
        "isError": True,
    }
