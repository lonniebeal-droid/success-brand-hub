from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable


SCHEMA_VERSION = "google_sheets_sandbox_v1"
ALLOWED_MODES = {"disabled", "mock", "sandbox"}
ALLOWED_AUTH_MODES = {"adc", "json", "mock", "disabled"}
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SPREADSHEET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,100}$")
REDACTED_PHONE_PATTERN = re.compile(r"^\*\*\*\d{4}$|^\[redacted\]$")
REDACTED_EMAIL_PATTERN = re.compile(r"^[^@]{0,1}\*\*\*@\*\*\*$|^\[redacted\]$")


class GoogleSheetsSandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxRow:
    schema_version: str
    record_id: str
    created_timestamp: str
    redacted_phone: str
    redacted_email: str
    reason_category: str
    urgency: str
    status: str
    source: str
    request_id: str

    def validate(self) -> "SandboxRow":
        if self.schema_version != SCHEMA_VERSION:
            raise GoogleSheetsSandboxError("unsupported row schema")
        if not REDACTED_PHONE_PATTERN.fullmatch(self.redacted_phone):
            raise GoogleSheetsSandboxError("phone must be redacted")
        if not REDACTED_EMAIL_PATTERN.fullmatch(self.redacted_email):
            raise GoogleSheetsSandboxError("email must be redacted")
        values = asdict(self)
        if self.reason_category not in {"appointment", "billing", "service", "callback", "support", "general", "intake"}:
            raise GoogleSheetsSandboxError("unsupported reason category")
        if self.source not in {"crm", "jessie"}:
            raise GoogleSheetsSandboxError("unsupported source")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", self.request_id):
            raise GoogleSheetsSandboxError("invalid request ID")
        if any(".." in str(value) or str(value).startswith(("/", "~", "file:")) for value in values.values()):
            raise GoogleSheetsSandboxError("local paths are not allowed")
        if any(re.search(r"(sk-[A-Za-z0-9_-]{20,}|-----BEGIN .*PRIVATE KEY-----)", str(value)) for value in values.values()):
            raise GoogleSheetsSandboxError("secrets are not allowed")
        if any(key not in SandboxRow.__dataclass_fields__ for key in values):
            raise GoogleSheetsSandboxError("unsupported field")
        return self

    def values(self) -> list[str]:
        self.validate()
        return list(asdict(self).values())


def redact_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return f"***{digits[-4:]}" if len(digits) >= 4 else "[redacted]"


def redact_email(value: str | None) -> str:
    if not value or "@" not in value:
        return "[redacted]"
    return f"{value.strip()[:1]}***@***"


class GoogleSheetsAdapter:
    """Disabled-by-default Google Sheets adapter for a dedicated test sheet."""

    def __init__(self, enabled: bool | None = None, mode: str | None = None, spreadsheet_id: str | None = None, worksheet_name: str | None = None, credentials_json: str | None = None, transport: Callable[..., dict] | None = None, max_retries: int = 2, auth_mode: str | None = None, project_id: str | None = None) -> None:
        self.enabled = enabled if enabled is not None else os.getenv("GOOGLE_SHEETS_SANDBOX_ENABLED", "false").lower() == "true"
        self.mode = mode or os.getenv("GOOGLE_SHEETS_MODE", "mock")
        self.spreadsheet_id = spreadsheet_id if spreadsheet_id is not None else os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
        self.worksheet_name = worksheet_name if worksheet_name is not None else os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "")
        self.credentials_json = credentials_json if credentials_json is not None else os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        inferred_auth = "json" if credentials_json else "adc"
        self.auth_mode = auth_mode or os.getenv("GOOGLE_AUTH_MODE") or inferred_auth
        self.project_id = project_id if project_id is not None else os.getenv("GCP_PROJECT_ID", "")
        self.transport = transport
        self.max_retries = max(0, min(max_retries, 2))
        self.network_calls = 0

    def status(self) -> dict[str, Any]:
        available = False
        if self.enabled and self.mode == "sandbox":
            try:
                self.validate_startup()
                available = True
            except GoogleSheetsSandboxError:
                available = False
        return {"enabled": self.enabled, "mode": self.mode, "auth_mode": self.auth_mode, "credentials_available": available}

    def validate_startup(self) -> None:
        if self.mode not in ALLOWED_MODES:
            raise GoogleSheetsSandboxError("invalid Google Sheets mode")
        if self.auth_mode not in ALLOWED_AUTH_MODES:
            raise GoogleSheetsSandboxError("invalid Google authentication mode")
        if not self.enabled or self.mode in {"disabled", "mock"}:
            return
        if not SPREADSHEET_ID_PATTERN.fullmatch(self.spreadsheet_id):
            raise GoogleSheetsSandboxError("invalid sandbox spreadsheet ID")
        if not self.worksheet_name.strip():
            raise GoogleSheetsSandboxError("sandbox worksheet name is required")
        if self.auth_mode in {"mock", "disabled"}:
            raise GoogleSheetsSandboxError("sandbox mode requires ADC or JSON authentication")
        self._load_credentials()

    def _load_credentials(self):
        try:
            if self.auth_mode == "adc":
                import google.auth
                credentials, detected_project = google.auth.default(scopes=[SHEETS_SCOPE])
                if not credentials:
                    raise GoogleSheetsSandboxError("Application Default Credentials are unavailable")
                return credentials, self.project_id or detected_project
            if self.auth_mode == "json":
                from google.oauth2 import service_account
                try:
                    info = json.loads(self.credentials_json)
                except (TypeError, json.JSONDecodeError) as exc:
                    raise GoogleSheetsSandboxError("Google JSON fallback credentials are missing or invalid") from exc
                if not {"client_email", "private_key", "token_uri"} <= set(info):
                    raise GoogleSheetsSandboxError("Google JSON fallback credentials are incomplete")
                return service_account.Credentials.from_service_account_info(info, scopes=[SHEETS_SCOPE]), self.project_id or info.get("project_id")
        except GoogleSheetsSandboxError:
            raise
        except Exception as exc:
            raise GoogleSheetsSandboxError("Google credentials are unavailable") from exc
        raise GoogleSheetsSandboxError("Google authentication is disabled")

    def append_row(self, row: SandboxRow) -> dict[str, Any]:
        row.validate()
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "mode": self.mode, "sandbox": True}
        if self.mode == "mock":
            return {"status": "mock", "mode": "mock", "sandbox": True, "row_reference": f"mock:{row.record_id}"}
        self.validate_startup()
        credentials, _ = self._load_credentials()
        transport = self.transport or self._google_transport
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                self.network_calls += 1
                result = transport(spreadsheet_id=self.spreadsheet_id, worksheet_name=self.worksheet_name, values=row.values(), credentials=credentials)
                return {"status": "written", "mode": "sandbox", "sandbox": True, "row_reference": str(result.get("updatedRange", "sandbox-row"))}
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(0)
        raise GoogleSheetsSandboxError("sandbox sheet write failed safely") from last_error

    @staticmethod
    def _google_transport(*, spreadsheet_id: str, worksheet_name: str, values: list[str], credentials) -> dict:
        import httpx
        from google.auth.transport.requests import Request
        credentials.refresh(Request())
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{worksheet_name}!A:J:append"
        response = httpx.post(url, params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, headers={"Authorization": f"Bearer {credentials.token}"}, json={"values": [values]}, timeout=5.0)
        response.raise_for_status()
        return response.json().get("updates", {})

    def test_connection(self) -> dict[str, Any]:
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "mode": self.mode}
        if self.mode == "mock":
            return {"status": "mock", "mode": "mock"}
        self.validate_startup()
        return {"status": "configured", "mode": "sandbox"}

    def append_redacted_intake(self, intake_id: str, intake_service=None) -> dict[str, Any]:
        if intake_service is None:
            return {"status": "disabled" if not self.enabled else self.mode, "mode": self.mode, "sandbox": True}
        record = intake_service.retrieve_intake(intake_id)
        if not record:
            raise GoogleSheetsSandboxError("intake not found")
        row = SandboxRow(SCHEMA_VERSION, intake_id, record.get("created_at") or datetime.now(timezone.utc).isoformat(), redact_phone(record.get("phone_number")), redact_email(record.get("email")), "intake", record.get("urgency", "normal"), record.get("status", "new"), "jessie", "legacy-adapter")
        return self.append_row(row)
