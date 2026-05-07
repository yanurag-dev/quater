"""Handler parameter binding."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import dataclass
from types import UnionType
from typing import Union, get_args, get_origin, get_type_hints

from quater.core import Handler
from quater.exceptions import BadRequestError, RouteBindingError
from quater.request import Request

_EMPTY = inspect.Signature.empty


@dataclass(slots=True, frozen=True)
class BoundParameter:
    name: str
    source: str
    annotation: object
    default: object


@dataclass(slots=True, frozen=True)
class HandlerPlan:
    handler: Handler
    parameters: tuple[BoundParameter, ...]

    async def call(self, request: Request, path_params: Mapping[str, object]) -> object:
        kwargs: dict[str, object] = {}
        for parameter in self.parameters:
            if parameter.source == "request":
                kwargs[parameter.name] = request
            elif parameter.source == "path":
                kwargs[parameter.name] = path_params[parameter.name]
            elif parameter.source == "query":
                kwargs[parameter.name] = _bind_query_parameter(request, parameter)
            elif parameter.source == "body":
                kwargs[parameter.name] = await _bind_body_parameter(request, parameter)

        return await self.handler(**kwargs)


def build_handler_plan(
    handler: Handler,
    *,
    path_param_names: frozenset[str],
) -> HandlerPlan:
    if not inspect.iscoroutinefunction(handler):
        raise RouteBindingError("Route handlers must be async functions")

    signature = inspect.signature(handler)
    try:
        type_hints = get_type_hints(handler)
    except NameError:
        type_hints = handler.__annotations__
    body_parameters = 0
    parameters: list[BoundParameter] = []

    for name, parameter in signature.parameters.items():
        if parameter.kind not in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }:
            raise RouteBindingError(
                f"Unsupported parameter kind for {name!r}: {parameter.kind!s}"
            )

        annotation = type_hints.get(name, parameter.annotation)
        source = _parameter_source(name, annotation, path_param_names)
        if source == "body":
            body_parameters += 1
            if body_parameters > 1:
                raise RouteBindingError("Only one body parameter is supported")

        parameters.append(
            BoundParameter(
                name=name,
                source=source,
                annotation=annotation,
                default=parameter.default,
            )
        )

    return HandlerPlan(handler=handler, parameters=tuple(parameters))


def _parameter_source(
    name: str,
    annotation: object,
    path_param_names: frozenset[str],
) -> str:
    if name in path_param_names:
        return "path"
    if name == "request" or annotation is Request:
        return "request"
    if _is_query_type(annotation):
        return "query"
    return "body"


def _bind_query_parameter(request: Request, parameter: BoundParameter) -> object:
    value = request.query.get(parameter.name)
    if value is None:
        if parameter.default is not _EMPTY:
            return parameter.default
        if _allows_none(parameter.annotation):
            return None
        raise BadRequestError(f"Missing required query parameter: {parameter.name}")
    return _convert_scalar(value, parameter.annotation, parameter.name)


async def _bind_body_parameter(request: Request, parameter: BoundParameter) -> object:
    data = await request.json()
    annotation = parameter.annotation
    if annotation is _EMPTY or annotation is object:
        return data
    if annotation in {dict, list}:
        return data

    try:
        import msgspec

        return msgspec.convert(data, type=annotation)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(
            f"Invalid JSON body for parameter: {parameter.name}"
        ) from exc


def _is_query_type(annotation: object) -> bool:
    if annotation is _EMPTY:
        return True
    annotation = _strip_optional(annotation)
    return annotation in {str, int, float, bool}


def _convert_scalar(value: str, annotation: object, name: str) -> object:
    annotation = _strip_optional(annotation)
    if annotation is _EMPTY or annotation is str:
        return value
    if annotation is int:
        try:
            return int(value)
        except ValueError as exc:
            raise BadRequestError(f"Invalid integer query parameter: {name}") from exc
    if annotation is float:
        try:
            return float(value)
        except ValueError as exc:
            raise BadRequestError(f"Invalid float query parameter: {name}") from exc
    if annotation is bool:
        return _parse_bool(value, name)
    return value


def _parse_bool(value: str, name: str) -> bool:
    normalized = value.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise BadRequestError(f"Invalid boolean query parameter: {name}")


def _strip_optional(annotation: object) -> object:
    origin = get_origin(annotation)
    if origin not in {UnionType, Union}:
        return annotation
    args = tuple(arg for arg in get_args(annotation) if arg is not type(None))
    return args[0] if len(args) == 1 else annotation


def _allows_none(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin not in {UnionType, Union}:
        return False
    return type(None) in get_args(annotation)
