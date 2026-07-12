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
- JESSE_API_KEY: shared development API key for local requests.
- JESSE_ENVIRONMENT: development, test, or similar local value.
- JESSE_DATA_PATH: local JSON store path.
- JESSE_LOG_LEVEL: INFO or DEBUG.

## API-key usage

Protected routes require the X-API-Key header:

```bash
curl -H "X-API-Key: replace-with-dev-key" http://localhost:8000/health
```

The health route remains public.

## Feature flags

These flags default to false and are controlled via environment variables:
- JESSE_TWILIO_ENABLED
- JESSE_ELEVENLABS_ENABLED
- JESSE_GOOGLE_CALENDAR_ENABLED
- JESSE_GMAIL_ENABLED
- JESSE_GOOGLE_SHEETS_ENABLED
- JESSE_N8N_ENABLED

## Security limitations
- API keys are checked only for local development requests.
- Logs are structured and redacted, but this is not a production security boundary.
- No authentication, rate limiting, HTTPS, or secret rotation layer is configured here.

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
