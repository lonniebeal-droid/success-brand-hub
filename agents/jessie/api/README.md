# Jesse local API

This directory contains a local-only FastAPI application for the Jessie intake engine.

## Development-only warning
- This API is for local development and testing only.
- No live Twilio, ElevenLabs, Google, n8n, or production integrations are connected here.
- Intake data is stored locally in a JSON file under agents/jessie/data/.
- Responses intentionally omit sensitive values such as full phone numbers and email addresses.

## Environment setup

Copy the example environment file and replace the placeholder values before starting the app:

```bash
cd /workspaces/success-brand-hub
cp .env.example .env
source .venv/bin/activate
pip install -r requirements.txt
```

Required values:
- JESSE_ENVIRONMENT: development, test, or similar local value.
- JESSE_DATA_PATH: local JSON store path.
- JESSE_LOG_LEVEL: INFO or DEBUG.
- JESSE_ADMIN_TOKEN: admin service token for unrestricted local access.
- JESSE_TWILIO_TOKEN: token for Twilio-style local integrations.
- JESSE_ELEVENLABS_TOKEN: token for ElevenLabs-style local integrations.
- JESSE_N8N_TOKEN: token for workflow automation integrations.
- JESSE_GOOGLE_TOKEN: token for Google-oriented local integrations.
- JESSE_RATE_LIMIT_PER_KEY: maximum requests per service token per minute.
- JESSE_RATE_LIMIT_PER_IP: maximum requests per client IP per minute.

## Service-token usage

Protected routes require the X-API-Key header and a matching service token:

```bash
curl -H "X-API-Key: replace-with-admin-token" http://localhost:8000/health
```

The health route remains public. Other routes enforce service-specific permissions and request rate limits.

## Feature flags

These flags default to false and are controlled via environment variables:
- JESSE_TWILIO_ENABLED
- JESSE_ELEVENLABS_ENABLED
- JESSE_GOOGLE_CALENDAR_ENABLED
- JESSE_GMAIL_ENABLED
- JESSE_GOOGLE_SHEETS_ENABLED
- JESSE_N8N_ENABLED

## Hardening notes
- Service tokens are checked for local development requests and mapped to service identities.
- Route-level permissions are enforced per service, with admin access allowed for all routes.
- Requests are rate-limited per service token and client IP.
- Every request receives an X-Request-ID header and audit logs are emitted in a structured, redacted form.
- This remains a local-only development boundary and is not a production security substitute.

## Run locally

```bash
uvicorn agents.jessie.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Routes
- POST /intakes
- GET /intakes/{intake_id}
- GET /callbacks/pending
- PATCH /intakes/{intake_id}/status
- GET /intakes/{intake_id}/summary
- GET /health
