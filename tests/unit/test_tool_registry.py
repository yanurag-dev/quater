from __future__ import annotations

import pytest

from quater import App
from quater.exceptions import ConfigurationError
from quater.tools.registry import build_tool_registry


def test_registry_exposes_only_routes_marked_as_tools() -> None:
    app = App()

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


def test_duplicate_tool_names_fail_when_registry_is_built() -> None:
    app = App()

    @app.get("/users/{id:int}", tool=True, name="lookup")
    async def lookup_user(id: int) -> dict[str, int]:
        return {"id": id}

    @app.get("/orders/{id:int}", tool=True, name="lookup")
    async def lookup_order(id: int) -> dict[str, int]:
        return {"id": id}

    with pytest.raises(ConfigurationError, match="Duplicate tool name"):
        build_tool_registry(app.routes)


def test_mcp_enabled_app_builds_tool_registry_during_route_compile() -> None:
    app = App(mcp_enabled=True)

    @app.get("/items/{id:int}", tool=True)
    async def get_item(id: int) -> dict[str, int]:
        return {"id": id}

    app.compile_routes()

    assert app._compiled_tool_registry().get("get_item") is not None
