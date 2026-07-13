#!/usr/bin/env python3
"""Safely export, validate, plan, and deploy Make/ElevenLabs config patches."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


SCHEMA_VERSION = 1
REDACTED = "__REDACTED__"
SECRET_KEY = re.compile(
    r"(?:api[_-]?key|authorization|bearer|client[_-]?secret|credential|password|"
    r"private[_-]?key|refresh[_-]?token|secret|token|webhook[_-]?url)$",
    re.IGNORECASE,
)
SENSITIVE_URL = re.compile(r"^https?://", re.IGNORECASE)
ALLOWED_PROVIDERS = {"elevenlabs", "make"}
ALLOWED_TARGETS = {"staging", "production"}
ELEVENLABS_PATCH_KEYS = {
    "conversation_config",
    "name",
    "platform_settings",
    "tags",
    "version_description",
    "workflow",
}
MAKE_PATCH_KEYS = {"blueprint", "folderId", "name", "scheduling"}
RESOURCE_ID_ENVS = {
    "elevenlabs": {"ELEVENLABS_AGENT_ID"},
    "make": {
        "MAKE_APPOINTMENT_SCENARIO_ID",
        "MAKE_CANCELLATION_SCENARIO_ID",
        "MAKE_RESCHEDULE_SCENARIO_ID",
    },
}


class ConfigSyncError(RuntimeError):
    """A safe, user-facing config synchronization error."""


Transport = Callable[[str, str, dict[str, str], bytes | None], dict[str, Any]]


def _http_json(method: str, url: str, headers: dict[str, str], body: bytes | None) -> dict[str, Any]:
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - hosts are allowlisted below
            raw = response.read()
    except HTTPError as exc:
        raise ConfigSyncError(f"provider returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ConfigSyncError("provider request failed") from exc
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigSyncError("provider returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ConfigSyncError("provider returned an unexpected JSON shape")
    return parsed


def _nested_json(value: str) -> Any | None:
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def redact(value: Any, key: str = "") -> Any:
    """Redact credentials and outbound URLs, including JSON encoded as strings."""
    if SECRET_KEY.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {name: redact(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, str):
        nested = _nested_json(value)
        if nested is not None:
            return json.dumps(redact(nested), sort_keys=True, separators=(",", ":"))
        if SENSITIVE_URL.match(value):
            return REDACTED
    return value


def _scan(value: Any, path: str = "payload") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if SECRET_KEY.search(key):
                findings.append(f"secret-like field is not allowed: {child}")
            findings.extend(_scan(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_scan(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if value == REDACTED:
            findings.append(f"redacted placeholder must be resolved outside GitHub: {path}")
        nested = _nested_json(value)
        if nested is not None:
            findings.extend(_scan(nested, path))
        elif SENSITIVE_URL.match(value):
            findings.append(f"outbound URL is not allowed in tracked config: {path}")
    return findings


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigSyncError(f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigSyncError(f"manifest is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ConfigSyncError("manifest must be a JSON object")
    return data


def validate_manifest(data: dict[str, Any], *, allow_empty: bool = True) -> None:
    required = {"schema_version", "provider", "target", "resource_id_env", "payload"}
    missing = sorted(required - data.keys())
    if missing:
        raise ConfigSyncError("manifest is missing: " + ", ".join(missing))
    if data["schema_version"] != SCHEMA_VERSION:
        raise ConfigSyncError(f"schema_version must be {SCHEMA_VERSION}")
    provider = data["provider"]
    target = data["target"]
    payload = data["payload"]
    if provider not in ALLOWED_PROVIDERS:
        raise ConfigSyncError("provider must be elevenlabs or make")
    if target not in ALLOWED_TARGETS:
        raise ConfigSyncError("target must be staging or production")
    if not isinstance(data["resource_id_env"], str) or not re.fullmatch(r"[A-Z][A-Z0-9_]+", data["resource_id_env"]):
        raise ConfigSyncError("resource_id_env must name an uppercase environment variable")
    if data["resource_id_env"] not in RESOURCE_ID_ENVS[provider]:
        raise ConfigSyncError("resource_id_env is not approved for this provider")
    if not isinstance(payload, dict):
        raise ConfigSyncError("payload must be an object")
    if not payload and not allow_empty:
        raise ConfigSyncError("payload is empty; export and review the provider config first")
    allowed = ELEVENLABS_PATCH_KEYS if provider == "elevenlabs" else MAKE_PATCH_KEYS
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ConfigSyncError("unsupported payload fields: " + ", ".join(unknown))
    findings = _scan(payload)
    if findings:
        raise ConfigSyncError("; ".join(findings))
    if provider == "make" and "blueprint" in payload and not isinstance(payload["blueprint"], str):
        raise ConfigSyncError("Make blueprint must be a JSON-encoded string")


def _resource_id(manifest: dict[str, Any]) -> str:
    name = manifest["resource_id_env"]
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigSyncError(f"required environment variable is missing: {name}")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ConfigSyncError(f"invalid resource identifier in {name}")
    return value


def _elevenlabs_export(transport: Transport, agent_id: str) -> dict[str, Any]:
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise ConfigSyncError("ELEVENLABS_API_KEY is missing")
    query: dict[str, str] = {}
    branch_id = os.getenv("ELEVENLABS_BRANCH_ID", "").strip()
    if branch_id:
        query["branch_id"] = branch_id
    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    if query:
        url += "?" + urlencode(query)
    response = transport("GET", url, {"xi-api-key": api_key, "Accept": "application/json"}, None)
    return {key: redact(response[key], key) for key in ELEVENLABS_PATCH_KEYS if key in response and key != "version_description"}


def _make_base_url() -> str:
    base = os.getenv("MAKE_API_BASE_URL", "").rstrip("/")
    if not base:
        raise ConfigSyncError("MAKE_API_BASE_URL is missing")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".make.com"):
        raise ConfigSyncError("MAKE_API_BASE_URL must be an HTTPS Make zone, for example https://us1.make.com/api/v2")
    if not parsed.path.endswith("/api/v2"):
        raise ConfigSyncError("MAKE_API_BASE_URL must end with /api/v2")
    return base


def _make_auth() -> dict[str, str]:
    token = os.getenv("MAKE_API_TOKEN", "")
    if not token:
        raise ConfigSyncError("MAKE_API_TOKEN is missing")
    return {"Authorization": f"Token {token}", "Accept": "application/json"}


def _extract_blueprint(response: dict[str, Any]) -> str:
    candidates: list[Any] = [response.get("blueprint")]
    nested = response.get("response")
    if isinstance(nested, dict):
        candidates.extend([nested.get("blueprint"), nested.get("code")])
    elif isinstance(nested, str):
        candidates.append(nested)
    candidates.append(response.get("code"))
    for candidate in candidates:
        if isinstance(candidate, str) and _nested_json(candidate) is not None:
            return candidate
        if isinstance(candidate, dict):
            return json.dumps(candidate, sort_keys=True, separators=(",", ":"))
    raise ConfigSyncError("Make blueprint response did not contain a blueprint")


def _make_export(transport: Transport, scenario_id: str) -> dict[str, Any]:
    base = _make_base_url()
    headers = _make_auth()
    details = transport("GET", f"{base}/scenarios/{scenario_id}", headers, None)
    blueprint_response = transport("GET", f"{base}/scenarios/{scenario_id}/blueprint?draft=true", headers, None)
    scenario = details.get("scenario", details)
    payload: dict[str, Any] = {"blueprint": _extract_blueprint(blueprint_response)}
    if isinstance(scenario, dict):
        for key in ("name", "scheduling"):
            if key in scenario:
                payload[key] = scenario[key]
    return redact(payload)


def export_manifest(provider: str, target: str, resource_id_env: str, transport: Transport = _http_json) -> dict[str, Any]:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider,
        "target": target,
        "resource_id_env": resource_id_env,
        "payload": {},
    }
    validate_manifest(manifest)
    resource_id = _resource_id(manifest)
    if provider == "elevenlabs":
        manifest["payload"] = _elevenlabs_export(transport, resource_id)
    else:
        manifest["payload"] = _make_export(transport, resource_id)
    return manifest


def _deploy(manifest: dict[str, Any], transport: Transport = _http_json) -> None:
    resource_id = _resource_id(manifest)
    payload = json.dumps(manifest["payload"], separators=(",", ":")).encode()
    if manifest["provider"] == "elevenlabs":
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            raise ConfigSyncError("ELEVENLABS_API_KEY is missing")
        query = {}
        branch_id = os.getenv("ELEVENLABS_BRANCH_ID", "").strip()
        if branch_id:
            query["branch_id"] = branch_id
        url = f"https://api.elevenlabs.io/v1/convai/agents/{resource_id}"
        if query:
            url += "?" + urlencode(query)
        transport("PATCH", url, {"xi-api-key": api_key, "Content-Type": "application/json"}, payload)
        return
    base = _make_base_url()
    headers = _make_auth() | {"Content-Type": "application/json"}
    transport("PATCH", f"{base}/scenarios/{resource_id}", headers, payload)


def plan(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": manifest["provider"],
        "target": manifest["target"],
        "resource_configured": bool(os.getenv(manifest["resource_id_env"], "")),
        "payload_fields": sorted(manifest["payload"]),
        "external_write": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("manifest", type=Path)
    export = sub.add_parser("export")
    export.add_argument("--provider", choices=sorted(ALLOWED_PROVIDERS), required=True)
    export.add_argument("--target", choices=sorted(ALLOWED_TARGETS), required=True)
    export.add_argument("--resource-id-env", required=True)
    export.add_argument("--output", type=Path, required=True)
    deploy = sub.add_parser("deploy")
    deploy.add_argument("manifest", type=Path)
    deploy.add_argument("--apply", action="store_true")
    deploy.add_argument("--confirm-production", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            validate_manifest(load_manifest(args.manifest))
            print(json.dumps({"status": "valid", "manifest": str(args.manifest)}))
            return 0
        if args.command == "export":
            manifest = export_manifest(args.provider, args.target, args.resource_id_env)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"status": "exported", "provider": args.provider, "output": str(args.output)}))
            return 0
        manifest = load_manifest(args.manifest)
        validate_manifest(manifest, allow_empty=not args.apply)
        if not args.apply:
            print(json.dumps(plan(manifest), sort_keys=True))
            return 0
        if os.getenv("EXTERNAL_CONFIG_DEPLOY_ENABLED", "false").lower() != "true":
            raise ConfigSyncError("external config deployment is disabled")
        if manifest["target"] == "production" and args.confirm_production != "DEPLOY":
            raise ConfigSyncError("production deployment requires --confirm-production DEPLOY")
        _deploy(manifest)
        print(json.dumps({"status": "applied", "provider": manifest["provider"], "target": manifest["target"]}))
        return 0
    except ConfigSyncError as exc:
        print(f"external-config-sync: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
