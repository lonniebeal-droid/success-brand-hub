from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import require_role
from .service import GmailSandbox, GmailSandboxError


class GmailDraftRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=120)


def create_gmail_sandbox_router(factory=GmailSandbox) -> APIRouter:
    router = APIRouter(prefix="/sandbox/gmail", tags=["gmail-sandbox"])

    @router.get("/status")
    def status(_: dict = Depends(require_role("viewer"))):
        return factory().status()

    @router.post("/drafts", status_code=201)
    def create_draft(payload: GmailDraftRequest, request: Request, _: dict = Depends(require_role("manager"))):
        try:
            return factory().create_draft(payload.subject, request.headers.get("X-Request-ID", "gmail-sandbox"))
        except GmailSandboxError as exc:
            raise HTTPException(400, str(exc)) from exc

    return router
