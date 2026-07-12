# Success Brand Core Platform v1

The platform separates agent-specific runtimes from shared infrastructure.

## Shared core

- `core/registry.py` discovers agent directories without executing them.
- `core/messaging.py` provides priority queues, direct messages, and broadcast.
- `core/memory/` provides namespace-aware local memory, persistence, text search, and a vector-store placeholder.
- `core/api.py` exposes health, registry, status, delegation, task, messaging, and memory-search routes.

## Executive runtimes

- Ju routes and delegates work, records delegation memory, publishes events, and produces executive reports.
- Michelle tracks tasks and projects, plans workflows, aggregates status, sends notifications, and escalates urgent work to Ju.
- Jesse remains the completed intake and sandbox platform and is not rebuilt by this release.

## Current boundaries

All new state is local or in-memory by default. The executive dashboard is read-only. Authentication, durable databases, distributed queues, live notifications, and production deployment of the core API are future phases.
