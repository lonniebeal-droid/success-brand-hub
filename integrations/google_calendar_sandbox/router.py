from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import require_role
from .service import GoogleCalendarSandbox, GoogleCalendarSandboxError


class CalendarEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    start_at: datetime
    end_at: datetime


def create_google_calendar_router(factory=GoogleCalendarSandbox) -> APIRouter:
    router = APIRouter(prefix="/sandbox/google-calendar", tags=["google-calendar-sandbox"])

    @router.get("/status")
    def status(_: dict = Depends(require_role("viewer"))):
        return factory().status()

    @router.post("/events", status_code=201)
    def create_event(payload: CalendarEventRequest, request: Request, _: dict = Depends(require_role("manager"))):
        try:
            return factory().create_event(payload.title, payload.start_at, payload.end_at, request.headers.get("X-Request-ID", "calendar-sandbox"))
        except GoogleCalendarSandboxError as exc:
            raise HTTPException(400, str(exc)) from exc

    @router.delete("/events/{event_id}")
    def delete_event(event_id: str, _: dict = Depends(require_role("manager"))):
        try:
            return factory().delete_event(event_id)
        except GoogleCalendarSandboxError as exc:
            raise HTTPException(400, str(exc)) from exc

    return router
