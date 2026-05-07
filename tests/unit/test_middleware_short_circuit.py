from __future__ import annotations

import pytest

from quater import App, Request, Response, TextResponse


@pytest.mark.asyncio
async def test_before_middleware_short_circuits_handler_but_runs_after() -> None:
    app = App()
    events: list[str] = []

    @app.before_request
    async def stop(request: Request) -> Response | None:
        events.append("before")
        return TextResponse("stopped", status_code=202)

    @app.after_response
    async def after(request: Request, response: Response) -> Response:
        events.append("after")
        response.headers = (*response.headers, ("x-after", "ran"))
        return response

    @app.get("/short")
    async def handler() -> dict[str, bool]:
        events.append("handler")
        return {"ok": True}

    response = await app.handle(Request(method="GET", path="/short"))

    assert response.status_code == 202
    assert response.body == b"stopped"
    assert ("x-after", "ran") in response.headers
    assert events == ["before", "after"]
