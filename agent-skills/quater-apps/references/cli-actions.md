# CLI Actions

Use Quater CLI actions when the `quater` command is available or the user has a
configured remote.

Full docs: https://quater.devilsautumn.com/en/latest/actions

## Local Actions

Local actions import the app in process and do not require a running server:

```bash
export QUATER_APP=main:app
export QUATER_TOKEN=<token>
quater actions list
```

Use `--app main:app` and `--token <token>` when environment variables are not
set. Do not print token values.

## Remote Actions

Remote actions call a hosted Quater app:

```bash
quater connect store https://api.example.com --token <token>
quater actions list store
```

Remote discovery uses:

```text
GET /.well-known/quater-actions.json
```

Remote execution uses:

```text
POST /__quater__/actions/call
```

Use HTTPS for deployed remotes. Localhost may use HTTP.

## Progressive Discovery

Use this order:

```bash
quater actions list
quater actions search order
quater actions describe update_order_status
```

`list` and `search` are intentionally compact. Use `describe` before building a
call.

## Calling Actions

Action arguments are rendered as CLI flags:

```bash
quater call get_order --order-id ord_1001
```

Objects and arrays are JSON strings:

```bash
quater call create_order \
  --order '{"customer_id":"cust_123","sku":"sku-coffee","quantity":2}'
```

Use `--json` when another agent or script needs machine-readable output.

## Dry-Run And Approval

Use dry-run before mutations:

```bash
quater call update_order_status \
  --dry-run \
  --order-id ord_1001 \
  --status shipped
```

Dry-run returns the action path, whether approval is required, and the argument
hash. The hash is for one exact action call and canonical argument set.

Use approval tokens only when provided:

```bash
quater call update_order_status \
  --approval <approval-token> \
  --order-id ord_1001 \
  --status shipped
```

## Files

Routes with `File` parameters cannot be CLI actions in this release. Use HTTP
for upload routes.

## Common Failures

- `--app is required unless QUATER_APP is set`: set `QUATER_APP` or pass `--app`.
- `Unknown CLI action`: rediscover and check the route has `cli=True`.
- `401 Unauthorized`: auth failed at the CLI surface or route auth layer.
- `approval_required`: ask for the approval token for the displayed argument
  hash.
- `Invalid JSON value`: object and array arguments must be valid JSON.
