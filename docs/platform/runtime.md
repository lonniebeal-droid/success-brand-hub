# Agent runtime

The runtime provides a persistent priority task queue, background worker, scheduled task eligibility, retries, heartbeat state, completion results, duration tracking, and failure status. Workers execute registered local handlers; external services remain disabled. Multi-process locking and a distributed broker remain production prerequisites.
