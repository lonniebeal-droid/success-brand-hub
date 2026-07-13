from dataclasses import asdict

from .config import AgentConfig, load_config
from .memory import MemoryStore
from .tasks import TaskManager


class MichelleAgent:
    """Compatibility facade backed by the Michelle v1 local task store."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or load_config()
        self.memory = MemoryStore(self.config.memory_file)
        self.tasks = TaskManager()

    def create_task(self, title: str, assignee: str):
        task = self.tasks.create_task(title, assignee)
        self.memory.data["tasks"].append(asdict(task))
        self.memory.save()
        return task

    def complete_task(self, task_id: str, notes: str = ""):
        task = self.tasks.tasks[task_id]
        task.status, task.notes = "completed", notes
        self.memory.data["tasks"] = [asdict(item) for item in self.tasks.tasks.values()]
        self.memory.save()
        return task

    def log_activity(self, message: str) -> None:
        self.memory.data["activity_log"].append(message)
        self.memory.save()
