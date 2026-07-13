from pathlib import Path

from fastapi.testclient import TestClient

from agents.ju.src.events import EventDispatcher
from agents.ju.src.runtime import JuRuntime
from agents.michelle.src.runtime import MichelleRuntime
from core.api import create_core_app
from core.memory import MemoryManager, VectorMemoryPlaceholder
from core.messaging import Message, MessageBus
from core.registry import AgentRegistry


def make_agents(tmp_path: Path):
    root = tmp_path / "agents"
    for name, runtime in [("ju", True), ("michelle", True), ("jessie", True), ("sales", False), ("content", False), ("finance", False), ("workspace", False), ("operations", False)]:
        folder = root / name
        folder.mkdir(parents=True)
        (folder / "README.md").write_text(f"# {name}", encoding="utf-8")
        if runtime:
            (folder / "src").mkdir()
    return root


def test_registry_discovers_agents_without_importing(tmp_path):
    registry = AgentRegistry(make_agents(tmp_path))
    agents = registry.discover()
    assert agents["ju"].runtime_available is True
    assert agents["sales"].status == "planned"


def test_message_bus_prioritizes_and_broadcasts():
    bus = MessageBus()
    bus.send_message(Message("ju", "michelle", "normal", priority=5))
    bus.send_message(Message("ju", "michelle", "urgent", priority=1))
    assert bus.receive_message("michelle").subject == "urgent"
    ids = bus.broadcast("ju", ["michelle", "sales"], "update")
    assert len(ids) == 2


def test_memory_persists_and_searches(tmp_path):
    path = tmp_path / "memory.json"
    memory = MemoryManager(path)
    memory.remember("projects", "Launch the Jesse dashboard", {"owner": "michelle"})
    assert memory.search("jesse")[0].namespace == "projects"
    assert MemoryManager(path).list("projects")[0].metadata["owner"] == "michelle"
    assert VectorMemoryPlaceholder().search("anything") == []


def test_ju_routes_delegates_and_reports(tmp_path):
    runtime = JuRuntime(make_agents(tmp_path))
    item = runtime.delegate("Create a social content campaign", priority=3)
    assert item.assignee == "content"
    assert runtime.messages.receive_message("content").payload["task_id"] == item.id
    assert runtime.status()["delegations"]["total"] == 1


def test_event_dispatcher_notifies_subscribers():
    received = []
    events = EventDispatcher()
    events.subscribe("ready", received.append)
    assert events.dispatch("ready", {"agent": "ju"}) == 1
    assert received == [{"agent": "ju"}]


def test_michelle_tracks_projects_and_escalates(tmp_path):
    runtime = MichelleRuntime(make_agents(tmp_path))
    task = runtime.create_task("Handle urgent intake", "jessie", priority=1, project="client launch")
    assert task.id in runtime.projects.ensure("client launch").task_ids
    assert runtime.notifications.notifications[0].recipient == "ju"
    assert runtime.status()["task_counts"]["open"] == 1


def test_workflow_engine_plans_steps(tmp_path):
    runtime = MichelleRuntime(make_agents(tmp_path))
    runtime.workflows.register("onboarding", ["create folder", "assign owner"])
    assert runtime.workflows.plan("onboarding")[1]["status"] == "pending"


def test_core_api_controls_runtime(tmp_path):
    app = create_core_app(make_agents(tmp_path))
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        delegation = client.post("/delegations", json={"description": "Prepare sales proposal", "priority": 2})
        assert delegation.status_code == 201
        assert delegation.json()["assignee"] == "sales"
        task = client.post("/tasks", json={"title": "Call client", "owner": "jessie", "project": "launch"})
        assert task.status_code == 201
        queued = client.post("/messages", json={"sender": "ju", "recipient": "finance", "subject": "review"})
        assert queued.status_code == 202
        assert client.get("/messages/finance").json()["subject"] == "review"
