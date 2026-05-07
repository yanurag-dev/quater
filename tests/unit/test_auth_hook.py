from __future__ import annotations

import pytest

from quater import App, Request
from quater.typing import AuthContext, AuthRequest


@pytest.mark.asyncio
async def test_auth_context_is_attached_before_handler_runs() -> None:
    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        return AuthContext(
            subject=ctx.headers["authorization"].removeprefix("Bearer "),
            metadata={"source": "test"},
        )

    app = App(auth=authenticate)

    @app.get("/me")
    async def me(request: Request) -> dict[str, object]:
        assert request.auth is not None
        return {
            "subject": request.auth.subject,
            "source": request.auth.metadata["source"],
        }

    response = await app.handle(
        Request(
            method="GET",
            path="/me",
            headers={"authorization": "Bearer user_123"},
        )
    )

    assert response.status_code == 200
    assert response.body == b'{"subject":"user_123","source":"test"}'


@pytest.mark.asyncio
async def test_missing_auth_context_denies_request_before_handler() -> None:
    handler_calls = 0

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        return None

    app = App(auth=authenticate)

    @app.get("/private")
    async def private() -> dict[str, bool]:
        nonlocal handler_calls
        handler_calls += 1
        return {"ok": True}

    response = await app.handle(Request(method="GET", path="/private"))

    assert response.status_code == 401
    assert response.body == b"Unauthorized"
    assert handler_calls == 0


@pytest.mark.asyncio
async def test_auth_hook_errors_do_not_leak_authorization_values() -> None:
    secret_token = "secret-token"

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        raise RuntimeError(f"failed to verify {ctx.headers['authorization']}")

    app = App(auth=authenticate)

    @app.get("/private")
    async def private() -> dict[str, bool]:
        return {"ok": True}

    response = await app.handle(
        Request(
            method="GET",
            path="/private",
            headers={"authorization": secret_token},
        )
    )

    assert response.status_code == 500
    assert response.body == b"Internal Server Error"
    assert secret_token.encode() not in response.body


@pytest.mark.asyncio
async def test_auth_request_headers_are_read_only() -> None:
    seen_mutation_error = False

    async def authenticate(ctx: AuthRequest) -> AuthContext | None:
        nonlocal seen_mutation_error
        try:
            ctx.headers["authorization"] = "changed"  # type: ignore[index]
        except TypeError:
            seen_mutation_error = True
        return AuthContext(subject=ctx.headers["authorization"])

    app = App(auth=authenticate)

    @app.get("/me")
    async def me(request: Request) -> dict[str, str]:
        assert request.auth is not None
        return {"subject": request.auth.subject}

    response = await app.handle(
        Request(method="GET", path="/me", headers={"authorization": "user_1"})
    )

    assert response.status_code == 200
    assert seen_mutation_error is True
    assert response.body == b'{"subject":"user_1"}'
