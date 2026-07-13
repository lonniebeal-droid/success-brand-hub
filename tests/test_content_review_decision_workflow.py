from pathlib import Path


WORKFLOW = Path(".github/workflows/content-review-decision.yml")


def test_review_decision_workflow_is_manual_and_non_publishing() -> None:
    content = WORKFLOW.read_text()
    assert "workflow_dispatch" in content
    assert "archive_uri:" in content
    assert "- approve" in content
    assert "- reject" in content
    assert "review_note:" in content
    assert "environment: staging" in content
    assert "id-token: write" in content
    assert "google-github-actions/auth@v3" in content
    assert "if_generation_match=0" in content
    assert '"publishing_enabled": False' in content
    assert '"publishing_authorized": False' in content
    assert "retention-days: 90" in content
    assert "deploy-production" not in content
    assert "allow-unauthenticated" not in content
    assert "service_account_json" not in content.casefold()
