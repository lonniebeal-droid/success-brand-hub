import json
from pathlib import Path

from agents.michelle.agent import MichelleAgent
from agents.michelle.config import AgentConfig, load_config
from agents.michelle.memory import MemoryStore
from agents.michelle.tasks import TaskManager


def test_michelle_agent_tracks_tasks_and_history(tmp_path):
    config = AgentConfig(
        name="Michelle",
        workspace_root=str(tmp_path),
        memory_file=str(tmp_path / "memory.json"),
        log_file=str(tmp_path / "activity.log"),
    )
    agent = MichelleAgent(config=config)

    task = agent.create_task("Prepare executive brief", assignee="Ju")
    assert task.title == "Prepare executive brief"
    assert task.assignee == "Ju"

    agent.log_activity("Reviewed priorities")
    agent.log_activity("Scheduled follow-up")

    agent.complete_task(task.id, notes="Ready for review")

    data = json.loads(Path(config.memory_file).read_text())
    assert data["tasks"][0]["status"] == "completed"
    assert len(data["activity_log"]) == 2


def test_task_manager_routes_work_to_supported_agents():
    manager = TaskManager()
    task = manager.create_task("Route this to Jesse", assignee="Jesse")
    assert task.assignee == "Jesse"
    assert manager.route_task(task) == "Jesse"

    task_two = manager.create_task("Route this to Ju", assignee="Ju")
    assert manager.route_task(task_two) == "Ju"


def test_load_config_uses_defaults(tmp_path):
    config = load_config(str(tmp_path))
    assert config.name == "Michelle"
    assert config.workspace_root == str(tmp_path)
