from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Migration


class Database:
    SCHEMA_VERSION = "0001_platform_v2"

    def __init__(self, url: str | None = None) -> None:
        self.url = url or os.getenv("PLATFORM_DATABASE_URL", "sqlite:///core/data/platform.db")
        if self.url.startswith("sqlite:///"):
            Path(self.url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(self.url, connect_args={"check_same_thread": False} if self.url.startswith("sqlite") else {})
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def migrate(self) -> str:
        Base.metadata.create_all(self.engine)
        with self.session() as session:
            if session.get(Migration, self.SCHEMA_VERSION) is None:
                session.add(Migration(version=self.SCHEMA_VERSION))
                session.commit()
        return self.SCHEMA_VERSION

    def session(self) -> Session:
        return self.session_factory()

    def tables(self) -> list[str]:
        return inspect(self.engine).get_table_names()


_database: Database | None = None


def get_database(url: str | None = None) -> Database:
    global _database
    if url is not None or _database is None:
        _database = Database(url)
        _database.migrate()
    return _database
