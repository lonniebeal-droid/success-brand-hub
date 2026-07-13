from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable


class DeploymentError(RuntimeError):
    """A safe deployment validation or execution failure."""


@dataclass
class DeploymentAdapter:
    name: str
    required_variables: tuple[str, ...] = ()

    def missing_variables(self, environment: str) -> list[str]:
        if environment == "development":
            return []
        return [name for name in self.required_variables if not os.getenv(name)]

    def validate(self, environment: str, *, approved: bool = False) -> dict[str, Any]:
        if environment not in {"development", "staging", "production"}:
            raise DeploymentError("invalid deployment environment")
        missing = self.missing_variables(environment)
        if environment == "production" and not approved:
            raise DeploymentError("production approval is required")
        return {
            "adapter": self.name,
            "environment": environment,
            "valid": not missing,
            "missing_variables": missing,
            "secrets_redacted": True,
        }

    def deploy(self, environment: str, *, dry_run: bool = True, approved: bool = False) -> dict[str, Any]:
        validation = self.validate(environment, approved=approved)
        # A dry run must remain useful before optional third-party integrations
        # are configured. Report missing configuration, but only block an
        # execution attempt that could otherwise use that integration.
        if not validation["valid"] and not dry_run:
            raise DeploymentError(f"{self.name} configuration is incomplete")
        return {
            **validation,
            "status": (
                "configuration_required"
                if dry_run and not validation["valid"]
                else "planned" if dry_run else "simulated"
            ),
            "dry_run": dry_run,
            "external_action": False,
            "rollback_metadata": {"captured": False, "reason": "adapter is network-free"},
        }

    @staticmethod
    def redact(values: Iterable[str]) -> list[str]:
        return ["[configured]" if value else "[missing]" for value in values]
