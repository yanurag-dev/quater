"""Argument parsing helpers for action calls."""

from __future__ import annotations

import re
from collections.abc import Sequence

from quater.cli.errors import CLIUsageError
from quater.exceptions import RequestJSONError
from quater.serialization import loads_json

_JSON_SCALAR = frozenset({"true", "false", "null"})
_JSON_NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$")


def parse_headers(*, token: str | None, headers: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if token is not None:
        token = token.strip()
        if not token:
            raise CLIUsageError("Auth token must not be empty")
        parsed["authorization"] = f"Bearer {token}"

    for header in headers:
        name, separator, value = header.partition(":")
        normalized_name = name.strip().lower()
        if not separator or not normalized_name:
            raise CLIUsageError("Headers must be provided as 'Name: value'")
        if normalized_name == "authorization" and token is not None:
            raise CLIUsageError("Use either --token or an Authorization header")
        parsed[normalized_name] = value.strip()

    return parsed


def parse_action_arguments(raw_arguments: Sequence[str]) -> dict[str, object]:
    arguments: dict[str, object] = {}
    index = 0
    while index < len(raw_arguments):
        token = raw_arguments[index]
        if token == "--":
            index += 1
            continue
        if not token.startswith("--") or token == "--":
            raise CLIUsageError(f"Unexpected action argument {token!r}")

        raw_name = token[2:]
        if "=" in raw_name:
            raw_name, raw_value = raw_name.split("=", 1)
        else:
            index += 1
            if index >= len(raw_arguments) or raw_arguments[index].startswith("--"):
                raise CLIUsageError(f"Missing value for action argument --{raw_name}")
            raw_value = raw_arguments[index]

        name = raw_name.strip().replace("-", "_")
        if not name.isidentifier():
            raise CLIUsageError(f"Invalid action argument name --{raw_name}")
        if name in arguments:
            raise CLIUsageError(f"Duplicate action argument --{raw_name}")

        arguments[name] = parse_value(raw_value, name=name)
        index += 1

    return arguments


def parse_value(value: str, *, name: str) -> object:
    stripped = value.strip()
    if not _should_parse_json(stripped):
        return value
    try:
        return loads_json(stripped.encode("utf-8"))
    except RequestJSONError as exc:
        raise CLIUsageError(f"Invalid JSON value for --{name}") from exc


def _should_parse_json(value: str) -> bool:
    if value in _JSON_SCALAR:
        return True
    if value.startswith(("{", "[", '"')):
        return True
    return bool(_JSON_NUMBER.fullmatch(value))
