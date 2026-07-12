# Development guide

Jesse is a local, non-production FastAPI intake service with JSON or in-memory storage, service-scoped tokens, request IDs, audit logging, rate limits, aggregate reporting, a CLI, mock adapters, and an Astro development dashboard.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill only local development tokens in `.env`; never commit that file.

## Run

```bash
uvicorn agents.jessie.api.main:app --reload
python -m agents.jessie.cli run-demo
npm run build
```

Dashboard path: `/jessie-dashboard`. It intentionally renders an offline-safe empty state and does not place a dashboard token in client assets.

## Test

```bash
python -m pytest agents/jessie/tests -q
npm run build
```
