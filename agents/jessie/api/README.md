# Jesse local API

This directory contains a local-only FastAPI application for the Jessie intake engine.

## Notes
- No live Twilio, ElevenLabs, Google, n8n, or production integrations are used here.
- Intake data is stored locally in a JSON file under agents/jessie/data/.
- Responses intentionally omit sensitive values such as full phone numbers and email addresses.

## Setup

```bash
cd /workspaces/success-brand-hub
source .venv/bin/activate
pip install fastapi uvicorn httpx
```

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
