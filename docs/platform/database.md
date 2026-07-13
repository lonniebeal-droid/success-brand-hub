# Platform database

Platform v2 uses SQLite through SQLAlchemy for staging persistence. Automatic, idempotent startup migration creates agents, tasks, messages, memories, appointments, call logs, reports, users, refresh tokens, notifications, and schema migration records. The SQLite file is ignored by Git and must be backed up before staging upgrades.
