from __future__ import annotations

from typing import Any, Dict

from agents.jessie.src.intake_service import IntakeService


class GoogleSheetsAdapter:
    def __init__(self, enabled: bool = False, mode: str = "mock") -> None:
        self.enabled = enabled
        self.mode = mode

    def append_redacted_intake(self, intake_id: str, intake_service: IntakeService | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "mode": self.mode, "sandbox": True}
        if intake_service is None:
            return {"status": "ok", "mode": self.mode, "sandbox": True, "message": "mock sheet write"}
        record = intake_service.retrieve_intake(intake_id)
        return {"status": "ok", "mode": self.mode, "sandbox": True, "intake_id": intake_id, "record_present": bool(record), "message": "mock sheet write"}
