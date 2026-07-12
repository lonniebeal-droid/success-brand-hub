# Security model

This is a development sandbox, not a production security boundary.

- `/health` is public; protected routes require a named service token.
- Authorization is allow-listed for admin, Twilio, ElevenLabs, n8n, Google, and dashboard identities.
- Request IDs are validated and returned in responses.
- Logs omit tokens, request bodies, phone numbers, emails, and raw intake records.
- In-memory rate limits apply per service, IP, and route.
- Local JSON writes are atomic where supported and may create ignored backups.
- `.env`, caller data, logs, backups, caches, and build output are ignored.

Production still requires managed secrets, TLS, distributed throttling, token rotation, tenant isolation, immutable audit storage, retention/deletion policies, monitoring, backups, and an independent security review.
