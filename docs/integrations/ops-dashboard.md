# Jesse operations dashboard

`src/pages/jessie-dashboard.astro` is a client-rendered, read-only view of Jesse intake status, Make.com automation status, and SuccessBrand call center analytics. It signs in through the existing `/login` endpoint and reuses the platform’s JWT + role system; no new authentication mechanism was added. All requests require the `viewer` role.

## Backend endpoints

- `GET /ops/jesse-status` calls `integrations/jesse_status_adapter.py`, which checks `/health` on the configured Jesse API and, if a dashboard token is present, reads aggregate counts from `/reports/summary`. It never forwards caller data and never returns the token.
- `GET /ops/make-status` calls `integrations/make_adapter.py`, which reads Make.com scenario state, recent execution logs, and a Data Store cursor value using the Make REST API. It never returns the Make API token.
- `GET /ops/conversations/latest` returns the newest stored conversation with a redacted conversation id (`core/memory/persistent.py:latest_conversation`) and a short excerpt only.
- `GET /callcenter/analytics` and `GET /callcenter/calls` (existing router, extended) now also report `successful`, `failed`, and `transfer_errors` counts and accept an `outcome` filter.

## Environment variables

Both adapters fail safe: if any required variable is missing they return a `not_configured` status and make zero network calls.

- `JESSE_API_URL`, `JESSE_DASHBOARD_TOKEN` — required for live Jesse status.
- `MAKE_API_BASE_URL`, `MAKE_API_TOKEN`, `MAKE_STATUS_SCENARIO_ID` — required for live Make scenario and execution status.
- `MAKE_DATA_STORE_ID`, `MAKE_DATA_STORE_CURSOR_KEY` (defaults to `cursor`) — required for the Data Store cursor card.
- `PUBLIC_PLATFORM_API_URL` — the platform API base URL the dashboard calls from the browser; defaults to `http://127.0.0.1:8000` for local development.

## Privacy and safety

- Caller phone numbers are redacted to a last-four form before they are stored; the dashboard only ever displays `caller_redacted`.
- Conversation ids are redacted to a last-four form; full ids are never sent to the browser.
- Neither adapter accepts or returns credentials; tokens stay server-side and only a boolean `configured` flag reaches the client.
- When an integration is not configured or unreachable, the corresponding panel shows a clearly labelled empty or error state instead of fabricated data.
- Call center analytics are tagged with `"mode": "mock"` while the underlying data is sandbox/mock data; the dashboard renders a visible "mock data" badge whenever that mode is reported.

## Rollback

Revert `src/pages/jessie-dashboard.astro`, the three `/ops/*` routes in `core/platform_api.py`, and the two new integration adapter modules. No database migrations or credential rotation are required, since neither adapter writes data or introduces new secrets.
