"""Compiled route dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from quater.core import RouteDefinition
from quater.exceptions import RouteConflictError
from quater.middleware import MiddlewareStack, RouteHandler, compile_middleware_pipeline
from quater.params import HandlerPlan, build_handler_plan
from quater.request import Request
from quater.response import Response, TextResponse, normalize_response
from quater.routing import (
    ParamSegment,
    RoutePattern,
    StaticSegment,
    parse_route_pattern,
    split_request_path,
)


@dataclass(slots=True, frozen=True)
class CompiledRoute:
    definition: RouteDefinition
    pattern: RoutePattern
    handler_plan: HandlerPlan
    pipeline: RouteHandler

    async def dispatch(
        self,
        request: Request,
        path_params: dict[str, object],
    ) -> Response:
        return await self.pipeline(request, path_params)


@dataclass(slots=True)
class RouterNode:
    static_children: dict[str, RouterNode] = field(default_factory=dict)
    param_child: tuple[ParamSegment, RouterNode] | None = None
    routes: dict[str, CompiledRoute] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class Match:
    route: CompiledRoute | None
    path_params: dict[str, object]
    allowed_methods: frozenset[str]


class Router:
    """Compiled route matcher and dispatcher."""

    __slots__ = ("_fallback_pipeline", "_root")

    def __init__(self) -> None:
        self._root = RouterNode()
        self._fallback_pipeline = compile_middleware_pipeline(
            self._fallback_endpoint,
            global_stack=MiddlewareStack(),
            route_stack=MiddlewareStack(),
            debug=False,
        )

    @classmethod
    def compile(
        cls,
        routes: tuple[RouteDefinition, ...],
        *,
        middleware: MiddlewareStack | None = None,
        debug: bool = False,
    ) -> Router:
        router = cls()
        global_middleware = middleware or MiddlewareStack()
        router._fallback_pipeline = compile_middleware_pipeline(
            router._fallback_endpoint,
            global_stack=global_middleware,
            route_stack=MiddlewareStack(),
            debug=debug,
        )
        seen_shapes: dict[tuple[str, tuple[tuple[str, str], ...]], str] = {}
        for route in routes:
            pattern = parse_route_pattern(route.path)
            shape_key = (route.method, pattern.shape)
            if shape_key in seen_shapes:
                raise RouteConflictError(
                    f"Route {route.method} {route.path!r} conflicts with "
                    f"{seen_shapes[shape_key]!r}"
                )
            seen_shapes[shape_key] = route.path
            router._insert(
                route,
                pattern,
                global_middleware=global_middleware,
                debug=debug,
            )
        return router

    async def dispatch(self, request: Request) -> Response:
        match = self.match(request.method, request.path)
        if match.route is None:
            return await self._fallback_pipeline(request, {})

        return await match.route.dispatch(request, match.path_params)

    async def _fallback_endpoint(
        self,
        request: Request,
        path_params: Mapping[str, object],
    ) -> Response:
        match = self.match(request.method, request.path)
        if match.allowed_methods:
            allow = ", ".join(sorted(match.allowed_methods))
            return TextResponse(
                "Method Not Allowed",
                status_code=405,
                headers={"allow": allow},
            )
        return TextResponse(f"Not found: {request.path}", status_code=404)

    def match(self, method: str, path: str) -> Match:
        node = self._root
        path_params: dict[str, object] = {}

        for segment in split_request_path(path):
            static_child = node.static_children.get(segment)
            if static_child is not None:
                node = static_child
                continue

            if node.param_child is None:
                return Match(None, {}, frozenset())

            param, child = node.param_child
            try:
                path_params[param.name] = param.converter(segment)
            except ValueError:
                return Match(None, {}, frozenset())
            node = child

        route = node.routes.get(method.upper())
        return Match(route, path_params, frozenset(node.routes))

    def _insert(
        self,
        route: RouteDefinition,
        pattern: RoutePattern,
        *,
        global_middleware: MiddlewareStack,
        debug: bool,
    ) -> None:
        node = self._root
        for segment in pattern.segments:
            if isinstance(segment, StaticSegment):
                node = node.static_children.setdefault(segment.value, RouterNode())
                continue

            if node.param_child is None:
                node.param_child = (segment, RouterNode())
            else:
                existing, _ = node.param_child
                if (
                    existing.converter_name != segment.converter_name
                    or existing.name != segment.name
                ):
                    raise RouteConflictError(
                        "Dynamic routes at the same position must use the same name "
                        "and converter"
                    )
            node = node.param_child[1]

        if route.method in node.routes:
            raise RouteConflictError(f"Duplicate route: {route.method} {route.path}")

        handler_plan = build_handler_plan(
            route.handler,
            path_param_names=pattern.param_names,
        )

        async def endpoint(
            request: Request,
            path_params: Mapping[str, object],
        ) -> Response:
            result = await handler_plan.call(request, path_params)
            return normalize_response(result)

        node.routes[route.method] = CompiledRoute(
            definition=route,
            pattern=pattern,
            handler_plan=handler_plan,
            pipeline=compile_middleware_pipeline(
                endpoint,
                global_stack=global_middleware,
                route_stack=route.middleware,
                debug=debug,
            ),
        )
