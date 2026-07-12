import pytest
from fastapi.testclient import TestClient

from agents.jessie.api.main import create_app
from agents.jessie.src.intake_service import IntakeService


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("JESSE_API_KEY", "test-api-key")
    monkeypatch.setenv("JESSE_ENVIRONMENT", "test")
    monkeypatch.setenv("JESSE_DATA_PATH", str(tmp_path / "intakes.json"))
    monkeypatch.setenv("JESSE_LOG_LEVEL", "INFO")

    data_file = tmp_path / "intakes.json"
    service = IntakeService(data_file=str(data_file))
    app = create_app(service=service)
    with TestClient(app) as test_client:
        yield test_client


def auth_headers():
    return {"X-API-Key": "test-api-key"}


def test_health_endpoint_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_api_key_is_rejected(client):
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


def test_invalid_api_key_is_rejected(client):
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
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_create_intake_route_returns_redacted_response(client):
    payload = {
        "caller_name": "Ada Lovelace",
        "phone_number": "(555) 123-4567",
        "email": "ada@example.com",
        "reason_for_call": "Consultation",
        "urgency": "normal",
        "preferred_callback_time": "tomorrow",
        "consent_to_store": True,
    }

    response = client.post("/intakes", json=payload, headers=auth_headers())

    assert response.status_code == 201
    body = response.json()
    assert body["caller_name"] == "Ada Lovelace"
    assert body["status"] == "new"
    assert "email" not in body
    assert "phone_number" not in body
    assert "id" in body


def test_get_intake_route_returns_redacted_payload(client):
    intake = client.post(
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
        headers=auth_headers(),
    ).json()

    response = client.get(f"/intakes/{intake['id']}", headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["caller_name"] == "Grace Hopper"
    assert "email" not in body
    assert "phone_number" not in body


def test_pending_callbacks_route_lists_new_intakes(client):
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
        headers=auth_headers(),
    )

    response = client.get("/callbacks/pending", headers=auth_headers())

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "new"


def test_update_status_route_changes_status(client):
    intake = client.post(
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
        headers=auth_headers(),
    ).json()

    response = client.patch(
        f"/intakes/{intake['id']}/status",
        json={"status": "scheduled"},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"


def test_summary_route_returns_redacted_summary(client):
    intake = client.post(
        "/intakes",
        json={
            "caller_name": "Ada Lovelace",
            "phone_number": "(555) 123-4567",
            "email": "ada@example.com",
            "reason_for_call": "Consultation",
            "urgency": "high",
            "preferred_callback_time": "tomorrow",
            "consent_to_store": True,
        },
        headers=auth_headers(),
    ).json()

    response = client.get(f"/intakes/{intake['id']}/summary", headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert "Ada Lovelace" in body["summary"]
    assert "4567" in body["summary"]
    assert "ada@example.com" not in body["summary"]
    assert "example.com" not in body["summary"]


def test_invalid_payload_returns_bad_request(client):
    response = client.post(
        "/intakes",
        json={
            "caller_name": "Ada Lovelace",
            "phone_number": "invalid-phone",
            "email": "ada@example.com",
            "reason_for_call": "Consultation",
            "urgency": "normal",
            "preferred_callback_time": "tomorrow",
            "consent_to_store": True,
        },
        headers=auth_headers(),
    )

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


def test_logs_do_not_expose_secrets(client, caplog):
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
            headers=auth_headers(),
        )

    log_output = caplog.text
    assert "test-api-key" not in log_output
    assert "ada@example.com" not in log_output
    assert "(555) 123-4567" not in log_output


def test_safe_error_responses_do_not_leak_internal_details(client):
    response = client.get("/intakes/does-not-exist", headers=auth_headers())

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "traceback" not in payload["error"]["message"].lower()
    assert "does-not-exist" not in payload["error"]["message"].lower()
