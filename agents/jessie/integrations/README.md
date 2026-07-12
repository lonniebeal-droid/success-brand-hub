# Jesse sandbox integrations

These adapters model future Twilio, ElevenLabs, Google Calendar, Google Sheets, Gmail, and n8n connections. They are disabled by default, run in `mock` mode, and make no network requests.

Each adapter returns an explicit `sandbox: true` marker. Enabling a feature flag only enables its local simulation; it does not configure or modify an external account.

Before any live adapter is introduced, add a reviewed credential provider, strict timeouts, bounded retries, idempotency, contract tests, redaction tests, and a separate sandbox account.
