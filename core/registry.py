from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentRecord:
    name: str
    path: str
    documented: bool
    runtime_available: bool
    status: str


class AgentRegistry:
    """Discovers agent folders without importing or executing agent code."""

    def __init__(self, agents_path: str | Path = "agents") -> None:
        self.agents_path = Path(agents_path)
        self._agents: dict[str, AgentRecord] = {}

    def discover(self) -> dict[str, AgentRecord]:
        discovered: dict[str, AgentRecord] = {}
        if not self.agents_path.exists():
            self._agents = discovered
            return discovered
        for path in sorted(self.agents_path.iterdir()):
            if not path.is_dir() or path.name.startswith((".", "__")):
                continue
            documented = (path / "README.md").exists()
            runtime = (path / "src").is_dir()
            discovered[path.name] = AgentRecord(
                name=path.name,
                path=str(path),
                documented=documented,
                runtime_available=runtime,
                status="ready" if runtime else "planned",
            )
        self._agents = discovered
        return dict(discovered)

    def get(self, name: str) -> AgentRecord | None:
        if not self._agents:
            self.discover()
        return self._agents.get(name.lower())

    def all(self) -> list[AgentRecord]:
        if not self._agents:
            self.discover()
        return list(self._agents.values())

    def snapshot(self) -> list[dict[str, object]]:
        return [asdict(agent) for agent in self.all()]
