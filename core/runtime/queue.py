from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from core.database.database import Database
from core.database.models import Task


class PersistentTaskQueue:
    def __init__(self, database: Database) -> None:
        self.database = database

    def enqueue(self, title: str, owner: str, payload: dict | None = None, priority: int = 5, scheduled_for=None, max_attempts: int = 3) -> Task:
        task = Task(id=str(uuid.uuid4()), title=title, owner=owner, payload=payload or {}, priority=priority, scheduled_for=scheduled_for, max_attempts=max_attempts)
        with self.database.session() as session:
            session.add(task)
            session.commit()
        return task

    def claim(self, owner: str | None = None) -> Task | None:
        now = datetime.now(timezone.utc)
        with self.database.session() as session:
            query = select(Task).where(Task.status.in_(["queued", "retry"]), (Task.scheduled_for.is_(None)) | (Task.scheduled_for <= now)).order_by(Task.priority.asc(), Task.created_at.asc())
            if owner:
                query = query.where(Task.owner == owner)
            task = session.scalar(query.limit(1))
            if not task:
                return None
            task.status = "running"
            task.attempts += 1
            session.commit()
            return task

    def complete(self, task_id: str, result: dict, duration: float) -> Task:
        with self.database.session() as session:
            task = session.get(Task, task_id)
            task.status, task.result, task.duration_seconds = "completed", result, duration
            task.completed_at = datetime.now(timezone.utc)
            session.commit()
            return task

    def fail(self, task_id: str, error: str) -> Task:
        with self.database.session() as session:
            task = session.get(Task, task_id)
            task.error = error[:500]
            task.status = "retry" if task.attempts < task.max_attempts else "failed"
            session.commit()
            return task

    def depth(self) -> int:
        with self.database.session() as session:
            return len(session.scalars(select(Task).where(Task.status.in_(["queued", "retry"]))).all())
