"""Small exception types used by the Quater CLI."""

from __future__ import annotations


class CLIError(Exception):
    exit_code = 1


class CLIUsageError(CLIError):
    exit_code = 2
