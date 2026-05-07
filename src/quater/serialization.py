"""JSON serialization helpers."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

import msgspec

from quater.exceptions import RequestJSONError


def dumps_json(value: object) -> bytes:
    """Serialize a value as JSON bytes."""

    return msgspec.json.encode(_json_ready(value))


def loads_json(data: bytes) -> Any:
    """Decode JSON bytes."""

    try:
        return msgspec.json.decode(data)
    except msgspec.DecodeError as exc:
        raise RequestJSONError from exc


def _json_ready(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value
