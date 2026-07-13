from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import require_role


PROVIDERS = ("google_calendar", "gmail", "n8n", "twilio", "elevenlabs")


@dataclass(frozen=True)
class ProviderState:
    provider: str
    enabled: bool
    mode: str
    operation: str = "status"
    human_approval_required: bool = True


class SandboxOperation(BaseModel):
    operation: str = Field(min_length=1, max_length=80)
    record_id: str = Field(min_length=1, max_length=120)
    payload: dict = Field(default_factory=dict)


def provider_state(provider: str) -> ProviderState:
    if provider not in PROVIDERS:
        raise ValueError("unknown sandbox provider")
    prefix = provider.upper()
    enabled = os.getenv(f"{prefix}_SANDBOX_ENABLED", "false").casefold() == "true"
    mode = os.getenv(f"{prefix}_MODE", "mock").casefold()
    if mode not in {"disabled", "mock", "sandbox"} or not enabled:
        mode = "disabled"
    return ProviderState(provider, enabled, mode)


def execute(provider: str, request: SandboxOperation) -> dict:
    state = provider_state(provider)
    if state.mode == "disabled":
        return {**asdict(state), "status": "disabled", "network_calls": 0}
    if state.mode == "mock":
        return {**asdict(state), "status": "mock", "network_calls": 0, "operation_id": str(uuid.uuid4()), "record_id": request.record_id}
    raise RuntimeError("sandbox transport is not configured for this provider")


def create_sandbox_provider_router() -> APIRouter:
    router = APIRouter(prefix="/sandbox/providers", tags=["sandbox-providers"])

    @router.get("")
    def statuses(_: dict = Depends(require_role("viewer"))):
        return [asdict(provider_state(provider)) for provider in PROVIDERS]

    @router.get("/{provider}")
    def status(provider: str, _: dict = Depends(require_role("viewer"))):
        try:
            return asdict(provider_state(provider))
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/{provider}/operations", status_code=202)
    def operation(provider: str, payload: SandboxOperation, _: dict = Depends(require_role("manager"))):
        try:
            return execute(provider, payload)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(503, "provider sandbox transport unavailable") from exc

    return router
