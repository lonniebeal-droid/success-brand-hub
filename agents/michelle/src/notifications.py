from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Notification:
    recipient: str
    message: str
    level: str = "info"


class NotificationCenter:
    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    def notify(self, recipient: str, message: str, level: str = "info") -> Notification:
        note = Notification(recipient, message, level)
        self.notifications.append(note)
        return note

    def escalate(self, message: str, recipient: str = "ju") -> Notification:
        return self.notify(recipient, message, "urgent")
