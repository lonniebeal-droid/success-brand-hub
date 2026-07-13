from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from core.auth import create_user
from core.database.database import Database
from core.platform_api import create_app
from integrations.elevenlabs_sandbox.service import ElevenLabsSandbox, ElevenLabsSandboxError
from integrations.twilio_sandbox.service import TwilioSandbox, TwilioSandboxError


def test_twilio_disabled_mock_and_signed_sandbox(monkeypatch):
    assert TwilioSandbox().verify_inbound("https://example.test", {}, "")["status"] == "disabled"
    monkeypatch.setenv("TWILIO_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("TWILIO_MODE", "mock")
    assert TwilioSandbox().verify_inbound("https://example.test", {}, "")["status"] == "mock"
    url = "https://sandbox.example.test/twilio"
    token = "test-auth-token-123456789"
    params = {"CallSid": "CA_TEST_ONLY", "From": "+15005550006"}
    signature = RequestValidator(token).compute_signature(url, params)
    monkeypatch.setenv("TWILIO_MODE", "sandbox")
    monkeypatch.setenv("TWILIO_SANDBOX_AUTH_TOKEN", token)
    monkeypatch.setenv("TWILIO_SANDBOX_PUBLIC_URL", url)
    result = TwilioSandbox().verify_inbound(url, params, signature)
    assert result["status"] == "verified" and result["network_calls"] == 0
    with pytest.raises(TwilioSandboxError, match="signature"):
        TwilioSandbox().verify_inbound(url, params, "invalid")


def test_elevenlabs_disabled_mock_and_signed_sandbox(monkeypatch):
    assert ElevenLabsSandbox().verify_event("{}", "test")["status"] == "disabled"
    monkeypatch.setenv("ELEVENLABS_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_MODE", "mock")
    assert ElevenLabsSandbox().verify_event("{}", "test")["status"] == "mock"
    monkeypatch.setenv("ELEVENLABS_MODE", "sandbox")
    monkeypatch.setenv("ELEVENLABS_SANDBOX_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_SANDBOX_AGENT_ID", "test-agent")
    monkeypatch.setenv("ELEVENLABS_SANDBOX_WEBHOOK_SECRET", "test-webhook-secret-123")

    class Webhooks:
        def construct_event(self, **kwargs):
            return {"type": "post_call_transcription", "data": {"private": "not returned"}}

    class Client:
        webhooks = Webhooks()

    result = ElevenLabsSandbox(lambda **kwargs: Client()).verify_event("{}", "t=1,v0=fake")
    assert result == {
        "status": "verified",
        "accepted": True,
        "network_calls": 0,
        "event_type": "post_call_transcription",
        "payload_stored": False,
    }


def test_new_routes_enforce_roles(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "remaining-sandbox-test-secret-123456789")
    db = Database(f"sqlite:///{tmp_path / 'remaining.db'}")
    db.migrate()
    with db.session() as session:
        create_user(session, "viewer", "viewer-password", "viewer")
        create_user(session, "manager", "manager-password", "manager")
    client = TestClient(create_app(db))
    viewer = client.post("/login", json={"username": "viewer", "password": "viewer-password"}).json()["access_token"]
    manager = client.post("/login", json={"username": "manager", "password": "manager-password"}).json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer}"}
    manager_headers = {"Authorization": f"Bearer {manager}"}
    assert client.get("/sandbox/twilio/status", headers=viewer_headers).status_code == 200
    assert client.get("/sandbox/elevenlabs/status", headers=viewer_headers).status_code == 200
    twilio_payload = {"url": "https://example.test", "params": {}, "signature": ""}
    eleven_payload = {"raw_body": "{}", "signature": "test"}
    assert client.post("/sandbox/twilio/verify-webhook", headers=viewer_headers, json=twilio_payload).status_code == 403
    assert client.post("/sandbox/elevenlabs/verify-webhook", headers=viewer_headers, json=eleven_payload).status_code == 403
    assert client.post("/sandbox/twilio/verify-webhook", headers=manager_headers, json=twilio_payload).status_code == 200
    assert client.post("/sandbox/elevenlabs/verify-webhook", headers=manager_headers, json=eleven_payload).status_code == 200
    assert client.post("/sandbox/twilio/webhook").status_code == 503
    assert client.post("/sandbox/elevenlabs/webhook").status_code == 503

    callback_url = "https://sandbox.example.test/twilio"
    token = "test-auth-token-123456789"
    form = {"CallSid": "CA_TEST_ONLY"}
    monkeypatch.setenv("TWILIO_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("TWILIO_MODE", "sandbox")
    monkeypatch.setenv("TWILIO_SANDBOX_AUTH_TOKEN", token)
    monkeypatch.setenv("TWILIO_SANDBOX_PUBLIC_URL", callback_url)
    signature = RequestValidator(token).compute_signature(callback_url, form)
    verified = client.post(
        "/sandbox/twilio/webhook",
        data=form,
        headers={"X-Twilio-Signature": signature},
    )
    assert verified.status_code == 200 and verified.text == "<Response/>"

    monkeypatch.setenv("ELEVENLABS_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_MODE", "mock")
    assert client.post("/sandbox/elevenlabs/webhook", content="{}").json()["status"] == "mock"


def test_controlled_workflows_are_manual_and_non_operational():
    n8n = Path(".github/workflows/n8n-controlled-sandbox-test.yml").read_text()
    twilio = Path(".github/workflows/twilio-auth-readiness.yml").read_text()
    eleven = Path(".github/workflows/elevenlabs-auth-readiness.yml").read_text()
    assert "workflow_dispatch:" in n8n and "TRIGGER SYNTHETIC N8N TEST" in n8n
    assert "client_data_sent: false" in n8n and "sandbox_feature_enabled: false" in n8n
    assert "workflow_dispatch:" in twilio and "calls_created: 0" in twilio and "messages_sent: 0" in twilio
    assert "/Calls" not in twilio and "/Messages" not in twilio
    assert "workflow_dispatch:" in eleven and "conversations_started: 0" in eleven
    assert "text-to-speech" not in eleven and "audio_generated: false" in eleven
