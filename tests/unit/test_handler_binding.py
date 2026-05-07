from __future__ import annotations

import pytest

from quater import App, Request
from quater.response import Response, TextResponse
from quater.typing import AuthContext


@pytest.mark.asyncio
async def test_path_params_are_converted_and_bound_by_name() -> None:
    app = App()

    @app.get("/users/{id:int}")
    async def get_user(id: int) -> dict[str, int]:
        return {"id": id}

    response = await app.handle(Request(method="GET", path="/users/42"))

    assert response.status_code == 200
    assert response.body == b'{"id":42}'


@pytest.mark.asyncio
async def test_request_injection_uses_same_request_object() -> None:
    app = App()
    auth = AuthContext(subject="user_1")

    @app.get("/whoami")
    async def whoami(request: Request) -> dict[str, str]:
        assert request.auth is auth
        return {"subject": request.auth.subject if request.auth else "none"}

    response = await app.handle(Request(method="GET", path="/whoami", auth=auth))

    assert response.status_code == 200
    assert response.body == b'{"subject":"user_1"}'


@pytest.mark.asyncio
async def test_handler_response_objects_pass_through_normalization() -> None:
    app = App()

    @app.get("/ready")
    async def ready() -> Response:
        return TextResponse("ready", status_code=202)

    response = await app.handle(Request(method="GET", path="/ready"))

    assert response.status_code == 202
    assert response.body == b"ready"


@pytest.mark.asyncio
async def test_unsupported_handler_return_value_is_not_silently_serialized() -> None:
    class Unsupported:
        pass

    app = App()

    @app.get("/bad")
    async def bad() -> Unsupported:
        return Unsupported()

    response = await app.handle(Request(method="GET", path="/bad"))

    assert response.status_code == 500
    assert response.body == b"Internal Server Error"
