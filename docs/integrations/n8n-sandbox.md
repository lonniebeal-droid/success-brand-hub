# n8n sandbox

The n8n adapter is a disabled-by-default, outbound-only staging webhook integration. It accepts only synthetic record identifiers and never includes client names, phone numbers, email addresses, notes, credentials, or arbitrary payload fields.

## Modes

- `disabled`: no network calls.
- `mock`: validates the controlled operation locally and makes no network calls.
- `sandbox`: posts a signed, minimal JSON payload to one HTTPS allowlisted host.

## Configuration

```text
N8N_SANDBOX_ENABLED=false
N8N_MODE=mock
N8N_SANDBOX_WEBHOOK_URL=
N8N_SANDBOX_ALLOWED_HOST=
N8N_SANDBOX_SIGNING_SECRET=
```

Keep the signing secret in the GitHub `staging` environment. The URL and allowlisted hostname may be environment variables. Do not reuse a production webhook or signing secret.

## Data contract

The adapter sends only `schema_version`, an allowlisted `operation`, a synthetic `record_id`, a request ID, and `synthetic: true`. The canonical JSON body is signed with HMAC-SHA256 in `X-SuccessBrand-Signature`.

## First controlled test

Create a staging-only n8n webhook that verifies the signature and records only the synthetic request ID. Keep `N8N_SANDBOX_ENABLED=false` until the webhook, host allowlist, secret storage, and human approval are verified. Start in mock mode; enable sandbox mode for exactly one synthetic operation, review the n8n execution, then disable the feature again.

## Rollback

Set `N8N_SANDBOX_ENABLED=false`, deactivate the n8n test workflow, and rotate the sandbox signing secret. No production workflow should depend on this adapter.
