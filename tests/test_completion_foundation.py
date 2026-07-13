from fastapi.testclient import TestClient

from core.auth import create_user
from core.content_system import SuccessBrandContentSystem
from core.database.database import Database
from core.memory.persistent import PersistentMemoryEngine
from core.notifications import NotificationService
from core.platform_api import create_app


def test_semantic_search_is_operational(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'memory.db'}")
    db.migrate()
    memory = PersistentMemoryEngine(db)
    first = memory.remember("content", "anxiety grounding exercise")
    memory.remember("sales", "proposal follow up")
    result = memory.semantic_search("anxiety exercise")
    assert result["available"] is True
    assert result["provider"] == "local-token-cosine-v1"
    assert result["results"][0]["id"] == first.id


def test_external_notifications_fail_closed(tmp_path, monkeypatch):
    db = Database(f"sqlite:///{tmp_path / 'notifications.db'}")
    db.migrate()
    service = NotificationService(db)
    assert service.send("masked", "test", "email").status == "disabled"
    monkeypatch.setenv("SMS_DELIVERY_MODE", "mock")
    assert service.send("masked", "test", "sms").status == "mock"


def test_content_pack_is_review_only():
    pack = SuccessBrandContentSystem().create_pack("emotional burnout")
    assert pack["status"] == "draft"
    assert pack["human_review_required"] is True
    assert pack["format"].startswith("9:16")


def test_delegation_and_content_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "completion-test-secret-123456789")
    db = Database(f"sqlite:///{tmp_path / 'api.db'}")
    db.migrate()
    with db.session() as session:
        create_user(session, "manager", "manager-password", "manager")
    client = TestClient(create_app(db))
    token = client.post("/login", json={"username": "manager", "password": "manager-password"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    delegated = client.post("/orchestration/delegate", headers=headers, json={"objective": "Create a depression content campaign"})
    assert delegated.status_code == 201
    assert delegated.json()["owner"] == "content"
    assert delegated.json()["human_approval_required"] is True
    pack = client.post("/content/packs", headers=headers, json={"topic": "depression education"})
    assert pack.status_code == 201 and pack.json()["status"] == "draft"
