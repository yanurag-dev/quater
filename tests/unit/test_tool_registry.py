from __future__ import annotations

import pytest

from quater import Quater
from quater.core import RouteDefinition
from quater.exceptions import ConfigurationError
from quater.tools.registry import build_tool_registry
from quater.typing import AuthContext, AuthRequest


async def allow_mcp_auth(ctx: AuthRequest) -> AuthContext | None:
    return AuthContext(subject="mcp")


def test_registry_exposes_only_routes_marked_as_tools() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/private")
    async def private() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/public", tool=True)
    async def public() -> dict[str, bool]:
        """Return the public status."""
        return {"ok": True}

    registry = build_tool_registry(app.routes)

    assert list(registry.tools) == ["public"]
    assert registry.tools["public"].description == "Return the public status."


def test_explicit_tool_description_overrides_handler_docstring() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/public", tool=True, description="Return public status for agents.")
    async def public() -> dict[str, bool]:
        """This fallback docstring should not be used."""
        return {"ok": True}

    registry = build_tool_registry(app.routes)

    assert registry.list_tools()[0]["description"] == "Return public status for agents."


def test_tool_routes_must_define_a_description() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    with pytest.raises(ConfigurationError, match="non-empty description"):

        @app.get("/public", tool=True)
        async def public() -> dict[str, bool]:
            return {"ok": True}


def test_registry_defensively_rejects_missing_tool_description() -> None:
    async def public() -> dict[str, bool]:
        return {"ok": True}

    route = RouteDefinition(
        method="GET",
        path="/public",
        handler=public,
        name="public",
        tool=True,
    )

    with pytest.raises(ConfigurationError, match="non-empty description"):
        build_tool_registry((route,))


def test_tool_descriptions_have_a_reasonable_size_limit() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    with pytest.raises(ConfigurationError, match="1000 characters"):

        @app.get("/public", tool=True, description="x" * 1001)
        async def public() -> dict[str, bool]:
            return {"ok": True}


def test_duplicate_tool_names_fail_when_registry_is_built() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/users/{id:int}", tool=True, name="lookup", description="Find a user.")
    async def lookup_user(id: int) -> dict[str, int]:
        return {"id": id}

    @app.get(
        "/orders/{id:int}",
        tool=True,
        name="lookup",
        description="Find an order.",
    )
    async def lookup_order(id: int) -> dict[str, int]:
        return {"id": id}

    with pytest.raises(ConfigurationError, match="Duplicate tool name"):
        build_tool_registry(app.routes)


def test_app_builds_tool_registry_during_route_compile() -> None:
    app = Quater(mcp_auth=allow_mcp_auth)

    @app.get("/items/{id:int}", tool=True, description="Fetch one item.")
    async def get_item(id: int) -> dict[str, int]:
        return {"id": id}

    app.compile_routes()

    assert app._compiled_tool_registry().get("get_item") is not None


def test_tool_routes_require_mcp_auth() -> None:
    app = Quater()

    with pytest.raises(ConfigurationError, match="MCP tools require mcp_auth"):

        @app.get("/items/{id:int}", tool=True, description="Fetch one item.")
        async def get_item(id: int) -> dict[str, int]:
            return {"id": id}
