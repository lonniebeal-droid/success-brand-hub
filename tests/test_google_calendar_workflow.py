from pathlib import Path


WORKFLOW = Path(".github/workflows/google-calendar-controlled-write.yml")


def test_calendar_workflow_is_manual_wif_and_fake_only():
    content = WORKFLOW.read_text()
    assert "workflow_dispatch" in content
    assert "environment: staging" in content
    assert "id-token: write" in content
    assert "google-github-actions/auth@v3" in content
    assert "calendar.events" in content
    assert "JESSE_GOOGLE_STAGING_CALENDAR_ID" in content
    assert "SuccessBrand Sandbox Appointment Test" in content
    assert '"attendees":' not in content
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" not in content
    assert "sandbox-calendar-controlled-v1" in content
    assert "duplicate_request_id" in content
