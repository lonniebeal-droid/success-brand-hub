from __future__ import annotations

from dataclasses import dataclass

from core.runtime.queue import PersistentTaskQueue


ROUTES = {
    "content": "content",
    "campaign": "content",
    "lead": "sales",
    "proposal": "sales",
    "research": "research",
    "invoice": "finance",
    "budget": "finance",
    "workflow": "automation",
    "calendar": "workspace",
    "email": "workspace",
    "intake": "jessie",
    "appointment": "jessie",
}


@dataclass(frozen=True)
class DelegationDecision:
    owner: str
    reason: str


class AgentOrchestrator:
    """Routes approved work to one specialist without activating external providers."""

    def __init__(self, queue: PersistentTaskQueue) -> None:
        self.queue = queue

    def decide(self, objective: str) -> DelegationDecision:
        normalized = objective.casefold()
        for keyword, owner in ROUTES.items():
            if keyword in normalized:
                return DelegationDecision(owner, f"matched:{keyword}")
        return DelegationDecision("michelle", "default:operations-review")

    def delegate(self, objective: str, payload: dict | None = None, priority: int = 5):
        decision = self.decide(objective)
        task = self.queue.enqueue(
            title=objective,
            owner=decision.owner,
            payload={**(payload or {}), "delegation_reason": decision.reason, "human_approval_required": True},
            priority=priority,
        )
        return task, decision
