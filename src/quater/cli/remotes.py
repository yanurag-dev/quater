"""Local remote-service configuration for the Quater CLI."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from quater.cli.errors import CLIUsageError

CONFIG_FILE_MODE = 0o600
CONFIG_DIR_MODE = 0o700


@dataclass(slots=True, frozen=True)
class RemoteConfig:
    name: str
    url: str
    token: str | None = None
    manifest: dict[str, object] | None = None


def quater_home() -> Path:
    configured = os.environ.get("QUATER_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".quater"


def config_path() -> Path:
    return quater_home() / "remotes.json"


def load_remotes() -> dict[str, RemoteConfig]:
    path = config_path()
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CLIUsageError("Could not read Quater remote config") from exc

    if not isinstance(raw, dict):
        raise CLIUsageError("Quater remote config is invalid")
    raw_remotes = raw.get("remotes", {})
    if not isinstance(raw_remotes, dict):
        raise CLIUsageError("Quater remote config is invalid")

    remotes: dict[str, RemoteConfig] = {}
    for name, value in raw_remotes.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            raise CLIUsageError("Quater remote config is invalid")
        url = value.get("url")
        token = value.get("token")
        manifest = value.get("manifest")
        if not isinstance(url, str):
            raise CLIUsageError("Quater remote config is invalid")
        if token is not None and (not isinstance(token, str) or not token.strip()):
            raise CLIUsageError("Quater remote config is invalid")
        if manifest is not None and not isinstance(manifest, dict):
            raise CLIUsageError("Quater remote config is invalid")
        validated_name = validate_remote_name(name)
        validated_url = validate_remote_url(url)
        remotes[name] = RemoteConfig(
            name=validated_name,
            url=validated_url,
            token=token,
            manifest=cast(dict[str, object] | None, manifest),
        )
    return remotes


def save_remote(remote: RemoteConfig) -> None:
    remotes = load_remotes()
    remotes[remote.name] = remote
    _write_remotes(remotes)


def _write_remotes(remotes: dict[str, RemoteConfig]) -> None:
    path = config_path()
    path.parent.mkdir(mode=CONFIG_DIR_MODE, parents=True, exist_ok=True)
    os.chmod(path.parent, CONFIG_DIR_MODE)

    payload: dict[str, Any] = {
        "remotes": {
            name: {
                "url": remote.url,
                "token": remote.token,
                "manifest": remote.manifest,
            }
            for name, remote in sorted(remotes.items())
        }
    }

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

    os.chmod(tmp_path, CONFIG_FILE_MODE)
    tmp_path.replace(path)
    os.chmod(path, CONFIG_FILE_MODE)


def get_remote(name: str) -> RemoteConfig:
    remote = load_remotes().get(name)
    if remote is None:
        raise CLIUsageError(f"Unknown remote {name!r}")
    return remote


def validate_remote_name(name: str) -> str:
    if not name or not all(char.isalnum() or char in {"-", "_"} for char in name):
        raise CLIUsageError(
            "Remote names may contain only letters, numbers, '-' and '_'"
        )
    return name


def validate_remote_url(url: str) -> str:
    if url != url.strip() or any(char.isspace() for char in url):
        raise CLIUsageError("Remote URL must not contain whitespace")

    normalized = url.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise CLIUsageError("Remote URL must be an absolute http(s) URL")
    if parsed.scheme == "http" and not _is_local_host(parsed.hostname):
        raise CLIUsageError("Remote URL must use HTTPS unless it targets localhost")
    if parsed.username or parsed.password:
        raise CLIUsageError("Remote URL must not include credentials")
    if parsed.query or parsed.fragment:
        raise CLIUsageError("Remote URL must not include query strings or fragments")
    return normalized


def _is_local_host(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"}
