# Gmail Sandbox v1

This integration is disabled by default and creates **drafts only**. It never sends email.

## Safety contract

- `GMAIL_SANDBOX_ENABLED=false` and `GMAIL_MODE=mock` are the defaults.
- Only a dedicated address containing `test` or `sandbox` may be configured as mailbox and recipient.
- Draft bodies are synthetic and contain no client, caller, appointment, clinical, or production data.
- Manager access is required to create a draft; Viewer and Agent access is status-only.
- WIF/ADC uses the minimum `gmail.compose` scope. Tokens and mailbox addresses are not returned by the status endpoint.

## Important authentication limitation

Workload Identity Federation authenticates the staging service account, but it does not automatically give that identity access to a Gmail mailbox. The preferred setup for a dedicated test mailbox is user-consent OAuth with the minimum `gmail.compose` scope. Workspace domain-wide delegation remains an optional administrator-controlled alternative and must never target a production mailbox.

Until approved test-mailbox access exists, leave the integration disabled. The current implementation fails safely if ADC lacks mailbox permission.

## Configuration

```text
GMAIL_SANDBOX_ENABLED=false
GMAIL_MODE=mock
GMAIL_SANDBOX_MAILBOX=
GMAIL_SANDBOX_RECIPIENT=
GMAIL_AUTH_MODE=oauth
```

Store `GMAIL_OAUTH_CLIENT_ID`, `GMAIL_OAUTH_CLIENT_SECRET`, and `GMAIL_OAUTH_REFRESH_TOKEN` as protected GitHub `staging` environment secrets. Never commit them or print them. OAuth consent must be completed manually while signed into the dedicated test mailbox.

After security review, sandbox mode may be enabled only in the GitHub `staging` environment. The first controlled test must create one synthetic draft, confirm it remains unsent, and then delete it manually.
