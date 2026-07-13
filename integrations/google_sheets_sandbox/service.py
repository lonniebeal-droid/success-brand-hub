from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from agents.jessie.integrations.google_sheets_adapter import GoogleSheetsAdapter, GoogleSheetsSandboxError, SCHEMA_VERSION, SandboxRow, redact_email, redact_phone
from agents.jessie.src.intake_service import IntakeService
from core.database.database import Database
from core.database.models import Base
from crm.models import CRMActivity, CRMParty
from .models import GoogleSheetsSandboxWrite


class GoogleSheetsSandboxService:
    def __init__(self, database: Database, adapter: GoogleSheetsAdapter | None = None, intake_service: IntakeService | None = None) -> None:
        self.database = database
        self.adapter = adapter or GoogleSheetsAdapter()
        self.intake_service = intake_service
        Base.metadata.create_all(database.engine)

    @staticmethod
    def reason_category(value: str | None) -> str:
        text = (value or "general").lower()
        for category in ("appointment", "billing", "service", "callback", "support"):
            if category in text:
                return category
        return "general"

    def _record_write(self, source: str, record_id: str, request_id: str, status: str, row_reference: str | None = None, error_code: str | None = None) -> GoogleSheetsSandboxWrite:
        record = GoogleSheetsSandboxWrite(id=str(uuid.uuid4()), source=source, record_id=record_id, request_id=request_id, status=status, row_reference=row_reference, error_code=error_code)
        with self.database.session() as session:
            session.add(record)
            try: session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise GoogleSheetsSandboxError("record already written to sandbox") from exc
        return record

    def _already_written(self, source: str, record_id: str) -> bool:
        with self.database.session() as session:
            return session.scalar(select(GoogleSheetsSandboxWrite.id).where(GoogleSheetsSandboxWrite.source == source, GoogleSheetsSandboxWrite.record_id == record_id)) is not None

    def write_intake(self, intake_id: str, request_id: str) -> dict:
        if self._already_written("jessie", intake_id): raise GoogleSheetsSandboxError("record already written to sandbox")
        if self.intake_service is None: raise GoogleSheetsSandboxError("Jesse intake storage is unavailable")
        intake = self.intake_service.retrieve_intake(intake_id)
        if not intake: raise GoogleSheetsSandboxError("intake not found")
        row = SandboxRow(SCHEMA_VERSION, intake_id, intake.get("created_at") or datetime.now(timezone.utc).isoformat(), redact_phone(intake.get("phone_number")), redact_email(intake.get("email")), self.reason_category(intake.get("reason_for_call")), intake.get("urgency", "normal"), intake.get("status", "new"), "jessie", request_id)
        return self._write("jessie", intake_id, request_id, row)

    def write_lead(self, lead_id: str, request_id: str) -> dict:
        if self._already_written("crm", lead_id): raise GoogleSheetsSandboxError("record already written to sandbox")
        with self.database.session() as session:
            lead = session.get(CRMParty, lead_id)
            if not lead or lead.kind != "lead": raise GoogleSheetsSandboxError("CRM lead not found")
            row = SandboxRow(SCHEMA_VERSION, lead.id, lead.created_at.isoformat(), redact_phone(lead.phone), redact_email(lead.email), self.reason_category(lead.metadata_json.get("reason")), lead.metadata_json.get("urgency", "normal"), lead.status, lead.source, request_id)
        result = self._write("crm", lead_id, request_id, row)
        with self.database.session() as session:
            session.add(CRMActivity(id=str(uuid.uuid4()), party_id=lead_id, event="google_sheets_sandbox_written", detail={"row_reference": result.get("row_reference"), "request_id": request_id})); session.commit()
        return result

    def _write(self, source: str, record_id: str, request_id: str, row: SandboxRow) -> dict:
        try:
            result = self.adapter.append_row(row)
            status = result["status"]
            if status in {"disabled"}:
                return result
            self._record_write(source, record_id, request_id, status, result.get("row_reference"))
            return result
        except GoogleSheetsSandboxError as exc:
            if str(exc) == "sandbox sheet write failed safely":
                self._record_write(source, record_id, request_id, "failed", error_code="write_failed")
            raise
        except Exception as exc:
            self._record_write(source, record_id, request_id, "failed", error_code="write_failed")
            raise GoogleSheetsSandboxError("sandbox write failed safely") from exc

    def status(self) -> dict:
        with self.database.session() as session:
            successes = session.scalar(select(func.count()).select_from(GoogleSheetsSandboxWrite).where(GoogleSheetsSandboxWrite.status.in_(["mock", "written"]))) or 0
            failures = session.scalar(select(func.count()).select_from(GoogleSheetsSandboxWrite).where(GoogleSheetsSandboxWrite.status == "failed")) or 0
            last = session.scalar(select(GoogleSheetsSandboxWrite).order_by(GoogleSheetsSandboxWrite.created_at.desc()).limit(1))
        return {**self.adapter.status(), "last_success": last.created_at.isoformat() if last and last.status in {"mock", "written"} else None, "last_error_safe": last.error_code if last and last.status == "failed" else None, "success_count": successes, "failure_count": failures}
