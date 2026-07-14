import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from core.database.database import Database
from core.database.models import Base
from .models import AgentAvailability, CallRecord

# Recognized call outcomes used by the operations dashboard. These are
# documented values for the free-text CallRecord.outcome column; unrecognized
# free-text outcomes remain supported and are simply not bucketed below.
FAILED_OUTCOMES = ("failed", "no_answer", "voicemail_only", "dropped")
TRANSFER_ERROR_OUTCOME = "transfer_error"


class CallCenterService:
    def __init__(self, database: Database) -> None:
        self.database = database
        Base.metadata.create_all(database.engine)

    @staticmethod
    def redact_phone(value: str | None) -> str:
        digits = re.sub(r"\D", "", value or "")
        return f"***{digits[-4:]}" if digits else "[redacted]"

    def receive_mock_call(self, caller: str | None, agent: str | None = "jessie", metadata: dict | None = None) -> CallRecord:
        now = datetime.now(timezone.utc).isoformat()
        call = CallRecord(id=str(uuid.uuid4()), agent=agent, caller_redacted=self.redact_phone(caller), timeline=[{"event": "incoming", "at": now}], metadata_json={"mode": "mock", **(metadata or {})})
        with self.database.session() as session: session.add(call); session.commit()
        return call

    def update_call(self, call_id: str, state: str, outcome: str | None = None, duration_seconds: float | None = None) -> CallRecord:
        with self.database.session() as session:
            call = session.get(CallRecord, call_id)
            if not call: raise KeyError("call not found")
            call.state, call.outcome, call.duration_seconds = state, outcome, duration_seconds
            call.timeline = [*call.timeline, {"event": state, "at": datetime.now(timezone.utc).isoformat(), "outcome": outcome}]
            session.commit(); return call

    def list_calls(self, state: str | None = None, outcome: str | None = None) -> list[CallRecord]:
        with self.database.session() as session:
            query = select(CallRecord)
            if state: query = query.where(CallRecord.state == state)
            if outcome: query = query.where(CallRecord.outcome == outcome)
            return list(session.scalars(query.order_by(CallRecord.created_at.desc())).all())

    def set_availability(self, agent: str, status: str) -> AgentAvailability:
        with self.database.session() as session:
            record = session.get(AgentAvailability, agent) or AgentAvailability(agent=agent)
            record.status = status; session.add(record); session.commit(); return record

    def analytics(self) -> dict:
        with self.database.session() as session:
            def count(*conditions) -> int:
                query = select(func.count()).select_from(CallRecord)
                for condition in conditions:
                    query = query.where(condition)
                return session.scalar(query) or 0

            total = count()
            missed = count(CallRecord.state == "missed")
            active = count(CallRecord.state == "active")
            callbacks = count(CallRecord.state == "callback")
            transfer_errors = count(CallRecord.outcome == TRANSFER_ERROR_OUTCOME)
            failed = count(or_(CallRecord.state == "missed", CallRecord.outcome.in_(FAILED_OUTCOMES)))
            successful = count(
                CallRecord.state == "completed",
                or_(CallRecord.outcome.is_(None), CallRecord.outcome.not_in((*FAILED_OUTCOMES, TRANSFER_ERROR_OUTCOME))),
            )
            return {
                "mode": "mock",
                "total": total,
                "missed": missed,
                "active": active,
                "callback_queue": callbacks,
                "successful": successful,
                "failed": failed,
                "transfer_errors": transfer_errors,
            }
