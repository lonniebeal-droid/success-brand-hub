from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import require_role
from .service import ElevenLabsSandbox, ElevenLabsSandboxError


class ElevenLabsWebhookVerification(BaseModel):
    raw_body: str = Field(min_length=2, max_length=100_000)
    signature: str = Field(min_length=1, max_length=1000)


def create_elevenlabs_sandbox_router(factory=ElevenLabsSandbox) -> APIRouter:
    router = APIRouter(prefix="/sandbox/elevenlabs", tags=["elevenlabs-sandbox"])

    @router.get("/status")
    def status(_: dict = Depends(require_role("viewer"))):
        return factory().status()

    @router.post("/verify-webhook")
    def verify(payload: ElevenLabsWebhookVerification, _: dict = Depends(require_role("manager"))):
        try:
            return factory().verify_event(payload.raw_body, payload.signature)
        except ElevenLabsSandboxError as exc:
            raise HTTPException(401, str(exc)) from exc

    @router.post("/webhook")
    async def provider_webhook(request: Request):
        service = factory()
        if not service.enabled or service.mode == "disabled":
            raise HTTPException(503, "ElevenLabs sandbox is disabled")
        try:
            return service.verify_event(
                (await request.body()).decode("utf-8"),
                request.headers.get("ElevenLabs-Signature", ""),
            )
        except ElevenLabsSandboxError as exc:
            raise HTTPException(401, str(exc)) from exc

    return router
