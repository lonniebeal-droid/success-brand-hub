# Success Brand Hub Architecture

## Runtime

The FastAPI platform provides JWT/RBAC, SQLite persistence, migrations, a durable task queue, scheduling, notification records, agent delegation, content-pack generation, CRM, call-center records, and local semantic retrieval. Astro supplies six staging dashboards and public-facing pages.

## Agent flow

1. An Admin or Manager submits an objective.
2. The orchestration router selects one specialist using explicit routing rules.
3. A durable task is created with `human_approval_required: true`.
4. A worker processes locally approved work.
5. External actions pass through disabled-by-default provider adapters.
6. Activity, results, and failures are stored without credentials or raw caller data.

## Integrations

- Google Sheets supports disabled, mock, and WIF/ADC-backed staging modes.
- Google Calendar, Gmail, n8n, Twilio, and ElevenLabs expose protected disabled/mock control-plane endpoints.
- No provider is enabled by default. Sandbox mode fails closed until its approved transport and account configuration exist.

## Security boundaries

- Admin: identity and system administration.
- Manager: delegation and manual sandbox operations.
- Agent: approved task and content operations.
- Viewer: read-only status.
- Secrets are supplied by environment or workload identity, never repository files.
- Content and external operations require human review.

## Data and retrieval

SQLite stores platform, CRM, call-center, memory, and integration audit records. Memory search supports literal lookup and deterministic local token-cosine ranking. External embedding providers may be added later behind the same disabled-by-default pattern.

## Deployment

Development, staging, and production are separate. Cloud Run staging and GitHub OIDC/WIF are configured. Production integrations and deployment remain intentionally disabled until provider-specific approval, privacy review, rollback testing, and monitoring are complete.
