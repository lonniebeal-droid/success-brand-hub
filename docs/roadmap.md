# Success Brand Hub Roadmap

## Completed

- Repository architecture and department specifications
- Jesse, Ju, and Michelle local runtimes
- JWT/RBAC, persistence, migrations, queue, scheduling, monitoring, CRM, and mock call center
- Six Astro pages and staging container workflow
- Google Workload Identity Federation and one controlled redacted Sheet write
- WIF/ADC Google Sheets application adapter
- Deterministic semantic memory retrieval
- Review-only SuccessBrand content packs
- Agent delegation and disabled/mock provider control plane

## Account-dependent staging gates

These are code-ready control-plane capabilities, not active providers:

- Google Calendar test calendar and scoped OAuth/ADC transport
- Gmail test mailbox and draft-only OAuth transport
- n8n staging instance, signed webhook, and dead-letter workflow
- Twilio test number and approved call policy
- ElevenLabs cloned test agent and approved voice policy

Each provider requires account ownership, managed configuration, a dedicated review, and one controlled fake-data test. No production activation is implied.

## Operational readiness gates

- Human-approved SuccessBrand knowledge facts and clinical language
- Field-level CRM privacy policy and encrypted document storage
- Backup restore drill and incident-response exercise
- Monitoring alerts, audit retention, and rate-limit review
- Accessibility and mobile QA
- Production privacy, security, and mental-health safety approval

## Release rule

No feature moves from `disabled` to `sandbox`, or from `sandbox` to `production`, without a reviewed pull request, passing tests, an approved account configuration, a rollback path, and human authorization.
