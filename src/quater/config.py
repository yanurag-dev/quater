"""Typed application configuration for Quater."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from ipaddress import ip_network
from typing import Literal, TypeAlias

from quater.cors import CORSConfig
from quater.exceptions import ConfigurationError

SecurityMode: TypeAlias = Literal["strict", "relaxed", "off"]
MaxBodySize: TypeAlias = int | str

_SIZE_UNITS = {
    "b": 1,
    "kb": 1024,
    "mb": 1024 * 1024,
    "gb": 1024 * 1024 * 1024,
}


@dataclass(slots=True, frozen=True)
class AppConfig:
    """Immutable app configuration."""

    debug: bool = False
    security: SecurityMode = "strict"
    allowed_hosts: tuple[str, ...] = ()
    trusted_proxies: tuple[str, ...] = ()
    max_body_size: int = 2 * 1024 * 1024
    cors: CORSConfig | None = None
    content_security_policy: str | None = None
    mcp_enabled: bool = False
    mcp_path: str = "/mcp"
    mcp_allowed_origins: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.security not in {"strict", "relaxed", "off"}:
            raise ConfigurationError(f"Unsupported security mode: {self.security!r}")
        if self.max_body_size < 0:
            raise ConfigurationError("max_body_size must be greater than or equal to 0")
        if any(not _is_valid_ip_network(proxy) for proxy in self.trusted_proxies):
            raise ConfigurationError(
                "trusted_proxies must contain IP addresses or CIDR networks"
            )
        if (
            self.content_security_policy is not None
            and not self.content_security_policy.strip()
        ):
            raise ConfigurationError("content_security_policy must not be empty")
        if not self.mcp_path.startswith("/"):
            raise ConfigurationError("mcp_path must start with '/'")
        if "?" in self.mcp_path or "#" in self.mcp_path:
            raise ConfigurationError(
                "mcp_path must not include query strings or fragments"
            )

    def with_overrides(
        self,
        *,
        debug: bool | None = None,
        security: SecurityMode | None = None,
        allowed_hosts: Iterable[str] | None = None,
        trusted_proxies: Iterable[str] | None = None,
        max_body_size: MaxBodySize | None = None,
        cors: CORSConfig | None = None,
        content_security_policy: str | None = None,
        mcp_enabled: bool | None = None,
        mcp_path: str | None = None,
        mcp_allowed_origins: Iterable[str] | None = None,
    ) -> AppConfig:
        """Return a new config with explicit overrides applied."""

        return replace(
            self,
            debug=self.debug if debug is None else debug,
            security=self.security if security is None else security,
            allowed_hosts=(
                self.allowed_hosts
                if allowed_hosts is None
                else _normalize_string_tuple(allowed_hosts, "allowed_hosts")
            ),
            trusted_proxies=(
                self.trusted_proxies
                if trusted_proxies is None
                else _normalize_string_tuple(trusted_proxies, "trusted_proxies")
            ),
            max_body_size=(
                self.max_body_size
                if max_body_size is None
                else parse_size(max_body_size, field_name="max_body_size")
            ),
            cors=self.cors if cors is None else cors,
            content_security_policy=(
                self.content_security_policy
                if content_security_policy is None
                else content_security_policy
            ),
            mcp_enabled=self.mcp_enabled if mcp_enabled is None else mcp_enabled,
            mcp_path=self.mcp_path if mcp_path is None else mcp_path,
            mcp_allowed_origins=(
                self.mcp_allowed_origins
                if mcp_allowed_origins is None
                else _normalize_string_tuple(
                    mcp_allowed_origins,
                    "mcp_allowed_origins",
                )
            ),
        )


def parse_size(value: MaxBodySize, *, field_name: str) -> int:
    """Parse byte sizes such as ``"2mb"`` into integer bytes."""

    if isinstance(value, int):
        if value < 0:
            raise ConfigurationError(f"{field_name} must be greater than or equal to 0")
        return value

    normalized = value.strip().lower()
    if not normalized:
        raise ConfigurationError(f"{field_name} must not be empty")

    digits = "".join(char for char in normalized if char.isdigit())
    unit = normalized[len(digits) :].strip()
    if not digits or unit not in _SIZE_UNITS:
        allowed = ", ".join(sorted(_SIZE_UNITS))
        raise ConfigurationError(
            f"{field_name} must be bytes or a string like '2mb' ({allowed})"
        )

    return int(digits) * _SIZE_UNITS[unit]


def _normalize_string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(values)
    if any(not value for value in normalized):
        raise ConfigurationError(f"{field_name} cannot contain empty values")
    return normalized


def _is_valid_ip_network(value: str) -> bool:
    try:
        ip_network(value, strict=False)
    except ValueError:
        return False
    return True
