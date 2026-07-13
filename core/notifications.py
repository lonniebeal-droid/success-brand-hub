from __future__ import annotations

import uuid
import os

from core.database.database import Database
from core.database.models import Notification


class NotificationService:
    CHANNELS = {"dashboard", "internal", "email", "sms"}

    def __init__(self, database: Database) -> None:
        self.database = database

    def send(self, recipient: str, message: str, channel: str = "internal") -> Notification:
        if channel not in self.CHANNELS:
            raise ValueError("unsupported notification channel")
        mode = os.getenv(f"{channel.upper()}_DELIVERY_MODE", "disabled").casefold()
        if channel in {"email", "sms"}:
            status = "mock" if mode == "mock" else "disabled"
        else:
            status = "queued"
        record = Notification(id=str(uuid.uuid4()), recipient=recipient, message=message, channel=channel, status=status)
        with self.database.session() as session:
            session.add(record)
            session.commit()
        return record

    def task_alert(self, owner: str, task_title: str) -> Notification:
        return self.send(owner, f"Task alert: {task_title}", "dashboard")
