"""Response primitives."""

from __future__ import annotations

from collections.abc import AsyncIterable, Mapping
from dataclasses import is_dataclass
from typing import TypeAlias

from quater.datastructures import HeaderItems, normalize_response_headers
from quater.exceptions import ResponseConversionError

ResponseBody: TypeAlias = bytes | bytearray | memoryview


class Response:
    """HTTP response data independent of any server protocol."""

    __slots__ = ("body", "headers", "status_code")

    def __init__(
        self,
        body: bytes = b"",
        *,
        status_code: int = 200,
        headers: HeaderItems | Mapping[str, str] | None = None,
        content_type: str | None = None,
    ) -> None:
        normalized_headers = normalize_response_headers(headers)
        if content_type is not None and not _has_header(
            normalized_headers, "content-type"
        ):
            normalized_headers = (*normalized_headers, ("content-type", content_type))

        self.body = body
        self.status_code = status_code
        self.headers = normalized_headers

    @property
    def is_streaming(self) -> bool:
        return False


class JSONResponse(Response):
    """JSON response serialized with msgspec."""

    def __init__(
        self,
        content: object,
        *,
        status_code: int = 200,
        headers: HeaderItems | Mapping[str, str] | None = None,
    ) -> None:
        from quater.serialization import dumps_json

        super().__init__(
            dumps_json(content),
            status_code=status_code,
            headers=headers,
            content_type="application/json",
        )


class TextResponse(Response):
    """UTF-8 text response."""

    def __init__(
        self,
        content: str,
        *,
        status_code: int = 200,
        headers: HeaderItems | Mapping[str, str] | None = None,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        super().__init__(
            content.encode("utf-8"),
            status_code=status_code,
            headers=headers,
            content_type=content_type,
        )


class BytesResponse(Response):
    """Raw byte response."""

    def __init__(
        self,
        content: ResponseBody,
        *,
        status_code: int = 200,
        headers: HeaderItems | Mapping[str, str] | None = None,
        content_type: str = "application/octet-stream",
    ) -> None:
        super().__init__(
            bytes(content),
            status_code=status_code,
            headers=headers,
            content_type=content_type,
        )


class StreamResponse(Response):
    """Response backed by an async byte iterator."""

    __slots__ = ("body_iterator",)

    def __init__(
        self,
        body_iterator: AsyncIterable[bytes],
        *,
        status_code: int = 200,
        headers: HeaderItems | Mapping[str, str] | None = None,
        content_type: str = "application/octet-stream",
    ) -> None:
        super().__init__(
            b"",
            status_code=status_code,
            headers=headers,
            content_type=content_type,
        )
        self.body_iterator = body_iterator

    @property
    def is_streaming(self) -> bool:
        return True


class RedirectResponse(Response):
    """Redirect response with a Location header."""

    def __init__(
        self,
        location: str,
        *,
        status_code: int = 307,
        headers: HeaderItems | Mapping[str, str] | None = None,
    ) -> None:
        normalized = (*normalize_response_headers(headers), ("location", location))
        super().__init__(b"", status_code=status_code, headers=normalized)


class EmptyResponse(Response):
    """Response with no body."""

    def __init__(
        self,
        *,
        status_code: int = 204,
        headers: HeaderItems | Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(b"", status_code=status_code, headers=headers)


def normalize_response(value: object) -> Response:
    """Convert common handler return values into response objects."""

    if isinstance(value, Response):
        return value
    if value is None:
        return EmptyResponse()
    if isinstance(value, bytes | bytearray | memoryview):
        return BytesResponse(value)
    if isinstance(value, str):
        return TextResponse(value)
    if _is_json_response_value(value):
        return JSONResponse(value)

    raise ResponseConversionError(
        f"Cannot convert {type(value).__name__!r} into a response"
    )


def _is_json_response_value(value: object) -> bool:
    if isinstance(value, dict | list | tuple | bool | int | float):
        return True
    if is_dataclass(value) and not isinstance(value, type):
        return True

    import msgspec

    return isinstance(value, msgspec.Struct)


def _has_header(headers: tuple[tuple[str, str], ...], key: str) -> bool:
    return any(name == key for name, _ in headers)
