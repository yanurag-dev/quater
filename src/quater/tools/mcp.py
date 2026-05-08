"""MCP Streamable HTTP JSON response path."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import cast

from quater.config import AppConfig
from quater.exceptions import BadRequestError, HTTPError, RequestJSONError
from quater.request import Request
from quater.response import JSONResponse, Response, StreamResponse, TextResponse
from quater.tools.audit import AuditHook, ToolAuditEvent, sanitize_arguments
from quater.tools.registry import ToolRegistry
from quater.typing import RequestContext

JSONRPC_VERSION = "2.0"


async def mcp_request_context(request: Request) -> RequestContext:
    try:
        payload = await request.json()
    except RequestJSONError:
        return RequestContext()

    if not isinstance(payload, Mapping):
        return RequestContext()
    if payload.get("method") != "tools/call":
        return RequestContext()

    params = payload.get("params")
    if not isinstance(params, Mapping):
        return RequestContext(source="tool")

    name = params.get("name")
    return RequestContext(
        source="tool",
        tool_name=name if isinstance(name, str) else None,
    )


def validate_mcp_origin(request: Request, config: AppConfig) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return

    allowed = config.mcp_allowed_origins
    if not allowed and config.cors is not None:
        allowed = config.cors.allowed_origins
    if not allowed or "*" in allowed or origin in allowed:
        return

    raise BadRequestError("Invalid MCP Origin")


async def handle_mcp_request(
    request: Request,
    registry: ToolRegistry,
    *,
    audit_hook: AuditHook | None = None,
    debug: bool = False,
) -> Response:
    if request.method != "POST":
        return TextResponse(
            "Method Not Allowed",
            status_code=405,
            headers={"allow": "POST"},
        )

    try:
        payload = await _json_rpc_payload(request)
    except _JSONRPCError as exc:
        return _json_rpc_error(exc.request_id, exc.code, exc.message)
    request_id = payload.get("id")
    method = payload.get("method")
    if payload.get("jsonrpc") != JSONRPC_VERSION or not isinstance(method, str):
        return _json_rpc_error(request_id, -32600, "Invalid Request")

    if method == "tools/list":
        return _json_rpc_result(request_id, {"tools": registry.list_tools()})
    if method == "tools/call":
        return await _handle_tools_call(
            request,
            request_id,
            payload.get("params"),
            registry,
            audit_hook=audit_hook,
            debug=debug,
        )
    return _json_rpc_error(request_id, -32601, "Method not found")


async def _json_rpc_payload(request: Request) -> Mapping[str, object]:
    try:
        payload = await request.json()
    except RequestJSONError:
        raise _JSONRPCError(None, -32700, "Parse error") from None
    if not isinstance(payload, Mapping):
        raise _JSONRPCError(None, -32600, "Invalid Request")
    return cast(Mapping[str, object], payload)


async def _handle_tools_call(
    request: Request,
    request_id: object,
    params: object,
    registry: ToolRegistry,
    *,
    audit_hook: AuditHook | None,
    debug: bool,
) -> Response:
    if not isinstance(params, Mapping):
        return _json_rpc_error(request_id, -32602, "Invalid params")

    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, Mapping):
        return _json_rpc_error(request_id, -32602, "Invalid params")

    tool = registry.get(name)
    if tool is None:
        return _json_rpc_error(request_id, -32602, "Unknown tool")

    start = time.perf_counter()
    try:
        response = await tool.call(request, cast(Mapping[str, object], arguments))
    except BadRequestError as exc:
        await _audit(
            audit_hook,
            request,
            name,
            arguments,
            success=False,
            start=start,
        )
        return _json_rpc_error(request_id, -32602, exc.detail)
    except HTTPError as exc:
        await _audit(
            audit_hook,
            request,
            name,
            arguments,
            success=False,
            start=start,
        )
        return TextResponse(exc.detail, status_code=exc.status_code)
    except Exception as exc:
        await _audit(
            audit_hook,
            request,
            name,
            arguments,
            success=False,
            start=start,
        )
        detail = f"{type(exc).__name__}: {exc}" if debug else "Tool call failed"
        return _json_rpc_result(request_id, _tool_result(detail, is_error=True))

    success = response.status_code < 400
    await _audit(
        audit_hook,
        request,
        name,
        arguments,
        success=success,
        start=start,
    )
    return _json_rpc_result(
        request_id,
        await _tool_result_response(response, is_error=not success),
    )


async def _tool_result_response(
    response: Response,
    *,
    is_error: bool,
) -> dict[str, object]:
    if isinstance(response, StreamResponse):
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        text = b"".join(chunks).decode("utf-8", errors="replace")
    else:
        text = response.body.decode("utf-8", errors="replace")
    return _tool_result(text, is_error=is_error)


def _tool_result(text: str, *, is_error: bool) -> dict[str, object]:
    return {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }


async def _audit(
    audit_hook: AuditHook | None,
    request: Request,
    tool_name: str,
    arguments: Mapping[str, object],
    *,
    success: bool,
    start: float,
) -> None:
    if audit_hook is None:
        return

    event = ToolAuditEvent(
        tool_name=tool_name,
        subject=request.auth.subject if request.auth is not None else None,
        success=success,
        duration_ms=(time.perf_counter() - start) * 1000,
        arguments=sanitize_arguments(arguments),
    )
    try:
        await audit_hook(event)
    except Exception:
        return


def _json_rpc_result(request_id: object, result: object) -> JSONResponse:
    return JSONResponse(
        {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }
    )


def _json_rpc_error(request_id: object, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {"code": code, "message": message},
        }
    )


class _JSONRPCError(Exception):
    def __init__(self, request_id: object, code: int, message: str) -> None:
        self.request_id = request_id
        self.code = code
        self.message = message
        super().__init__(message)
