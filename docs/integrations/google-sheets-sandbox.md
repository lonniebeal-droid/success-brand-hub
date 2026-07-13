# Google Sheets sandbox v1

This integration writes only manually triggered, redacted rows to a dedicated non-production Google Sheet. It defaults to disabled and mock mode. It never enables production workflows.

## Create the test Sheet

Create a spreadsheet used only for staging. Add a worksheet such as `Sandbox Leads` with columns: `schema_version`, `record_id`, `created_timestamp`, `redacted_phone`, `redacted_email`, `reason_category`, `urgency`, `status`, `source`, and `request_id`.

## Service account and staging variables

Create a Google Cloud service account for staging, enable the Google Sheets API, and share only the test spreadsheet with the service-account email as Editor. Do not create, download, or store a JSON service-account key. GitHub Actions authenticates with Workload Identity Federation and the application uses Application Default Credentials.

Set `GOOGLE_SHEETS_SANDBOX_ENABLED=true`, `GOOGLE_SHEETS_MODE=sandbox`, `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_SHEETS_WORKSHEET_NAME`, `GOOGLE_AUTH_MODE=adc`, and `GCP_PROJECT_ID=success-brand-staging` as GitHub staging environment variables. The v1 adapter rejects any project, spreadsheet, or worksheet outside its staging allowlist. Never expose these values to Astro or browser JavaScript.

## Permissions and manual flow

Viewer may read status only. Admin and Manager may test the connection and manually write a Jesse intake or CRM lead. Agent is denied write access. The intended manual flow is Jesse intake to CRM lead to one redacted Sheet row. Duplicate source-record pairs are rejected.

## Redaction and failures

Only the final four phone digits and a masked email marker may leave the platform. Raw notes and caller content are excluded. Writes retry at most twice, errors are safe, and credentials are never logged. Successful CRM writes create an activity event containing only a row reference and request ID.

## Test, disable, and rollback

Call `POST /sandbox/google-sheets/test-connection` as an Admin or Manager. This validates configuration without writing a row. Set `GOOGLE_SHEETS_SANDBOX_ENABLED=false` to stop all writes immediately. Remove the service account's access to the sandbox spreadsheet to fully disconnect. Revert this feature branch to remove code; retain the test sheet until audit requirements are satisfied.

This remains a sandbox integration. Managed staging deployment, audit-log review, retention policy, retry monitoring, and human approval are required before broader use.
