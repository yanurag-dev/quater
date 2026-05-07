"""JSON schema generation for exposed tools."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from types import UnionType
from typing import Any, Union, cast, get_args, get_origin

from quater.params import BoundParameter

_EMPTY = object()


def tool_input_schema(parameters: tuple[BoundParameter, ...]) -> dict[str, object]:
    properties: dict[str, object] = {}
    required: list[str] = []

    for parameter in parameters:
        if parameter.source == "request":
            continue

        properties[parameter.name] = annotation_schema(parameter.annotation)
        if _parameter_required(parameter):
            required.append(parameter.name)

    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def annotation_schema(annotation: object) -> dict[str, object]:
    annotation = _strip_optional(annotation)
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is list:
        return {"type": "array"}
    if annotation is dict or annotation in {_EMPTY, object, Any}:
        return {"type": "object"}

    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        item_schema = annotation_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}
    if origin is dict:
        return {"type": "object"}
    if _is_msgspec_struct(annotation):
        return _msgspec_struct_schema(annotation)
    if is_dataclass(annotation) and isinstance(annotation, type):
        return _dataclass_schema(annotation)
    return {"type": "object"}


def _parameter_required(parameter: BoundParameter) -> bool:
    from inspect import Signature

    return parameter.default is Signature.empty and not _allows_none(
        parameter.annotation
    )


def _msgspec_struct_schema(annotation: object) -> dict[str, object]:
    import msgspec

    properties: dict[str, object] = {}
    required: list[str] = []
    for field in msgspec.structs.fields(cast(type[Any], annotation)):
        properties[field.name] = annotation_schema(field.type)
        if field.required:
            required.append(field.name)

    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _dataclass_schema(annotation: type[object]) -> dict[str, object]:
    from dataclasses import MISSING

    properties: dict[str, object] = {}
    required: list[str] = []
    for field in fields(cast(Any, annotation)):
        properties[field.name] = annotation_schema(field.type)
        if field.default is MISSING and field.default_factory is MISSING:
            required.append(field.name)

    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _is_msgspec_struct(annotation: object) -> bool:
    import msgspec

    return isinstance(annotation, type) and issubclass(annotation, msgspec.Struct)


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
