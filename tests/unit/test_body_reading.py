from __future__ import annotations

import pytest

from quater.exceptions import PayloadTooLargeError, RequestJSONError
from quater.request import Request


@pytest.mark.asyncio
async def test_body_is_read_once_and_cached() -> None:
    calls = 0

    async def read_body() -> bytes:
        nonlocal calls
        calls += 1
        return b'{"ok": true}'

    request = Request(method="POST", path="/items", body=read_body)

    first = await request.body()
    second = await request.body()

    assert first == b'{"ok": true}'
    assert second == b'{"ok": true}'
    assert calls == 1


@pytest.mark.asyncio
async def test_json_is_decoded_once_and_cached() -> None:
    calls = 0

    async def read_body() -> bytes:
        nonlocal calls
        calls += 1
        return b'{"ok": true}'

    request = Request(method="POST", path="/items", body=read_body)

    first = await request.json()
    second = await request.json()

    assert first == {"ok": True}
    assert second is first
    assert calls == 1


@pytest.mark.asyncio
async def test_malformed_json_raises_safe_framework_error() -> None:
    request = Request(method="POST", path="/items", body=b'{"broken"')

    with pytest.raises(RequestJSONError) as exc_info:
        await request.json()

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Malformed JSON body"


@pytest.mark.asyncio
async def test_body_size_limit_is_checked_before_json_decode() -> None:
    request = Request(
        method="POST",
        path="/items",
        body=b'{"ok": true}',
        max_body_size=4,
    )

    with pytest.raises(PayloadTooLargeError) as exc_info:
        await request.json()

    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_body_size_limit_failure_is_cached_without_re_reading() -> None:
    calls = 0

    async def read_body() -> bytes:
        nonlocal calls
        calls += 1
        return b"too large" if calls == 1 else b"ok"

    request = Request(
        method="POST",
        path="/items",
        body=read_body,
        max_body_size=4,
    )

    with pytest.raises(PayloadTooLargeError):
        await request.body()
    with pytest.raises(PayloadTooLargeError):
        await request.body()

    assert calls == 1


@pytest.mark.asyncio
async def test_body_reader_failure_is_cached_without_re_reading() -> None:
    calls = 0

    async def read_body() -> bytes:
        nonlocal calls
        calls += 1
        raise RuntimeError("read failed")

    request = Request(method="POST", path="/items", body=read_body)

    with pytest.raises(RuntimeError, match="read failed"):
        await request.body()
    with pytest.raises(RuntimeError, match="read failed"):
        await request.body()

    assert calls == 1
