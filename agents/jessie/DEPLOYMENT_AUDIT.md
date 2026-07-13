# Jesse deployment audit

## Current repository state

- Source of truth: GitHub repository, default branch `main`.
- Application: local FastAPI intake API, storage abstraction, reporting, CLI, mock integrations, and Astro development dashboard.
- Prompts and operational configuration: Markdown and YAML under `agents/jessie/`; environment template at `.env.example`.
- Existing deployment scripts before this change: none.
- Existing staging environment: no verified external staging deployment was documented.
- Existing production deployment: no repository-controlled production deployment was documented.

## Integration references

- ElevenLabs: documentation and mock adapter only; no agent ID or credential is stored.
- Twilio: documentation and mock adapter only; no phone number, routing target, or credential is stored.
- n8n: documentation and mock adapter only; no workflow URL, ID, or credential is stored.
- Google Calendar, Gmail, and Sheets: documentation and mock adapters only; no resource IDs or credentials are stored.

## Missing deployment inputs

Dedicated staging credentials and identifiers are still required through protected GitHub Environment secrets. Production identifiers, credentials, backup procedures, approvers, and rollback ownership remain intentionally unset. No values were invented during this build.
