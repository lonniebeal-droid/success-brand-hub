from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from core.database.database import Database
from core.database.models import Appointment


class CalendarAdapter:
    """Local calendar abstraction; no Google calls are implemented."""

    provider = "local-sqlite"


class SchedulingService:
    def __init__(self, database: Database, calendar: CalendarAdapter | None = None) -> None:
        self.database, self.calendar = database, calendar or CalendarAdapter()

    def conflicts(self, start_at: datetime, end_at: datetime, exclude_id: str | None = None) -> bool:
        with self.database.session() as session:
            query = select(Appointment).where(Appointment.status != "cancelled", Appointment.start_at < end_at, Appointment.end_at > start_at)
            if exclude_id:
                query = query.where(Appointment.id != exclude_id)
            return session.scalar(query.limit(1)) is not None

    def availability(self, start_at: datetime, end_at: datetime) -> dict:
        return {"available": not self.conflicts(start_at, end_at), "provider": self.calendar.provider}

    def schedule(self, title: str, start_at: datetime, end_at: datetime, attendee: str | None = None) -> Appointment:
        if end_at <= start_at or self.conflicts(start_at, end_at):
            raise ValueError("appointment conflicts with existing availability")
        record = Appointment(id=str(uuid.uuid4()), title=title, start_at=start_at, end_at=end_at, attendee=attendee)
        with self.database.session() as session:
            session.add(record)
            session.commit()
        return record

    def reschedule(self, appointment_id: str, start_at: datetime, end_at: datetime) -> Appointment:
        if end_at <= start_at or self.conflicts(start_at, end_at, appointment_id):
            raise ValueError("appointment conflicts with existing availability")
        with self.database.session() as session:
            record = session.get(Appointment, appointment_id)
            if not record:
                raise KeyError("appointment not found")
            record.start_at, record.end_at = start_at, end_at
            session.commit()
            return record
