from __future__ import annotations

from typing import Any, Dict

from agents.jessie.src.intake_service import IntakeService


class N8NAdapter:
    def __init__(self, enabled: bool = False, mode: str = "mock") -> None:
        self.enabled = enabled
        self.mode = mode

    def deliver_event(self, intake_id: str, intake_service: IntakeService | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "mode": self.mode, "sandbox": True}
        return {"status": "ok", "mode": self.mode, "sandbox": True, "intake_id": intake_id, "message": "mock n8n event delivered"}
