# Business Operations Layer

The CRM persists clients, prospects, leads, contacts, notes, tasks, follow-ups, document references, tags, activity, and status history. Jesse intake records may be copied into CRM leads through an authenticated staging endpoint; Jesse itself is unchanged.

The call center persists simulated incoming, active, missed, callback, and completed calls with redacted caller identifiers, timelines, outcomes, availability, queue state, and aggregate analytics. It performs no network or telephony actions. Both routers reuse Platform v2 JWT roles.
