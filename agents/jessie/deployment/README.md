# Jesse deployment system

This package validates deployment intent and gates. It performs no network calls and cannot alter ElevenLabs, Twilio, n8n, or Google resources. GitHub Actions provides the controlled workflow; live adapter implementations remain future work.

Development and staging require passing tests. Production additionally requires verified staging, controlled verification, manual GitHub Environment approval, a configuration backup, and a recorded rollback target.
