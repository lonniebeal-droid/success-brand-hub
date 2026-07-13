import base64
from email import message_from_bytes

import pytest
from fastapi.testclient import TestClient

from core.auth import create_user
from core.database.database import Database
from core.platform_api import create_app
from integrations.gmail_sandbox.service import GMAIL_COMPOSE_SCOPE, GmailSandbox, GmailSandboxError


def test_disabled_and_mock_modes_never_use_network(monkeypatch):
    calls = []
    assert GmailSandbox(lambda **kwargs: calls.append(kwargs)).create_draft("Sandbox test", "r1")["status"] == "disabled"
    monkeypatch.setenv("GMAIL_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GMAIL_MODE", "mock")
    assert GmailSandbox(lambda **kwargs: calls.append(kwargs)).create_draft("Sandbox test", "r2")["status"] == "mock"
    assert calls == []


def test_sandbox_creates_only_synthetic_draft(monkeypatch):
    monkeypatch.setenv("GMAIL_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GMAIL_MODE", "sandbox")
    monkeypatch.setenv("GMAIL_SANDBOX_MAILBOX", "successbrand-sandbox-test@example.com")
    monkeypatch.setenv("GMAIL_SANDBOX_RECIPIENT", "successbrand-test-inbox@example.com")
    monkeypatch.setenv("GCP_PROJECT_ID", "success-brand-staging")
    captured = {}
    def transport(**kwargs):
        captured.update(kwargs)
        return {"id": "draft-1"}
    result = GmailSandbox(transport).create_draft("SuccessBrand sandbox test", "request-1")
    assert result == {"status": "draft-created", "network_calls": 1, "draft_only": True, "draft_reference": "draft-1"}
    raw = captured["payload"]["message"]["raw"]
    message = message_from_bytes(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    assert message["To"] == "successbrand-test-inbox@example.com"
    assert message["X-SuccessBrand-Sandbox-Request-ID"] == "request-1"
    assert "client" in message.get_payload().casefold()
    assert "send" not in captured


def test_real_looking_mailboxes_are_rejected(monkeypatch):
    monkeypatch.setenv("GMAIL_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GMAIL_MODE", "sandbox")
    monkeypatch.setenv("GMAIL_SANDBOX_MAILBOX", "staff@example.com")
    monkeypatch.setenv("GMAIL_SANDBOX_RECIPIENT", "client@example.com")
    monkeypatch.setenv("GCP_PROJECT_ID", "success-brand-staging")
    with pytest.raises(GmailSandboxError):
        GmailSandbox().create_draft("Test", "r")


def test_google_transport_uses_compose_scope(monkeypatch):
    captured = {}
    class Credentials:
        token = "token-not-printed"
        def refresh(self, request): captured["refreshed"] = True
    class Response:
        status_code = 200
        def raise_for_status(self): return None
        def json(self): return {"id": "draft-1"}
    monkeypatch.setattr("google.auth.default", lambda *, scopes: (captured.update(scopes=scopes) or Credentials(), "success-brand-staging"))
    monkeypatch.setattr("httpx.post", lambda url, **kwargs: captured.update(url=url, kwargs=kwargs) or Response())
    result = GmailSandbox._google_transport(mailbox="sandbox-test@example.com", project_id="success-brand-staging", auth_mode="adc", payload={"message": {"raw": "fake"}})
    assert result["id"] == "draft-1"
    assert captured["scopes"] == [GMAIL_COMPOSE_SCOPE]
    assert captured["refreshed"] is True
    assert captured["url"].endswith("/users/me/drafts")


def test_oauth_transport_refreshes_without_logging_secrets(monkeypatch):
    monkeypatch.setenv("GMAIL_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GMAIL_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GMAIL_OAUTH_REFRESH_TOKEN", "test-refresh-token")
    captured = []
    class Response:
        status_code = 200
        def __init__(self, body): self.body = body
        def raise_for_status(self): return None
        def json(self): return self.body
    def fake_post(url, **kwargs):
        captured.append((url, kwargs))
        return Response({"access_token": "short-lived-test-token"} if "oauth2" in url else {"id": "draft-2"})
    monkeypatch.setattr("httpx.post", fake_post)
    result = GmailSandbox._google_transport(mailbox="sandbox-test@example.com", project_id="success-brand-staging", auth_mode="oauth", payload={"message": {"raw": "fake"}})
    assert result["id"] == "draft-2"
    assert captured[0][0] == "https://oauth2.googleapis.com/token"
    assert captured[0][1]["data"]["grant_type"] == "refresh_token"
    assert captured[1][1]["headers"]["Authorization"] == "Bearer short-lived-test-token"


def test_oauth_fails_closed_when_secrets_are_missing(monkeypatch):
    for name in ("GMAIL_OAUTH_CLIENT_ID", "GMAIL_OAUTH_CLIENT_SECRET", "GMAIL_OAUTH_REFRESH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(GmailSandboxError, match="incomplete"):
        GmailSandbox._oauth_access_token()


def test_routes_are_protected(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "gmail-test-secret-123456789012345")
    db = Database(f"sqlite:///{tmp_path / 'gmail.db'}")
    db.migrate()
    with db.session() as session:
        create_user(session, "viewer", "viewer-password", "viewer")
        create_user(session, "manager", "manager-password", "manager")
    client = TestClient(create_app(db))
    viewer = client.post("/login", json={"username": "viewer", "password": "viewer-password"}).json()["access_token"]
    manager = client.post("/login", json={"username": "manager", "password": "manager-password"}).json()["access_token"]
    assert client.get("/sandbox/gmail/status", headers={"Authorization": f"Bearer {viewer}"}).status_code == 200
    payload = {"subject": "Synthetic draft"}
    assert client.post("/sandbox/gmail/drafts", headers={"Authorization": f"Bearer {viewer}"}, json=payload).status_code == 403
    response = client.post("/sandbox/gmail/drafts", headers={"Authorization": f"Bearer {manager}"}, json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "disabled"
