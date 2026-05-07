"""Small immutable data views used by requests and responses."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from http.cookies import SimpleCookie
from re import Pattern, compile
from typing import TypeAlias
from urllib.parse import parse_qsl

from quater.exceptions import BadRequestError

HeaderValue: TypeAlias = str | bytes
HeaderItems: TypeAlias = Iterable[tuple[HeaderValue, HeaderValue]]

_BAD_PERCENT_ESCAPE: Pattern[str] = compile(r"%(?![0-9A-Fa-f]{2})")


class Headers(Mapping[str, str]):
    """Case-insensitive HTTP header mapping."""

    __slots__ = ("_items", "_lookup")

    def __init__(self, items: HeaderItems | Mapping[str, str] = ()) -> None:
        pairs = items.items() if isinstance(items, Mapping) else items
        normalized = tuple(
            (_decode_header(name).lower(), _decode_header(value))
            for name, value in pairs
        )
        self._items = normalized
        self._lookup = dict(normalized)

    def __getitem__(self, key: str) -> str:
        return self._lookup[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return iter(self._lookup)

    def __len__(self) -> int:
        return len(self._lookup)

    @property
    def raw(self) -> tuple[tuple[str, str], ...]:
        return self._items

    def get_all(self, key: str) -> tuple[str, ...]:
        normalized = key.lower()
        return tuple(value for name, value in self._items if name == normalized)


class QueryParams(Mapping[str, str]):
    """Query string mapping with access to repeated values."""

    __slots__ = ("_items", "_lookup")

    def __init__(self, items: Iterable[tuple[str, str]]) -> None:
        normalized = tuple(items)
        self._items = normalized
        self._lookup = dict(normalized)

    @classmethod
    def from_query_string(cls, query_string: str | bytes) -> QueryParams:
        raw = _decode_query_string(query_string)
        if _BAD_PERCENT_ESCAPE.search(raw):
            raise BadRequestError("Malformed query string")

        try:
            parsed = parse_qsl(raw, keep_blank_values=True, errors="strict")
        except UnicodeDecodeError as exc:
            raise BadRequestError("Malformed query string") from exc

        return cls(parsed)

    def __getitem__(self, key: str) -> str:
        return self._lookup[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._lookup)

    def __len__(self) -> int:
        return len(self._lookup)

    @property
    def raw(self) -> tuple[tuple[str, str], ...]:
        return self._items

    def get_all(self, key: str) -> tuple[str, ...]:
        return tuple(value for name, value in self._items if name == key)


class Cookies(Mapping[str, str]):
    """Parsed request cookies."""

    __slots__ = ("_cookies",)

    def __init__(self, cookies: Mapping[str, str] | None = None) -> None:
        self._cookies = dict(cookies or {})

    @classmethod
    def from_cookie_header(cls, value: str | None) -> Cookies:
        if not value:
            return cls()

        parsed = SimpleCookie()
        parsed.load(value)
        return cls({key: morsel.value for key, morsel in parsed.items()})

    def __getitem__(self, key: str) -> str:
        return self._cookies[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._cookies)

    def __len__(self) -> int:
        return len(self._cookies)


def normalize_response_headers(
    headers: HeaderItems | Mapping[str, str] | None = None,
) -> tuple[tuple[str, str], ...]:
    if headers is None:
        return ()
    pairs = headers.items() if isinstance(headers, Mapping) else headers
    return tuple(
        (_decode_header(name).lower(), _decode_header(value)) for name, value in pairs
    )


def _decode_header(value: HeaderValue) -> str:
    if isinstance(value, bytes):
        return value.decode("latin-1")
    return value


def _decode_query_string(value: str | bytes) -> str:
    if isinstance(value, bytes):
        try:
            return value.decode("ascii")
        except UnicodeDecodeError as exc:
            raise BadRequestError("Malformed query string") from exc
    return value
