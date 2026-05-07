from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest

from quater import App, Request, Response


@pytest.mark.asyncio
async def test_global_and_route_middleware_order_is_stable() -> None:
    app = App()
    events: list[str] = []

    @app.before_request
    async def global_before(request: Request) -> Response | None:
        events.append("global_before")
        return None

    async def route_before(request: Request) -> Response | None:
        events.append("route_before")
        return None

    @app.around_request
    async def global_around(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        events.append("global_around_before")
        response = await call_next(request)
        events.append("global_around_after")
        return response

    async def route_around(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        events.append("route_around_before")
        response = await call_next(request)
        events.append("route_around_after")
        return response

    async def route_after(request: Request, response: Response) -> Response:
        events.append("route_after")
        return response

    @app.after_response
    async def global_after(request: Request, response: Response) -> Response:
        events.append("global_after")
        return response

    @app.get(
        "/order",
        before=[route_before],
        around=[route_around],
        after=[route_after],
    )
    async def handler() -> dict[str, bool]:
        events.append("handler")
        return {"ok": True}

    response = await app.handle(Request(method="GET", path="/order"))

    assert response.status_code == 200
    assert events == [
        "global_before",
        "route_before",
        "global_around_before",
        "route_around_before",
        "handler",
        "route_around_after",
        "global_around_after",
        "route_after",
        "global_after",
    ]


@pytest.mark.asyncio
async def test_after_middleware_can_replace_response() -> None:
    app = App()

    @app.after_response
    async def add_header(request: Request, response: Response) -> Response:
        response.headers = (*response.headers, ("x-test", "yes"))
        return response

    @app.get("/headers")
    async def handler() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(Request(method="GET", path="/headers"))

    assert ("x-test", "yes") in response.headers


@pytest.mark.asyncio
async def test_global_after_middleware_runs_for_not_found_responses() -> None:
    app = App()

    @app.after_response
    async def add_header(request: Request, response: Response) -> Response:
        response.headers = (*response.headers, ("x-global", "yes"))
        return response

    response = await app.handle(Request(method="GET", path="/missing"))

    assert response.status_code == 404
    assert ("x-global", "yes") in response.headers
