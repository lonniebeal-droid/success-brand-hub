from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from core.database.models import Task
from core.runtime.queue import PersistentTaskQueue


class RuntimeScheduler:
    def __init__(self, queue: PersistentTaskQueue) -> None:
        self.queue = queue

    def due(self) -> list[Task]:
        now = datetime.now(timezone.utc)
        with self.queue.database.session() as session:
            return list(session.scalars(select(Task).where(Task.status == "queued", Task.scheduled_for.is_not(None), Task.scheduled_for <= now)).all())
