from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.auth import (
    create_user,
    issue_access_token,
    issue_refresh_token,
    require_role,
    require_user,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from core.database.database import Database, get_database
from core.database.models import Agent, Appointment, Message, Notification, Report, Task, User
from core.memory.persistent import PersistentMemoryEngine
from core.notifications import NotificationService
from core.runtime.monitor import SystemMonitor
from core.runtime.queue import PersistentTaskQueue
from core.runtime.worker import BackgroundWorker
from core.scheduling import SchedulingService
from core.orchestration import AgentOrchestrator
from core.content_system import SuccessBrandContentSystem
from crm.router import create_crm_router
from callcenter.router import create_callcenter_router
from integrations.google_sheets_sandbox.router import create_google_sheets_router
from integrations.sandbox_providers import create_sandbox_provider_router
from integrations.google_calendar_sandbox import create_google_calendar_router


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserRequest(LoginRequest):
    role: str = "viewer"


class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    owner: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    scheduled_for: datetime | None = None


class MemoryRequest(BaseModel):
    namespace: str
    content: str
    kind: str = "long_term"
    conversation_id: str | None = None


class NotificationRequest(BaseModel):
    recipient: str
    message: str
    channel: str = "internal"


class AppointmentRequest(BaseModel):
    title: str
    start_at: datetime
    end_at: datetime
    attendee: str | None = None


class DelegationRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=300)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)


class ContentPackRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    audience: str = Field(default="adults", min_length=1, max_length=80)


def _public(model: Any) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


def create_app(database: Database | None = None) -> FastAPI:
    db = database or get_database()
    queue = PersistentTaskQueue(db)
    worker = BackgroundWorker(queue)
    memory = PersistentMemoryEngine(db)
    notifications = NotificationService(db)
    scheduling = SchedulingService(db)
    monitor = SystemMonitor(queue, [worker])
    orchestrator = AgentOrchestrator(queue)
    content_system = SuccessBrandContentSystem()
    app = FastAPI(title="Success Brand Platform v2", version="2.0.0")
    app.include_router(create_crm_router(db))
    app.include_router(create_callcenter_router(db))
    app.include_router(create_google_sheets_router(db))
    app.include_router(create_sandbox_provider_router())
    app.include_router(create_google_calendar_router())

    @app.middleware("http")
    async def integration_request_id(request, call_next):
        request_id = request.headers.get("X-Request-ID")
        if not request_id or not re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", request_id):
            request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "environment": os.getenv("PLATFORM_ENVIRONMENT", "staging")}

    @app.post("/login")
    def login(payload: LoginRequest):
        with db.session() as session:
            user = session.scalar(select(User).where(User.username == payload.username.strip().casefold(), User.active.is_(True)))
            if not user or not verify_password(payload.password, user.password_hash):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
            return {"access_token": issue_access_token(user), "refresh_token": issue_refresh_token(session, user), "token_type": "bearer"}

    @app.post("/refresh")
    def refresh(payload: RefreshRequest):
        with db.session() as session:
            user, next_refresh = rotate_refresh_token(session, payload.refresh_token)
            return {"access_token": issue_access_token(user), "refresh_token": next_refresh, "token_type": "bearer"}

    @app.post("/logout")
    def logout(payload: RefreshRequest, _: dict = Depends(require_user)):
        with db.session() as session:
            revoke_refresh_token(session, payload.refresh_token)
        return {"logged_out": True}

    @app.get("/me")
    def me(user: dict = Depends(require_user)):
        return {"id": int(user["sub"]), "username": user["username"], "role": user["role"]}

    @app.post("/users", status_code=201)
    def add_user(payload: UserRequest, _: dict = Depends(require_role("admin"))):
        with db.session() as session:
            try:
                return _public(create_user(session, payload.username, payload.password, payload.role))
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc

    @app.get("/agents")
    def agents(_: dict = Depends(require_role("viewer"))):
        with db.session() as session:
            return [_public(item) for item in session.scalars(select(Agent).order_by(Agent.name)).all()]

    @app.post("/tasks", status_code=201)
    def create_task(payload: TaskRequest, _: dict = Depends(require_role("manager"))):
        return _public(queue.enqueue(**payload.model_dump()))

    @app.post("/orchestration/delegate", status_code=201)
    def delegate(payload: DelegationRequest, _: dict = Depends(require_role("manager"))):
        task, decision = orchestrator.delegate(payload.objective, payload.payload, payload.priority)
        return {"task": _public(task), "owner": decision.owner, "reason": decision.reason, "human_approval_required": True}

    @app.post("/content/packs", status_code=201)
    def create_content_pack(payload: ContentPackRequest, _: dict = Depends(require_role("agent"))):
        return content_system.create_pack(payload.topic, payload.audience)

    @app.get("/tasks")
    def tasks(task_status: str | None = Query(default=None, alias="status"), _: dict = Depends(require_role("viewer"))):
        with db.session() as session:
            query = select(Task).order_by(Task.created_at.desc())
            if task_status:
                query = query.where(Task.status == task_status)
            return [_public(item) for item in session.scalars(query).all()]

    @app.post("/workers/run-once")
    def run_once(owner: str | None = None, _: dict = Depends(require_role("agent"))):
        result = worker.process_once(owner)
        return {"processed": result is not None, "task": _public(result) if result else None}

    @app.get("/monitor")
    def monitoring(_: dict = Depends(require_role("viewer"))):
        return monitor.snapshot()

    @app.post("/memory", status_code=201)
    def remember(payload: MemoryRequest, _: dict = Depends(require_role("agent"))):
        return _public(memory.remember(**payload.model_dump()))

    @app.get("/memory/search")
    def search_memory(q: str, namespace: str | None = None, _: dict = Depends(require_role("viewer"))):
        return [_public(item) for item in memory.search(q, namespace)]

    @app.get("/memory/semantic-search")
    def semantic_memory(q: str, limit: int = Query(default=10, ge=1, le=50), _: dict = Depends(require_role("viewer"))):
        return memory.semantic_search(q, limit)

    @app.get("/conversations/{conversation_id}")
    def conversation(conversation_id: str, _: dict = Depends(require_role("viewer"))):
        return [_public(item) for item in memory.conversation(conversation_id)]

    @app.get("/conversations/{conversation_id}/summary")
    def conversation_summary(conversation_id: str, _: dict = Depends(require_role("viewer"))):
        return memory.summarize(conversation_id)

    @app.post("/notifications", status_code=201)
    def notify(payload: NotificationRequest, _: dict = Depends(require_role("manager"))):
        return _public(notifications.send(**payload.model_dump()))

    @app.get("/notifications")
    def list_notifications(_: dict = Depends(require_role("viewer"))):
        with db.session() as session:
            return [_public(item) for item in session.scalars(select(Notification).order_by(Notification.created_at.desc())).all()]

    @app.post("/appointments", status_code=201)
    def schedule(payload: AppointmentRequest, _: dict = Depends(require_role("manager"))):
        try:
            return _public(scheduling.schedule(**payload.model_dump()))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/appointments/availability")
    def availability(start_at: datetime, end_at: datetime, _: dict = Depends(require_role("viewer"))):
        return scheduling.availability(start_at, end_at)

    @app.patch("/appointments/{appointment_id}")
    def reschedule(appointment_id: str, payload: AppointmentRequest, _: dict = Depends(require_role("manager"))):
        try:
            return _public(scheduling.reschedule(appointment_id, payload.start_at, payload.end_at))
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/messages")
    def messages(_: dict = Depends(require_role("viewer"))):
        with db.session() as session:
            return [_public(item) for item in session.scalars(select(Message).order_by(Message.created_at.desc())).all()]

    @app.get("/reports")
    def reports(_: dict = Depends(require_role("viewer"))):
        with db.session() as session:
            return [_public(item) for item in session.scalars(select(Report).order_by(Report.created_at.desc())).all()]

    @app.get("/system/status")
    def system_status(_: dict = Depends(require_role("viewer"))):
        with db.session() as session:
            return {
                "environment": os.getenv("PLATFORM_ENVIRONMENT", "staging"),
                "database": "sqlite",
                "queue_depth": queue.depth(),
                "appointments": len(session.scalars(select(Appointment)).all()),
                "monitor": monitor.snapshot(),
                "production_ready": False,
            }

    return app


app = create_app()
