import os

import pytest
from fastapi.testclient import TestClient

from agents.jessie.api.main import create_app
from agents.jessie.integrations.base import SandboxAdapter
from agents.jessie.integrations.google_calendar_adapter import GoogleCalendarAdapter
from agents.jessie.src.intake_service import IntakeService


@pytest.fixture()
def platform_client(tmp_path, monkeypatch):
    tokens = {
        "JESSE_ADMIN_TOKEN": "admin-test-token",
        "JESSE_TWILIO_TOKEN": "twilio-test-token",
        "JESSE_ELEVENLABS_TOKEN": "elevenlabs-test-token",
        "JESSE_N8N_TOKEN": "n8n-test-token",
        "JESSE_GOOGLE_TOKEN": "google-test-token",
        "JESSE_DASHBOARD_TOKEN": "dashboard-test-token",
    }
    for name, value in tokens.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("JESSE_DATA_PATH", str(tmp_path / "intakes.json"))
    monkeypatch.setenv("JESSE_RATE_LIMIT_REQUESTS", "50")
    service = IntakeService(data_file=str(tmp_path / "intakes.json"))
    app = create_app(service=service)
    with TestClient(app) as client:
        yield client


def headers(identity="admin"):
    return {"X-API-Key": f"{identity}-test-token"}


def test_dashboard_can_read_reports_but_not_create_intakes(platform_client):
    report = platform_client.get("/reports/summary", headers=headers("dashboard"))
    denied = platform_client.post("/intakes", headers=headers("dashboard"), json={})
    assert report.status_code == 200
    assert denied.status_code == 403


def test_status_and_reports_are_redacted(platform_client):
    status = platform_client.get("/integrations/status", headers=headers())
    report = platform_client.get("/reports/security", headers=headers())
    assert status.status_code == 200
    assert status.json()["sandbox"] is True
    assert report.status_code == 200
    serialized = f"{status.json()} {report.json()}"
    assert "test-token" not in serialized
    assert "phone_number" not in serialized
    assert "email" not in serialized


def test_disabled_sandbox_route_never_claims_external_action(platform_client):
    response = platform_client.get("/sandbox/calendar/slots", headers=headers("google"))
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"
    assert response.json()["sandbox"] is True


def test_mock_adapter_reports_no_network_activity():
    assert SandboxAdapter().status()["network_activity"] is False
    assert GoogleCalendarAdapter(enabled=True, mode="mock").create_mock_booking({"slot": "slot-1"})["sandbox"] is True
