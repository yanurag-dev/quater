"""Application root for Quater."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import TYPE_CHECKING, Any, TypeVar, cast, overload

from quater.auth import authenticate_request
from quater.config import AppConfig, MaxBodySize, SecurityMode
from quater.core import Handler, RouteDefinition
from quater.cors import CORSConfig, add_cors_headers, is_cors_preflight
from quater.exceptions import MiddlewareStateError
from quater.lifespan import LifespanManager
from quater.middleware import (
    AfterMiddleware,
    AroundMiddleware,
    BeforeMiddleware,
    ExceptionHandlerEntry,
    ExceptionMiddleware,
    MiddlewareStack,
    default_exception_response,
)
from quater.request import Request
from quater.response import EmptyResponse, Response
from quater.router import Router
from quater.security import (
    RequestSecurityContext,
    add_security_headers,
    prepare_request_security,
    resolve_request_security_context,
)
from quater.tools.descriptions import (
    normalize_route_description,
    resolve_tool_description,
)
from quater.typing import Authenticate, LifespanHook

HandlerT = TypeVar("HandlerT", bound=Handler)


if TYPE_CHECKING:
    from quater.adapters.asgi import ASGIAdapter, ASGIReceive, ASGIScope, ASGISend
    from quater.adapters.rsgi import (
        RSGIAdapter,
        RSGICallbackResult,
        RSGIHTTPProtocol,
        RSGIScope,
        RSGIWebSocketProtocol,
    )
    from quater.adapters.wsgi import StartResponse, WSGIAdapter, WSGIEnvironment
    from quater.tools.audit import AuditHook
    from quater.tools.registry import ToolRegistry


class Quater:
    """Central Quater application object."""

    __slots__ = (
        "config",
        "mcp_audit",
        "name",
        "_asgi_adapter",
        "_lifespan",
        "_middleware",
        "_rsgi_adapter",
        "_router",
        "_routes",
        "_routes_dirty",
        "_tool_registry",
        "_wsgi_adapter",
    )

    def __init__(
        self,
        *,
        name: str | None = None,
        config: AppConfig | None = None,
        debug: bool | None = None,
        security: SecurityMode | None = None,
        allowed_hosts: Iterable[str] | None = None,
        trusted_proxies: Iterable[str] | None = None,
        max_body_size: MaxBodySize | None = None,
        cors: CORSConfig | None = None,
        content_security_policy: str | None = None,
        mcp_enabled: bool | None = None,
        mcp_path: str | None = None,
        mcp_allowed_origins: Iterable[str] | None = None,
        mcp_audit: AuditHook | None = None,
    ) -> None:
        self.name = name
        self.config = (config or AppConfig()).with_overrides(
            debug=debug,
            security=security,
            allowed_hosts=allowed_hosts,
            trusted_proxies=trusted_proxies,
            max_body_size=max_body_size,
            cors=cors,
            content_security_policy=content_security_policy,
            mcp_enabled=mcp_enabled,
            mcp_path=mcp_path,
            mcp_allowed_origins=mcp_allowed_origins,
        )
        self.mcp_audit = mcp_audit
        self._asgi_adapter: ASGIAdapter | None = None
        self._lifespan = LifespanManager()
        self._middleware = MiddlewareStack()
        self._rsgi_adapter: RSGIAdapter | None = None
        self._routes: list[RouteDefinition] = []
        self._router: Router | None = None
        self._tool_registry: ToolRegistry | None = None
        self._wsgi_adapter: WSGIAdapter | None = None
        self._routes_dirty = True

    @property
    def routes(self) -> tuple[RouteDefinition, ...]:
        """Registered route definitions."""

        return tuple(self._routes)

    @property
    def asgi(self) -> ASGIAdapter:
        adapter = self._asgi_adapter
        if adapter is None:
            from quater.adapters.asgi import ASGIAdapter

            adapter = ASGIAdapter(self)
            self._asgi_adapter = adapter
        return adapter

    @property
    def rsgi(self) -> RSGIAdapter:
        adapter = self._rsgi_adapter
        if adapter is None:
            from quater.adapters.rsgi import RSGIAdapter

            adapter = RSGIAdapter(self)
            self._rsgi_adapter = adapter
        return adapter

    @property
    def wsgi(self) -> WSGIAdapter:
        adapter = self._wsgi_adapter
        if adapter is None:
            from quater.adapters.wsgi import WSGIAdapter

            adapter = WSGIAdapter(self)
            self._wsgi_adapter = adapter
        return adapter

    @property
    def __rsgi__(self) -> RSGIAdapter:
        return self.rsgi

    @overload
    def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceive,
        send: ASGISend,
        /,
    ) -> Awaitable[None]: ...

    @overload
    def __call__(
        self,
        environ: WSGIEnvironment,
        start_response: StartResponse,
        /,
    ) -> Iterable[bytes]: ...

    @overload
    def __call__(
        self,
        scope: RSGIScope,
        protocol: RSGIHTTPProtocol | RSGIWebSocketProtocol,
        /,
    ) -> RSGICallbackResult: ...

    def __call__(
        self,
        scope_or_environ: object,
        receive_or_start_response_or_protocol: object,
        send: object | None = None,
        /,
    ) -> object:
        if send is not None:
            return self.asgi(
                cast("ASGIScope", scope_or_environ),
                cast("ASGIReceive", receive_or_start_response_or_protocol),
                cast("ASGISend", send),
            )

        if isinstance(scope_or_environ, dict):
            return self.wsgi(
                cast("WSGIEnvironment", scope_or_environ),
                cast("StartResponse", receive_or_start_response_or_protocol),
            )
        return self.rsgi(
            cast("RSGIScope", scope_or_environ),
            cast(
                "RSGIHTTPProtocol | RSGIWebSocketProtocol",
                receive_or_start_response_or_protocol,
            ),
        )

    def add_route(
        self,
        method: str,
        path: str,
        handler: Handler,
        *,
        name: str | None = None,
        description: str | None = None,
        tool: bool = False,
        auth: Authenticate | None = None,
        metadata: dict[str, Any] | None = None,
        before: Iterable[BeforeMiddleware] = (),
        after: Iterable[AfterMiddleware] = (),
        around: Iterable[AroundMiddleware] = (),
        exception_handlers: Iterable[ExceptionHandlerEntry] = (),
    ) -> RouteDefinition:
        """Register route metadata without compiling or matching it."""

        route_name = name
        if route_name is None:
            discovered_name = getattr(handler, "__name__", None)
            route_name = (
                discovered_name if isinstance(discovered_name, str) else "anonymous"
            )
        route_description = (
            resolve_tool_description(route_name, description, handler)
            if tool
            else normalize_route_description(description)
        )

        route = RouteDefinition(
            method=method.upper(),
            path=path,
            handler=handler,
            name=route_name,
            description=route_description,
            tool=tool,
            auth=auth,
            metadata=dict(metadata or {}),
            middleware=MiddlewareStack.from_parts(
                before=before,
                after=after,
                around=around,
                exception_handlers=exception_handlers,
            ),
        )
        self._routes.append(route)
        self._tool_registry = None
        self._routes_dirty = True
        return route

    def route(
        self,
        method: str,
        path: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tool: bool = False,
        auth: Authenticate | None = None,
        metadata: dict[str, Any] | None = None,
        before: Iterable[BeforeMiddleware] = (),
        after: Iterable[AfterMiddleware] = (),
        around: Iterable[AroundMiddleware] = (),
        exception_handlers: Iterable[ExceptionHandlerEntry] = (),
    ) -> Callable[[HandlerT], HandlerT]:
        """Register a handler for an HTTP method and path."""

        def decorator(handler: HandlerT) -> HandlerT:
            self.add_route(
                method,
                path,
                handler,
                name=name,
                description=description,
                tool=tool,
                auth=auth,
                metadata=metadata,
                before=before,
                after=after,
                around=around,
                exception_handlers=exception_handlers,
            )
            return handler

        return decorator

    def get(
        self,
        path: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tool: bool = False,
        auth: Authenticate | None = None,
        metadata: dict[str, Any] | None = None,
        before: Iterable[BeforeMiddleware] = (),
        after: Iterable[AfterMiddleware] = (),
        around: Iterable[AroundMiddleware] = (),
        exception_handlers: Iterable[ExceptionHandlerEntry] = (),
    ) -> Callable[[HandlerT], HandlerT]:
        return self.route(
            "GET",
            path,
            name=name,
            description=description,
            tool=tool,
            auth=auth,
            metadata=metadata,
            before=before,
            after=after,
            around=around,
            exception_handlers=exception_handlers,
        )

    def post(
        self,
        path: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tool: bool = False,
        auth: Authenticate | None = None,
        metadata: dict[str, Any] | None = None,
        before: Iterable[BeforeMiddleware] = (),
        after: Iterable[AfterMiddleware] = (),
        around: Iterable[AroundMiddleware] = (),
        exception_handlers: Iterable[ExceptionHandlerEntry] = (),
    ) -> Callable[[HandlerT], HandlerT]:
        return self.route(
            "POST",
            path,
            name=name,
            description=description,
            tool=tool,
            auth=auth,
            metadata=metadata,
            before=before,
            after=after,
            around=around,
            exception_handlers=exception_handlers,
        )

    def put(
        self,
        path: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tool: bool = False,
        auth: Authenticate | None = None,
        metadata: dict[str, Any] | None = None,
        before: Iterable[BeforeMiddleware] = (),
        after: Iterable[AfterMiddleware] = (),
        around: Iterable[AroundMiddleware] = (),
        exception_handlers: Iterable[ExceptionHandlerEntry] = (),
    ) -> Callable[[HandlerT], HandlerT]:
        return self.route(
            "PUT",
            path,
            name=name,
            description=description,
            tool=tool,
            auth=auth,
            metadata=metadata,
            before=before,
            after=after,
            around=around,
            exception_handlers=exception_handlers,
        )

    def patch(
        self,
        path: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tool: bool = False,
        auth: Authenticate | None = None,
        metadata: dict[str, Any] | None = None,
        before: Iterable[BeforeMiddleware] = (),
        after: Iterable[AfterMiddleware] = (),
        around: Iterable[AroundMiddleware] = (),
        exception_handlers: Iterable[ExceptionHandlerEntry] = (),
    ) -> Callable[[HandlerT], HandlerT]:
        return self.route(
            "PATCH",
            path,
            name=name,
            description=description,
            tool=tool,
            auth=auth,
            metadata=metadata,
            before=before,
            after=after,
            around=around,
            exception_handlers=exception_handlers,
        )

    def delete(
        self,
        path: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tool: bool = False,
        auth: Authenticate | None = None,
        metadata: dict[str, Any] | None = None,
        before: Iterable[BeforeMiddleware] = (),
        after: Iterable[AfterMiddleware] = (),
        around: Iterable[AroundMiddleware] = (),
        exception_handlers: Iterable[ExceptionHandlerEntry] = (),
    ) -> Callable[[HandlerT], HandlerT]:
        return self.route(
            "DELETE",
            path,
            name=name,
            description=description,
            tool=tool,
            auth=auth,
            metadata=metadata,
            before=before,
            after=after,
            around=around,
            exception_handlers=exception_handlers,
        )

    def compile_routes(self) -> Router:
        """Compile route definitions into a dispatcher."""

        self._router = Router.compile(
            tuple(self._routes),
            middleware=self._middleware,
            debug=self.config.debug,
        )
        if self.config.mcp_enabled:
            from quater.tools.registry import build_tool_registry

            self._tool_registry = build_tool_registry(tuple(self._routes))
        self._routes_dirty = False
        return self._router

    def before_request(self, middleware: BeforeMiddleware) -> BeforeMiddleware:
        """Register a global before-request middleware."""

        self._ensure_middleware_mutable()
        self._middleware = MiddlewareStack(
            before=(*self._middleware.before, middleware),
            after=self._middleware.after,
            around=self._middleware.around,
            exception_handlers=self._middleware.exception_handlers,
        )
        return middleware

    def after_response(self, middleware: AfterMiddleware) -> AfterMiddleware:
        """Register a global after-response middleware."""

        self._ensure_middleware_mutable()
        self._middleware = MiddlewareStack(
            before=self._middleware.before,
            after=(*self._middleware.after, middleware),
            around=self._middleware.around,
            exception_handlers=self._middleware.exception_handlers,
        )
        return middleware

    def around_request(self, middleware: AroundMiddleware) -> AroundMiddleware:
        """Register a global around-request middleware."""

        self._ensure_middleware_mutable()
        self._middleware = MiddlewareStack(
            before=self._middleware.before,
            after=self._middleware.after,
            around=(*self._middleware.around, middleware),
            exception_handlers=self._middleware.exception_handlers,
        )
        return middleware

    def exception_handler(
        self,
        exception_type: type[Exception],
    ) -> Callable[[ExceptionMiddleware], ExceptionMiddleware]:
        """Register a global exception handler."""

        def decorator(handler: ExceptionMiddleware) -> ExceptionMiddleware:
            self._ensure_middleware_mutable()
            self._middleware = MiddlewareStack(
                before=self._middleware.before,
                after=self._middleware.after,
                around=self._middleware.around,
                exception_handlers=(
                    *self._middleware.exception_handlers,
                    ExceptionHandlerEntry(exception_type, handler),
                ),
            )
            return handler

        return decorator

    def on_startup(self, hook: LifespanHook) -> LifespanHook:
        """Register an async startup hook and return it for decorator usage."""

        return self._lifespan.on_startup(hook)

    def on_shutdown(self, hook: LifespanHook) -> LifespanHook:
        """Register an async shutdown hook and return it for decorator usage."""

        return self._lifespan.on_shutdown(hook)

    async def startup(self) -> None:
        """Run startup hooks once."""

        await self._lifespan.startup()

    async def shutdown(self) -> None:
        """Run shutdown hooks once after startup."""

        await self._lifespan.shutdown()

    async def handle(self, request: Request) -> Response:
        """Handle a normalized request through the core dispatcher."""

        return await self._handle_request(request)

    async def _handle_request(self, request: Request) -> Response:
        context = resolve_request_security_context(request, self.config)
        is_mcp_request = (
            self.config.mcp_enabled and request.path == self.config.mcp_path
        )
        try:
            context = prepare_request_security(request, self.config)
            if self.config.cors is not None and is_cors_preflight(request):
                return self._finalize_response(EmptyResponse(), request, context)
            if is_mcp_request:
                from quater.tools.mcp import mcp_request_context, validate_mcp_origin

                validate_mcp_origin(request, self.config)
                request.context = await mcp_request_context(request)
            if not is_mcp_request:
                router = self._compiled_router()
                match = router.match(request.method, request.path)
                if match.route is not None:
                    await self._authenticate_route(match.route.definition, request)
        except Exception as exc:
            response = default_exception_response(exc, debug=self.config.debug)
            return self._finalize_response(response, request, context)

        if is_mcp_request:
            from quater.tools.mcp import handle_mcp_request

            response = await handle_mcp_request(
                request,
                self._compiled_tool_registry(),
                audit_hook=self.mcp_audit,
                debug=self.config.debug,
            )
        else:
            response = await router.dispatch_match(request, match)
        return self._finalize_response(response, request, context)

    def _compiled_router(self) -> Router:
        if self._router is None or self._routes_dirty:
            return self.compile_routes()
        return self._router

    def _compiled_tool_registry(self) -> ToolRegistry:
        if self._tool_registry is None or self._routes_dirty:
            from quater.tools.registry import build_tool_registry

            self._tool_registry = build_tool_registry(tuple(self._routes))
        return self._tool_registry

    def _ensure_middleware_mutable(self) -> None:
        if self._router is not None:
            raise MiddlewareStateError(
                "Cannot register middleware after routes are compiled"
            )

    async def _authenticate_route(
        self,
        route: RouteDefinition,
        request: Request,
    ) -> None:
        if route.auth is None or request.auth is not None:
            return
        await authenticate_request(route.auth, request)

    def _finalize_response(
        self,
        response: Response,
        request: Request,
        context: RequestSecurityContext,
    ) -> Response:
        if self.config.cors is not None:
            response = add_cors_headers(response, request, self.config.cors)
        return add_security_headers(response, context, self.config)
