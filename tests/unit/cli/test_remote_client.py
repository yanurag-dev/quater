from __future__ import annotations

import pytest

from quater.cli.client import (
    MAX_REMOTE_RESPONSE_BYTES,
    RemoteClientError,
    RemoteResponse,
    _read_limited_body,
    fetch_manifest,
)


class OversizedResponse:
    def read(self, size: int = -1) -> bytes:
        assert size == MAX_REMOTE_RESPONSE_BYTES + 1
        return b"x" * size


def test_fetch_manifest_rejects_http_error_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request_json(
        method: str,
        url: str,
        *,
        token: str | None,
        body: bytes | None = None,
    ) -> RemoteResponse:
        return RemoteResponse(
            status_code=401,
            body={"ok": False, "error": {"code": "unauthorized"}},
        )

    monkeypatch.setattr("quater.cli.client._request_json", fake_request_json)

    with pytest.raises(RemoteClientError, match="401"):
        fetch_manifest("https://api.example.com", token="bad-token")


def test_fetch_manifest_rejects_non_quater_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request_json(
        method: str,
        url: str,
        *,
        token: str | None,
        body: bytes | None = None,
    ) -> RemoteResponse:
        return RemoteResponse(status_code=200, body={"status": "ok"})

    monkeypatch.setattr("quater.cli.client._request_json", fake_request_json)

    with pytest.raises(RemoteClientError, match="manifest is invalid"):
        fetch_manifest("https://api.example.com", token="secret")


def test_remote_client_rejects_oversized_responses() -> None:
    with pytest.raises(RemoteClientError, match="too large"):
        _read_limited_body(OversizedResponse())
