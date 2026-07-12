from __future__ import annotations

import time
from typing import Callable

from core.runtime.queue import PersistentTaskQueue


class BackgroundWorker:
    def __init__(self, queue: PersistentTaskQueue, handlers: dict[str, Callable[[dict], dict]] | None = None) -> None:
        self.queue = queue
        self.handlers = handlers or {}
        self.status = "idle"
        self.last_heartbeat = time.time()

    def heartbeat(self) -> dict:
        self.last_heartbeat = time.time()
        return {"status": self.status, "timestamp": self.last_heartbeat}

    def process_once(self, owner: str | None = None):
        task = self.queue.claim(owner)
        if not task:
            return None
        self.status = "running"
        started = time.perf_counter()
        try:
            handler = self.handlers.get(task.owner, lambda payload: {"accepted": True, "payload": payload})
            result = handler(task.payload)
            return self.queue.complete(task.id, result, time.perf_counter() - started)
        except Exception as exc:
            return self.queue.fail(task.id, str(exc))
        finally:
            self.status = "idle"
            self.heartbeat()
