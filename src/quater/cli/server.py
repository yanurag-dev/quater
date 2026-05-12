"""Granian-backed server commands for the Quater CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from quater.app import Quater
from quater.cli.apps import load_app
from quater.cli.discovery import resolve_app_target
from quater.cli.errors import CLIUsageError
from quater.exceptions import QuaterError

ServerEnvironment = Literal["development", "production"]
ServerInterface = Literal["rsgi", "asgi", "wsgi"]
ServerLoop = Literal["auto", "asyncio", "rloop", "uvloop", "winloop"]
ServerLogLevel = Literal["critical", "error", "warning", "info", "debug"]


@dataclass(slots=True, frozen=True)
class ServerOptions:
    target: str | None
    environment: ServerEnvironment
    host: str
    port: int
    interface: ServerInterface
    loop: ServerLoop
    workers: int
    reload: bool
    access_log: bool
    log_level: ServerLogLevel
    factory: bool
    working_dir: Path | None = None
    strict_production: bool = True


def serve(options: ServerOptions) -> None:
    """Validate the target and hand off to Granian."""

    _set_environment(options.environment)
    resolved = _resolve_server_options(options)
    if resolved.environment == "production" and resolved.strict_production:
        app = _load_quater_app(
            resolved.target,
            factory=resolved.factory,
            working_dir=resolved.working_dir,
        )
        _validate_production_app(app)

    _serve_with_granian(resolved)


def production_safety_issues(app: Quater) -> tuple[str, ...]:
    """Return configuration issues that should block production startup."""

    issues: list[str] = []
    config = app.config
    if config.debug:
        issues.append("debug must be disabled")
    if config.security != "strict":
        issues.append("security must be 'strict'")
    if not config.allowed_hosts:
        issues.append("allowed_hosts must be configured")
    elif "*" in config.allowed_hosts:
        issues.append("allowed_hosts must not contain '*'")
    return tuple(issues)


def _resolve_server_options(options: ServerOptions) -> ServerOptions:
    discovered = resolve_app_target(
        options.target,
        working_dir=options.working_dir,
    )
    return replace(
        options,
        target=discovered.target,
        factory=options.factory or discovered.factory,
    )


def _load_quater_app(
    target: str | None,
    *,
    factory: bool,
    working_dir: Path | None,
) -> Quater:
    if target is None:
        raise CLIUsageError("Could not find a Quater app")
    return load_app(target, factory=factory, working_dir=working_dir)


def _validate_production_app(app: Quater) -> None:
    try:
        app.compile_routes()
    except QuaterError as exc:
        raise CLIUsageError(str(exc)) from exc

    issues = production_safety_issues(app)
    if issues:
        joined = "\n".join(f"- {issue}" for issue in issues)
        raise CLIUsageError(f"Production safety check failed:\n{joined}")


def _set_environment(environment: ServerEnvironment) -> None:
    os.environ["QUATER_ENV"] = environment


def _serve_with_granian(options: ServerOptions) -> None:
    try:
        from granian import Granian
        from granian.constants import Interfaces, Loops
        from granian.log import LogLevels
    except ImportError as exc:
        raise CLIUsageError("Granian is required to run Quater applications") from exc

    server = Granian(
        _require_target(options.target),
        address=options.host,
        port=options.port,
        interface=Interfaces(options.interface),
        workers=options.workers,
        loop=Loops(options.loop),
        log_access=options.access_log,
        log_level=LogLevels(options.log_level),
        reload=options.reload,
        factory=options.factory,
        working_dir=options.working_dir,
    )
    server.serve()


def _require_target(target: str | None) -> str:
    if target is None:
        raise CLIUsageError("Could not find a Quater app")
    return target
