from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from core.auth import require_role
from core.database.database import Database
from .models import CRMParty
from .service import CRMService


class PartyCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    status: str = "new"
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)


class PartyUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    tags: list[str] | None = None


class TaskCreate(BaseModel):
    title: str
    party_id: str | None = None
    due_at: datetime | None = None
    follow_up: bool = False


class NoteCreate(BaseModel):
    body: str


class DocumentCreate(BaseModel):
    name: str
    reference: str


def public(item):
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    if isinstance(item, CRMParty):
        if data.get("phone"):
            digits = "".join(character for character in data["phone"] if character.isdigit())
            data["phone"] = f"***{digits[-4:]}" if digits else "[redacted]"
        if data.get("email"):
            local = data["email"].split("@", 1)[0]
            data["email"] = f"{local[:1]}***@***"
    return data


def create_crm_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/crm", tags=["crm"])
    service = CRMService(database)

    def list_kind(kind, search, status, tag):
        return [public(item) for item in service.list_parties(kind, search, status, tag)]

    @router.get("/clients")
    def clients(search: str | None = None, status: str | None = None, tag: str | None = None, _: dict = Depends(require_role("viewer"))): return list_kind("client", search, status, tag)

    @router.post("/clients", status_code=201)
    def create_client(payload: PartyCreate, _: dict = Depends(require_role("manager"))): return public(service.create_party("client", **payload.model_dump()))

    @router.patch("/clients/{party_id}")
    def update_client(party_id: str, payload: PartyUpdate, _: dict = Depends(require_role("manager"))):
        try: return public(service.update_party(party_id, payload.model_dump(exclude_unset=True)))
        except KeyError as exc: raise HTTPException(404, str(exc)) from exc

    @router.delete("/clients/{party_id}", status_code=204)
    def delete_client(party_id: str, _: dict = Depends(require_role("admin"))):
        try: service.delete_party(party_id)
        except KeyError as exc: raise HTTPException(404, str(exc)) from exc
        return Response(status_code=204)

    @router.get("/leads")
    def leads(search: str | None = None, status: str | None = None, tag: str | None = None, _: dict = Depends(require_role("viewer"))): return list_kind("lead", search, status, tag)

    @router.post("/leads", status_code=201)
    def create_lead(payload: PartyCreate, _: dict = Depends(require_role("agent"))): return public(service.create_party("lead", **payload.model_dump()))

    @router.get("/tasks")
    def tasks(status: str | None = None, _: dict = Depends(require_role("viewer"))): return [public(item) for item in service.list_tasks(status)]

    @router.post("/tasks", status_code=201)
    def create_task(payload: TaskCreate, _: dict = Depends(require_role("agent"))): return public(service.create_task(**payload.model_dump()))

    @router.post("/jessie/intakes", status_code=201)
    def import_intake(payload: dict, _: dict = Depends(require_role("agent"))): return public(service.import_jessie_intake(payload))

    @router.post("/clients/{party_id}/notes", status_code=201)
    def add_note(party_id: str, payload: NoteCreate, _: dict = Depends(require_role("agent"))):
        try: return public(service.add_note(party_id, payload.body))
        except KeyError as exc: raise HTTPException(404, str(exc)) from exc

    @router.post("/clients/{party_id}/documents", status_code=201)
    def add_document(party_id: str, payload: DocumentCreate, _: dict = Depends(require_role("manager"))):
        try: return public(service.add_document(party_id, payload.name, payload.reference))
        except KeyError as exc: raise HTTPException(404, str(exc)) from exc
        except ValueError as exc: raise HTTPException(400, str(exc)) from exc

    @router.get("/clients/{party_id}/timeline")
    def timeline(party_id: str, _: dict = Depends(require_role("viewer"))): return [public(item) for item in service.timeline(party_id)]

    @router.get("/clients/{party_id}/status-history")
    def status_history(party_id: str, _: dict = Depends(require_role("viewer"))): return [public(item) for item in service.status_history(party_id)]

    return router
