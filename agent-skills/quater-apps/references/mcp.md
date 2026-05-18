# MCP Access

Use MCP when the user gives a Quater MCP URL or asks an agent to call Quater
tools. Quater's MCP endpoint is normally:

```text
https://example.com/mcp
```

Local development may use:

```text
http://127.0.0.1:8000/mcp
```

## Auth Rules

Send bearer auth on every MCP HTTP request:

```json
{
  "headers": {
    "Authorization": "Bearer <token>"
  }
}
```

Do not treat `initialize` as login. Quater does not create an MCP session from
`initialize`. If the token expires, the next request fails.

## Discovery Before Call

Use `tools/list` first. Then call only tool names returned by the server.

Tool schemas are generated from the route handler's public inputs:

- path parameters
- query parameters
- header and cookie parameters
- JSON body parameters
- form fields

Injected resources, request objects, auth state, app state, and framework
internals are not caller arguments.

## Calling Tools

Use `tools/call` with arguments that match the discovered `inputSchema`.

Do not add extra fields. Quater schemas use `additionalProperties: false` where
possible.

## Approval

For approval-protected tools, send the approval token in `_meta`:

```json
{
  "name": "update_order_status",
  "arguments": {
    "order_id": "ord_1001",
    "status": "shipped"
  },
  "_meta": {
    "approvalToken": "<approval-token>"
  }
}
```

If the server returns `approval_required`, report the action name and argument
hash. Do not guess approval tokens.

## Files

Quater does not expose `File` parameters as MCP tools in this release. Use HTTP
for file upload routes.

## Error Handling

- `401 Unauthorized`: auth failed at the MCP surface or route auth layer.
- `Invalid MCP Origin`: browser origin is not allowed.
- `Unsupported protocol version`: retry with a supported MCP protocol version or
  omit the version header.
- `Tool not found`: rediscover tools and check the route is exposed.
- `Tool response too large`: ask the user whether to narrow the query or use a
  different endpoint.
