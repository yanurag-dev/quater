from __future__ import annotations

import inspect

import pytest

from quater import App, Request


@pytest.mark.asyncio
async def test_static_routes_win_before_dynamic_routes() -> None:
    app = App()

    @app.get("/users/{id:int}")
    async def get_user(id: int) -> dict[str, int]:
        return {"id": id}

    @app.get("/users/me")
    async def get_me() -> dict[str, str]:
        return {"name": "me"}

    response = await app.handle(Request(method="GET", path="/users/me"))

    assert response.status_code == 200
    assert response.body == b'{"name":"me"}'


@pytest.mark.asyncio
async def test_typed_path_param_rejection_does_not_call_handler() -> None:
    app = App()
    calls = 0

    @app.get("/users/{id:int}")
    async def get_user(id: int) -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"id": id}

    response = await app.handle(Request(method="GET", path="/users/not-an-int"))

    assert response.status_code == 404
    assert calls == 0


@pytest.mark.asyncio
async def test_method_not_allowed_lists_supported_methods() -> None:
    app = App()

    @app.get("/items/{id:int}")
    async def get_item(id: int) -> dict[str, int]:
        return {"id": id}

    @app.post("/items/{id:int}")
    async def update_item(id: int) -> dict[str, int]:
        return {"id": id}

    response = await app.handle(Request(method="DELETE", path="/items/1"))

    assert response.status_code == 405
    headers = dict(response.headers)
    assert headers["allow"] == "GET, POST"
    assert headers["content-type"] == "text/plain; charset=utf-8"
    assert headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_no_runtime_signature_inspection_after_compile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = App()

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.compile_routes()

    def fail_signature(_: object) -> inspect.Signature:
        raise AssertionError("signature inspection happened during dispatch")

    monkeypatch.setattr(inspect, "signature", fail_signature)

    response = await app.handle(Request(method="GET", path="/health"))

    assert response.status_code == 200
    assert response.body == b'{"ok":true}'
