from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class Task:
    title: str
    owner: str
    priority: int = 5
    project: str = "general"
    id: str = ""
    status: str = "open"
    created_at: str = ""

    def __post_init__(self) -> None:
        self.id = self.id or str(uuid.uuid4())
        self.created_at = self.created_at or datetime.now(timezone.utc).isoformat()


class TaskManager:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def create(self, title: str, owner: str, priority: int = 5, project: str = "general") -> Task:
        if not title.strip() or not owner.strip() or not 1 <= priority <= 10:
            raise ValueError("valid title, owner, and priority are required")
        task = Task(title.strip(), owner.strip(), priority, project.strip() or "general")
        self.tasks[task.id] = task
        return task

    def update_status(self, task_id: str, status: str) -> Task:
        if task_id not in self.tasks:
            raise KeyError("task not found")
        self.tasks[task_id].status = status
        return self.tasks[task_id]

    def snapshot(self) -> list[dict[str, object]]:
        return [asdict(task) for task in self.tasks.values()]
