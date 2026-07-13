from pathlib import Path


def test_controlled_draft_workflow_is_manual_explicit_and_unsent():
    workflow = Path(".github/workflows/gmail-controlled-draft-test.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "environment: staging" in workflow
    assert 'test "$CONFIRMATION" = "CREATE UNSENT DRAFT"' in workflow
    assert "https://oauth2.googleapis.com/token" in workflow
    assert "https://gmail.googleapis.com/gmail/v1/users/me/drafts" in workflow
    assert "users/me/messages/send" not in workflow
    assert "recipient_present: false" in workflow
    assert "email_sent: false" in workflow
    assert "sandbox_feature_enabled: false" in workflow
    assert "GMAIL_OAUTH_REFRESH_TOKEN" in workflow
    assert "message[\"To\"]" not in workflow
    assert "draft_reference" not in workflow


def test_controlled_draft_workflow_does_not_log_sensitive_responses():
    workflow = Path(".github/workflows/gmail-controlled-draft-test.yml").read_text()
    assert "::add-mask::$access_token" in workflow
    assert "cat $response_file" not in workflow
    assert "cat \"$response_file\"" not in workflow
    assert "echo $access_token" not in workflow
    assert "echo \"$access_token\"" not in workflow
