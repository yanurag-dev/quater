"""Public typing helpers for framework extension points."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, TypeAlias


def _empty_str_map() -> Mapping[str, str]:
    return MappingProxyType({})


def _empty_metadata() -> Mapping[str, object]:
    return MappingProxyType({})


@dataclass(slots=True, frozen=True)
class RequestContext:
    """Small per-call context shared by HTTP APIs and tool calls."""

    source: Literal["api", "mcp", "tool"] = "api"
    tool_name: str | None = None


@dataclass(slots=True, frozen=True)
class AuthRequest:
    """Small request view passed to the future central auth hook."""

    method: str
    path: str
    headers: Mapping[str, str] = _empty_str_map()
    context: RequestContext = field(default_factory=RequestContext)


@dataclass(slots=True, frozen=True)
class AuthContext:
    """Authenticated subject information returned by a user auth hook."""

    subject: str
    metadata: Mapping[str, object] = _empty_metadata()


Authenticate: TypeAlias = Callable[[AuthRequest], Awaitable[AuthContext | None]]
LifespanHook: TypeAlias = Callable[[], Awaitable[None]]

__all__ = [
    "Authenticate",
    "AuthContext",
    "AuthRequest",
    "LifespanHook",
    "RequestContext",
]
