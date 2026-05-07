from __future__ import annotations

import pytest

from quater import App, HTTPError, Request, Response, TextResponse
from quater.exceptions import MiddlewareStateError
from quater.middleware import ExceptionHandlerEntry


@pytest.mark.asyncio
async def test_http_error_maps_to_safe_response() -> None:
    app = App()

    @app.get("/missing")
    async def handler() -> dict[str, bool]:
        raise HTTPError("Nope", status_code=404)

    response = await app.handle(Request(method="GET", path="/missing"))

    assert response.status_code == 404
    assert response.body == b"Nope"


@pytest.mark.asyncio
async def test_custom_exception_handler_maps_route_error() -> None:
    app = App()

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: Exception) -> Response | None:
        return TextResponse(f"handled: {exc}", status_code=418)

    @app.get("/boom")
    async def handler() -> dict[str, bool]:
        raise ValueError("bad")

    response = await app.handle(Request(method="GET", path="/boom"))

    assert response.status_code == 418
    assert response.body == b"handled: bad"


@pytest.mark.asyncio
async def test_route_exception_handler_runs_before_global_handler() -> None:
    app = App()

    @app.exception_handler(ValueError)
    async def global_handler(request: Request, exc: Exception) -> Response | None:
        return TextResponse("global", status_code=500)

    async def route_handler(request: Request, exc: Exception) -> Response | None:
        return TextResponse("route", status_code=409)

    @app.get(
        "/boom",
        exception_handlers=[ExceptionHandlerEntry(ValueError, route_handler)],
    )
    async def handler() -> dict[str, bool]:
        raise ValueError("bad")

    response = await app.handle(Request(method="GET", path="/boom"))

    assert response.status_code == 409
    assert response.body == b"route"


@pytest.mark.asyncio
async def test_exception_handler_failure_becomes_default_error_response() -> None:
    app = App()

    @app.exception_handler(ValueError)
    async def broken_handler(request: Request, exc: Exception) -> Response | None:
        raise RuntimeError("handler failed")

    @app.get("/boom")
    async def handler() -> dict[str, bool]:
        raise ValueError("bad")

    response = await app.handle(Request(method="GET", path="/boom"))

    assert response.status_code == 500
    assert response.body == b"Internal Server Error"


@pytest.mark.asyncio
async def test_after_middleware_runs_for_mapped_exception_responses() -> None:
    app = App()

    @app.after_response
    async def add_header(request: Request, response: Response) -> Response:
        response.headers = (*response.headers, ("x-error-safe", "yes"))
        return response

    @app.get("/boom")
    async def handler() -> dict[str, bool]:
        raise RuntimeError("broken")

    response = await app.handle(Request(method="GET", path="/boom"))

    assert response.status_code == 500
    assert ("x-error-safe", "yes") in response.headers


def test_global_middleware_cannot_be_registered_after_compile() -> None:
    app = App()
    app.compile_routes()

    async def middleware(request: Request) -> Response | None:
        return None

    with pytest.raises(MiddlewareStateError):
        app.before_request(middleware)
