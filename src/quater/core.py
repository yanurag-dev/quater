"""Transport-neutral core contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from quater.middleware import MiddlewareStack

Handler: TypeAlias = Callable[..., Awaitable[object]]


@dataclass(slots=True, frozen=True)
class RouteDefinition:
    """Route metadata registered on an application."""

    method: str
    path: str
    handler: Handler
    name: str
    tool: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    middleware: MiddlewareStack = field(default_factory=MiddlewareStack)
