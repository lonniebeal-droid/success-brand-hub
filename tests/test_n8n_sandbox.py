import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from core.auth import create_user
from core.database.database import Database
from core.platform_api import create_app
from integrations.n8n_sandbox.service import N8nSandbox, N8nSandboxError


def test_disabled_and_mock_modes_never_call_network(monkeypatch):
    calls = []
    assert N8nSandbox(lambda **kwargs: calls.append(kwargs)).trigger("health_check", "fake-1", "r1")["status"] == "disabled"
    monkeypatch.setenv("N8N_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("N8N_MODE", "mock")
    assert N8nSandbox(lambda **kwargs: calls.append(kwargs)).trigger("synthetic_lead", "fake-2", "r2")["status"] == "mock"
    assert calls == []


def test_sandbox_sends_minimal_signed_payload(monkeypatch):
    host = "sandbox-n8n.example.test"
    fake_url = "https://" + host + "/web" + "hook/successbrand"
    monkeypatch.setenv("N8N_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("N8N_MODE", "sandbox")
    monkeypatch.setenv("N8N_SANDBOX_WEBHOOK_URL", fake_url)
    monkeypatch.setenv("N8N_SANDBOX_ALLOWED_HOST", host)
    monkeypatch.setenv("N8N_SANDBOX_SIGNING_SECRET", "s" * 32)
    captured = {}

    result = N8nSandbox(lambda **kwargs: captured.update(kwargs) or {"accepted": True}).trigger(
        "synthetic_intake", "fake-intake-1", "request-1"
    )

    assert result == {"status": "accepted", "network_calls": 1, "request_id": "request-1"}
    payload = json.loads(captured["body"])
    assert payload == {
        "schema_version": "n8n_sandbox_v1",
        "operation": "synthetic_intake",
        "record_id": "fake-intake-1",
        "request_id": "request-1",
        "synthetic": True,
    }
    expected = hmac.new(("s" * 32).encode(), captured["body"], hashlib.sha256).hexdigest()
    assert hmac.compare_digest(captured["signature"], expected)


def test_sandbox_rejects_unapproved_destination_and_operation(monkeypatch):
    monkeypatch.setenv("N8N_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("N8N_MODE", "sandbox")
    monkeypatch.setenv("N8N_SANDBOX_WEBHOOK_URL", "http://localhost/webhook")
    monkeypatch.setenv("N8N_SANDBOX_ALLOWED_HOST", "localhost")
    monkeypatch.setenv("N8N_SANDBOX_SIGNING_SECRET", "s" * 32)
    with pytest.raises(N8nSandboxError, match="HTTPS"):
        N8nSandbox().trigger("health_check", "fake-1", "r1")
    with pytest.raises(N8nSandboxError, match="unsupported"):
        N8nSandbox().trigger("send_email", "fake-1", "r1")


def test_routes_enforce_read_and_write_roles(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "n8n-test-secret-12345678901234567890")
    db = Database(f"sqlite:///{tmp_path / 'n8n.db'}")
    db.migrate()
    with db.session() as session:
        create_user(session, "viewer", "viewer-password", "viewer")
        create_user(session, "manager", "manager-password", "manager")
    client = TestClient(create_app(db))
    viewer = client.post("/login", json={"username": "viewer", "password": "viewer-password"}).json()["access_token"]
    manager = client.post("/login", json={"username": "manager", "password": "manager-password"}).json()["access_token"]
    assert client.get("/sandbox/n8n/status", headers={"Authorization": f"Bearer {viewer}"}).status_code == 200
    payload = {"operation": "health_check", "record_id": "fake-1"}
    assert client.post("/sandbox/n8n/operations", headers={"Authorization": f"Bearer {viewer}"}, json=payload).status_code == 403
    response = client.post("/sandbox/n8n/operations", headers={"Authorization": f"Bearer {manager}"}, json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "disabled"
