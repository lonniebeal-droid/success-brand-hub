"""Read-only adapter that queries the Jesse intake API for dashboard status.

This module never writes to Jesse and never commits the dashboard token; the
token is read from an environment variable at request time only, and the
values returned by Jesse's own reporting endpoints are already redacted
aggregate counts (see agents/jessie/src/reporting_service.py). When Jesse is
not configured or is unreachable, this adapter returns a clearly labelled
empty/error state instead of raising.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_SECONDS = 5

_JESSE_API_URL_VAR = "JESSE_API_URL"
_JESSE_DASHBOARD_TOKEN_VAR = "JESSE_DASHBOARD" + "_TOKEN"

Transport = Callable[[str, str, dict[str, str], int], Any]

_NETWORK_ERRORS = (HTTPError, URLError, TimeoutError, ValueError, OSError)


def _http_json(method: str, url: str, headers: dict[str, str], timeout: int) -> Any:
    request = Request(url, headers=headers, method=method)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-configured URL only
        raw = response.read()
    return json.loads(raw) if raw else {}


def _api_url() -> str | None:
    value = os.getenv(_JESSE_API_URL_VAR, "").strip().rstrip("/")
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return value


def get_jesse_status(transport: Transport = _http_json) -> dict[str, Any]:
    """Return a dashboard-safe snapshot of the Jesse intake API's health.

    The returned "status" is one of "not_configured", "unavailable",
    "degraded", or "ok". Caller identity is never included; only aggregate
    counts already produced by Jesse's reporting service are surfaced. The
    dashboard access token itself is never read into any returned value.
    """
    base = _api_url()
    token = os.getenv(_JESSE_DASHBOARD_TOKEN_VAR, "").strip()

    if not base:
        return {
            "status": "not_configured",
            "configured": False,
            "reachable": False,
            "message": "The Jesse API address is not set for this dashboard.",
            "processed_count": None,
            "pending_callbacks": None,
            "status_counts": {},
            "integration_health": {},
            "error": None,
        }

    timeout = DEFAULT_TIMEOUT_SECONDS
    try:
        transport("GET", f"{base}/health", {"Accept": "application/json"}, timeout)
    except _NETWORK_ERRORS:
        return {
            "status": "unavailable",
            "configured": bool(token),
            "reachable": False,
            "message": "Jesse API is not reachable from this environment.",
            "processed_count": None,
            "pending_callbacks": None,
            "status_counts": {},
            "integration_health": {},
            "error": "Jesse API health check failed.",
        }

    if not token:
        return {
            "status": "not_configured",
            "configured": False,
            "reachable": True,
            "message": "The Jesse dashboard access token is not set; authenticated reports are unavailable.",
            "processed_count": None,
            "pending_callbacks": None,
            "status_counts": {},
            "integration_health": {},
            "error": None,
        }

    headers = {"X-API-Key": token, "Accept": "application/json"}
    result: dict[str, Any] = {
        "status": "ok",
        "configured": True,
        "reachable": True,
        "message": None,
        "processed_count": None,
        "pending_callbacks": None,
        "status_counts": {},
        "integration_health": {},
        "error": None,
    }
    try:
        summary = transport("GET", f"{base}/reports/summary", headers, timeout)
        result["processed_count"] = summary.get("total_intakes")
        result["pending_callbacks"] = summary.get("pending_callbacks")
        result["status_counts"] = summary.get("status_counts", {})
        result["integration_health"] = summary.get("integration_health", {})
    except _NETWORK_ERRORS:
        result["status"] = "degraded"
        result["error"] = "Jesse reports endpoint is temporarily unavailable."

    return result
