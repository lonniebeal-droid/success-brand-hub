from __future__ import annotations

import uuid
from pathlib import PurePath

from sqlalchemy import or_, select

from core.database.database import Database
from core.database.models import Base
from .models import CRMActivity, CRMDocument, CRMNote, CRMParty, CRMStatusHistory, CRMTask


class CRMService:
    KINDS = {"client", "prospect", "lead", "contact"}

    def __init__(self, database: Database) -> None:
        self.database = database
        Base.metadata.create_all(database.engine)

    def create_party(self, kind: str, name: str, email: str | None = None, phone: str | None = None, status: str = "new", source: str = "manual", tags: list[str] | None = None, metadata: dict | None = None) -> CRMParty:
        if kind not in self.KINDS or not name.strip():
            raise ValueError("valid kind and name are required")
        party = CRMParty(id=str(uuid.uuid4()), kind=kind, name=name.strip(), email=email, phone=phone, status=status, source=source, tags=tags or [], metadata_json=metadata or {})
        with self.database.session() as session:
            session.add_all([party, CRMActivity(id=str(uuid.uuid4()), party_id=party.id, event="created", detail={"source": source}), CRMStatusHistory(id=str(uuid.uuid4()), party_id=party.id, previous_status=None, new_status=status)])
            session.commit()
        return party

    def list_parties(self, kind: str, search: str | None = None, status: str | None = None, tag: str | None = None) -> list[CRMParty]:
        with self.database.session() as session:
            query = select(CRMParty).where(CRMParty.kind == kind)
            if search:
                term = f"%{search}%"
                query = query.where(or_(CRMParty.name.ilike(term), CRMParty.email.ilike(term), CRMParty.phone.ilike(term)))
            if status:
                query = query.where(CRMParty.status == status)
            records = list(session.scalars(query.order_by(CRMParty.updated_at.desc())).all())
            return [record for record in records if not tag or tag in record.tags]

    def update_party(self, party_id: str, changes: dict) -> CRMParty:
        allowed = {"name", "email", "phone", "status", "tags", "metadata_json"}
        with self.database.session() as session:
            party = session.get(CRMParty, party_id)
            if not party:
                raise KeyError("CRM record not found")
            old_status = party.status
            for key, value in changes.items():
                if key in allowed and value is not None:
                    setattr(party, key, value)
            session.add(CRMActivity(id=str(uuid.uuid4()), party_id=party.id, event="updated", detail={"fields": sorted(set(changes) & allowed)}))
            if party.status != old_status:
                session.add(CRMStatusHistory(id=str(uuid.uuid4()), party_id=party.id, previous_status=old_status, new_status=party.status))
            session.commit()
            return party

    def delete_party(self, party_id: str) -> None:
        with self.database.session() as session:
            party = session.get(CRMParty, party_id)
            if not party:
                raise KeyError("CRM record not found")
            session.delete(party)
            session.commit()

    def create_task(self, title: str, party_id: str | None = None, due_at=None, follow_up: bool = False) -> CRMTask:
        task = CRMTask(id=str(uuid.uuid4()), title=title, party_id=party_id, due_at=due_at, follow_up=follow_up)
        with self.database.session() as session:
            session.add(task); session.commit()
        return task

    def list_tasks(self, status: str | None = None) -> list[CRMTask]:
        with self.database.session() as session:
            query = select(CRMTask)
            if status: query = query.where(CRMTask.status == status)
            return list(session.scalars(query.order_by(CRMTask.created_at.desc())).all())

    def add_note(self, party_id: str, body: str) -> CRMNote:
        note = CRMNote(id=str(uuid.uuid4()), party_id=party_id, body=body)
        with self.database.session() as session:
            if not session.get(CRMParty, party_id): raise KeyError("CRM record not found")
            session.add_all([note, CRMActivity(id=str(uuid.uuid4()), party_id=party_id, event="note_added", detail={})]); session.commit()
        return note

    def add_document(self, party_id: str, name: str, reference: str) -> CRMDocument:
        if reference.startswith(("file:", "/", "~")) or ".." in PurePath(reference).parts:
            raise ValueError("document reference must not expose a local filesystem path")
        document = CRMDocument(id=str(uuid.uuid4()), party_id=party_id, name=name, reference=reference)
        with self.database.session() as session:
            if not session.get(CRMParty, party_id): raise KeyError("CRM record not found")
            session.add_all([document, CRMActivity(id=str(uuid.uuid4()), party_id=party_id, event="document_added", detail={"name": name})]); session.commit()
        return document

    def timeline(self, party_id: str) -> list[CRMActivity]:
        with self.database.session() as session:
            return list(session.scalars(select(CRMActivity).where(CRMActivity.party_id == party_id).order_by(CRMActivity.created_at.desc())).all())

    def status_history(self, party_id: str) -> list[CRMStatusHistory]:
        with self.database.session() as session:
            return list(session.scalars(select(CRMStatusHistory).where(CRMStatusHistory.party_id == party_id).order_by(CRMStatusHistory.created_at.desc())).all())

    def import_jessie_intake(self, intake: dict) -> CRMParty:
        return self.create_party("lead", intake.get("caller_name", "Unknown caller"), intake.get("email"), intake.get("phone_number"), "new", "jessie", ["jessie-intake"], {"intake_id": intake.get("id"), "urgency": intake.get("urgency"), "reason": intake.get("reason_for_call")})
