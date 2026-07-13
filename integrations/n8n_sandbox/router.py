from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import require_role
from .service import N8nSandbox, N8nSandboxError


class N8nTriggerRequest(BaseModel):
    operation: str = Field(min_length=1, max_length=80)
    record_id: str = Field(min_length=1, max_length=120)


def create_n8n_sandbox_router(factory=N8nSandbox) -> APIRouter:
    router = APIRouter(prefix="/sandbox/n8n", tags=["n8n-sandbox"])

    @router.get("/status")
    def status(_: dict = Depends(require_role("viewer"))):
        return factory().status()

    @router.post("/operations", status_code=202)
    def trigger(payload: N8nTriggerRequest, request: Request, _: dict = Depends(require_role("manager"))):
        try:
            return factory().trigger(
                payload.operation,
                payload.record_id,
                request.headers.get("X-Request-ID", "n8n-sandbox"),
            )
        except N8nSandboxError as exc:
            raise HTTPException(400, str(exc)) from exc

    return router
