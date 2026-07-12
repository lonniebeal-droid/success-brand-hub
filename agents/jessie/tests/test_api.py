import pytest
from fastapi.testclient import TestClient

from agents.jessie.api.main import create_app
from agents.jessie.src.intake_service import IntakeService


@pytest.fixture()
def client(tmp_path):
    data_file = tmp_path / "intakes.json"
    service = IntakeService(data_file=str(data_file))
    app = create_app(service=service)
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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

    response = client.post("/intakes", json=payload)

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
    ).json()

    response = client.get(f"/intakes/{intake['id']}")

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
    )

    response = client.get("/callbacks/pending")

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
    ).json()

    response = client.patch(f"/intakes/{intake['id']}/status", json={"status": "scheduled"})

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
    ).json()

    response = client.get(f"/intakes/{intake['id']}/summary")

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
    )

    assert response.status_code == 400
    assert "detail" in response.json()
