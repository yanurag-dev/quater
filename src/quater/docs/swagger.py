"""Swagger UI asset helpers."""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from pathlib import Path

from quater.exceptions import ConfigurationError
from quater.response import BytesResponse
from quater.serialization import dumps_json

SWAGGER_UI_ASSETS = (
    "swagger-ui.css",
    "swagger-ui-bundle.js",
    "swagger-ui-standalone-preset.js",
    "favicon-32x32.png",
)

_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
}


def swagger_ui_asset_response(asset_name: str) -> BytesResponse:
    suffix = Path(asset_name).suffix
    return BytesResponse(
        _swagger_ui_asset_bytes(asset_name),
        headers={"cache-control": "public, max-age=3600"},
        content_type=_CONTENT_TYPES.get(suffix, "application/octet-stream"),
    )


def swagger_ui_initializer_response(openapi_path: str) -> BytesResponse:
    script = (
        "window.onload = function() {"
        "window.ui = SwaggerUIBundle({"
        f"url: {dumps_json(openapi_path).decode('utf-8')},"
        "dom_id: '#swagger-ui',"
        "deepLinking: true,"
        "presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],"
        "layout: 'StandaloneLayout',"
        "showExtensions: true,"
        "showCommonExtensions: true"
        "});"
        "};"
    )
    return BytesResponse(
        script.encode("utf-8"),
        headers={"cache-control": "no-store"},
        content_type="application/javascript; charset=utf-8",
    )


@lru_cache(maxsize=len(SWAGGER_UI_ASSETS))
def _swagger_ui_asset_bytes(asset_name: str) -> bytes:
    if asset_name not in SWAGGER_UI_ASSETS:
        raise ConfigurationError("Unsupported Swagger UI asset")

    path = _swagger_ui_asset_dir() / asset_name
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ConfigurationError("Swagger UI asset is unavailable") from exc


@lru_cache(maxsize=1)
def _swagger_ui_asset_dir() -> Path:
    bundle = import_module("swagger_ui_bundle")
    value = getattr(bundle, "swagger_ui_path", None)
    if not isinstance(value, str | Path):
        raise ConfigurationError("swagger-ui-bundle is not installed correctly")
    return Path(value)
