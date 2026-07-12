from __future__ import annotations

import os
import resource

from sqlalchemy import func, select

from core.database.models import Task
from core.runtime.queue import PersistentTaskQueue
from core.runtime.worker import BackgroundWorker


class SystemMonitor:
    def __init__(self, queue: PersistentTaskQueue, workers: list[BackgroundWorker] | None = None) -> None:
        self.queue, self.workers = queue, workers or []

    def snapshot(self) -> dict:
        with self.queue.database.session() as session:
            total = session.scalar(select(func.count()).select_from(Task)) or 0
            failed = session.scalar(select(func.count()).select_from(Task).where(Task.status == "failed")) or 0
            average = session.scalar(select(func.avg(Task.duration_seconds)).where(Task.duration_seconds.is_not(None))) or 0
        return {
            "cpu_load": list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
            "memory_max_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "queue_depth": self.queue.depth(),
            "workers": [worker.heartbeat() for worker in self.workers],
            "average_task_duration": float(average),
            "error_rate": failed / total if total else 0.0,
        }
