from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from core.messaging import Message, MessageBus
from .router import TaskRouter


@dataclass
class Delegation:
    description: str
    assignee: str
    priority: int
    id: str = ""
    status: str = "delegated"
    created_at: str = ""

    def __post_init__(self) -> None:
        self.id = self.id or str(uuid.uuid4())
        self.created_at = self.created_at or datetime.now(timezone.utc).isoformat()


class OrchestrationEngine:
    def __init__(self, router: TaskRouter, bus: MessageBus) -> None:
        self.router, self.bus = router, bus
        self.delegations: dict[str, Delegation] = {}

    def delegate(self, description: str, priority: int = 5) -> Delegation:
        assignee = self.router.route(description)
        item = Delegation(description, assignee, priority)
        self.delegations[item.id] = item
        self.bus.send_message(Message("ju", assignee, "task.delegated", {"task_id": item.id, "description": description}, priority))
        return item

    def report(self) -> dict[str, object]:
        by_agent: dict[str, int] = {}
        for item in self.delegations.values():
            by_agent[item.assignee] = by_agent.get(item.assignee, 0) + 1
        return {"total": len(self.delegations), "by_agent": by_agent, "items": [asdict(item) for item in self.delegations.values()]}
