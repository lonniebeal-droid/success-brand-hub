from __future__ import annotations

from typing import Any, Dict

from agents.jessie.src.intake_service import IntakeService


class ElevenLabsAdapter:
    def __init__(self, enabled: bool = False, mode: str = "mock") -> None:
        self.enabled = enabled
        self.mode = mode

    def receive_transcript(self, payload: Dict[str, Any], intake_service: IntakeService | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "mode": self.mode, "sandbox": True}
        transcript = payload.get("text", "")
        return {"status": "ok", "mode": self.mode, "sandbox": True, "transcript_length": len(transcript), "message": "mock transcript accepted"}
