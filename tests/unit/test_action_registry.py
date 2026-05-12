from __future__ import annotations

import pytest

from quater import Quater
from quater.actions.registry import build_action_registry
from quater.exceptions import ConfigurationError
from quater.typing import ApprovalRequest, AuthContext, AuthRequest


async def allow_auth(ctx: AuthRequest) -> AuthContext | None:
    return AuthContext(subject=ctx.context.source)


async def approve_action(ctx: ApprovalRequest) -> bool:
    return ctx.token == "approved"


def test_cli_actions_require_cli_auth() -> None:
    app = Quater()

    with pytest.raises(ConfigurationError, match="CLI actions require cli_auth"):

        @app.post("/invoices/{id:int}/paid", cli=True, description="Mark paid.")
        async def mark_paid(id: int) -> dict[str, int]:
            return {"id": id}


def test_cli_actions_must_define_a_description() -> None:
    app = Quater(cli_auth=allow_auth)

    with pytest.raises(ConfigurationError, match="non-empty description"):

        @app.post("/invoices/{id:int}/paid", cli=True)
        async def mark_paid(id: int) -> dict[str, int]:
            return {"id": id}


def test_cli_action_description_can_come_from_handler_docstring() -> None:
    app = Quater(cli_auth=allow_auth)

    @app.post("/invoices/{id:int}/paid", cli=True)
    async def mark_paid(id: int) -> dict[str, int]:
        """Mark an invoice as paid."""
        return {"id": id}

    route = app.routes[0]

    assert route.cli is True
    assert route.tool is False
    assert route.description == "Mark an invoice as paid."


def test_approval_requires_an_action_surface() -> None:
    app = Quater(action_approval=approve_action)

    with pytest.raises(ConfigurationError, match="needs_approval requires"):

        @app.post("/invoices/{id:int}/paid", needs_approval=True)
        async def mark_paid(id: int) -> dict[str, int]:
            return {"id": id}


def test_approval_required_actions_need_approval_hook() -> None:
    app = Quater(cli_auth=allow_auth)

    with pytest.raises(
        ConfigurationError,
        match="Approval-required actions require action_approval",
    ):

        @app.post(
            "/invoices/{id:int}/paid",
            cli=True,
            needs_approval=True,
            description="Mark paid.",
        )
        async def mark_paid(id: int) -> dict[str, int]:
            return {"id": id}


def test_action_registry_exposes_cli_and_tool_routes() -> None:
    app = Quater(
        cli_auth=allow_auth,
        mcp_auth=allow_auth,
        action_approval=approve_action,
    )

    @app.post(
        "/invoices/{id:int}/paid",
        name="invoices.mark_paid",
        cli=True,
        tool=True,
        needs_approval=True,
        description="Mark an invoice as paid.",
    )
    async def mark_paid(id: int) -> dict[str, int]:
        return {"id": id}

    registry = build_action_registry(app.routes)
    action = registry.get("invoices.mark_paid")

    assert action is not None
    assert action.cli is True
    assert action.tool is True
    assert action.needs_approval is True
    assert action.description == "Mark an invoice as paid."
    assert registry.cli_actions() == (action,)
    assert registry.tool_actions() == (action,)


def test_duplicate_action_names_fail_when_registry_is_built() -> None:
    app = Quater(cli_auth=allow_auth, mcp_auth=allow_auth)

    @app.get("/users/{id:int}", cli=True, name="lookup", description="Find a user.")
    async def lookup_user(id: int) -> dict[str, int]:
        return {"id": id}

    @app.get("/orders/{id:int}", tool=True, name="lookup", description="Find order.")
    async def lookup_order(id: int) -> dict[str, int]:
        return {"id": id}

    with pytest.raises(ConfigurationError, match="Duplicate action name: lookup"):
        build_action_registry(app.routes)


def test_externally_callable_routes_need_a_stable_name() -> None:
    app = Quater(cli_auth=allow_auth)

    class CallableHandler:
        async def __call__(self) -> dict[str, bool]:
            return {"ok": True}

    with pytest.raises(ConfigurationError, match="require a name"):
        app.add_route(
            "POST",
            "/callable",
            CallableHandler(),
            cli=True,
            description="Run callable handler.",
        )
