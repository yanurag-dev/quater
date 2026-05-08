"""Compiled route dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

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
)

if TYPE_CHECKING:
    from quater._router import RouteMatcher

_EMPTY_PATH_PARAMS: Mapping[str, object] = {}


@dataclass(slots=True, frozen=True)
class CompiledRoute:
    definition: RouteDefinition
    pattern: RoutePattern
    handler_plan: HandlerPlan
    pipeline: RouteHandler

    async def dispatch(
        self,
        request: Request,
        path_params: Mapping[str, object],
    ) -> Response:
        return await self.pipeline(request, path_params)


@dataclass(slots=True, frozen=True)
class Match:
    route: CompiledRoute | None
    path_params: Mapping[str, object]
    allowed_methods: frozenset[str]


class Router:
    """Compiled route matcher and dispatcher."""

    __slots__ = ("_fallback_pipeline", "_matcher")

    def __init__(self) -> None:
        self._matcher = _new_route_matcher()
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
        method_shapes: dict[tuple[str, tuple[tuple[str, str], ...]], str] = {}
        signatures: dict[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]] = {}
        allowed_paths: dict[tuple[tuple[str, str], ...], RoutePattern] = {}
        allowed_methods: dict[tuple[tuple[str, str], ...], set[str]] = {}

        for route in routes:
            pattern = parse_route_pattern(route.path)
            route_shape = _route_shape(pattern)
            method_key = (route.method, route_shape)
            if method_key in method_shapes:
                raise RouteConflictError(
                    f"Route {route.method} {route.path!r} conflicts with "
                    f"{method_shapes[method_key]!r}"
                )
            method_shapes[method_key] = route.path

            signature = _param_signature(pattern)
            existing_signature = signatures.get(route_shape)
            if existing_signature is not None and existing_signature != signature:
                raise RouteConflictError(
                    "Dynamic routes at the same position must use the same name "
                    "and converter"
                )
            signatures[route_shape] = signature
            allowed_paths.setdefault(route_shape, pattern)
            allowed_methods.setdefault(route_shape, set()).add(route.method)

            compiled_route = router._compile_route(
                route,
                pattern,
                global_middleware=global_middleware,
                debug=debug,
            )

            try:
                router._matcher.insert_route(
                    route.method,
                    _native_path(pattern),
                    compiled_route,
                    _param_specs(pattern),
                )
            except ValueError as exc:
                raise RouteConflictError(str(exc)) from exc

        for route_shape, pattern in allowed_paths.items():
            try:
                router._matcher.insert_allowed(
                    _native_path(pattern),
                    sorted(allowed_methods[route_shape]),
                    _param_specs(pattern),
                )
            except ValueError as exc:
                raise RouteConflictError(str(exc)) from exc

        return router

    async def dispatch(self, request: Request) -> Response:
        match = self.match(request.method, request.path)
        return await self.dispatch_match(request, match)

    async def dispatch_match(self, request: Request, match: Match) -> Response:
        if match.route is None:
            return await self._fallback_pipeline(request, _EMPTY_PATH_PARAMS)

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
        route_match = self._matcher.match_route(method.upper(), path)
        if route_match is not None:
            route, path_params = route_match
            return Match(
                cast(CompiledRoute, route),
                _EMPTY_PATH_PARAMS if path_params is None else path_params,
                frozenset(),
            )

        allowed_methods = self._matcher.allowed_methods(path)
        if allowed_methods is not None:
            return Match(None, _EMPTY_PATH_PARAMS, frozenset(allowed_methods))
        return Match(None, _EMPTY_PATH_PARAMS, frozenset())

    def _compile_route(
        self,
        route: RouteDefinition,
        pattern: RoutePattern,
        *,
        global_middleware: MiddlewareStack,
        debug: bool,
    ) -> CompiledRoute:
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

        return CompiledRoute(
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


def _new_route_matcher() -> RouteMatcher:
    from quater._router import RouteMatcher

    return RouteMatcher()


def _native_path(pattern: RoutePattern) -> str:
    if not pattern.segments:
        return "/"

    parts: list[str] = []
    for segment in pattern.segments:
        if isinstance(segment, StaticSegment):
            parts.append(_native_static_segment(segment.value))
        else:
            parts.append(f"{{{segment.name}}}")
    return "/" + "/".join(parts)


def _native_static_segment(value: str) -> str:
    return value.replace("{", "{{").replace("}", "}}")


def _route_shape(pattern: RoutePattern) -> tuple[tuple[str, str], ...]:
    parts: list[tuple[str, str]] = []
    for segment in pattern.segments:
        if isinstance(segment, StaticSegment):
            parts.append(("static", segment.value))
        else:
            parts.append(("param", ""))
    return tuple(parts)


def _param_signature(pattern: RoutePattern) -> tuple[tuple[str, str], ...]:
    return tuple(
        (segment.name, segment.converter_name)
        for segment in pattern.segments
        if isinstance(segment, ParamSegment)
    )


def _param_specs(pattern: RoutePattern) -> tuple[tuple[str, str], ...]:
    return tuple(
        (segment.name, segment.converter_name)
        for segment in pattern.segments
        if isinstance(segment, ParamSegment)
    )
