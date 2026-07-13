from __future__ import annotations

import os

from elevenlabs.client import ElevenLabs


class ElevenLabsSandboxError(RuntimeError):
    pass


class ElevenLabsSandbox:
    """Signed-webhook boundary for a staging-only ElevenLabs agent."""

    def __init__(self, client_factory=ElevenLabs) -> None:
        self.enabled = os.getenv("ELEVENLABS_SANDBOX_ENABLED", "false").casefold() == "true"
        self.mode = os.getenv("ELEVENLABS_MODE", "mock").casefold()
        self.api_key = os.getenv("ELEVENLABS_SANDBOX_API_KEY", "")
        self.agent_id = os.getenv("ELEVENLABS_SANDBOX_AGENT_ID", "")
        self.webhook_secret = os.getenv("ELEVENLABS_SANDBOX_WEBHOOK_SECRET", "")
        self.client_factory = client_factory

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode if self.enabled else "disabled",
            "agent_configured": bool(self.agent_id),
            "signature_validation": True,
            "voice_generation_enabled": False,
            "outbound_calls_enabled": False,
            "human_approval_required": True,
        }

    def validate(self) -> None:
        if self.mode not in {"disabled", "mock", "sandbox"}:
            raise ElevenLabsSandboxError("invalid ElevenLabs sandbox mode")
        if self.mode != "sandbox":
            return
        if not self.enabled:
            raise ElevenLabsSandboxError("ElevenLabs sandbox is disabled")
        if not self.api_key or not self.agent_id or len(self.webhook_secret) < 16:
            raise ElevenLabsSandboxError("ElevenLabs sandbox configuration is incomplete")

    def verify_event(self, raw_body: str, signature: str) -> dict:
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "accepted": False, "network_calls": 0}
        if self.mode == "mock":
            return {"status": "mock", "accepted": True, "network_calls": 0}
        self.validate()
        try:
            event = self.client_factory(api_key=self.api_key).webhooks.construct_event(
                rawBody=raw_body,
                sig_header=signature,
                secret=self.webhook_secret,
            )
        except Exception as exc:
            raise ElevenLabsSandboxError("invalid ElevenLabs webhook signature") from exc
        event_type = event.get("type")
        if event_type not in {"post_call_transcription"}:
            raise ElevenLabsSandboxError("unsupported ElevenLabs sandbox event")
        return {
            "status": "verified",
            "accepted": True,
            "network_calls": 0,
            "event_type": event_type,
            "payload_stored": False,
        }
