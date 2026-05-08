"""Tool description validation."""

from __future__ import annotations

from quater.exceptions import ConfigurationError

MAX_TOOL_DESCRIPTION_LENGTH = 1000


def normalize_route_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_tool_description(value: str | None) -> str | None:
    normalized = normalize_route_description(value)
    if normalized is None:
        return None
    if len(normalized) > MAX_TOOL_DESCRIPTION_LENGTH:
        raise ConfigurationError(
            "Tool descriptions must be 1000 characters or fewer"
        )
    return normalized


def handler_tool_description(handler: object) -> str | None:
    doc = getattr(handler, "__doc__", None)
    if not isinstance(doc, str):
        return None
    first_line = doc.strip().splitlines()[0] if doc.strip() else ""
    return normalize_tool_description(first_line)


def resolve_tool_description(
    route_name: str,
    explicit_description: str | None,
    handler: object,
) -> str:
    description = normalize_tool_description(explicit_description)
    if description is not None:
        return description

    description = handler_tool_description(handler)
    if description is not None:
        return description

    raise ConfigurationError(
        f"Tool route {route_name!r} must define a non-empty description"
    )
