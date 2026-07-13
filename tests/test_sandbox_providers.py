from fastapi.testclient import TestClient

from core.auth import create_user
from core.database.database import Database
from core.platform_api import create_app
from integrations.sandbox_providers import SandboxOperation, execute, provider_state


def test_all_providers_fail_closed(monkeypatch):
    for provider in ("google_calendar", "gmail", "n8n", "twilio", "elevenlabs"):
        monkeypatch.delenv(f"{provider.upper()}_SANDBOX_ENABLED", raising=False)
        assert provider_state(provider).mode == "disabled"
        result = execute(provider, SandboxOperation(operation="test", record_id="fake-1"))
        assert result["network_calls"] == 0 and result["status"] == "disabled"


def test_mock_provider_never_calls_network(monkeypatch):
    monkeypatch.setenv("GMAIL_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GMAIL_MODE", "mock")
    result = execute("gmail", SandboxOperation(operation="create_draft", record_id="fake-1"))
    assert result["status"] == "mock" and result["network_calls"] == 0


def test_provider_routes_enforce_roles(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "provider-test-secret-123456789012345")
    db = Database(f"sqlite:///{tmp_path / 'providers.db'}")
    db.migrate()
    with db.session() as session:
        create_user(session, "viewer", "viewer-password", "viewer")
        create_user(session, "manager", "manager-password", "manager")
    client = TestClient(create_app(db))
    viewer_token = client.post("/login", json={"username": "viewer", "password": "viewer-password"}).json()["access_token"]
    manager_token = client.post("/login", json={"username": "manager", "password": "manager-password"}).json()["access_token"]
    assert client.get("/sandbox/providers", headers={"Authorization": f"Bearer {viewer_token}"}).status_code == 200
    denied = client.post("/sandbox/providers/gmail/operations", headers={"Authorization": f"Bearer {viewer_token}"}, json={"operation": "create_draft", "record_id": "fake-1"})
    assert denied.status_code == 403
    accepted = client.post("/sandbox/providers/gmail/operations", headers={"Authorization": f"Bearer {manager_token}"}, json={"operation": "create_draft", "record_id": "fake-1"})
    assert accepted.status_code == 202 and accepted.json()["network_calls"] == 0
