from __future__ import annotations

import pytest

from quater import Quater, Request
from quater.typing import AuthContext, AuthRequest


@pytest.mark.asyncio
async def test_allowed_host_accepts_matching_host_with_port() -> None:
    app = Quater(allowed_hosts=["api.example.com"])

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(
            method="GET",
            path="/health",
            headers={"host": "api.example.com:8443"},
        )
    )

    assert response.status_code == 200
    assert response.body == b'{"ok":true}'


@pytest.mark.asyncio
async def test_rejected_host_never_reaches_auth_or_handler() -> None:
    auth_calls = 0
    handler_calls = 0

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        nonlocal auth_calls
        auth_calls += 1
        return AuthContext(subject="user_1")

    app = Quater(allowed_hosts=["api.example.com"])

    @app.get("/private", auth=authenticate)
    async def private() -> dict[str, bool]:
        nonlocal handler_calls
        handler_calls += 1
        return {"ok": True}

    response = await app.handle(
        Request(method="GET", path="/private", headers={"host": "evil.example.com"})
    )

    assert response.status_code == 400
    assert response.body == b"Invalid Host header"
    assert auth_calls == 0
    assert handler_calls == 0


@pytest.mark.asyncio
async def test_duplicate_host_header_is_rejected_before_auth_or_handler() -> None:
    auth_calls = 0
    handler_calls = 0

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        nonlocal auth_calls
        auth_calls += 1
        return AuthContext(subject="user_1")

    app = Quater(allowed_hosts=["api.example.com"])

    @app.get("/private", auth=authenticate)
    async def private() -> dict[str, bool]:
        nonlocal handler_calls
        handler_calls += 1
        return {"ok": True}

    response = await app.handle(
        Request(
            method="GET",
            path="/private",
            headers=(
                ("host", "api.example.com"),
                ("host", "evil.example.com"),
            ),
        )
    )

    assert response.status_code == 400
    assert response.body == b"Invalid Host header"
    assert auth_calls == 0
    assert handler_calls == 0


@pytest.mark.asyncio
async def test_host_and_authority_must_agree() -> None:
    app = Quater(allowed_hosts=["api.example.com"])

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(
            method="GET",
            path="/health",
            headers=(
                ("host", "api.example.com"),
                (":authority", "evil.example.com"),
            ),
        )
    )

    assert response.status_code == 400
    assert response.body == b"Invalid Host header"


@pytest.mark.asyncio
async def test_forwarded_host_is_honored_only_from_trusted_proxy() -> None:
    app = Quater(
        allowed_hosts=["api.example.com"],
        trusted_proxies=["10.0.0.0/8"],
    )

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    trusted_response = await app.handle(
        Request(
            method="GET",
            path="/health",
            headers={"host": "internal", "x-forwarded-host": "api.example.com"},
            client="10.1.2.3",
        )
    )
    untrusted_response = await app.handle(
        Request(
            method="GET",
            path="/health",
            headers={"host": "internal", "x-forwarded-host": "api.example.com"},
            client="203.0.113.9",
        )
    )

    assert trusted_response.status_code == 200
    assert untrusted_response.status_code == 400
