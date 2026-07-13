from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database.models import Base, utcnow


class CRMParty(Base):
    __tablename__ = "crm_parties"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str | None] = mapped_column(String(160), index=True)
    phone: Mapped[str | None] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CRMNote(Base):
    __tablename__ = "crm_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("crm_parties.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CRMTask(Base):
    __tablename__ = "crm_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    party_id: Mapped[str | None] = mapped_column(ForeignKey("crm_parties.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CRMDocument(Base):
    __tablename__ = "crm_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("crm_parties.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    reference: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CRMActivity(Base):
    __tablename__ = "crm_activity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("crm_parties.id"), index=True)
    event: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CRMStatusHistory(Base):
    __tablename__ = "crm_status_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("crm_parties.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
