import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from agents.jessie.integrations.google_sheets_adapter import GoogleSheetsAdapter, GoogleSheetsSandboxError, SCHEMA_VERSION, SandboxRow, redact_email, redact_phone
from agents.jessie.src.intake_service import IntakeService
from agents.jessie.src.storage import InMemoryStorage
from core.auth import create_user
from core.database.database import Database
from core.platform_api import create_app
from crm.models import CRMActivity
from crm.service import CRMService
from integrations.google_sheets_sandbox.service import GoogleSheetsSandboxService


@pytest.fixture
def db(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'sheets.db'}")
    database.migrate()
    return database


def row():
    return SandboxRow(SCHEMA_VERSION, "record-1", "2026-01-01T00:00:00Z", "***1234", "a***@***", "appointment", "normal", "new", "crm", "request-1")


def credentials():
    return json.dumps({"client_email": "sandbox-service@example.invalid", "private_key": "test-only-key", "token_uri": "https://oauth2.googleapis.com/token"})


def test_disabled_and_mock_modes_never_call_network():
    calls = []
    disabled = GoogleSheetsAdapter(enabled=False, mode="mock", transport=lambda **kwargs: calls.append(kwargs))
    assert disabled.append_row(row())["status"] == "disabled" and calls == [] and disabled.network_calls == 0
    mock = GoogleSheetsAdapter(enabled=True, mode="mock", transport=lambda **kwargs: calls.append(kwargs))
    assert mock.append_row(row())["status"] == "mock" and calls == [] and mock.network_calls == 0


def test_sandbox_mode_mocked_transport_redacts_and_retries():
    attempts = []
    def transport(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1: raise RuntimeError("temporary")
        return {"updatedRange": "Sandbox Leads!A2:J2"}
    adapter = GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", credentials(), transport, max_retries=2)
    result = adapter.append_row(row())
    assert result["status"] == "written" and len(attempts) == 2
    values = attempts[-1]["values"]
    assert "***1234" in values and "a***@***" in values
    assert not any("555" in value or "@example" in value for value in values)


def test_startup_validation_and_strict_contract():
    with pytest.raises(GoogleSheetsSandboxError): GoogleSheetsAdapter(True, "sandbox", "bad", "Sheet", credentials()).validate_startup()
    with pytest.raises(GoogleSheetsSandboxError): GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sheet", "").validate_startup()
    with pytest.raises(GoogleSheetsSandboxError): SandboxRow(SCHEMA_VERSION, "x", "now", "555-111-2222", "raw@example.com", "general", "normal", "new", "crm", "r").validate()
    assert redact_phone("555-111-9876") == "***9876" and redact_email("private@example.com") == "p***@***"


def test_duplicate_prevention_crm_activity_and_jessie_handoff(db):
    adapter = GoogleSheetsAdapter(True, "mock")
    intake_store = InMemoryStorage()
    intake = IntakeService(storage=intake_store)
    created = intake.create_intake("Test Caller", "555-111-2222", "caller@example.test", "appointment request", consent_to_store=True)
    service = GoogleSheetsSandboxService(db, adapter, intake)
    assert service.write_intake(created["id"], "req-intake")["status"] == "mock"
    with pytest.raises(GoogleSheetsSandboxError): service.write_intake(created["id"], "req-repeat")
    lead = CRMService(db).create_party("lead", "Private Lead", "lead@example.test", "555-222-3333", source="jessie", metadata={"reason": "support", "urgency": "high"})
    assert service.write_lead(lead.id, "req-lead")["status"] == "mock"
    with db.session() as session:
        event = session.scalar(select(CRMActivity).where(CRMActivity.party_id == lead.id, CRMActivity.event == "google_sheets_sandbox_written"))
        assert event and "spreadsheet" not in event.detail and "credentials" not in event.detail


def auth_client(db, monkeypatch, role):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "google-sheets-sandbox-test-secret-12345")
    monkeypatch.setenv("GOOGLE_SHEETS_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_SHEETS_MODE", "mock")
    with db.session() as session: create_user(session, role, f"{role}-password", role)
    client = TestClient(create_app(db))
    token = client.post("/login", json={"username": role, "password": f"{role}-password"}).json()["access_token"]
    return client, {"Authorization": f"Bearer {token}", "X-Request-ID": f"request-{role}"}


def test_permissions_status_and_safe_errors(db, monkeypatch):
    viewer, viewer_headers = auth_client(db, monkeypatch, "viewer")
    status = viewer.get("/sandbox/google-sheets/status", headers=viewer_headers)
    assert status.status_code == 200 and status.headers["X-Request-ID"] == "request-viewer"
    assert "spreadsheet_id" not in status.json()
    assert viewer.post("/sandbox/google-sheets/test-connection", headers=viewer_headers).status_code == 403

    manager, manager_headers = auth_client(db, monkeypatch, "manager")
    result = manager.post("/sandbox/google-sheets/leads/missing", headers=manager_headers)
    assert result.status_code == 409 and result.headers.get("X-Request-ID")
    assert "sqlite" not in result.text.lower() and "credentials" not in result.text.lower()

    agent, agent_headers = auth_client(db, monkeypatch, "agent")
    assert agent.get("/sandbox/google-sheets/status", headers=agent_headers).status_code == 200
    assert agent.post("/sandbox/google-sheets/test-connection", headers=agent_headers).status_code == 403


def test_no_secrets_logged(caplog):
    secret = "private-key-material-must-not-log"
    adapter = GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", credentials().replace("test-only-key", secret), lambda **kwargs: (_ for _ in ()).throw(RuntimeError(secret)), max_retries=0)
    with pytest.raises(GoogleSheetsSandboxError): adapter.append_row(row())
    assert secret not in caplog.text


def test_failed_write_is_counted_safely(db):
    adapter = GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", credentials(), lambda **kwargs: (_ for _ in ()).throw(RuntimeError("transport failed")), max_retries=0)
    service = GoogleSheetsSandboxService(db, adapter)
    with pytest.raises(GoogleSheetsSandboxError): service._write("crm", "lead-failure", "request-failure", row())
    status = service.status()
    assert status["failure_count"] == 1 and status["last_error"] == "write_failed"
