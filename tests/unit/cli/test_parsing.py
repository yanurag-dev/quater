from __future__ import annotations

import pytest

from quater.cli.errors import CLIUsageError
from quater.cli.parsing import parse_action_arguments, parse_headers


def test_cli_rejects_duplicate_dynamic_arguments() -> None:
    with pytest.raises(CLIUsageError, match="Duplicate action argument --id"):
        parse_action_arguments(["--id", "1", "--id", "2"])


def test_cli_parses_json_scalars_and_objects() -> None:
    assert parse_action_arguments(
        [
            "--id",
            "7",
            "--active",
            "true",
            "--user",
            '{"name":"Ada"}',
        ]
    ) == {
        "id": 7,
        "active": True,
        "user": {"name": "Ada"},
    }


def test_cli_rejects_invalid_json_like_values() -> None:
    with pytest.raises(CLIUsageError, match="Invalid JSON value"):
        parse_action_arguments(["--user", '{"name":'])


def test_cli_rejects_missing_dynamic_argument_value() -> None:
    with pytest.raises(CLIUsageError, match="Missing value"):
        parse_action_arguments(["--id"])


def test_cli_rejects_invalid_header_shape() -> None:
    with pytest.raises(CLIUsageError, match="Headers must be provided"):
        parse_headers(token=None, headers=["Authorization"])


def test_cli_rejects_conflicting_authorization_inputs() -> None:
    with pytest.raises(CLIUsageError, match="Use either --token"):
        parse_headers(token="secret", headers=["Authorization: Bearer other"])


def test_cli_rejects_empty_token() -> None:
    with pytest.raises(CLIUsageError, match="Auth token must not be empty"):
        parse_headers(token=" ", headers=[])
