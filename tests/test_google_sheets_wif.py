import json
from pathlib import Path

import pytest

from agents.jessie.integrations.google_sheets_adapter import GoogleSheetsAdapter, GoogleSheetsSandboxError, SHEETS_SCOPE


class FakeCredentials:
    token = "short-lived-test-token"
    def refresh(self, request): pass


def test_adc_uses_default_credentials_with_sheets_scope(monkeypatch):
    captured = {}
    def fake_default(*, scopes):
        captured["scopes"] = scopes
        return FakeCredentials(), "detected-project"
    monkeypatch.setattr("google.auth.default", fake_default)
    adapter = GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", auth_mode="adc")
    credentials, project = adapter._load_credentials()
    assert isinstance(credentials, FakeCredentials)
    assert captured["scopes"] == [SHEETS_SCOPE]
    assert project == "detected-project"


def test_adc_unavailable_fails_safely(monkeypatch):
    monkeypatch.setattr("google.auth.default", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("metadata unavailable")))
    adapter = GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", auth_mode="adc")
    with pytest.raises(GoogleSheetsSandboxError, match="credentials are unavailable"):
        adapter.validate_startup()


def test_json_fallback_is_environment_only_and_validated(monkeypatch):
    info = {"client_email": "fallback@example.invalid", "private_key": "test-only", "token_uri": "https://oauth2.googleapis.com/token", "project_id": "sandbox-project"}
    monkeypatch.setattr("google.oauth2.service_account.Credentials.from_service_account_info", lambda supplied, scopes: FakeCredentials())
    adapter = GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", json.dumps(info), auth_mode="json")
    credentials, project = adapter._load_credentials()
    assert isinstance(credentials, FakeCredentials) and project == "sandbox-project"
    with pytest.raises(GoogleSheetsSandboxError, match="missing or invalid"):
        GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", "not-json", auth_mode="json").validate_startup()


def test_status_exposes_only_safe_fields(monkeypatch):
    monkeypatch.setattr("google.auth.default", lambda **kwargs: (FakeCredentials(), "secret-project"))
    adapter = GoogleSheetsAdapter(True, "sandbox", "A_valid_sandbox_spreadsheet_123", "Sandbox Leads", auth_mode="adc", project_id="private-project")
    status = adapter.status()
    assert status == {"enabled": True, "mode": "sandbox", "auth_mode": "adc", "credentials_available": True}
    rendered = json.dumps(status)
    assert "private-project" not in rendered and "spreadsheet" not in rendered and "service" not in rendered


def test_mock_disabled_and_defaults_never_load_credentials(monkeypatch):
    monkeypatch.setattr("google.auth.default", lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not load ADC")))
    assert GoogleSheetsAdapter(False, "mock", auth_mode="adc").status()["credentials_available"] is False
    assert GoogleSheetsAdapter(True, "mock", auth_mode="mock").test_connection()["status"] == "mock"
    env = Path(".env.example").read_text()
    assert "GOOGLE_SHEETS_SANDBOX_ENABLED=false" in env
    assert "GOOGLE_SHEETS_MODE=mock" in env
    assert "GOOGLE_AUTH_MODE=adc" in env


def test_staging_workflow_uses_oidc_without_json_key_handling():
    workflow = Path(".github/workflows/deploy-staging.yml").read_text()
    assert "id-token: write" in workflow
    assert "google-github-actions/auth@v3" in workflow
    assert "vars.GCP_WORKLOAD_IDENTITY_PROVIDER" in workflow
    assert "vars.GCP_SERVICE_ACCOUNT" in workflow
    assert "vars.GCP_PROJECT_ID" in workflow
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" not in workflow
    assert "JESSE_GOOGLE_CREDENTIALS_JSON" not in workflow
