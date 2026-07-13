from datetime import datetime

from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database.models import Base, utcnow


class CallRecord(Base):
    __tablename__ = "callcenter_calls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    direction: Mapped[str] = mapped_column(String(20), default="incoming")
    state: Mapped[str] = mapped_column(String(30), default="incoming", index=True)
    agent: Mapped[str | None] = mapped_column(String(80), index=True)
    caller_redacted: Mapped[str] = mapped_column(String(80), default="[redacted]")
    outcome: Mapped[str | None] = mapped_column(String(80), index=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AgentAvailability(Base):
    __tablename__ = "callcenter_agent_availability"
    agent: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="offline", index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
