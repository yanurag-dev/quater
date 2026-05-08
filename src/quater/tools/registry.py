"""Tool registry built from route metadata."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from inspect import Signature
from types import UnionType
from typing import Union, get_args, get_origin
from urllib.parse import quote, urlencode

from quater.auth import authenticate_request
from quater.core import RouteDefinition
from quater.exceptions import BadRequestError, ConfigurationError
from quater.params import BoundParameter, HandlerPlan, build_handler_plan
from quater.request import Request
from quater.response import Response, normalize_response
from quater.routing import ParamSegment, RoutePattern, parse_route_pattern
from quater.serialization import dumps_json
from quater.tools.schema import tool_input_schema
from quater.typing import RequestContext


@dataclass(slots=True, frozen=True)
class ToolDefinition:
    name: str
    description: str | None
    route: RouteDefinition
    pattern: RoutePattern
    handler_plan: HandlerPlan
    input_schema: dict[str, object]

    async def call(
        self,
        request: Request,
        arguments: Mapping[str, object],
    ) -> Response:
        path_params, query_string, body = self._build_request_parts(arguments)
        tool_request = Request(
            method=self.route.method,
            path=_render_tool_path(self.pattern, path_params),
            scheme=request.scheme,
            headers=request.headers.raw,
            query_string=query_string,
            body=body,
            auth=request.auth,
            client=request.client,
            max_body_size=request.max_body_size,
            context=RequestContext(source="tool", tool_name=self.name),
        )
        if self.route.auth is not None:
            await authenticate_request(self.route.auth, tool_request)
            request.auth = tool_request.auth
        result = await self.handler_plan.call(tool_request, path_params)
        return normalize_response(result)

    def as_mcp_tool(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "inputSchema": self.input_schema,
        }
        if self.description:
            payload["description"] = self.description
        return payload

    def _build_request_parts(
        self,
        arguments: Mapping[str, object],
    ) -> tuple[dict[str, object], str, bytes]:
        expected_names = {
            parameter.name
            for parameter in self.handler_plan.parameters
            if parameter.source != "request"
        }
        unknown = sorted(set(arguments) - expected_names)
        if unknown:
            raise BadRequestError(f"Unknown tool argument: {unknown[0]}")

        path_params: dict[str, object] = {}
        query_items: list[tuple[str, str]] = []
        body_value: object = None
        has_body = False

        converters = _path_converters(self.pattern)
        for parameter in self.handler_plan.parameters:
            if parameter.source == "request":
                continue
            if parameter.name not in arguments:
                value = _missing_value(parameter)
                if value is _MISSING and parameter.source != "query":
                    raise BadRequestError(f"Missing tool argument: {parameter.name}")
            else:
                value = arguments[parameter.name]

            if parameter.source == "path":
                path_params[parameter.name] = _convert_path_argument(
                    parameter.name,
                    value,
                    converters,
                )
            elif parameter.source == "query":
                if value is not _MISSING:
                    query_items.append((parameter.name, _argument_to_query(value)))
            elif parameter.source == "body":
                body_value = value
                has_body = True

        return (
            path_params,
            urlencode(query_items),
            dumps_json(body_value) if has_body else b"",
        )


@dataclass(slots=True, frozen=True)
class ToolRegistry:
    tools: Mapping[str, ToolDefinition]

    def list_tools(self) -> list[dict[str, object]]:
        return [tool.as_mcp_tool() for tool in self.tools.values()]

    def get(self, name: str) -> ToolDefinition | None:
        return self.tools.get(name)


def build_tool_registry(routes: tuple[RouteDefinition, ...]) -> ToolRegistry:
    tools: dict[str, ToolDefinition] = {}
    for route in routes:
        if not route.tool:
            continue

        name = route.name
        if name in tools:
            raise ConfigurationError(f"Duplicate tool name: {name}")

        pattern = parse_route_pattern(route.path)
        handler_plan = build_handler_plan(
            route.handler,
            path_param_names=pattern.param_names,
        )
        tools[name] = ToolDefinition(
            name=name,
            description=_handler_description(route.handler),
            route=route,
            pattern=pattern,
            handler_plan=handler_plan,
            input_schema=tool_input_schema(handler_plan.parameters),
        )

    return ToolRegistry(tools=tools)


_MISSING = object()


def _missing_value(parameter: BoundParameter) -> object:
    if parameter.default is not Signature.empty:
        return parameter.default
    if _allows_none(parameter.annotation):
        if parameter.source == "body":
            return None
        return _MISSING
    return _MISSING


def _path_converters(pattern: RoutePattern) -> dict[str, ParamSegment]:
    return {
        segment.name: segment
        for segment in pattern.segments
        if isinstance(segment, ParamSegment)
    }


def _convert_path_argument(
    name: str,
    value: object,
    converters: Mapping[str, ParamSegment],
) -> object:
    converter = converters[name]
    try:
        return converter.converter(str(value))
    except ValueError as exc:
        raise BadRequestError(f"Invalid path argument: {name}") from exc


def _argument_to_query(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _render_tool_path(
    pattern: RoutePattern,
    path_params: Mapping[str, object],
) -> str:
    parts: list[str] = []
    for segment in pattern.segments:
        if isinstance(segment, ParamSegment):
            parts.append(quote(str(path_params[segment.name]), safe=""))
        else:
            parts.append(segment.value)
    return "/" + "/".join(parts)


def _handler_description(handler: object) -> str | None:
    doc = getattr(handler, "__doc__", None)
    if not isinstance(doc, str):
        return None
    first_line = doc.strip().splitlines()[0] if doc.strip() else ""
    return first_line or None


def _allows_none(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin not in {UnionType, Union}:
        return False
    return type(None) in get_args(annotation)
