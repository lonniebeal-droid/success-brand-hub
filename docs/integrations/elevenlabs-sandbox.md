# ElevenLabs sandbox

ElevenLabs is disabled by default. The provider-compatible `/sandbox/elevenlabs/webhook` endpoint verifies `ElevenLabs-Signature` on `post_call_transcription` events and does not retain transcript payloads. The protected `/sandbox/elevenlabs/verify-webhook` route supports administrative validation. The readiness workflow performs one read-only agent lookup; it cannot start conversations or generate audio.

Use a restricted, quota-limited staging API key, a cloned staging agent ID, and a separate webhook secret. Store keys and secrets in the GitHub `staging` environment. Keep `ELEVENLABS_SANDBOX_ENABLED=false` until the cloned agent and webhook are reviewed.

Disable the feature, disable the workspace webhook, and rotate the staging key and webhook secret to roll back.
