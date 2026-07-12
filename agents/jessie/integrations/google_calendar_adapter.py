from __future__ import annotations

from typing import Any, Dict


class GoogleCalendarAdapter:
    def __init__(self, enabled: bool = False, mode: str = "mock") -> None:
        self.enabled = enabled
        self.mode = mode

    def get_mock_slots(self) -> Dict[str, Any]:
        return {"status": "ok", "mode": self.mode, "sandbox": True, "slots": [{"id": "slot-1", "time": "10:00"}, {"id": "slot-2", "time": "14:00"}]}

    def create_mock_booking(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "mode": self.mode, "sandbox": True}
        return {"status": "ok", "mode": self.mode, "sandbox": True, "booking": {"slot": payload.get("slot", "slot-1"), "confirmed": True}}
