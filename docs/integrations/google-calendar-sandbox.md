# Google Calendar sandbox

The Calendar integration uses GitHub OIDC/WIF and Application Default Credentials. It is disabled by default and targets only the separately shared `SuccessBrand Sandbox Calendar`.

## Configuration

- `GOOGLE_CALENDAR_SANDBOX_ENABLED=false`
- `GOOGLE_CALENDAR_MODE=mock`
- `JESSE_GOOGLE_STAGING_CALENDAR_ID` stored as a GitHub staging environment variable
- `GCP_PROJECT_ID=success-brand-staging`

## Safety

- Admin and Manager may manually create or delete sandbox events.
- Viewer may read safe status only.
- No attendees, phone numbers, emails, notes, or real client data are included.
- The Calendar ID and access token are never returned by the API.
- Sandbox writes require explicit feature enablement and human approval.
