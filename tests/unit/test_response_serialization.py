from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import cast

import msgspec
import pytest

from quater.exceptions import ResponseConversionError
from quater.response import (
    BytesResponse,
    EmptyResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamResponse,
    TextResponse,
    normalize_response,
    validate_response,
)


class UserOut(msgspec.Struct):
    id: int
    name: str


@dataclass(frozen=True)
class DataclassOut:
    ok: bool


def test_response_preserves_explicit_content_type_without_duplicate() -> None:
    response = JSONResponse(
        {"ok": True},
        headers={"Content-Type": "application/custom"},
    )

    assert response.body == b'{"ok":true}'
    assert response.headers == (("content-type", "application/custom"),)


def test_msgspec_struct_serializes_as_json() -> None:
    response = JSONResponse(UserOut(id=1, name="Ada"))

    assert response.body == b'{"id":1,"name":"Ada"}'
    assert response.headers == (("content-type", "application/json"),)


def test_dataclass_return_value_serializes_as_json() -> None:
    response = normalize_response(DataclassOut(ok=True))

    assert isinstance(response, JSONResponse)
    assert response.body == b'{"ok":true}'


def test_bytes_fast_path_does_not_use_json_encoding() -> None:
    response = normalize_response(b'{"already":"encoded"}')

    assert isinstance(response, BytesResponse)
    assert response.body == b'{"already":"encoded"}'
    assert response.headers == (("content-type", "application/octet-stream"),)


def test_common_return_values_normalize_to_responses() -> None:
    explicit = Response(b"ready", status_code=202)

    assert normalize_response(explicit) is explicit
    assert isinstance(normalize_response({"ok": True}), JSONResponse)
    assert isinstance(normalize_response([1, 2]), JSONResponse)
    assert isinstance(normalize_response((1, 2)), JSONResponse)
    assert isinstance(normalize_response("hello"), TextResponse)
    assert isinstance(normalize_response(None), EmptyResponse)


def test_explicit_response_rejects_invalid_body_type() -> None:
    with pytest.raises(ResponseConversionError, match="Response body"):
        Response(cast(bytes, "not bytes"))


@pytest.mark.parametrize("status_code", [cast(int, "200"), True, 99, 600])
def test_explicit_response_rejects_invalid_status_code(status_code: int) -> None:
    with pytest.raises(ResponseConversionError, match="Response status_code"):
        Response(b"ok", status_code=status_code)


def test_explicit_response_accepts_bytes_like_body_when_validated() -> None:
    response = Response(b"ok")
    response.body = cast(bytes, bytearray(b"mutated"))

    validate_response(response)

    assert response.body == b"mutated"


def test_redirect_response_sets_location_header() -> None:
    response = RedirectResponse("/login", status_code=302)

    assert response.status_code == 302
    assert response.headers == (("location", "/login"),)
    assert response.body == b""


@pytest.mark.asyncio
async def test_stream_response_does_not_consume_iterator_at_construction() -> None:
    consumed: list[bytes] = []

    async def chunks() -> AsyncIterator[bytes]:
        consumed.append(b"first")
        yield b"first"

    response = StreamResponse(chunks())

    assert response.is_streaming is True
    assert consumed == []
    assert [chunk async for chunk in response.body_iterator] == [b"first"]
    assert consumed == [b"first"]


def test_unsupported_return_value_raises_clear_error() -> None:
    class Unsupported:
        pass

    with pytest.raises(ResponseConversionError):
        normalize_response(Unsupported())


def test_set_cookie_sets_simple_key_value() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc123")
    header = response.headers[0][1]
    assert header.startswith("session=abc123")


def test_set_cookie_rejects_semicolon_in_value() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie value"):
        response.set_cookie("data", "a;b")


def test_set_cookie_rejects_space_in_value() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie value"):
        response.set_cookie("data", "a b")


def test_set_cookie_rejects_double_quote_in_value() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie value"):
        response.set_cookie("key", 'val"ue')


def test_set_cookie_rejects_backslash_in_value() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie value"):
        response.set_cookie("key", "val\\ue")


def test_set_cookie_appends_multiple_cookies() -> None:
    response = Response(b"ok")
    response.set_cookie("a", "1")
    response.set_cookie("b", "2")
    assert response.headers[0][1].startswith("a=1")
    assert response.headers[1][1].startswith("b=2")


def test_set_cookie_sets_max_age() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", max_age=3600)
    assert "Max-Age=3600" in response.headers[0][1]


def test_set_cookie_sets_expires_as_http_date() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", expires=0)
    assert "Expires=Thu, 01 Jan 1970 00:00:00 GMT" in response.headers[0][1]


def test_set_cookie_sets_httponly() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", httponly=True)
    assert "; HttpOnly" in response.headers[0][1]


def test_set_cookie_sets_secure() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", secure=True)
    assert "; Secure" in response.headers[0][1]


def test_set_cookie_sets_samesite() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", samesite="strict")
    assert "; SameSite=Strict" in response.headers[0][1]


def test_set_cookie_empty_samesite_omits_attribute() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", samesite=None)
    assert "SameSite" not in response.headers[0][1]


def test_set_cookie_default_path_is_slash() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc")
    assert "; Path=/" in response.headers[0][1]


def test_set_cookie_custom_domain() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", domain="example.com")
    assert "; Domain=example.com" in response.headers[0][1]


def test_set_cookie_samesite_none_requires_secure() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Secure"):
        response.set_cookie("session", "abc", samesite="none")


def test_set_cookie_samesite_none_with_secure_succeeds() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", samesite="none", secure=True)
    assert "; SameSite=None" in response.headers[0][1]
    assert "; Secure" in response.headers[0][1]


def test_set_cookie_rejects_invalid_cookie_name() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie name"):
        response.set_cookie("bad;key", "x")
    with pytest.raises(ValueError, match="Invalid cookie name"):
        response.set_cookie("bad=key", "x")


def test_set_cookie_rejects_empty_cookie_name() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie name"):
        response.set_cookie("", "x")


def test_set_cookie_path_none_omits_attribute() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc", path=None)
    assert "Path=" not in response.headers[0][1]


def test_set_cookie_rejects_semicolon_in_path() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie path"):
        response.set_cookie("session", "abc", path="/api; Secure")


def test_set_cookie_rejects_semicolon_in_domain() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie domain"):
        response.set_cookie("session", "abc", domain="example.com; HttpOnly")


def test_delete_cookie_clears_with_max_age_zero() -> None:
    response = Response(b"ok")
    response.set_cookie("session", "abc")
    response.delete_cookie("session")
    set_cookie = response.headers[1][1]
    assert "session=" in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "Expires=Thu, 01 Jan 1970 00:00:00 GMT" in set_cookie


def test_delete_cookie_supports_custom_path_and_domain() -> None:
    response = Response(b"ok")
    response.delete_cookie("session", path="/app", domain="example.com")
    set_cookie = response.headers[0][1]
    assert "Path=/app" in set_cookie
    assert "Domain=example.com" in set_cookie


def test_set_cookie_rejects_colon_in_name() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid cookie name"):
        response.set_cookie("foo:bar", "x")


def test_set_cookie_normalizes_samesite_case() -> None:
    response = Response(b"ok")
    response.set_cookie("s", "v", samesite="LAX")  # type: ignore[arg-type]
    assert "; SameSite=Lax" in response.headers[0][1]


def test_set_cookie_rejects_invalid_samesite() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Invalid SameSite"):
        response.set_cookie("s", "v", samesite="garbage")  # type: ignore[arg-type]


def test_set_cookie_samesite_none_uppercase_requires_secure() -> None:
    response = Response(b"ok")
    with pytest.raises(ValueError, match="Secure"):
        response.set_cookie("s", "v", samesite="None", secure=False)  # type: ignore[arg-type]


def test_delete_cookie_accepts_secure_and_samesite() -> None:
    response = Response(b"ok")
    response.delete_cookie("__Secure-session", secure=True, samesite="none")
    set_cookie = response.headers[0][1]
    assert "; Secure" in set_cookie
    assert "; SameSite=None" in set_cookie


def test_set_cookie_round_trip_value_no_quotes() -> None:
    """Value written to Set-Cookie must match what the parser reads back."""
    from quater.datastructures import Cookies

    response = Response(b"ok")
    response.set_cookie("token", "abc123")
    set_cookie_header = response.headers[0][1]
    # Extract value portion: everything between first "=" and first ";"
    raw_value = set_cookie_header.split("=", 1)[1].split(";")[0]
    cookies = Cookies.from_cookie_header(f"token={raw_value}")
    assert cookies["token"] == "abc123"


def test_set_cookie_round_trip_value_with_special_chars() -> None:
    """Values with supported special characters round-trip correctly."""
    from quater.datastructures import Cookies

    response = Response(b"ok")
    response.set_cookie("data", "abc=123/xyz")
    set_cookie_header = response.headers[0][1]
    raw_value = set_cookie_header.split("=", 1)[1].split(";")[0]
    cookies = Cookies.from_cookie_header(f"data={raw_value}")
    assert cookies["data"] == "abc=123/xyz"
