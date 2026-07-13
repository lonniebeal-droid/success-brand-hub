# Google Sheets sandbox v1

This integration writes only manually triggered, redacted rows to a dedicated non-production Sheet. It defaults to disabled and mock mode.

## Test Sheet

Create a staging-only spreadsheet and a `Sandbox Leads` worksheet with columns: `schema_version`, `record_id`, `created_timestamp`, `redacted_phone`, `redacted_email`, `reason_category`, `urgency`, `status`, `source`, and `request_id`.

## Preferred WIF architecture

GitHub Actions obtains a short-lived OIDC token using `id-token: write`. `google-github-actions/auth@v3` exchanges it through the configured Workload Identity Provider and impersonates the staging service account. The action creates temporary Application Default Credentials for the job; no long-lived key is created or stored.

Create a GitHub-specific workload identity pool/provider restricted to `lonniebeal-droid/success-brand-hub` and, where possible, the staging environment and approved workflow. Grant that federated principal `roles/iam.workloadIdentityUser` on the staging-only service account. Share only the test Sheet with the service-account email.

Configure GitHub environment variables `GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, and `GCP_SERVICE_ACCOUNT`. Configure staging with `GOOGLE_AUTH_MODE=adc`, `GOOGLE_SHEETS_MODE=sandbox`, the test Sheet ID, and worksheet name. Keep `GOOGLE_SHEETS_SANDBOX_ENABLED=false` until final review.

ADC uses `google.auth.default()` scoped only to Google Sheets. Missing ADC fails safely without revealing the project, provider, service account, credential source, or tokens.

## Discouraged JSON fallback

`GOOGLE_AUTH_MODE=json` reads `GOOGLE_SERVICE_ACCOUNT_JSON` only from the environment. Credential file paths are unsupported. This long-lived-key mode is discouraged and is never the default.

## Permissions and manual flow

Viewer and Agent may read status only. Admin and Manager may test and manually write a Jesse intake or CRM lead. Duplicate source-record pairs are rejected.

## Redaction and failures

Only final-four phone data and masked email markers may leave the platform. Raw notes and caller content are excluded. Writes retry at most twice, errors are safe, and credentials are never logged.

## Exact staging order

1. Configure the Google pool, OIDC provider, repository condition, and service-account impersonation.
2. Add the three GitHub environment variables.
3. Share only the test Sheet with the staging service account.
4. Deploy with the feature disabled and confirm ADC is available.
5. Set the Sheet ID and worksheet name, then test the connection.
6. Enable the feature only for one approved manual write.
7. Verify redaction, audit logs, CRM activity, and counters; then disable again.

## Disable and rollback

Set `GOOGLE_SHEETS_SANDBOX_ENABLED=false` to stop writes. Remove the WIF IAM binding to disconnect GitHub. If JSON fallback was ever used, revoke its key. Revert the feature commit to remove code. This remains sandbox-only and requires human approval before broader use.
