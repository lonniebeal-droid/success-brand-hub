from __future__ import annotations

from typing import Any, Dict

from agents.jessie.src.intake_service import IntakeService


class TwilioAdapter:
    def __init__(self, enabled: bool = False, mode: str = "mock") -> None:
        self.enabled = enabled
        self.mode = mode

    def receive_inbound_call(self, payload: Dict[str, Any], intake_service: IntakeService | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "mode": self.mode, "sandbox": True}
        if intake_service is None:
            return {"status": "ok", "mode": self.mode, "sandbox": True, "message": "mock inbound call received"}
        intake_service.create_intake(
            caller_name="Twilio Mock",
            phone_number=payload.get("phone", "0000000000"),
            email="mock@twilio.local",
            reason_for_call="Mock inbound call",
            urgency="normal",
            preferred_callback_time=None,
            consent_to_store=True,
        )
        return {"status": "ok", "mode": self.mode, "sandbox": True, "message": "mock inbound call received"}
