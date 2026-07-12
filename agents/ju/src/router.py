from __future__ import annotations

from core.registry import AgentRegistry


class TaskRouter:
    ROUTES = {
        "call": "jessie", "appointment": "jessie", "intake": "jessie",
        "content": "content", "video": "content", "social": "content",
        "lead": "sales", "sale": "sales", "proposal": "sales",
        "invoice": "finance", "budget": "finance", "expense": "finance",
        "workflow": "operations", "project": "michelle", "deadline": "michelle",
        "email": "workspace", "calendar": "workspace", "drive": "workspace",
    }

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def route(self, description: str) -> str:
        normalized = description.casefold()
        for keyword, agent in self.ROUTES.items():
            if keyword in normalized and self.registry.get(agent):
                return agent
        return "michelle" if self.registry.get("michelle") else "ju"
