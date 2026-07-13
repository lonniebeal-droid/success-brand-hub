from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from core.auth import require_role
from .service import TwilioSandbox, TwilioSandboxError


class TwilioWebhookVerification(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    params: dict[str, str] = Field(default_factory=dict)
    signature: str = Field(default="", max_length=500)


def create_twilio_sandbox_router(factory=TwilioSandbox) -> APIRouter:
    router = APIRouter(prefix="/sandbox/twilio", tags=["twilio-sandbox"])

    @router.get("/status")
    def status(_: dict = Depends(require_role("viewer"))):
        return factory().status()

    @router.post("/verify-webhook")
    def verify(payload: TwilioWebhookVerification, _: dict = Depends(require_role("manager"))):
        try:
            return factory().verify_inbound(payload.url, payload.params, payload.signature)
        except TwilioSandboxError as exc:
            raise HTTPException(401, str(exc)) from exc

    @router.post("/webhook", response_class=Response)
    async def provider_webhook(request: Request):
        service = factory()
        if not service.enabled or service.mode == "disabled":
            raise HTTPException(503, "Twilio sandbox is disabled")
        body = (await request.body()).decode("utf-8")
        params = dict(parse_qsl(body, keep_blank_values=True))
        try:
            service.verify_inbound(
                service.callback_url,
                params,
                request.headers.get("X-Twilio-Signature", ""),
            )
        except TwilioSandboxError as exc:
            raise HTTPException(401, str(exc)) from exc
        return Response(content="<Response/>", media_type="application/xml")

    return router
