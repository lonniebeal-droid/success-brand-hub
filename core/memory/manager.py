from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    namespace: str
    content: str
    metadata: dict[str, Any]
    id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        self.id = self.id or str(uuid.uuid4())
        self.created_at = self.created_at or datetime.now(timezone.utc).isoformat()


class MemoryManager:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._entries: list[MemoryEntry] = []
        if self.path and self.path.exists():
            self._entries = [MemoryEntry(**item) for item in json.loads(self.path.read_text(encoding="utf-8"))]

    def remember(self, namespace: str, content: str, metadata: dict[str, Any] | None = None) -> MemoryEntry:
        if not namespace.strip() or not content.strip():
            raise ValueError("namespace and content are required")
        entry = MemoryEntry(namespace.strip(), content.strip(), metadata or {})
        self._entries.append(entry)
        self._save()
        return entry

    def search(self, query: str, namespace: str | None = None, limit: int = 20) -> list[MemoryEntry]:
        needle = query.casefold()
        matches = [entry for entry in self._entries if (namespace is None or entry.namespace == namespace) and needle in entry.content.casefold()]
        return matches[:limit]

    def list(self, namespace: str | None = None) -> list[MemoryEntry]:
        return [entry for entry in self._entries if namespace is None or entry.namespace == namespace]

    def _save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(item) for item in self._entries], indent=2), encoding="utf-8")


class SharedMemory(MemoryManager):
    """Namespace-aware memory shared by multiple local runtimes."""


class VectorMemoryPlaceholder:
    available = False

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        return []
