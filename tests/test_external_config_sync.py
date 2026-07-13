import json

import pytest

from scripts.external_config_sync import (
    ConfigSyncError,
    _deploy,
    export_manifest,
    plan,
    redact,
    validate_manifest,
)


def manifest(provider="elevenlabs", target="staging", payload=None):
    return {
        "schema_version": 1,
        "provider": provider,
        "target": target,
        "resource_id_env": "ELEVENLABS_AGENT_ID" if provider == "elevenlabs" else "MAKE_APPOINTMENT_SCENARIO_ID",
        "payload": {} if payload is None else payload,
    }


def test_empty_template_is_valid_but_not_deployable():
    data = manifest()
    validate_manifest(data)
    with pytest.raises(ConfigSyncError, match="payload is empty"):
        validate_manifest(data, allow_empty=False)


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"api_key": "secret"}, "unsupported payload fields"),
        ({"conversation_config": {"webhook_url": "https://example.com/hook"}}, "secret-like field"),
        ({"conversation_config": {"endpoint": "https://example.com/hook"}}, "outbound URL"),
        ({"conversation_config": {"endpoint": "__REDACTED__"}}, "redacted placeholder"),
    ],
)
def test_validation_rejects_sensitive_config(payload, message):
    with pytest.raises(ConfigSyncError, match=message):
        validate_manifest(manifest(payload=payload))


def test_redaction_handles_nested_make_blueprint_string():
    value = json.dumps({"modules": [{"parameters": {"webhook_url": "https://hooks.example.com/secret"}}]})
    redacted = json.loads(redact(value))
    assert redacted["modules"][0]["parameters"]["webhook_url"] == "__REDACTED__"


def test_elevenlabs_export_uses_get_and_returns_patch_fields(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_123")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    calls = []

    def transport(method, url, headers, body):
        calls.append((method, url, headers, body))
        return {
            "agent_id": "agent_123",
            "name": "Jesse staging",
            "conversation_config": {"agent": {"first_message": "Hello"}},
            "metadata": {"created": 1},
        }

    exported = export_manifest("elevenlabs", "staging", "ELEVENLABS_AGENT_ID", transport)
    assert exported["payload"] == {
        "conversation_config": {"agent": {"first_message": "Hello"}},
        "name": "Jesse staging",
    }
    assert calls[0][0] == "GET"
    assert calls[0][1].endswith("/v1/convai/agents/agent_123")
    assert calls[0][3] is None


def test_make_export_reads_details_and_draft_blueprint(monkeypatch):
    monkeypatch.setenv("MAKE_APPOINTMENT_SCENARIO_ID", "123")
    monkeypatch.setenv("MAKE_API_TOKEN", "test-token")
    monkeypatch.setenv("MAKE_API_BASE_URL", "https://us1.make.com/api/v2")
    calls = []

    def transport(method, url, headers, body):
        calls.append((method, url, headers, body))
        if url.endswith("/blueprint?draft=true"):
            return {"response": {"blueprint": '{"flow":[]}'}}
        return {"scenario": {"name": "Appointment staging", "scheduling": '{"type":"on-demand"}'}}

    exported = export_manifest("make", "staging", "MAKE_APPOINTMENT_SCENARIO_ID", transport)
    assert exported["payload"]["blueprint"] == '{"flow":[]}'
    assert exported["payload"]["name"] == "Appointment staging"
    assert len(calls) == 2
    assert all(call[0] == "GET" for call in calls)


def test_plan_never_exposes_resource_id(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "private-resource-id")
    result = plan(manifest(payload={"name": "Safe name"}))
    assert result["resource_configured"] is True
    assert "private-resource-id" not in json.dumps(result)
    assert result["external_write"] is False


def test_deploy_elevenlabs_patches_only_after_validation(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_123")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    calls = []

    def transport(method, url, headers, body):
        calls.append((method, url, headers, json.loads(body)))
        return {"agent_id": "agent_123"}

    data = manifest(payload={"name": "Jesse staging"})
    validate_manifest(data, allow_empty=False)
    _deploy(data, transport)
    assert calls == [
        (
            "PATCH",
            "https://api.elevenlabs.io/v1/convai/agents/agent_123",
            {"xi-api-key": "test-key", "Content-Type": "application/json"},
            {"name": "Jesse staging"},
        )
    ]


def test_deploy_make_patches_scenario(monkeypatch):
    monkeypatch.setenv("MAKE_APPOINTMENT_SCENARIO_ID", "456")
    monkeypatch.setenv("MAKE_API_TOKEN", "test-token")
    monkeypatch.setenv("MAKE_API_BASE_URL", "https://us1.make.com/api/v2")
    calls = []

    def transport(method, url, headers, body):
        calls.append((method, url, headers, json.loads(body)))
        return {"scenario": {"id": 456}}

    data = manifest("make", payload={"name": "Reschedule staging"})
    validate_manifest(data, allow_empty=False)
    _deploy(data, transport)
    assert calls[0][0:2] == ("PATCH", "https://us1.make.com/api/v2/scenarios/456")
    assert calls[0][3] == {"name": "Reschedule staging"}


@pytest.mark.parametrize(
    "url",
    [
        "http://us1.make.com/api/v2",
        "https://evil.example/api/v2",
        "https://us1.make.com/not-api",
    ],
)
def test_make_base_url_is_restricted(monkeypatch, url):
    monkeypatch.setenv("MAKE_APPOINTMENT_SCENARIO_ID", "456")
    monkeypatch.setenv("MAKE_API_TOKEN", "test-token")
    monkeypatch.setenv("MAKE_API_BASE_URL", url)
    with pytest.raises(ConfigSyncError, match="MAKE_API_BASE_URL"):
        _deploy(manifest("make", payload={"name": "Safe"}), lambda *args: {})
