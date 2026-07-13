from __future__ import annotations

import os
from collections.abc import Mapping

from twilio.request_validator import RequestValidator


class TwilioSandboxError(RuntimeError):
    pass


class TwilioSandbox:
    """Signature-verifying Twilio sandbox. It cannot initiate calls or messages."""

    def __init__(self) -> None:
        self.enabled = os.getenv("TWILIO_SANDBOX_ENABLED", "false").casefold() == "true"
        self.mode = os.getenv("TWILIO_MODE", "mock").casefold()
        self.auth_token = os.getenv("TWILIO_SANDBOX_AUTH_TOKEN", "")
        self.public_url = os.getenv("TWILIO_SANDBOX_PUBLIC_URL", "")

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode if self.enabled else "disabled",
            "signature_validation": True,
            "outbound_calls_enabled": False,
            "outbound_messages_enabled": False,
            "human_approval_required": True,
        }

    @property
    def callback_url(self) -> str:
        return self.public_url

    def validate(self) -> None:
        if self.mode not in {"disabled", "mock", "sandbox"}:
            raise TwilioSandboxError("invalid Twilio sandbox mode")
        if self.mode != "sandbox":
            return
        if not self.enabled:
            raise TwilioSandboxError("Twilio sandbox is disabled")
        if len(self.auth_token) < 16:
            raise TwilioSandboxError("Twilio sandbox authentication is unavailable")
        if not self.public_url.startswith("https://"):
            raise TwilioSandboxError("Twilio sandbox requires an HTTPS public URL")

    def verify_inbound(self, url: str, params: Mapping[str, str], signature: str) -> dict:
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "accepted": False, "network_calls": 0}
        if self.mode == "mock":
            return {"status": "mock", "accepted": True, "network_calls": 0}
        self.validate()
        if url != self.public_url:
            raise TwilioSandboxError("Twilio request URL does not match staging")
        if not signature or not RequestValidator(self.auth_token).validate(url, dict(params), signature):
            raise TwilioSandboxError("invalid Twilio webhook signature")
        return {"status": "verified", "accepted": True, "network_calls": 0, "synthetic_only": True}
