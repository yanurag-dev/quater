# Safety Rules

Use these rules when operating a Quater application for a human or another agent.

## Never Leak Secrets

Do not reveal:

- bearer tokens
- approval tokens
- cookies
- `Authorization` headers
- remote config contents
- environment variables that contain credentials

Redact secrets in explanations and logs.

## Discover Before Acting

Use action/tool discovery every time the available surface is unknown. Do not
infer a tool name from an HTTP path or a handler name unless discovery confirms
it.

## Mutations Need Extra Care

For operations that create, update, delete, send, charge, refund, deploy, or
change user-visible state:

1. Describe what will happen.
2. Use CLI dry-run when available.
3. Check whether approval is required.
4. Ask the user before executing if the operation is destructive or
   irreversible.

## Retry Policy

Safe to retry:

- discovery requests
- read-only tools/actions
- idempotent updates when the application says they are idempotent

Do not blindly retry:

- payments
- refunds
- email/SMS sends
- deletes
- status transitions
- inventory reservations
- deployment or migration actions

## Large Responses

If a Quater tool/action response is too large, narrow the request. Ask for
filters, ids, or pagination instead of raising response limits automatically.

## File Uploads

Use HTTP for upload routes. Do not try to smuggle file contents through MCP or
CLI arguments unless the backend explicitly provides a separate safe file
reference API.
