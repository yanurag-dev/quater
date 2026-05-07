from __future__ import annotations

import pytest

from quater import App, Request
from quater.cors import CORSConfig
from quater.exceptions import ConfigurationError


@pytest.mark.asyncio
async def test_allowed_origin_receives_cors_headers_and_vary_origin() -> None:
    app = App(
        cors=CORSConfig(
            allowed_origins=("https://app.example.com",),
            allow_credentials=True,
            expose_headers=("x-request-id",),
        )
    )

    @app.get("/items")
    async def items() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(
            method="GET",
            path="/items",
            headers={"origin": "https://app.example.com"},
        )
    )

    headers = dict(response.headers)
    assert headers["access-control-allow-origin"] == "https://app.example.com"
    assert headers["access-control-allow-credentials"] == "true"
    assert headers["access-control-expose-headers"] == "x-request-id"
    assert headers["vary"] == "Origin"


@pytest.mark.asyncio
async def test_disallowed_origin_does_not_receive_cors_headers() -> None:
    app = App(cors=CORSConfig(allowed_origins=("https://app.example.com",)))

    @app.get("/items")
    async def items() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(
            method="GET",
            path="/items",
            headers={"origin": "https://evil.example.com"},
        )
    )

    assert "access-control-allow-origin" not in dict(response.headers)


@pytest.mark.asyncio
async def test_preflight_response_includes_requested_method_and_headers() -> None:
    app = App(
        cors=CORSConfig(
            allowed_origins=("https://app.example.com",),
            allowed_headers=("authorization",),
            max_age=600,
        )
    )

    @app.route("OPTIONS", "/items")
    async def options() -> None:
        return None

    response = await app.handle(
        Request(
            method="OPTIONS",
            path="/items",
            headers={
                "origin": "https://app.example.com",
                "access-control-request-method": "POST",
                "access-control-request-headers": "authorization, x-client",
            },
        )
    )

    headers = dict(response.headers)
    assert response.status_code == 204
    assert "POST" in headers["access-control-allow-methods"]
    assert headers["access-control-allow-headers"] == "authorization, x-client"
    assert headers["access-control-max-age"] == "600"


def test_wildcard_origin_with_credentials_fails_configuration() -> None:
    with pytest.raises(ConfigurationError):
        CORSConfig(allowed_origins=("*",), allow_credentials=True)
