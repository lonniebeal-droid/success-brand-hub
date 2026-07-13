import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from core.database.database import Database
from core.database.models import Base
from .models import AgentAvailability, CallRecord


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

    def list_calls(self, state: str | None = None) -> list[CallRecord]:
        with self.database.session() as session:
            query = select(CallRecord)
            if state: query = query.where(CallRecord.state == state)
            return list(session.scalars(query.order_by(CallRecord.created_at.desc())).all())

    def set_availability(self, agent: str, status: str) -> AgentAvailability:
        with self.database.session() as session:
            record = session.get(AgentAvailability, agent) or AgentAvailability(agent=agent)
            record.status = status; session.add(record); session.commit(); return record

    def analytics(self) -> dict:
        with self.database.session() as session:
            total = session.scalar(select(func.count()).select_from(CallRecord)) or 0
            missed = session.scalar(select(func.count()).select_from(CallRecord).where(CallRecord.state == "missed")) or 0
            active = session.scalar(select(func.count()).select_from(CallRecord).where(CallRecord.state == "active")) or 0
            callbacks = session.scalar(select(func.count()).select_from(CallRecord).where(CallRecord.state == "callback")) or 0
        return {"mode": "mock", "total": total, "missed": missed, "active": active, "callback_queue": callbacks}
