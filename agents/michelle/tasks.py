import uuid
from dataclasses import asdict, dataclass


@dataclass
class Task:
    title: str
    assignee: str
    id: str = ""
    status: str = "open"
    notes: str = ""

    def __post_init__(self):
        self.id = self.id or str(uuid.uuid4())


class TaskManager:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def create_task(self, title: str, assignee: str) -> Task:
        task = Task(title, assignee)
        self.tasks[task.id] = task
        return task

    def route_task(self, task: Task) -> str:
        return task.assignee
