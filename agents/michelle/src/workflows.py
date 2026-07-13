from __future__ import annotations


class WorkflowEngine:
    def __init__(self) -> None:
        self.workflows: dict[str, list[str]] = {}

    def register(self, name: str, steps: list[str]) -> None:
        if not name.strip() or not steps:
            raise ValueError("workflow name and steps are required")
        self.workflows[name] = list(steps)

    def plan(self, name: str) -> list[dict[str, str]]:
        if name not in self.workflows:
            raise KeyError("workflow not found")
        return [{"step": step, "status": "pending"} for step in self.workflows[name]]
