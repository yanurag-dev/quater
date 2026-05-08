"""Tool exposure for MCP clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "AuditHook",
    "ToolAuditEvent",
    "ToolDefinition",
    "ToolRegistry",
    "build_tool_registry",
]

if TYPE_CHECKING:
    from quater.tools.audit import AuditHook, ToolAuditEvent
    from quater.tools.registry import ToolDefinition, ToolRegistry, build_tool_registry


def __getattr__(name: str) -> object:
    if name in {"AuditHook", "ToolAuditEvent"}:
        from quater.tools.audit import AuditHook, ToolAuditEvent

        value = {
            "AuditHook": AuditHook,
            "ToolAuditEvent": ToolAuditEvent,
        }[name]
        globals()[name] = value
        return value

    if name in {"ToolDefinition", "ToolRegistry", "build_tool_registry"}:
        from quater.tools.registry import (
            ToolDefinition,
            ToolRegistry,
            build_tool_registry,
        )

        value = {
            "ToolDefinition": ToolDefinition,
            "ToolRegistry": ToolRegistry,
            "build_tool_registry": build_tool_registry,
        }[name]
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
