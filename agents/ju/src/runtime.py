from __future__ import annotations

from pathlib import Path

from core.memory import SharedMemory
from core.messaging import MessageBus
from core.registry import AgentRegistry
from .events import EventDispatcher
from .orchestration import OrchestrationEngine
from .router import TaskRouter


class JuRuntime:
    def __init__(self, agents_path: str | Path = "agents", memory_path: str | Path | None = None) -> None:
        self.registry = AgentRegistry(agents_path)
        self.registry.discover()
        self.memory = SharedMemory(memory_path)
        self.messages = MessageBus()
        self.events = EventDispatcher()
        self.engine = OrchestrationEngine(TaskRouter(self.registry), self.messages)

    def delegate(self, description: str, priority: int = 5):
        item = self.engine.delegate(description, priority)
        self.memory.remember("ju.delegations", f"{item.id}: {description}", {"assignee": item.assignee})
        self.events.dispatch("task.delegated", {"task_id": item.id, "assignee": item.assignee})
        return item

    def status(self) -> dict[str, object]:
        return {"agent": "ju", "status": "ready", "agents": self.registry.snapshot(), "delegations": self.engine.report()}
