from pathlib import Path


WORKFLOW = Path(".github/workflows/content-vertex-controlled-pilot.yml")


def test_vertex_pilot_is_staging_only_and_bounded() -> None:
    content = WORKFLOW.read_text()
    assert "workflow_dispatch" in content
    assert "environment: staging" in content
    assert "id-token: write" in content
    assert "google-github-actions/auth@v3" in content
    assert "CONTENT_GENERATION_MODE: vertex" in content
    assert "CONTENT_STORAGE_MODE: gcs" in content
    assert "--quantity 1" in content
    assert "requires_human_approval" in content
    assert "actions/upload-artifact@v4" in content
    assert "retention-days: 7" in content
    assert "Approval must be recorded outside this package" in content
    assert "Publishing: disabled" in content
    assert "deploy-production" not in content
    assert "allow-unauthenticated" not in content
    assert "service_account_json" not in content.casefold()
