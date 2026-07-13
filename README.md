# Success Brand Hub

Success Brand Hub is a safety-first, multi-agent business platform for SuccessBrand. It combines Jesse client operations, Ju executive routing, Michelle operations, specialist departments, CRM, call-center records, durable tasks, memory, content planning, dashboards, and disabled-by-default external integrations.

## Current capabilities

- FastAPI platform with JWT authentication and Admin/Manager/Agent/Viewer roles
- SQLite persistence, idempotent migrations, task queue, workers, scheduling, monitoring, and notifications
- CRM and privacy-redacted mock call center
- Jesse, Ju, and Michelle runtimes
- Content, Sales, Automation, Research, Finance, Workspace, Mental Health, SuccessBrand, and CEO department specifications
- Local literal and semantic memory search
- Review-only SuccessBrand content-pack generation
- Google Sheets sandbox with WIF/ADC and controlled redacted writes
- Disabled/mock control plane for Calendar, Gmail, n8n, Twilio, and ElevenLabs
- Astro dashboards for executive, admin, Jesse, CRM, and call-center views

## Safety state

External providers are disabled by default. Department configuration remains inactive until approved. No credentials, raw caller data, or private service-account keys belong in this repository. Content and external actions require human approval.

## Development

```bash
python -m pip install -r requirements.txt
python -m pytest -q
npm install
npm run build
```

See [the architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and [Google Sheets sandbox guide](docs/integrations/google-sheets-sandbox.md).
