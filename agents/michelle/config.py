from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentConfig:
    name: str = "Michelle"
    workspace_root: str = "."
    memory_file: str = "agents/michelle/data/memory.json"
    log_file: str = "agents/michelle/data/activity.log"


def load_config(workspace_root: str = ".") -> AgentConfig:
    root = Path(workspace_root)
    return AgentConfig(workspace_root=str(root), memory_file=str(root / "memory.json"), log_file=str(root / "activity.log"))
