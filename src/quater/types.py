"""Backward-compatible typing aliases.

Prefer importing framework extension types from :mod:`quater.typing`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeAlias

from quater.typing import AuthContext, Authenticate, AuthRequest, LifespanHook

AsyncCallable: TypeAlias = Callable[..., Awaitable[object]]

__all__ = [
    "AsyncCallable",
    "Authenticate",
    "AuthContext",
    "AuthRequest",
    "LifespanHook",
]
