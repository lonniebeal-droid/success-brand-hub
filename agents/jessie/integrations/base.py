from dataclasses import dataclass
from typing import Any


@dataclass
class SandboxAdapter:
    """Shared, network-free configuration for development adapters."""

    enabled: bool = False
    mode: str = "mock"
    timeout_seconds: float = 2.0
    max_retries: int = 1

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "sandbox": True,
            "network_activity": False,
        }
