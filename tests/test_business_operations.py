import os

import pytest
from fastapi.testclient import TestClient

from callcenter.service import CallCenterService
from core.auth import create_user
from core.database.database import Database
from core.platform_api import create_app
from crm.service import CRMService


@pytest.fixture
def db(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'operations.db'}")
    database.migrate()
    return database


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "business-operations-test-secret-123456789")
    with db.session() as session:
        create_user(session, "admin", "operations-password", "admin")
    app = create_app(db)
    client = TestClient(app)
    token = client.post("/login", json={"username": "admin", "password": "operations-password"}).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_crm_lifecycle_search_status_and_jessie_import(db):
    crm = CRMService(db)
    client = crm.create_party("client", "Acme Health", "hello@example.test", "5550001234", tags=["priority"])
    assert crm.list_parties("client", search="Acme", tag="priority")[0].id == client.id
    updated = crm.update_party(client.id, {"status": "active"})
    assert updated.status == "active"
    task = crm.create_task("Follow up", client.id, follow_up=True)
    assert crm.list_tasks("open")[0].id == task.id
    assert crm.add_note(client.id, "Safe staging note").party_id == client.id
    assert crm.add_document(client.id, "Consent", "mock://document/1").party_id == client.id
    with pytest.raises(ValueError):
        crm.add_document(client.id, "Unsafe", "/Users/private/document.pdf")
    assert any(item.event == "note_added" for item in crm.timeline(client.id))
    assert crm.status_history(client.id)[0].new_status == "active"
    lead = crm.import_jessie_intake({"id": "intake-test", "caller_name": "Test Caller", "phone_number": "***1234", "reason_for_call": "Demo", "urgency": "normal"})
    assert lead.source == "jessie" and "jessie-intake" in lead.tags
    crm.delete_party(client.id)
    assert crm.list_parties("client") == []


def test_call_center_mock_flow_redaction_and_analytics(db):
    calls = CallCenterService(db)
    call = calls.receive_mock_call("555-000-4321")
    assert call.caller_redacted == "***4321" and call.metadata_json["mode"] == "mock"
    active = calls.update_call(call.id, "active")
    assert active.state == "active"
    callback = calls.update_call(call.id, "callback", "requested")
    assert callback.outcome == "requested"
    assert calls.analytics()["callback_queue"] == 1
    assert calls.set_availability("jessie", "available").status == "available"


def test_authenticated_crm_and_callcenter_routes(client):
    created = client.post("/crm/clients", json={"name": "Staging Client", "tags": ["new"]})
    assert created.status_code == 201
    assert len(client.get("/crm/clients?search=Staging").json()) == 1
    lead = client.post("/crm/jessie/intakes", json={"id": "safe-intake", "caller_name": "Mock Caller", "phone_number": "***9999"})
    assert lead.status_code == 201 and lead.json()["source"] == "jessie"
    call = client.post("/callcenter/calls/mock", json={"caller": "555-111-2222"})
    assert call.status_code == 201 and call.json()["caller_redacted"] == "***2222"
    assert client.get("/callcenter/analytics").json()["mode"] == "mock"


def test_crm_api_redacts_contact_fields(client):
    result = client.post("/crm/clients", json={"name": "Private Client", "email": "private@example.test", "phone": "555-333-9876"})
    assert result.json()["phone"] == "***9876"
    assert result.json()["email"] == "p***@***"
    payload = client.get("/crm/clients?search=Private").json()[0]
    assert payload["phone"] == "***9876" and payload["email"] == "p***@***"


def test_business_routes_require_auth(db):
    client = TestClient(create_app(db))
    assert client.get("/crm/clients").status_code == 401
    assert client.get("/callcenter/calls").status_code == 401


def test_viewer_is_read_only(db, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "business-operations-test-secret-123456789")
    with db.session() as session:
        create_user(session, "readonly", "readonly-password", "viewer")
    client = TestClient(create_app(db))
    token = client.post("/login", json={"username": "readonly", "password": "readonly-password"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    assert client.get("/crm/clients", headers=auth).status_code == 200
    assert client.get("/callcenter/calls", headers=auth).status_code == 200
    assert client.post("/crm/clients", json={"name": "Denied"}, headers=auth).status_code == 403
    assert client.post("/callcenter/calls/mock", json={}, headers=auth).status_code == 403
