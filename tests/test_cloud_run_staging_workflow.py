from pathlib import Path


WORKFLOW = Path(".github/workflows/deploy-cloud-run-staging.yml")


def test_cloud_run_staging_is_private_and_tightly_scaled() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "environment: staging" in workflow
    assert "id-token: write" in workflow
    assert "google-github-actions/auth@v3" in workflow
    assert '--no-allow-unauthenticated' in workflow
    assert '--service-account "$GCP_SERVICE_ACCOUNT"' in workflow
    assert '--min-instances 0' in workflow
    assert '--max-instances 1' in workflow
    assert '--cpu 1' in workflow
    assert '--memory 512Mi' in workflow
    assert "--allow-unauthenticated" not in workflow
    assert "--gpu" not in workflow
    assert "remove-iam-policy-binding" in workflow
    assert "--member allUsers" in workflow
    assert 'public_status' in workflow
    assert '"401"' in workflow and '"403"' in workflow


def test_cloud_run_staging_keeps_integrations_disabled() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    for setting in (
        "JESSE_TWILIO_ENABLED=false",
        "JESSE_ELEVENLABS_ENABLED=false",
        "JESSE_GOOGLE_CALENDAR_ENABLED=false",
        "JESSE_GMAIL_ENABLED=false",
        "JESSE_GOOGLE_SHEETS_ENABLED=false",
        "JESSE_N8N_ENABLED=false",
    ):
        assert setting in workflow
