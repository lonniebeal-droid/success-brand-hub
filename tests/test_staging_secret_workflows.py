from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_staging_secret_bootstrap_uses_wif_and_never_echoes_secret():
    content = (ROOT / ".github/workflows/bootstrap-jessie-staging-secret.yml").read_text()
    assert "contents: read" in content
    assert "id-token: write" in content
    assert "google-github-actions/auth@v3" in content
    assert "secrets.token_urlsafe" in content
    assert "roles/secretmanager.secretAccessor" in content
    assert "service-account-key" not in content


def test_application_write_is_staging_only_and_synthetic():
    content = (ROOT / ".github/workflows/google-sheets-application-controlled-write.yml").read_text()
    assert "environment: staging" in content
    assert "success-brand-jesse-staging" in content
    assert "app-controlled-${GITHUB_RUN_ID}" in content
    assert "5550000199" in content
    assert "test@example.com" in content
    assert "versions access latest" in content
    assert "token_format: id_token" in content
    assert "id_token_audience: ${{ env.SERVICE_URL }}" in content
    assert "print-identity-token" not in content


def test_cloud_run_reads_admin_token_from_secret_manager():
    content = (ROOT / ".github/workflows/deploy-cloud-run-staging.yml").read_text()
    assert "--set-secrets \"JESSE_ADMIN_TOKEN=jesse-staging-admin-token:latest\"" in content
