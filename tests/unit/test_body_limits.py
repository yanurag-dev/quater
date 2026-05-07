from __future__ import annotations

import pytest

from quater import App, Request


@pytest.mark.asyncio
async def test_content_length_over_limit_fails_before_body_reader_and_handler() -> None:
    reader_calls = 0
    handler_calls = 0

    async def read_body() -> bytes:
        nonlocal reader_calls
        reader_calls += 1
        return b"too large"

    app = App(max_body_size=4)

    @app.post("/upload")
    async def upload(request: Request) -> dict[str, int]:
        nonlocal handler_calls
        handler_calls += 1
        return {"size": len(await request.body())}

    response = await app.handle(
        Request(
            method="POST",
            path="/upload",
            headers={"content-length": "9"},
            body=read_body,
        )
    )

    assert response.status_code == 413
    assert response.body == b"Payload Too Large"
    assert reader_calls == 0
    assert handler_calls == 0


@pytest.mark.asyncio
async def test_body_reader_limit_uses_app_config_when_length_is_unknown() -> None:
    app = App(max_body_size=4)

    @app.post("/upload")
    async def upload(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    response = await app.handle(
        Request(method="POST", path="/upload", body=b"12345")
    )

    assert response.status_code == 413
    assert response.body == b"Payload Too Large"


@pytest.mark.asyncio
async def test_malformed_content_length_is_a_safe_request_error() -> None:
    app = App(max_body_size=4)

    @app.post("/upload")
    async def upload() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(
            method="POST",
            path="/upload",
            headers={"content-length": "four"},
            body=b"{}",
        )
    )

    assert response.status_code == 400
    assert response.body == b"Invalid Content-Length header"
