# Twilio sandbox

Twilio is disabled by default. The provider-compatible `/sandbox/twilio/webhook` endpoint validates `X-Twilio-Signature` and returns an empty TwiML response; it cannot initiate calls or messages. The protected `/sandbox/twilio/verify-webhook` route supports administrative validation. Authentication readiness uses a read-only account lookup and reports no account data.

Required staging secrets are `TWILIO_SANDBOX_ACCOUNT_SID` and `TWILIO_SANDBOX_AUTH_TOKEN`. Configure `TWILIO_SANDBOX_PUBLIC_URL` only for a private, reviewed staging endpoint. Keep `TWILIO_SANDBOX_ENABLED=false` until signature validation and the test number are approved.

Disable the feature and rotate the sandbox token to roll back. Never reuse production phone credentials.
