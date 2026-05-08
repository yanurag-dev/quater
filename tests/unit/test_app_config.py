from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from quater import Quater
from quater.config import AppConfig
from quater.exceptions import ConfigurationError
from quater.request import Request
from quater.response import Response


def test_app_config_copies_mutable_inputs() -> None:
    allowed_hosts = ["api.example.com"]
    app = Quater(allowed_hosts=allowed_hosts, trusted_proxies=["127.0.0.1"])

    allowed_hosts.append("evil.example.com")

    assert app.config.allowed_hosts == ("api.example.com",)
    assert app.config.trusted_proxies == ("127.0.0.1",)


def test_app_config_is_immutable_after_creation() -> None:
    app = Quater(debug=True)
    field_name = "debug"

    with pytest.raises(FrozenInstanceError):
        setattr(app.config, field_name, False)

    assert app.config.debug is True


def test_app_config_overrides_do_not_mutate_base_config() -> None:
    base = AppConfig(allowed_hosts=("api.example.com",))
    app = Quater(config=base, allowed_hosts=["admin.example.com"], max_body_size="2mb")

    assert base.allowed_hosts == ("api.example.com",)
    assert base.max_body_size == 2 * 1024 * 1024
    assert app.config.allowed_hosts == ("admin.example.com",)
    assert app.config.max_body_size == 2 * 1024 * 1024


def test_secure_defaults_are_represented_before_enforcement_exists() -> None:
    app = Quater()

    assert app.config.debug is False
    assert app.config.security == "strict"
    assert app.config.allowed_hosts == ()
    assert app.config.trusted_proxies == ()
    assert app.config.max_body_size == 2 * 1024 * 1024
    assert app.config.cors is None
    assert app.config.content_security_policy is None
    assert app.config.mcp_enabled is False
    assert app.config.mcp_path == "/mcp"
    assert app.config.mcp_allowed_origins == ()


@pytest.mark.parametrize("value", ["", "2", "mb", "2tb", "-1mb"])
def test_invalid_body_size_strings_fail_early(value: str) -> None:
    with pytest.raises(ConfigurationError):
        Quater(max_body_size=value)


@pytest.mark.parametrize("path", ["mcp", "/mcp?debug=true", "/mcp#tools"])
def test_invalid_mcp_paths_fail_early(path: str) -> None:
    with pytest.raises(ConfigurationError):
        Quater(mcp_path=path)


def test_trusted_proxies_must_be_ip_addresses_or_networks() -> None:
    with pytest.raises(ConfigurationError):
        Quater(trusted_proxies=["proxy.internal"])


def test_empty_content_security_policy_fails_early() -> None:
    with pytest.raises(ConfigurationError):
        Quater(content_security_policy=" ")


@pytest.mark.asyncio
async def test_unknown_request_returns_framework_response_object() -> None:
    response = await Quater().handle(Request(method="GET", path="/missing"))

    assert isinstance(response, Response)
    assert response.status_code == 404
    assert response.body == b"Not found: /missing"
    headers = dict(response.headers)
    assert headers["content-type"] == "text/plain; charset=utf-8"
    assert headers["x-content-type-options"] == "nosniff"


def test_route_metadata_can_be_registered_without_compiling_routes() -> None:
    async def handler() -> dict[str, bool]:
        return {"ok": True}

    app = Quater()
    route = app.add_route(
        "get",
        "/health",
        handler,
        tool=True,
        description="Check health.",
    )

    assert app.routes == (route,)
    assert route.method == "GET"
    assert route.path == "/health"
    assert route.handler is handler
    assert route.name == "handler"
    assert route.description == "Check health."
    assert route.tool is True
    assert route.auth is None
