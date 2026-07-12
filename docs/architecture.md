# Architecture

## Core platform runtime

Success Brand Hub now includes shared discovery, messaging, memory, and REST API services under `core/`. Ju provides executive routing, delegation, events, memory, and reporting. Michelle provides task, project, workflow, notification, status, and escalation services. See `docs/core-platform-architecture.md` for component boundaries and current limitations.

High-level architecture placeholder for Success Brand Hub.

Sections to include:

- Overview
  - Goals of the architecture
  - Design principles (scalability, modularity, observability, security)

- System Components
  - Agent orchestration layer
  - Active agents include Ju, Michelle, Sales, Research, Finance, Operations, and SuccessBrand
  - Integrations (Gmail, Drive, Calendar, ElevenLabs, Gemini, Twilio)
  - Storage and knowledge base
  - Web / UI components
  - Automation and workflow engines (n8n, Make, Zapier)

- Data Flow
  - Ingest -> Process -> Store -> Publish
  - Eventing and messaging patterns

- Security and Access
  - Authentication and secrets management
  - Audit logging and role-based access

- Deployment
  - Suggested deployment topology
  - Environment separation (dev/stage/prod)

- Observability
  - Logging, metrics, and tracing recommendations

Next steps:
- Produce component diagrams, sequence flows, and a more detailed component spec.
