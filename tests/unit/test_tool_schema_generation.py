from __future__ import annotations

import msgspec

from quater import App
from quater.tools.registry import build_tool_registry


def require_object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


class CancelReason(msgspec.Struct):
    reason: str
    notify: bool = False


def test_tool_schema_includes_path_query_and_body_parameters() -> None:
    app = App()

    @app.post("/orders/{id:int}/cancel", tool=True)
    async def cancel_order(
        id: int,
        dry_run: bool = False,
        payload: CancelReason | None = None,
    ) -> dict[str, object]:
        return {"id": id, "dry_run": dry_run, "payload": payload}

    registry = build_tool_registry(app.routes)
    schema = registry.tools["cancel_order"].input_schema
    properties = require_object(schema["properties"])
    payload_schema = require_object(properties["payload"])

    assert schema["required"] == ["id"]
    assert properties["id"] == {"type": "integer"}
    assert properties["dry_run"] == {"type": "boolean"}
    assert payload_schema == {
        "type": "object",
        "properties": {
            "reason": {"type": "string"},
            "notify": {"type": "boolean"},
        },
        "additionalProperties": False,
        "required": ["reason"],
    }


def test_tool_list_payload_uses_generated_input_schema() -> None:
    app = App()

    @app.get("/users/{id:int}", tool=True)
    async def get_user(id: int, include_email: bool = False) -> dict[str, object]:
        return {"id": id, "include_email": include_email}

    registry = build_tool_registry(app.routes)

    assert registry.list_tools() == [
        {
            "name": "get_user",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "include_email": {"type": "boolean"},
                },
                "additionalProperties": False,
                "required": ["id"],
            },
        }
    ]
