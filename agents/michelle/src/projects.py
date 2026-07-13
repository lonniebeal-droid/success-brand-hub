from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Project:
    name: str
    status: str = "active"
    task_ids: list[str] = field(default_factory=list)


class ProjectTracker:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    def ensure(self, name: str) -> Project:
        key = name.strip().casefold()
        if not key:
            raise ValueError("project name is required")
        return self.projects.setdefault(key, Project(name.strip()))

    def attach_task(self, project: str, task_id: str) -> None:
        record = self.ensure(project)
        if task_id not in record.task_ids:
            record.task_ids.append(task_id)
