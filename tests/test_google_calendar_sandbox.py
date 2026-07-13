from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from core.auth import create_user
from core.database.database import Database
from core.platform_api import create_app
from integrations.google_calendar_sandbox.service import CALENDAR_SCOPE, GoogleCalendarSandbox, GoogleCalendarSandboxError


def times():
    start = datetime.now(timezone.utc) + timedelta(days=1)
    return start, start + timedelta(minutes=30)


def test_disabled_and_mock_modes_make_no_network_calls(monkeypatch):
    calls = []
    start, end = times()
    adapter = GoogleCalendarSandbox(lambda **kwargs: calls.append(kwargs))
    assert adapter.create_event("Fake appointment", start, end, "r1")["status"] == "disabled"
    monkeypatch.setenv("GOOGLE_CALENDAR_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_CALENDAR_MODE", "mock")
    adapter = GoogleCalendarSandbox(lambda **kwargs: calls.append(kwargs))
    assert adapter.create_event("Fake appointment", start, end, "r2")["status"] == "mock"
    assert calls == []


def test_sandbox_payload_contains_no_client_data(monkeypatch):
    monkeypatch.setenv("GOOGLE_CALENDAR_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_CALENDAR_MODE", "sandbox")
    monkeypatch.setenv("JESSE_GOOGLE_STAGING_CALENDAR_ID", "fake@group.calendar.google.com")
    monkeypatch.setenv("GCP_PROJECT_ID", "success-brand-staging")
    captured = {}
    def transport(**kwargs):
        captured.update(kwargs)
        return {"id": "fake-event"}
    start, end = times()
    result = GoogleCalendarSandbox(transport).create_event("Sandbox appointment", start, end, "request-1")
    assert result["status"] == "created"
    assert captured["payload"]["summary"] == "Sandbox appointment"
    assert "client" not in str(captured["payload"]).casefold()
    assert "request-1" in str(captured["payload"])


def test_google_transport_uses_adc(monkeypatch):
    captured = {}
    class Credentials:
        token = "token-not-printed"
        def refresh(self, request): captured["refreshed"] = True
    class Response:
        def raise_for_status(self): return None
        def json(self): return {"id": "fake-event"}
    def fake_default(*, scopes):
        captured["scopes"] = scopes
        return Credentials(), "success-brand-staging"
    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return Response()
    monkeypatch.setattr("google.auth.default", fake_default)
    monkeypatch.setattr("httpx.request", fake_request)
    result = GoogleCalendarSandbox._google_transport(method="POST", calendar_id="fake@group.calendar.google.com", project_id="success-brand-staging", payload={"summary": "Fake"})
    assert result["id"] == "fake-event"
    assert captured["scopes"] == [CALENDAR_SCOPE]
    assert captured["refreshed"] is True
    assert captured["kwargs"]["headers"] == {"Authorization": "Bearer token-not-printed"}


def test_invalid_event_is_rejected(monkeypatch):
    monkeypatch.setenv("GOOGLE_CALENDAR_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_CALENDAR_MODE", "mock")
    start, end = times()
    with pytest.raises(GoogleCalendarSandboxError):
        GoogleCalendarSandbox().create_event("Fake", end, start, "r")


def test_routes_are_protected(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "calendar-test-secret-123456789012345")
    db = Database(f"sqlite:///{tmp_path / 'calendar.db'}")
    db.migrate()
    with db.session() as session:
        create_user(session, "viewer", "viewer-password", "viewer")
        create_user(session, "manager", "manager-password", "manager")
    client = TestClient(create_app(db))
    viewer = client.post("/login", json={"username": "viewer", "password": "viewer-password"}).json()["access_token"]
    manager = client.post("/login", json={"username": "manager", "password": "manager-password"}).json()["access_token"]
    assert client.get("/sandbox/google-calendar/status", headers={"Authorization": f"Bearer {viewer}"}).status_code == 200
    payload = {"title": "Fake appointment", "start_at": times()[0].isoformat(), "end_at": times()[1].isoformat()}
    assert client.post("/sandbox/google-calendar/events", headers={"Authorization": f"Bearer {viewer}"}, json=payload).status_code == 403
    assert client.post("/sandbox/google-calendar/events", headers={"Authorization": f"Bearer {manager}"}, json=payload).status_code == 201
