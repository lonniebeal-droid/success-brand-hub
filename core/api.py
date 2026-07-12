from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agents.ju.src.runtime import JuRuntime
from agents.michelle.src.runtime import MichelleRuntime
from core.memory import SharedMemory
from core.messaging import Message, MessageBus
from core.registry import AgentRegistry


class DelegationRequest(BaseModel):
    description: str = Field(min_length=1)
    priority: int = Field(default=5, ge=1, le=10)


class TaskRequest(BaseModel):
    title: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    priority: int = Field(default=5, ge=1, le=10)
    project: str = "general"


class MessageRequest(BaseModel):
    sender: str
    recipient: str
    subject: str
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)


def create_core_app(agents_path="agents") -> FastAPI:
    app = FastAPI(title="Success Brand Core API", version="1.0.0")
    registry = AgentRegistry(agents_path)
    registry.discover()
    bus = MessageBus()
    memory = SharedMemory()
    ju = JuRuntime(agents_path)
    ju.messages = bus
    ju.engine.bus = bus
    michelle = MichelleRuntime(agents_path, bus)
    app.state.services = {"registry": registry, "messages": bus, "memory": memory, "ju": ju, "michelle": michelle}

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "success-brand-core", "agents": len(registry.all())}

    @app.get("/agents")
    def agents():
        return registry.snapshot()

    @app.get("/agents/{name}/status")
    def agent_status(name: str):
        if name == "ju":
            return ju.status()
        if name == "michelle":
            return michelle.status()
        record = registry.get(name)
        if not record:
            raise HTTPException(404, "agent not found")
        return {"agent": name, "status": record.status, "runtime_available": record.runtime_available}

    @app.post("/delegations", status_code=201)
    def delegate(request: DelegationRequest):
        item = ju.delegate(request.description, request.priority)
        return item.__dict__

    @app.post("/tasks", status_code=201)
    def create_task(request: TaskRequest):
        return michelle.create_task(request.title, request.owner, request.priority, request.project).__dict__

    @app.post("/messages", status_code=202)
    def send_message(request: MessageRequest):
        message = Message(**request.model_dump())
        bus.send_message(message)
        return {"id": message.id, "status": "queued"}

    @app.get("/messages/{recipient}")
    def receive_message(recipient: str):
        message = bus.receive_message(recipient)
        return message.__dict__ if message else None

    @app.get("/memory/search")
    def search_memory(q: str, namespace: str | None = None):
        return [entry.__dict__ for entry in memory.search(q, namespace)]

    return app


app = create_core_app()
