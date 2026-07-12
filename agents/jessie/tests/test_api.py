import re

import pytest
from fastapi.testclient import TestClient

from agents.jessie.api.main import create_app
from agents.jessie.src.intake_service import IntakeService


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("JESSE_ADMIN_TOKEN", "admin-token")
    monkeypatch.setenv("JESSE_TWILIO_TOKEN", "twilio-token")
    monkeypatch.setenv("JESSE_ELEVENLABS_TOKEN", "elevenlabs-token")
    monkeypatch.setenv("JESSE_N8N_TOKEN", "n8n-token")
    monkeypatch.setenv("JESSE_GOOGLE_TOKEN", "google-token")
    monkeypatch.setenv("JESSE_ENVIRONMENT", "test")
    monkeypatch.setenv("JESSE_DATA_PATH", str(tmp_path / "intakes.json"))
    monkeypatch.setenv("JESSE_LOG_LEVEL", "INFO")
    monkeypatch.setenv("JESSE_RATE_LIMIT_PER_KEY", "2")
    monkeypatch.setenv("JESSE_RATE_LIMIT_PER_IP", "2")

    data_file = tmp_path / "intakes.json"
    service = IntakeService(data_file=str(data_file))
    app = create_app(service=service)
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(service: str = "admin") -> dict[str, str]:
    tokens = {
        "admin": "admin-token",
        "twilio": "twilio-token",
        "elevenlabs": "elevenlabs-token",
        "n8n": "n8n-token",
        "google": "google-token",
    }
    return {"X-API-Key": tokens[service]}


def test_health_endpoint_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_token_is_rejected(client):
    response = client.post(
        "/intakes",
        json={
            "caller_name": "Ada Lovelace",
            "phone_number": "(555) 123-4567",
            "email": "ada@example.com",
            "reason_for_call": "Consultation",
            "urgency": "normal",
            "preferred_callback_time": "tomorrow",
            "consent_to_store": True,
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_invalid_token_is_rejected(client):
    response = client.post(
        "/intakes",
        json={
            "caller_name": "Ada Lovelace",
            "phone_number": "(555) 123-4567",
            "email": "ada@example.com",
            "reason_for_call": "Consultation",
            "urgency": "normal",
            "preferred_callback_time": "tomorrow",
            "consent_to_store": True,
        },
        headers={"X-API-Key": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_valid_service_tokens_are_accepted(client):
    for service in ("admin", "twilio", "elevenlabs", "n8n"):
        response = client.post(
            "/intakes",
            json={
                "caller_name": "Ada Lovelace",
                "phone_number": "(555) 123-4567",
                "email": "ada@example.com",
                "reason_for_call": "Consultation",
                "urgency": "normal",
                "preferred_callback_time": "tomorrow",
                "consent_to_store": True,
            },
            headers=auth_headers(service=service),
        )
        assert response.status_code == 201


def test_permissions_by_service(client):
    create_response = client.post(
        "/intakes",
        json={
            "caller_name": "Grace Hopper",
            "phone_number": "(555) 765-4321",
            "email": "grace@example.com",
            "reason_for_call": "Callback",
            "urgency": "high",
            "preferred_callback_time": "today",
            "consent_to_store": True,
        },
        headers=auth_headers(service="twilio"),
    )
    assert create_response.status_code == 201

    callbacks_response = client.get("/callbacks/pending", headers=auth_headers(service="twilio"))
    assert callbacks_response.status_code == 403


def test_rate_limiting_enforces_limits(client):
    first = client.get("/callbacks/pending", headers=auth_headers(service="admin"))
    second = client.get("/callbacks/pending", headers=auth_headers(service="admin"))
    third = client.get("/callbacks/pending", headers=auth_headers(service="admin"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"


def test_request_id_is_generated(client):
    response = client.get("/health")
    assert response.headers.get("X-Request-ID")


def test_custom_request_id_is_accepted(client):
    response = client.get("/health", headers={"X-Request-ID": "req-1234"})
    assert response.headers.get("X-Request-ID") == "req-1234"


def test_malformed_request_id_is_rejected(client):
    response = client.get("/health", headers={"X-Request-ID": "bad id"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_feature_flags_default_to_false(client):
    assert client.app.state.feature_flags == {
        "twilio": False,
        "elevenlabs": False,
        "google_calendar": False,
        "gmail": False,
        "google_sheets": False,
        "n8n": False,
    }


def test_safe_audit_logs_do_not_expose_sensitive_data(client, caplog):
    with caplog.at_level("INFO", logger="jesse.api"):
        client.post(
            "/intakes",
            json={
                "caller_name": "Ada Lovelace",
                "phone_number": "(555) 123-4567",
                "email": "ada@example.com",
                "reason_for_call": "Consultation",
                "urgency": "normal",
                "preferred_callback_time": "tomorrow",
                "consent_to_store": True,
            },
            headers=auth_headers(service="admin"),
        )

    log_output = caplog.text
    assert "admin-token" not in log_output
    assert "ada@example.com" not in log_output
    assert "(555) 123-4567" not in log_output


def test_safe_error_responses_do_not_leak_internal_details(client):
    response = client.get("/intakes/does-not-exist", headers=auth_headers(service="admin"))

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "traceback" not in payload["error"]["message"].lower()
    assert "does-not-exist" not in payload["error"]["message"].lower()
