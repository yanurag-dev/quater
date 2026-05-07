"""Audit events for tool calls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import TypeAlias


@dataclass(slots=True, frozen=True)
class ToolAuditEvent:
    tool_name: str
    subject: str | None
    success: bool
    duration_ms: float
    arguments: Mapping[str, object]


AuditHook: TypeAlias = Callable[[ToolAuditEvent], Awaitable[None]]


def sanitize_arguments(arguments: Mapping[str, object]) -> Mapping[str, object]:
    return {name: "<redacted>" for name in arguments}
