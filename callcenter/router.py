from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import require_role
from core.database.database import Database
from .service import CallCenterService


class IncomingCall(BaseModel):
    caller: str | None = None
    agent: str | None = "jessie"
    metadata: dict = Field(default_factory=dict)


class CallUpdate(BaseModel):
    state: str
    outcome: str | None = None
    duration_seconds: float | None = None


class AvailabilityUpdate(BaseModel):
    status: str


def public(item): return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def create_callcenter_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/callcenter", tags=["callcenter"])
    service = CallCenterService(database)

    @router.post("/calls/mock", status_code=201)
    def incoming(payload: IncomingCall, _: dict = Depends(require_role("agent"))): return public(service.receive_mock_call(**payload.model_dump()))

    @router.get("/calls")
    def calls(state: str | None = None, _: dict = Depends(require_role("viewer"))): return [public(item) for item in service.list_calls(state)]

    @router.patch("/calls/{call_id}")
    def update(call_id: str, payload: CallUpdate, _: dict = Depends(require_role("agent"))):
        try: return public(service.update_call(call_id, **payload.model_dump()))
        except KeyError as exc: raise HTTPException(404, str(exc)) from exc

    @router.get("/callback-queue")
    def callbacks(_: dict = Depends(require_role("viewer"))): return [public(item) for item in service.list_calls("callback")]

    @router.get("/analytics")
    def analytics(_: dict = Depends(require_role("viewer"))): return service.analytics()

    @router.put("/agents/{agent}/availability")
    def availability(agent: str, payload: AvailabilityUpdate, _: dict = Depends(require_role("manager"))): return public(service.set_availability(agent, payload.status))

    return router
