from __future__ import annotations

import base64
import json
import os
from email.message import EmailMessage
from typing import Callable

import httpx


GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


class GmailSandboxError(RuntimeError):
    pass


class GmailSandbox:
    """Draft-only Gmail sandbox. It never sends a message."""

    def __init__(self, transport: Callable[..., dict] | None = None) -> None:
        self.enabled = os.getenv("GMAIL_SANDBOX_ENABLED", "false").casefold() == "true"
        self.mode = os.getenv("GMAIL_MODE", "mock").casefold()
        self.mailbox = os.getenv("GMAIL_SANDBOX_MAILBOX", "")
        self.recipient = os.getenv("GMAIL_SANDBOX_RECIPIENT", "")
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.transport = transport or self._google_transport

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode if self.enabled else "disabled",
            "auth_mode": "adc",
            "mailbox_configured": bool(self.mailbox),
            "recipient_configured": bool(self.recipient),
            "draft_only": True,
            "human_approval_required": True,
        }

    def validate(self) -> None:
        if self.mode not in {"mock", "sandbox", "disabled"}:
            raise GmailSandboxError("invalid Gmail sandbox mode")
        if self.mode == "sandbox":
            if not self.enabled:
                raise GmailSandboxError("Gmail sandbox is disabled")
            if not self.project_id:
                raise GmailSandboxError("staging project is not configured")
            if not self._safe_test_address(self.mailbox) or not self._safe_test_address(self.recipient):
                raise GmailSandboxError("dedicated test mailbox and recipient are required")

    @staticmethod
    def _safe_test_address(value: str) -> bool:
        local, separator, domain = value.strip().casefold().partition("@")
        return bool(separator and local and domain and ("test" in local or "sandbox" in local))

    def create_draft(self, subject: str, request_id: str) -> dict:
        if not subject.strip() or len(subject) > 120:
            raise GmailSandboxError("invalid draft subject")
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "network_calls": 0, "draft_only": True}
        if self.mode == "mock":
            return {"status": "mock", "network_calls": 0, "draft_only": True, "draft_reference": f"mock:{request_id}"}
        self.validate()
        message = EmailMessage()
        message["To"] = self.recipient
        message["From"] = self.mailbox
        message["Subject"] = subject.strip()
        message["X-SuccessBrand-Sandbox-Request-ID"] = request_id
        message.set_content("Synthetic Success Brand staging draft. No client or production data.")
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        result = self.transport(mailbox=self.mailbox, project_id=self.project_id, payload={"message": {"raw": raw}})
        return {"status": "draft-created", "network_calls": 1, "draft_only": True, "draft_reference": result.get("id", "gmail-draft")}

    @staticmethod
    def _google_transport(*, mailbox: str, project_id: str, payload: dict) -> dict:
        import google.auth
        from google.auth.transport.requests import Request

        credentials, detected_project = google.auth.default(scopes=[GMAIL_COMPOSE_SCOPE])
        if detected_project and detected_project != project_id:
            raise GmailSandboxError("ADC project does not match staging")
        credentials.refresh(Request())
        response = httpx.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
            headers={"Authorization": f"Bearer {credentials.token}"},
            json=payload,
            timeout=5.0,
        )
        if response.status_code in {401, 403}:
            raise GmailSandboxError("ADC identity has no approved test mailbox access")
        response.raise_for_status()
        return response.json()
