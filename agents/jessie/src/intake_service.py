import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class IntakeValidationError(ValueError):
    """Raised when an intake payload is invalid."""


class IntakeService:
    def __init__(self, data_file: Optional[str] = None):
        self.data_file = Path(data_file or "agents/jessie/data/intakes.json")
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.data_file.exists():
            try:
                payload = json.loads(self.data_file.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    self._records = payload
                else:
                    self._records = []
            except json.JSONDecodeError:
                self._records = []
        else:
            self._records = []

    def _save(self) -> None:
        self.data_file.write_text(json.dumps(self._records, indent=2), encoding="utf-8")

    def create_intake(
        self,
        caller_name: str,
        phone_number: str,
        email: str,
        reason_for_call: str,
        urgency: str = "normal",
        preferred_callback_time: Optional[str] = None,
        consent_to_store: bool = False,
    ) -> Dict[str, Any]:
        self._validate(
            caller_name=caller_name,
            phone_number=phone_number,
            email=email,
            reason_for_call=reason_for_call,
            urgency=urgency,
            consent_to_store=consent_to_store,
        )

        intake = {
            "id": str(uuid.uuid4()),
            "caller_name": caller_name.strip(),
            "phone_number": self._normalize_phone(phone_number),
            "email": email.strip().lower(),
            "reason_for_call": reason_for_call.strip(),
            "urgency": urgency.lower(),
            "preferred_callback_time": preferred_callback_time.strip() if preferred_callback_time else None,
            "consent_to_store": consent_to_store,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "new",
        }
        self._records.append(intake)
        self._save()
        return intake

    def retrieve_intake(self, intake_id: str) -> Optional[Dict[str, Any]]:
        for record in self._records:
            if record.get("id") == intake_id:
                return record
        return None

    def list_pending_callbacks(self) -> List[Dict[str, Any]]:
        return [record for record in self._records if record.get("status") == "new"]

    def update_status(self, intake_id: str, status: str) -> Dict[str, Any]:
        for record in self._records:
            if record.get("id") == intake_id:
                record["status"] = status.strip()
                self._save()
                return record
        raise LookupError(f"Intake {intake_id} not found")

    def generate_redacted_summary(self, intake_id: str) -> str:
        intake = self.retrieve_intake(intake_id)
        if not intake:
            raise LookupError(f"Intake {intake_id} not found")
        return (
            f"Intake {intake['id'][:8]} | {intake['caller_name']} | "
            f"Urgency: {intake['urgency']} | Phone: {self._redact_phone(intake['phone_number'])} | "
            f"Email: {self._redact_email(intake['email'])} | Status: {intake['status']}"
        )

    def log_intake_event(self, event: str, sensitive_value: Optional[str] = None) -> None:
        if not sensitive_value:
            redacted_sensitive = "[redacted]"
        elif "@" in sensitive_value:
            redacted_sensitive = self._redact_email(sensitive_value)
        else:
            redacted_sensitive = self._redact_phone(sensitive_value)

        phone_context = ""
        if self._records:
            latest_phone = self._records[-1].get("phone_number")
            phone_context = f" Phone={self._redact_phone(latest_phone)}"

        print(f"Event={event} Sensitive={redacted_sensitive}{phone_context}")

    def _validate(
        self,
        caller_name: str,
        phone_number: str,
        email: str,
        reason_for_call: str,
        urgency: str,
        consent_to_store: bool,
    ) -> None:
        if not caller_name or not caller_name.strip():
            raise IntakeValidationError("caller_name is required")
        if not self._is_valid_phone(phone_number):
            raise IntakeValidationError("phone_number must be in a valid format")
        if email and not self._is_valid_email(email):
            raise IntakeValidationError("email must be a valid email address")
        if not consent_to_store:
            raise IntakeValidationError("consent_to_store is required before storage")
        if urgency not in {"low", "normal", "high", "urgent"}:
            raise IntakeValidationError("urgency must be one of: low, normal, high, urgent")
        if not reason_for_call or not reason_for_call.strip():
            raise IntakeValidationError("reason_for_call is required")

    @staticmethod
    def _is_valid_phone(phone_number: str) -> bool:
        pattern = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")
        return bool(pattern.fullmatch(phone_number.strip()))

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        return bool(pattern.fullmatch(email.strip()))

    @staticmethod
    def _normalize_phone(phone_number: str) -> str:
        digits = re.sub(r"\D", "", phone_number)
        if len(digits) != 10:
            raise IntakeValidationError("phone_number must be in a valid format")
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    @staticmethod
    def _redact_phone(value: Optional[str]) -> str:
        if not value:
            return "[redacted]"
        digits = re.sub(r"\D", "", value)
        if len(digits) <= 4:
            return "***" + digits[-4:]
        return "***" + digits[-4:]

    @staticmethod
    def _redact_email(value: Optional[str]) -> str:
        if not value:
            return "[redacted]"
        local, _ = value.split("@", 1)
        return f"{local[0]}***@***"


def create_intake(service: IntakeService, **kwargs: Any) -> Dict[str, Any]:
    return service.create_intake(**kwargs)


def retrieve_intake(service: IntakeService, intake_id: str) -> Optional[Dict[str, Any]]:
    return service.retrieve_intake(intake_id)


def list_pending_callbacks(service: IntakeService) -> List[Dict[str, Any]]:
    return service.list_pending_callbacks()


def update_status(service: IntakeService, intake_id: str, status: str) -> Dict[str, Any]:
    return service.update_status(intake_id, status)


def generate_redacted_summary(service: IntakeService, intake_id: str) -> str:
    return service.generate_redacted_summary(intake_id)
