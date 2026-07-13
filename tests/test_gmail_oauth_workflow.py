from pathlib import Path


def test_gmail_oauth_readiness_is_manual_and_does_not_call_gmail():
    workflow = Path(".github/workflows/gmail-oauth-readiness.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "environment: staging" in workflow
    assert "https://oauth2.googleapis.com/token" in workflow
    assert "gmail.googleapis.com" not in workflow
    assert "gmail_api_called: false" in workflow
    assert "draft_created: false" in workflow
    assert "email_sent: false" in workflow
    assert "GMAIL_OAUTH_REFRESH_TOKEN" in workflow
