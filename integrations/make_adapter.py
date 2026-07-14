"""Read-only adapter for Make.com scenario status used by operational dashboards.

This adapter never writes to Make and never commits credentials. Access is
controlled entirely by environment variables (see .env.example) and every
network call is restricted to HTTPS hosts under *.make.com. When configuration
is missing or the Make API is unreachable, the adapter returns a clearly
labelled "not_configured"/"error" state instead of raising, so dashboards can
render a safe, honest empty/error state.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_SECONDS = 8

Transport = Callable[[str, str, dict[str, str], int], Any]

_NETWORK_ERRORS = (HTTPError, URLError, TimeoutError, ValueError, OSError)


class MakeAdapterError(RuntimeError):
    """Raised for safe, user-facing Make adapter configuration failures."""


def _http_json(method: str, url: str, headers: dict[str, str], timeout: int) -> Any:
    request = Request(url, headers=headers, method=method)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - host allowlisted below
        raw = response.read()
    return json.loads(raw) if raw else {}


def _base_url() -> str | None:
    base = os.getenv("MAKE_API_BASE_URL", "").strip().rstrip("/")
    if not base:
        return None
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".make.com"):
        raise MakeAdapterError(
            "MAKE_API_BASE_URL must be an HTTPS Make zone, for example https://us1.make.com/api/v2"
        )
    return base


def _auth_headers() -> dict[str, str] | None:
    token = os.getenv("MAKE_API_TOKEN", "").strip()
    if not token:
        return None
    return {"Authorization": f"Token {token}", "Accept": "application/json"}


def _scenario_id() -> str | None:
    value = os.getenv("MAKE_STATUS_SCENARIO_ID", "").strip() or os.getenv("MAKE_POLLER_SCENARIO_ID", "").strip()
    return value or None


def _not_configured(base: str | None, headers: dict[str, str] | None, scenario_id: str | None) -> dict[str, Any]:
    missing = []
    if not base:
        missing.append("MAKE_API_BASE_URL")
    if not headers:
        missing.append("MAKE_API_TOKEN")
    if not scenario_id:
        missing.append("MAKE_STATUS_SCENARIO_ID or MAKE_POLLER_SCENARIO_ID")
    return {
        "status": "not_configured",
        "configured": False,
        "message": "Make integration is not configured for this dashboard.",
        "missing_environment_variables": missing,
        "scenario": None,
        "executions": [],
        "processed_count": None,
        "data_store_cursor": None,
        "error": None,
    }


def get_make_status(transport: Transport = _http_json) -> dict[str, Any]:
    """Return a redacted, dashboard-safe snapshot of one Make scenario's health.

    The returned "status" is one of "not_configured", "error", "degraded", or
    "ok". The Make API token is never included in the response.
    """
    try:
        base = _base_url()
    except MakeAdapterError as exc:
        return {
            "status": "error",
            "configured": True,
            "error": str(exc),
            "scenario": None,
            "executions": [],
            "processed_count": None,
            "data_store_cursor": None,
        }

    headers = _auth_headers()
    scenario_id = _scenario_id()
    if not base or not headers or not scenario_id:
        return _not_configured(base, headers, scenario_id)

    timeout = DEFAULT_TIMEOUT_SECONDS
    result: dict[str, Any] = {
        "status": "ok",
        "configured": True,
        "scenario": None,
        "executions": [],
        "processed_count": None,
        "data_store_cursor": None,
        "error": None,
    }

    try:
        scenario_payload = transport("GET", f"{base}/scenarios/{scenario_id}", headers, timeout)
        scenario = scenario_payload.get("scenario", scenario_payload) if isinstance(scenario_payload, dict) else {}
        is_active = scenario.get("isActive")
        if is_active is None:
            is_active = scenario.get("is_active")
        result["scenario"] = {
            "id": scenario_id,
            "name": scenario.get("name"),
            "active": bool(is_active) if is_active is not None else None,
        }
    except _NETWORK_ERRORS:
        result["status"] = "error"
        result["error"] = "Unable to reach the Make scenario status endpoint."
        return result

    try:
        logs_query = urlencode({"pg[limit]": "5", "pg[sortDir]": "desc"})
        logs_payload = transport("GET", f"{base}/scenarios/{scenario_id}/logs?{logs_query}", headers, timeout)
        entries = logs_payload.get("scenarioLogs", logs_payload.get("logs", [])) if isinstance(logs_payload, dict) else []
        executions = []
        processed_total = 0
        has_operation_counts = False
        for entry in entries[:5]:
            operations = entry.get("operations")
            if isinstance(operations, (int, float)):
                processed_total += operations
                has_operation_counts = True
            executions.append({
                "id": entry.get("id"),
                "status": entry.get("status"),
                "started_at": entry.get("started") or entry.get("startedAt"),
                "finished_at": entry.get("finished") or entry.get("finishedAt"),
                "operations": operations,
            })
        result["executions"] = executions
        result["processed_count"] = processed_total if has_operation_counts else None
    except _NETWORK_ERRORS:
        result["status"] = "degraded"
        result["error"] = "Latest Make executions are temporarily unavailable."

    data_store_id = os.getenv("MAKE_DATA_STORE_ID", "").strip()
    cursor_key = os.getenv("MAKE_DATA_STORE_CURSOR_KEY", "cursor").strip() or "cursor"
    if data_store_id:
        try:
            store_query = urlencode({"pg[limit]": "1"})
            store_payload = transport("GET", f"{base}/data-stores/{data_store_id}/data?{store_query}", headers, timeout)
            records = store_payload.get("records", []) if isinstance(store_payload, dict) else []
            cursor_value = None
            if records:
                first = records[0]
                data = first.get("data", first) if isinstance(first, dict) else {}
                if isinstance(data, dict):
                    cursor_value = data.get(cursor_key)
            result["data_store_cursor"] = cursor_value
        except _NETWORK_ERRORS:
            result["data_store_cursor"] = None
            if result["status"] == "ok":
                result["status"] = "degraded"
            if not result["error"]:
                result["error"] = "Make Data Store cursor is temporarily unavailable."

    return result
