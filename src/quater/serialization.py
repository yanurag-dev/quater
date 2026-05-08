"""JSON serialization helpers."""

from __future__ import annotations

from typing import Any

import msgspec

from quater.exceptions import RequestJSONError


class JSONValidationError(ValueError):
    """Raised when valid JSON fails the requested Python type."""


def dumps_json(value: object) -> bytes:
    """Serialize a value as JSON bytes."""

    return msgspec.json.encode(value)


def loads_json(data: bytes) -> Any:
    """Decode JSON bytes."""

    try:
        return msgspec.json.decode(data)
    except msgspec.DecodeError as exc:
        raise RequestJSONError from exc


def loads_json_as(data: bytes, target: object) -> object:
    """Decode JSON bytes directly into a target type."""

    try:
        return msgspec.json.decode(data, type=target)
    except msgspec.ValidationError as exc:
        raise JSONValidationError from exc
    except msgspec.DecodeError as exc:
        raise RequestJSONError from exc
