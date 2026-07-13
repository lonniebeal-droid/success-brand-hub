from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Callable
from urllib.parse import urlparse

import httpx


ALLOWED_OPERATIONS = {"synthetic_intake", "synthetic_lead", "health_check"}


class N8nSandboxError(RuntimeError):
    pass


class N8nSandbox:
    """Disabled-by-default n8n webhook adapter for synthetic staging records."""

    def __init__(self, transport: Callable[..., dict] | None = None) -> None:
        self.enabled = os.getenv("N8N_SANDBOX_ENABLED", "false").casefold() == "true"
        self.mode = os.getenv("N8N_MODE", "mock").casefold()
        self.webhook_url = os.getenv("N8N_SANDBOX_WEBHOOK_URL", "")
        self.allowed_host = os.getenv("N8N_SANDBOX_ALLOWED_HOST", "").casefold()
        self.signing_secret = os.getenv("N8N_SANDBOX_SIGNING_SECRET", "")
        self.transport = transport or self._http_transport

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode if self.enabled else "disabled",
            "webhook_configured": bool(self.webhook_url),
            "signing_configured": bool(self.signing_secret),
            "human_approval_required": True,
        }

    def validate(self) -> None:
        if self.mode not in {"disabled", "mock", "sandbox"}:
            raise N8nSandboxError("invalid n8n sandbox mode")
        if self.mode != "sandbox":
            return
        if not self.enabled:
            raise N8nSandboxError("n8n sandbox is disabled")
        parsed = urlparse(self.webhook_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise N8nSandboxError("n8n sandbox requires an HTTPS webhook")
        if not self.allowed_host or parsed.hostname.casefold() != self.allowed_host:
            raise N8nSandboxError("n8n webhook host is not allowlisted")
        if len(self.signing_secret) < 32:
            raise N8nSandboxError("n8n signing secret is unavailable")

    def trigger(self, operation: str, record_id: str, request_id: str) -> dict:
        if operation not in ALLOWED_OPERATIONS:
            raise N8nSandboxError("unsupported n8n sandbox operation")
        if not record_id.strip() or len(record_id) > 120:
            raise N8nSandboxError("invalid synthetic record identifier")
        if not self.enabled or self.mode == "disabled":
            return {"status": "disabled", "network_calls": 0}
        if self.mode == "mock":
            return {"status": "mock", "network_calls": 0, "request_id": request_id}
        self.validate()
        payload = {
            "schema_version": "n8n_sandbox_v1",
            "operation": operation,
            "record_id": record_id.strip(),
            "request_id": request_id,
            "synthetic": True,
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(self.signing_secret.encode(), body, hashlib.sha256).hexdigest()
        self.transport(url=self.webhook_url, body=body, signature=signature, request_id=request_id)
        return {"status": "accepted", "network_calls": 1, "request_id": request_id}

    @staticmethod
    def _http_transport(*, url: str, body: bytes, signature: str, request_id: str) -> dict:
        response = httpx.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-SuccessBrand-Signature": f"sha256={signature}",
                "X-Request-ID": request_id,
            },
            timeout=5.0,
        )
        if response.status_code in {401, 403}:
            raise N8nSandboxError("n8n sandbox authorization is unavailable")
        response.raise_for_status()
        return {"accepted": True}
