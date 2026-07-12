from __future__ import annotations

import heapq
import itertools
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Message:
    sender: str
    recipient: str
    subject: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MessageBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[tuple[int, int, Message]]] = {}
        self._sequence = itertools.count()

    def send_message(self, message: Message) -> str:
        if not 1 <= message.priority <= 10:
            raise ValueError("priority must be between 1 and 10")
        queue = self._queues.setdefault(message.recipient, [])
        heapq.heappush(queue, (message.priority, next(self._sequence), message))
        return message.id

    def receive_message(self, recipient: str) -> Message | None:
        queue = self._queues.get(recipient, [])
        return heapq.heappop(queue)[2] if queue else None

    def broadcast(self, sender: str, recipients: list[str], subject: str, payload: dict[str, Any] | None = None, priority: int = 5) -> list[str]:
        return [self.send_message(Message(sender, recipient, subject, payload or {}, priority)) for recipient in recipients if recipient != sender]

    def pending(self, recipient: str) -> int:
        return len(self._queues.get(recipient, []))
