from __future__ import annotations

from typing import cast

import pytest

from quater import App
from quater.core import Handler
from quater.exceptions import RouteBindingError, RouteConflictError


def test_ambiguous_dynamic_route_shapes_are_rejected() -> None:
    app = App()

    @app.get("/users/{id}")
    async def by_id(id: str) -> dict[str, str]:
        return {"id": id}

    @app.get("/users/{name}")
    async def by_name(name: str) -> dict[str, str]:
        return {"name": name}

    with pytest.raises(RouteConflictError):
        app.compile_routes()


def test_duplicate_method_and_path_are_rejected() -> None:
    app = App()

    @app.get("/health")
    async def first() -> dict[str, bool]:
        return {"first": True}

    @app.get("/health")
    async def second() -> dict[str, bool]:
        return {"second": True}

    with pytest.raises(RouteConflictError):
        app.compile_routes()


def test_dynamic_route_names_must_match_across_methods() -> None:
    app = App()

    @app.get("/users/{id:int}")
    async def get_user(id: int) -> dict[str, int]:
        return {"id": id}

    @app.post("/users/{user_id:int}")
    async def update_user(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    with pytest.raises(RouteConflictError):
        app.compile_routes()


def test_sync_handlers_are_rejected_at_compile_time() -> None:
    app = App()

    def sync_handler() -> dict[str, bool]:
        return {"ok": True}

    app.add_route("GET", "/sync", cast(Handler, sync_handler))

    with pytest.raises(RouteBindingError):
        app.compile_routes()


def test_invalid_route_paths_are_rejected_at_compile_time() -> None:
    app = App()

    @app.get("missing-leading-slash")
    async def handler() -> dict[str, bool]:
        return {"ok": True}

    with pytest.raises(RouteBindingError):
        app.compile_routes()
