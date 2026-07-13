import json

import pytest

from agents.jessie.cli import build_parser
from agents.jessie.deployment.base import DeploymentAdapter, DeploymentError
from agents.jessie.deployment.orchestrator import DeploymentBlocked, DeploymentOrchestrator


SHA = "90ee3e101c73aa8ed34fec3206dfdf975c9d9af7"


@pytest.fixture()
def manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"commit_sha": "UNDEPLOYED", "rollback_target": None}), encoding="utf-8")
    return path


def test_dry_run_has_no_external_action(manifest):
    result = DeploymentOrchestrator(manifest, adapters=[]).deploy("development", SHA, dry_run=True, tests_passed=True)
    assert result["status"] == "validated"
    assert result["external_action"] is False


def test_dry_run_reports_missing_staging_secrets_without_external_action(manifest):
    adapter = DeploymentAdapter("example", ("JESSE_MISSING_SECRET",))
    result = DeploymentOrchestrator(manifest, [adapter]).deploy("staging", SHA, dry_run=True, tests_passed=True)
    assert result["adapters"][0]["valid"] is False
    assert result["adapters"][0]["status"] == "configuration_required"
    assert result["external_action"] is False


def test_missing_secrets_block_non_dry_run_staging(manifest):
    adapter = DeploymentAdapter("example", ("JESSE_MISSING_SECRET",))
    with pytest.raises(DeploymentError, match="incomplete"):
        DeploymentOrchestrator(manifest, [adapter]).deploy("staging", SHA, dry_run=False, tests_passed=True)


def test_staging_validates_with_configured_secret(manifest, monkeypatch):
    monkeypatch.setenv("JESSE_TEST_SECRET", "not-logged")
    adapter = DeploymentAdapter("example", ("JESSE_TEST_SECRET",))
    result = DeploymentOrchestrator(manifest, [adapter]).deploy("staging", SHA, tests_passed=True)
    assert result["adapters"][0]["valid"] is True
    assert "not-logged" not in json.dumps(result)


def test_production_requires_all_approvals(manifest):
    with pytest.raises(DeploymentBlocked, match="production gates"):
        DeploymentOrchestrator(manifest, []).deploy("production", SHA, tests_passed=True)


def test_failed_tests_block_every_deployment(manifest):
    with pytest.raises(DeploymentBlocked, match="passing tests"):
        DeploymentOrchestrator(manifest, []).deploy("staging", SHA, tests_passed=False)


def test_failed_staging_blocks_production(manifest):
    with pytest.raises(DeploymentBlocked, match="staging deployment"):
        DeploymentOrchestrator(manifest, []).deploy(
            "production", SHA, tests_passed=True, staging_succeeded=False,
            verification_completed=True, approved=True, backup_recorded=True, rollback_target="2301a98"
        )


def test_rollback_metadata_and_approval(manifest):
    orchestrator = DeploymentOrchestrator(manifest, [])
    with pytest.raises(DeploymentBlocked, match="approval"):
        orchestrator.rollback(SHA)
    assert orchestrator.rollback(SHA, approved=True)["target_sha"] == SHA


@pytest.mark.parametrize("bad_sha", ["main", "123", "not-a-sha!", ""])
def test_invalid_commit_sha_is_rejected(manifest, bad_sha):
    with pytest.raises(DeploymentBlocked, match="invalid"):
        DeploymentOrchestrator(manifest, []).deploy("development", bad_sha, tests_passed=True)


def test_invalid_environment_is_rejected():
    with pytest.raises(DeploymentError, match="invalid"):
        DeploymentAdapter("test").deploy("live", approved=True)


def test_cli_exposes_controlled_deployment_commands():
    parser = build_parser()
    assert parser.parse_args(["deploy-status"]).command == "deploy-status"
    assert parser.parse_args(["verify-staging", "--commit-sha", SHA]).command == "verify-staging"
    production = parser.parse_args(["deploy-production", "--commit-sha", SHA, "--rollback-sha", "2301a98"])
    assert production.confirm_production is False


def test_production_workflow_is_manual_only():
    workflow = open(".github/workflows/deploy-production.yml", encoding="utf-8").read()
    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "environment: production" in workflow
