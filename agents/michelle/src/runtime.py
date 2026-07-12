from __future__ import annotations

from core.messaging import Message, MessageBus
from core.registry import AgentRegistry
from .notifications import NotificationCenter
from .projects import ProjectTracker
from .tasks import TaskManager
from .workflows import WorkflowEngine


class MichelleRuntime:
    def __init__(self, agents_path="agents", messages: MessageBus | None = None) -> None:
        self.registry = AgentRegistry(agents_path)
        self.registry.discover()
        self.messages = messages or MessageBus()
        self.tasks = TaskManager()
        self.projects = ProjectTracker()
        self.workflows = WorkflowEngine()
        self.notifications = NotificationCenter()

    def create_task(self, title: str, owner: str, priority: int = 5, project: str = "general"):
        if not self.registry.get(owner):
            raise ValueError("owner is not a registered agent")
        task = self.tasks.create(title, owner, priority, project)
        self.projects.attach_task(project, task.id)
        self.messages.send_message(Message("michelle", owner, "task.assigned", {"task_id": task.id, "title": title}, priority))
        if priority <= 2:
            self.notifications.escalate(f"High-priority task assigned: {title}")
        return task

    def status(self) -> dict[str, object]:
        counts: dict[str, int] = {}
        for task in self.tasks.tasks.values():
            counts[task.status] = counts.get(task.status, 0) + 1
        return {"agent": "michelle", "status": "ready", "task_counts": counts, "projects": len(self.projects.projects), "notifications": len(self.notifications.notifications)}
