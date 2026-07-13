from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable
from urllib.parse import quote

import httpx


CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleCalendarSandboxError(RuntimeError):
    pass


class GoogleCalendarSandbox:
    def __init__(self, transport: Callable[..., dict] | None = None) -> None:
        self.enabled = os.getenv("GOOGLE_CALENDAR_SANDBOX_ENABLED", "false").casefold() == "true"
        self.mode = os.getenv("GOOGLE_CALENDAR_MODE", "mock").casefold()
        self.calendar_id = os.getenv("JESSE_GOOGLE_STAGING_CALENDAR_ID", "")
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.transport = transport or self._google_transport

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode if self.enabled else "disabled",
            "calendar_configured": bool(self.calendar_id),
            "auth_mode": "adc",
            "human_approval_required": True,
        }

    def validate(self) -> None:
        if self.mode not in {"mock", "sandbox", "disabled"}:
            raise GoogleCalendarSandboxError("invalid Calendar sandbox mode")
        if self.mode == "sandbox":
            if not self.enabled:
                raise GoogleCalendarSandboxError("Calendar sandbox is disabled")
            if not self.calendar_id.endswith("@group.calendar.google.com"):
                raise GoogleCalendarSandboxError("invalid staging Calendar ID")
            if not self.project_id:
                raise GoogleCalendarSandboxError("staging project is not configured")

    def create_event(self, title: str, start_at: datetime, end_at: datetime, request_id: str) -> dict:
        if end_at <= start_at:
            raise GoogleCalendarSandboxError("event end must be after start")
        if not title.strip() or len(title) > 120:
            raise GoogleCalendarSandboxError("invalid event title")
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "network_calls": 0}
        if self.mode == "mock":
            return {"status": "mock", "network_calls": 0, "event_reference": f"mock:{request_id}"}
        self.validate()
        payload = {
            "summary": title.strip(),
            "description": "Success Brand synthetic staging appointment.",
            "start": {"dateTime": start_at.isoformat()},
            "end": {"dateTime": end_at.isoformat()},
            "extendedProperties": {"private": {"request_id": request_id, "sandbox": "true"}},
        }
        result = self.transport(method="POST", calendar_id=self.calendar_id, project_id=self.project_id, payload=payload)
        return {"status": "created", "network_calls": 1, "event_reference": result.get("id", "calendar-event"), "html_link": None}

    def delete_event(self, event_id: str) -> dict:
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "network_calls": 0}
        if self.mode == "mock":
            return {"status": "mock-deleted", "network_calls": 0}
        self.validate()
        self.transport(method="DELETE", calendar_id=self.calendar_id, project_id=self.project_id, event_id=event_id)
        return {"status": "deleted", "network_calls": 1}

    @staticmethod
    def _google_transport(*, method: str, calendar_id: str, project_id: str, payload: dict | None = None, event_id: str | None = None) -> dict:
        import google.auth
        from google.auth.transport.requests import Request

        credentials, detected_project = google.auth.default(scopes=[CALENDAR_SCOPE])
        if detected_project and detected_project != project_id:
            raise GoogleCalendarSandboxError("ADC project does not match staging")
        credentials.refresh(Request())
        base = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id, safe='')}/events"
        url = f"{base}/{quote(event_id, safe='')}" if event_id else base
        response = httpx.request(method, url, headers={"Authorization": f"Bearer {credentials.token}"}, json=payload, timeout=5.0)
        response.raise_for_status()
        return response.json() if method != "DELETE" else {}
