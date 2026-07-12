from __future__ import annotations

from typing import Any, Dict, List

from agents.jessie.src.intake_service import IntakeService


class ReportingService:
    def __init__(self, intake_service: IntakeService, metrics: Dict[str, Any], integration_health: Dict[str, Any]) -> None:
        self.intake_service = intake_service
        self.metrics = metrics
        self.integration_health = integration_health

    def daily_report(self) -> Dict[str, Any]:
        records = self.intake_service.list_pending_callbacks()
        return {
            "summary": {
                "total_intakes": len(self.intake_service._records),
                "pending_callbacks": len(records),
                "status_counts": self._status_counts(),
                "urgency_counts": self._urgency_counts(),
            },
            "integrations": {
                "mock_appointments": self.metrics.get("mock_appointments", 0),
                "mock_sheet_writes": self.metrics.get("mock_sheet_writes", 0),
                "mock_follow_up_emails": self.metrics.get("mock_follow_up_emails", 0),
                "mock_n8n_events": self.metrics.get("mock_n8n_events", 0),
            },
            "mode": "mock",
            "sandbox": True,
        }

    def summary_report(self) -> Dict[str, Any]:
        return {
            "total_intakes": len(self.intake_service._records),
            "pending_callbacks": len(self.intake_service.list_pending_callbacks()),
            "status_counts": self._status_counts(),
            "urgency_counts": self._urgency_counts(),
            "integration_health": self.integration_health,
        }

    def integrations_report(self) -> Dict[str, Any]:
        return {"integrations": self.integration_health, "mock_counts": {"appointments": self.metrics.get("mock_appointments", 0), "sheet_writes": self.metrics.get("mock_sheet_writes", 0), "follow_up_emails": self.metrics.get("mock_follow_up_emails", 0), "n8n_events": self.metrics.get("mock_n8n_events", 0)}}

    def security_report(self) -> Dict[str, Any]:
        return {
            "api_request_count": self.metrics.get("api_requests", 0),
            "http_401_count": self.metrics.get("http_401", 0),
            "http_403_count": self.metrics.get("http_403", 0),
            "http_429_count": self.metrics.get("http_429", 0),
            "redacted": True,
        }

    def system_status(self) -> Dict[str, Any]:
        return {"status": "ok", "mode": "mock", "sandbox": True, "integrations": self.integration_health, "metrics": self.security_report()}

    def _status_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for record in self.intake_service._records:
            status = record.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _urgency_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for record in self.intake_service._records:
            urgency = record.get("urgency", "unknown")
            counts[urgency] = counts.get(urgency, 0) + 1
        return counts
