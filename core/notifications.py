from __future__ import annotations

import uuid

from core.database.database import Database
from core.database.models import Notification


class NotificationService:
    CHANNELS = {"dashboard", "internal", "email", "sms"}

    def __init__(self, database: Database) -> None:
        self.database = database

    def send(self, recipient: str, message: str, channel: str = "internal") -> Notification:
        if channel not in self.CHANNELS:
            raise ValueError("unsupported notification channel")
        status = "placeholder" if channel in {"email", "sms"} else "queued"
        record = Notification(id=str(uuid.uuid4()), recipient=recipient, message=message, channel=channel, status=status)
        with self.database.session() as session:
            session.add(record)
            session.commit()
        return record

    def task_alert(self, owner: str, task_title: str) -> Notification:
        return self.send(owner, f"Task alert: {task_title}", "dashboard")
