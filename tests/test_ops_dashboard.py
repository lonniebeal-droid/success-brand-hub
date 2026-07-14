import pytest
from fastapi.testclient import TestClient

from callcenter.service import CallCenterService
from core.auth import create_user
from core.database.database import Database
from core.memory.persistent import PersistentMemoryEngine
from core.platform_api import create_app
from integrations.jesse_status_adapter import get_jesse_status
from integrations.make_adapter import get_make_status


@pytest.fixture
def db(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'ops.db'}")
    database.migrate()
    return database


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "ops-dashboard-test-secret-123456789")
    with db.session() as session:
        create_user(session, "viewer1", "viewer-password", "viewer")
    app = create_app(db)
    api_client = TestClient(app)
    token = api_client.post("/login", json={"username": "viewer1", "password": "viewer-password"}).json()["access_token"]
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    return api_client


def _clear_make_env(monkeypatch):
    for name in ("MAKE_API_BASE_URL", "MAKE_API_TOKEN", "MAKE_STATUS_SCENARIO_ID", "MAKE_POLLER_SCENARIO_ID", "MAKE_DATA_STORE_ID"):
        monkeypatch.delenv(name, raising=False)


def test_make_status_not_configured_without_network_calls(monkeypatch):
    _clear_make_env(monkeypatch)

    def fail_transport(*args, **kwargs):
        raise AssertionError("network call should not happen when unconfigured")

    result = get_make_status(transport=fail_transport)
    assert result["status"] == "not_configured"
    assert result["configured"] is False
    assert result["executions"] == []


def test_make_status_ok_with_fake_transport(monkeypatch):
    _clear_make_env(monkeypatch)
    monkeypatch.setenv("MAKE_API_BASE_URL", "https://us1.make.com/api/v2")
    monkeypatch.setenv("MAKE_API_TOKEN", "test-token")
    monkeypatch.setenv("MAKE_STATUS_SCENARIO_ID", "123")
    monkeypatch.setenv("MAKE_DATA_STORE_ID", "456")
    monkeypatch.setenv("MAKE_DATA_STORE_CURSOR_KEY", "cursor")

    def fake_transport(method, url, headers, timeout):
        assert headers["Authorization"] == "Token test-token"
        if url.endswith("/scenarios/123"):
            return {"scenario": {"name": "Jesse Intake Poller Test", "isActive": False}}
        if "/scenarios/123/logs" in url:
            return {"scenarioLogs": [{"id": 1, "status": "success", "operations": 4, "started": "2026-07-14T00:00:00Z"}]}
        if "/data-stores/456/data" in url:
            return {"records": [{"data": {"cursor": "abc123"}}]}
        raise AssertionError(f"unexpected url {url}")

    result = get_make_status(transport=fake_transport)
    assert result["status"] == "ok"
    assert result["scenario"]["active"] is False
    assert result["processed_count"] == 4
    assert result["data_store_cursor"] == "abc123"


def test_make_status_reports_error_without_leaking_token(monkeypatch):
    _clear_make_env(monkeypatch)
    monkeypatch.setenv("MAKE_API_BASE_URL", "https://us1.make.com/api/v2")
    monkeypatch.setenv("MAKE_API_TOKEN", "super-secret-token")
    monkeypatch.setenv("MAKE_STATUS_SCENARIO_ID", "123")

    def failing_transport(method, url, headers, timeout):
        raise OSError("connection refused")

    result = get_make_status(transport=failing_transport)
    assert result["status"] == "error"
    assert "super-secret-token" not in str(result)


def test_jesse_status_not_configured(monkeypatch):
    monkeypatch.delenv("JESSE_API_URL", raising=False)

    def _fail(*args, **kwargs):
        raise AssertionError("no network calls expected when unconfigured")

    result = get_jesse_status(transport=_fail)
    assert result["status"] == "not_configured"


def test_jesse_status_not_configured_without_token_makes_no_network_calls(monkeypatch):
    monkeypatch.setenv("JESSE_API_URL", "http://127.0.0.1:8000")
    monkeypatch.delenv("JESSE_DASHBOARD_TOKEN", raising=False)

    def _fail(*args, **kwargs):
        raise AssertionError("no network calls expected when the dashboard token is missing")

    result = get_jesse_status(transport=_fail)
    assert result["status"] == "not_configured"
    assert result["reachable"] is False


def test_jesse_status_unreachable(monkeypatch):
    monkeypatch.setenv("JESSE_API_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("JESSE_DASHBOARD_TOKEN", "token")

    def failing_transport(method, url, headers, timeout):
        raise OSError("connection refused")

    result = get_jesse_status(transport=failing_transport)
    assert result["status"] == "unavailable"
    assert result["reachable"] is False


def test_jesse_status_ok_with_fake_transport(monkeypatch):
    monkeypatch.setenv("JESSE_API_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("JESSE_DASHBOARD_TOKEN", "dashboard-token")

    def fake_transport(method, url, headers, timeout):
        if url.endswith("/health"):
            return {"status": "ok"}
        if url.endswith("/reports/summary"):
            assert headers["X-API-Key"] == "dashboard-token"
            return {"total_intakes": 12, "pending_callbacks": 2, "status_counts": {"new": 2}, "integration_health": {}}
        raise AssertionError(f"unexpected url {url}")

    result = get_jesse_status(transport=fake_transport)
    assert result["status"] == "ok"
    assert result["processed_count"] == 12
    assert result["pending_callbacks"] == 2


def test_callcenter_analytics_reports_transfer_errors_separately(db):
    calls = CallCenterService(db)
    call = calls.receive_mock_call("555-000-1111")
    calls.update_call(call.id, "completed", outcome="transfer_error")
    analytics = calls.analytics()
    assert analytics["transfer_errors"] == 1
    assert analytics["successful"] == 0
    filtered = calls.list_calls(outcome="transfer_error")
    assert len(filtered) == 1
    assert filtered[0].caller_redacted == "***1111"


def test_callcenter_analytics_counts_successful_and_failed(db):
    calls = CallCenterService(db)
    good_call = calls.receive_mock_call("555-000-2222")
    calls.update_call(good_call.id, "completed", outcome="resolved")
    bad_call = calls.receive_mock_call("555-000-3333")
    calls.update_call(bad_call.id, "missed", outcome="no_answer")
    analytics = calls.analytics()
    assert analytics["successful"] == 1
    assert analytics["failed"] == 1


def test_memory_latest_conversation_is_redacted(db):
    memory = PersistentMemoryEngine(db)
    memory.remember("jessie", "First touch", conversation_id="conversation-one")
    memory.remember("jessie", "Second touch", conversation_id="conversation-two")
    latest = memory.latest_conversation()
    assert latest is not None
    assert latest["conversation_id_redacted"] == "***-two"
    assert "conversation-two" not in latest["conversation_id_redacted"]


def test_memory_latest_conversation_empty_state(db):
    memory = PersistentMemoryEngine(db)
    assert memory.latest_conversation() is None


def test_ops_routes_require_viewer_role(client):
    assert client.get("/ops/jesse-status").status_code == 200
    assert client.get("/ops/make-status").status_code == 200
    assert client.get("/ops/conversations/latest").status_code == 200


def test_ops_routes_require_auth(db):
    api_client = TestClient(create_app(db))
    assert api_client.get("/ops/jesse-status").status_code == 401
    assert api_client.get("/ops/make-status").status_code == 401
    assert api_client.get("/ops/conversations/latest").status_code == 401
