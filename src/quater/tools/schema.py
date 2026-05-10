"""JSON schema generation for exposed tools."""

from __future__ import annotations

from quater.params import BoundParameter
from quater.schema import annotation_schema, parameter_required


def tool_input_schema(parameters: tuple[BoundParameter, ...]) -> dict[str, object]:
    properties: dict[str, object] = {}
    required: list[str] = []

    for parameter in parameters:
        if parameter.source == "request":
            continue

        properties[parameter.name] = annotation_schema(parameter.annotation)
        if parameter_required(parameter):
            required.append(parameter.name)

    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


__all__ = ["annotation_schema", "tool_input_schema"]
