from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import DeploymentAdapter, DeploymentError
from .elevenlabs import ElevenLabsDeployment
from .google import GoogleDeployment
from .n8n import N8NDeployment
from .twilio import TwilioDeployment


class DeploymentBlocked(DeploymentError):
    """Raised when a required deployment gate is not satisfied."""


class DeploymentOrchestrator:
    def __init__(self, manifest_path: str | Path = "agents/jessie/deployment/manifest.json", adapters: list[DeploymentAdapter] | None = None) -> None:
        self.manifest_path = Path(manifest_path)
        self.adapters = adapters or [ElevenLabsDeployment(), TwilioDeployment(), N8NDeployment(), GoogleDeployment()]

    @staticmethod
    def validate_sha(commit_sha: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{7,40}", commit_sha):
            raise DeploymentBlocked("commit SHA is invalid")

    def load_manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def status(self) -> dict[str, Any]:
        return self.load_manifest()

    def deploy(
        self,
        environment: str,
        commit_sha: str,
        *,
        dry_run: bool = True,
        tests_passed: bool = False,
        staging_succeeded: bool = False,
        verification_completed: bool = False,
        approved: bool = False,
        backup_recorded: bool = False,
        rollback_target: str | None = None,
    ) -> dict[str, Any]:
        self.validate_sha(commit_sha)
        if not tests_passed:
            raise DeploymentBlocked("passing tests are required")
        if environment == "production":
            gates = {
                "staging deployment": staging_succeeded,
                "controlled verification": verification_completed,
                "manual approval": approved,
                "configuration backup": backup_recorded,
                "rollback target": bool(rollback_target),
            }
            missing = [name for name, passed in gates.items() if not passed]
            if missing:
                raise DeploymentBlocked("production gates missing: " + ", ".join(missing))
        results = [adapter.deploy(environment, dry_run=dry_run, approved=approved) for adapter in self.adapters]
        return {
            "environment": environment,
            "commit_sha": commit_sha,
            "dry_run": dry_run,
            "status": "validated" if dry_run else "simulated",
            "external_action": False,
            "adapters": results,
            "rollback_target": rollback_target,
        }

    def rollback(self, commit_sha: str, *, approved: bool = False) -> dict[str, Any]:
        self.validate_sha(commit_sha)
        if not approved:
            raise DeploymentBlocked("manual rollback approval is required")
        return {"status": "planned", "target_sha": commit_sha, "external_action": False, "approved": True}
