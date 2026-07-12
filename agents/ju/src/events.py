from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class EventDispatcher:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self._subscribers[event].append(handler)

    def dispatch(self, event: str, payload: dict[str, Any]) -> int:
        for handler in self._subscribers[event]:
            handler(payload)
        return len(self._subscribers[event])
