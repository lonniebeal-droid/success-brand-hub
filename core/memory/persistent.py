from __future__ import annotations

import uuid
import math
import re
from collections import Counter

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
        tokens = self._tokens(query)
        if not tokens:
            return {"available": True, "provider": "local-token-cosine-v1", "results": []}
        with self.database.session() as session:
            memories = list(session.scalars(select(Memory).order_by(Memory.created_at.desc())).all())
        query_vector = Counter(tokens)
        ranked = []
        for item in memories:
            score = self._cosine(query_vector, Counter(self._tokens(item.content)))
            if score > 0:
                ranked.append({"id": item.id, "namespace": item.namespace, "score": round(score, 6), "content": item.content})
        ranked.sort(key=lambda value: value["score"], reverse=True)
        return {"available": True, "provider": "local-token-cosine-v1", "results": ranked[:limit]}

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", value.casefold())

    @staticmethod
    def _cosine(left: Counter, right: Counter) -> float:
        if not left or not right:
            return 0.0
        numerator = sum(count * right.get(token, 0) for token, count in left.items())
        denominator = math.sqrt(sum(value * value for value in left.values())) * math.sqrt(sum(value * value for value in right.values()))
        return numerator / denominator if denominator else 0.0
