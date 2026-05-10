"""Public package surface for Quater."""

from quater.app import Quater
from quater.exceptions import HTTPError
from quater.request import Request
from quater.response import (
    BytesResponse,
    EmptyResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamResponse,
    TextResponse,
)
from quater.typing import AuthContext, AuthRequest

__version__ = "0.1.0"

__all__ = [
    "AuthContext",
    "AuthRequest",
    "BytesResponse",
    "EmptyResponse",
    "HTTPError",
    "HTMLResponse",
    "JSONResponse",
    "Quater",
    "RedirectResponse",
    "Request",
    "Response",
    "StreamResponse",
    "TextResponse",
    "__version__",
]
