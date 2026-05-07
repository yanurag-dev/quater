from __future__ import annotations

import pytest

from quater import App, Request, Response


def response_headers(response: Response) -> dict[str, str]:
    return dict(response.headers)


@pytest.mark.asyncio
async def test_secure_headers_are_added_to_not_found_responses() -> None:
    response = await App().handle(Request(method="GET", path="/missing"))

    headers = response_headers(response)
    assert response.status_code == 404
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "same-origin"
    assert headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_secure_headers_are_added_to_unexpected_error_responses() -> None:
    app = App()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("database password leaked here")

    response = await app.handle(Request(method="GET", path="/boom"))

    headers = response_headers(response)
    assert response.status_code == 500
    assert response.body == b"Internal Server Error"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_hsts_uses_forwarded_proto_only_from_trusted_proxy() -> None:
    app = App(trusted_proxies=["10.0.0.0/8"])

    trusted_response = await app.handle(
        Request(
            method="GET",
            path="/missing",
            headers={"host": "internal", "x-forwarded-proto": "https"},
            client="10.1.2.3",
        )
    )
    untrusted_response = await app.handle(
        Request(
            method="GET",
            path="/missing",
            headers={"host": "internal", "x-forwarded-proto": "https"},
            client="203.0.113.9",
        )
    )

    assert response_headers(trusted_response)["strict-transport-security"].startswith(
        "max-age="
    )
    assert "strict-transport-security" not in response_headers(untrusted_response)


@pytest.mark.asyncio
async def test_security_can_be_disabled_for_local_or_embedded_usage() -> None:
    response = await App(security="off").handle(Request(method="GET", path="/missing"))

    headers = response_headers(response)
    assert response.status_code == 404
    assert "x-content-type-options" not in headers
    assert "x-frame-options" not in headers


@pytest.mark.asyncio
async def test_configured_csp_is_preserved_without_overriding_handler_header() -> None:
    app = App(content_security_policy="default-src 'self'")

    @app.get("/custom")
    async def custom() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(Request(method="GET", path="/custom"))

    assert response_headers(response)["content-security-policy"] == "default-src 'self'"
