from __future__ import annotations

import uuid

from sqlalchemy import select

from core.database.database import Database
from core.database.models import Memory


class PersistentMemoryEngine:
    def __init__(self, database: Database) -> None:
        self.database = database

    def remember(self, namespace: str, content: str, kind: str = "long_term", conversation_id: str | None = None, metadata: dict | None = None) -> Memory:
        record = Memory(id=str(uuid.uuid4()), namespace=namespace, content=content, kind=kind, conversation_id=conversation_id, metadata_json=metadata or {})
        with self.database.session() as session:
            session.add(record)
            session.commit()
        return record

    def search(self, query: str, namespace: str | None = None, limit: int = 20) -> list[Memory]:
        with self.database.session() as session:
            statement = select(Memory).where(Memory.content.ilike(f"%{query}%"))
            if namespace:
                statement = statement.where(Memory.namespace == namespace)
            return list(session.scalars(statement.order_by(Memory.created_at.desc()).limit(limit)).all())

    def conversation(self, conversation_id: str) -> list[Memory]:
        with self.database.session() as session:
            return list(session.scalars(select(Memory).where(Memory.conversation_id == conversation_id).order_by(Memory.created_at)).all())

    def summarize(self, conversation_id: str, max_characters: int = 500) -> str:
        combined = " ".join(item.content for item in self.conversation(conversation_id))
        return combined[:max_characters]

    def semantic_search(self, query: str, limit: int = 10) -> dict:
        return {"available": False, "provider": "vector-placeholder", "fallback": [item.id for item in self.search(query, limit=limit)]}
