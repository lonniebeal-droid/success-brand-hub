from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from core.auth import create_user
from core.database.database import Database
from core.database.models import Migration
from core.memory.persistent import PersistentMemoryEngine
from core.notifications import NotificationService
from core.platform_api import create_app
from core.runtime.queue import PersistentTaskQueue
from core.runtime.scheduler import RuntimeScheduler
from core.runtime.worker import BackgroundWorker
from core.scheduling import SchedulingService


@pytest.fixture
def db(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'platform.db'}")
    database.migrate()
    return database


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "test-only-secret-that-is-long-enough-12345")
    with db.session() as session:
        create_user(session, "admin", "secure-test-password", "admin")
        create_user(session, "viewer", "secure-view-password", "viewer")
    return TestClient(create_app(db))


def login(client, username="admin", password="secure-test-password"):
    result = client.post("/login", json={"username": username, "password": password})
    assert result.status_code == 200
    return result.json()


def headers(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_migration_is_idempotent_and_schema_is_complete(db):
    assert db.migrate() == "0001_platform_v2"
    expected = {"agents", "tasks", "messages", "memories", "appointments", "call_logs", "reports", "users", "refresh_tokens", "notifications", "schema_migrations"}
    assert expected <= set(db.tables())
    with db.session() as session:
        assert session.query(Migration).count() == 1


def test_auth_login_refresh_logout_and_me(client):
    tokens = login(client)
    assert client.get("/me", headers=headers(tokens)).json()["role"] == "admin"
    refreshed = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    next_tokens = refreshed.json()
    assert client.post("/logout", json={"refresh_token": next_tokens["refresh_token"]}, headers=headers(next_tokens)).status_code == 200
    assert client.post("/refresh", json={"refresh_token": next_tokens["refresh_token"]}).status_code == 401


def test_api_protection_and_roles(client):
    assert client.get("/health").status_code == 200
    assert client.get("/tasks").status_code == 401
    viewer = login(client, "viewer", "secure-view-password")
    assert client.get("/tasks", headers=headers(viewer)).status_code == 200
    assert client.post("/tasks", json={"title": "No", "owner": "ju"}, headers=headers(viewer)).status_code == 403


def test_queue_worker_retry_and_scheduler(db):
    queue = PersistentTaskQueue(db)
    first = queue.enqueue("Work", "ju", {"value": 2})
    worker = BackgroundWorker(queue, {"ju": lambda payload: {"value": payload["value"] * 2}})
    done = worker.process_once("ju")
    assert done.id == first.id and done.status == "completed" and done.result == {"value": 4}
    queue.enqueue("Retry", "bad", {}, max_attempts=2)
    failing = BackgroundWorker(queue, {"bad": lambda _: (_ for _ in ()).throw(RuntimeError("safe failure"))})
    assert failing.process_once("bad").status == "retry"
    assert failing.process_once("bad").status == "failed"
    future = queue.enqueue("Later", "ju", {}, scheduled_for=datetime.now(timezone.utc) + timedelta(hours=1))
    scheduler = RuntimeScheduler(queue)
    assert future.id not in [item.id for item in scheduler.due()]


def test_memory_notifications_and_scheduling(db):
    memory = PersistentMemoryEngine(db)
    memory.remember("ops", "Important project update", "short_term", "chat-1")
    assert memory.search("project")[0].namespace == "ops"
    assert "Important" in memory.summarize("chat-1")
    assert memory.semantic_search("project")["provider"] == "vector-placeholder"
    notification = NotificationService(db).send("ju", "Task ready", "email")
    assert notification.status == "placeholder"
    scheduling = SchedulingService(db)
    start = datetime.now(timezone.utc) + timedelta(days=1)
    appointment = scheduling.schedule("Review", start, start + timedelta(hours=1))
    assert not scheduling.availability(start, start + timedelta(minutes=30))["available"]
    with pytest.raises(ValueError):
        scheduling.schedule("Conflict", start, start + timedelta(minutes=30))
    moved = scheduling.reschedule(appointment.id, start + timedelta(hours=2), start + timedelta(hours=3))
    assert moved.id == appointment.id


def test_platform_api_tasks_memory_notifications_and_calendar(client):
    auth = headers(login(client))
    task = client.post("/tasks", json={"title": "Route work", "owner": "ju"}, headers=auth)
    assert task.status_code == 201
    assert client.post("/workers/run-once", headers=auth).json()["processed"] is True
    assert client.post("/memory", json={"namespace": "ops", "content": "staging memory"}, headers=auth).status_code == 201
    assert len(client.get("/memory/search?q=staging", headers=auth).json()) == 1
    assert client.post("/notifications", json={"recipient": "ju", "message": "ready"}, headers=auth).status_code == 201
    start = datetime.now(timezone.utc) + timedelta(days=2)
    payload = {"title": "Staging review", "start_at": start.isoformat(), "end_at": (start + timedelta(hours=1)).isoformat()}
    assert client.post("/appointments", json=payload, headers=auth).status_code == 201
    assert client.get("/monitor", headers=auth).status_code == 200
