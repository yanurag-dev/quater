from __future__ import annotations

import pytest

from quater import App, Request


@pytest.mark.asyncio
async def test_unexpected_errors_are_sanitized_by_default() -> None:
    app = App()

    @app.get("/boom")
    async def handler() -> dict[str, bool]:
        raise RuntimeError("database password leaked")

    response = await app.handle(Request(method="GET", path="/boom"))

    assert response.status_code == 500
    assert response.body == b"Internal Server Error"


@pytest.mark.asyncio
async def test_debug_errors_include_exception_type_and_message() -> None:
    app = App(debug=True)

    @app.get("/boom")
    async def handler() -> dict[str, bool]:
        raise RuntimeError("broken test")

    response = await app.handle(Request(method="GET", path="/boom"))

    assert response.status_code == 500
    assert response.body == b"RuntimeError: broken test"
