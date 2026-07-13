import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agents.jessie.api.dependencies import get_service
from agents.jessie.api.schemas import IntakeCreateRequest, IntakeResponse, IntakeStatusUpdate, SummaryResponse
from agents.jessie.integrations.elevenlabs_adapter import ElevenLabsAdapter
from agents.jessie.integrations.gmail_adapter import GmailAdapter
from agents.jessie.integrations.google_calendar_adapter import GoogleCalendarAdapter
from agents.jessie.integrations.google_sheets_adapter import GoogleSheetsAdapter
from agents.jessie.integrations.n8n_adapter import N8NAdapter
from agents.jessie.integrations.twilio_adapter import TwilioAdapter
from agents.jessie.src.intake_service import IntakeService, IntakeValidationError
from agents.jessie.src.reporting_service import ReportingService


FEATURE_FLAG_NAMES = {
    "twilio": "JESSE_TWILIO_ENABLED",
    "elevenlabs": "JESSE_ELEVENLABS_ENABLED",
    "google_calendar": "JESSE_GOOGLE_CALENDAR_ENABLED",
    "gmail": "JESSE_GMAIL_ENABLED",
    "google_sheets": "JESSE_GOOGLE_SHEETS_ENABLED",
    "n8n": "JESSE_N8N_ENABLED",
}

SERVICE_TOKENS = {
    "admin": "JESSE_ADMIN_TOKEN",
    "twilio": "JESSE_TWILIO_TOKEN",
    "elevenlabs": "JESSE_ELEVENLABS_TOKEN",
    "n8n": "JESSE_N8N_TOKEN",
    "google": "JESSE_GOOGLE_TOKEN",
    "dashboard": "JESSE_DASHBOARD_TOKEN",
}

PERMISSIONS = {
    "admin": {"*"},
    "twilio": {"POST /intakes", "POST /sandbox/twilio/inbound", "GET /intakes/{param}/summary"},
    "elevenlabs": {"POST /intakes", "POST /sandbox/elevenlabs/transcript", "GET /intakes/{param}/summary"},
    "n8n": {"POST /intakes", "GET /intakes/{param}", "GET /callbacks/pending", "PATCH /intakes/{param}/status", "GET /intakes/{param}/summary", "POST /sandbox/n8n/events/{param}", "GET /reports/daily", "GET /reports/summary", "GET /reports/integrations", "GET /reports/security"},
    "google": {"GET /callbacks/pending", "PATCH /intakes/{param}/status", "GET /sandbox/calendar/slots", "POST /sandbox/calendar/book", "POST /sandbox/sheets/intakes/{param}", "POST /sandbox/gmail/follow-up/{param}"},
    "dashboard": {"GET /health", "GET /reports/daily", "GET /reports/summary", "GET /reports/integrations", "GET /reports/security", "GET /system/status", "GET /integrations/status"},
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if hasattr(record, "context"):
            payload["context"] = record.context
        return json.dumps(payload, sort_keys=True)


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value.strip())


def _get_settings() -> dict[str, Any]:
    return {
        "environment": os.getenv("JESSE_ENVIRONMENT", "development"),
        "data_path": os.getenv("JESSE_DATA_PATH", "agents/jessie/data/intakes.json"),
        "log_level": os.getenv("JESSE_LOG_LEVEL", "INFO").upper(),
        "service_tokens": {
            name: os.getenv(env_name, "").strip()
            for name, env_name in SERVICE_TOKENS.items()
        },
        "feature_flags": {
            name: _get_bool_env(env_name, False)
            for name, env_name in FEATURE_FLAG_NAMES.items()
        },
        "rate_limit_requests": _get_int_env("JESSE_RATE_LIMIT_REQUESTS", _get_int_env("JESSE_RATE_LIMIT_PER_KEY", 5)),
        "rate_limit_window_seconds": _get_int_env("JESSE_RATE_LIMIT_WINDOW_SECONDS", 60),
        "rate_limit_per_key": _get_int_env("JESSE_RATE_LIMIT_REQUESTS", _get_int_env("JESSE_RATE_LIMIT_PER_KEY", 5)),
        "rate_limit_per_ip": _get_int_env("JESSE_RATE_LIMIT_PER_IP", _get_int_env("JESSE_RATE_LIMIT_REQUESTS", _get_int_env("JESSE_RATE_LIMIT_PER_KEY", 5))),
        "integration_mode": os.getenv("JESSE_INTEGRATION_MODE", "mock"),
        "api_url": os.getenv("JESSE_API_URL", "http://127.0.0.1:8000"),
    }


def _build_logger(level_name: str) -> logging.Logger:
    logger = logging.getLogger("jesse.api")
    logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


def _error_response(status_code: int, code: str, message: str, request: Optional[Request] = None) -> JSONResponse:
    payload = {"error": {"code": code, "message": message}}
    request_id = None
    if request is not None:
        request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        payload["error"]["request_id"] = request_id
    response = JSONResponse(status_code=status_code, content=payload)
    if request_id is not None:
        response.headers["X-Request-ID"] = request_id
    return response


def create_app(service: Optional[IntakeService] = None) -> FastAPI:
    app = FastAPI(title="Jesse local intake API", version="0.1.0")
    settings = _get_settings()
    app.state.settings = settings
    app.state.feature_flags = settings["feature_flags"]
    app.state.logger = _build_logger(settings["log_level"])
    app.state.rate_limit_state: dict[str, list[float]] = defaultdict(list)
    app.state.metrics = {
        "api_requests": 0,
        "http_401": 0,
        "http_403": 0,
        "http_429": 0,
        "mock_appointments": 0,
        "mock_sheet_writes": 0,
        "mock_follow_up_emails": 0,
        "mock_n8n_events": 0,
    }
    app.state.integration_health = {
        "twilio": {"enabled": app.state.feature_flags["twilio"], "mode": settings["integration_mode"], "status": "mock"},
        "elevenlabs": {"enabled": app.state.feature_flags["elevenlabs"], "mode": settings["integration_mode"], "status": "mock"},
        "google_calendar": {"enabled": app.state.feature_flags["google_calendar"], "mode": settings["integration_mode"], "status": "mock"},
        "google_sheets": {"enabled": app.state.feature_flags["google_sheets"], "mode": settings["integration_mode"], "status": "mock"},
        "gmail": {"enabled": app.state.feature_flags["gmail"], "mode": settings["integration_mode"], "status": "mock"},
        "n8n": {"enabled": app.state.feature_flags["n8n"], "mode": settings["integration_mode"], "status": "mock"},
    }

    def get_intake_service() -> IntakeService:
        if service is not None:
            return service
        return get_service(data_file=settings["data_path"])

    def _get_service_identity(request: Request) -> Optional[str]:
        provided_key = request.headers.get("X-API-Key", "")
        for service_name, token in request.app.state.settings["service_tokens"].items():
            if token and provided_key == token:
                return service_name
        return None

    def _route_key(request: Request) -> str:
        route = request.scope.get("route")
        template = getattr(route, "path", request.url.path)
        template = re.sub(r"\{[^}]+\}", "{param}", template)
        return f"{request.method} {template}"

    def _extract_request_id(request: Request) -> str:
        request_id = request.headers.get("X-Request-ID")
        if request_id is None:
            return str(uuid.uuid4())
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", request_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request ID")
        return request_id

    def _check_rate_limit(request: Request, identity: str) -> None:
        if request.url.path == "/health":
            return
        now = time.time()
        client_host = request.client.host if request.client else "unknown"
        window_seconds = request.app.state.settings["rate_limit_window_seconds"]
        request_limit = request.app.state.settings["rate_limit_requests"]
        bucket = request.app.state.rate_limit_state[f"{identity}:{client_host}:{_route_key(request)}"]
        bucket[:] = [ts for ts in bucket if ts > now - window_seconds]
        if len(bucket) >= request_limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        bucket.append(now)

    def _check_permission(request: Request, service_name: str) -> None:
        route_key = _route_key(request)
        if route_key in PERMISSIONS.get(service_name, set()):
            return
        if service_name == "admin":
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    async def require_auth(request: Request) -> tuple[str, str]:
        service_name = _get_service_identity(request)
        if service_name is None:
            request.app.state.logger.warning(
                "auth.failed",
                extra={"context": {"event": "auth.failed", "environment": request.app.state.settings["environment"]}},
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        request.state.service_name = service_name
        _check_rate_limit(request, service_name)
        _check_permission(request, service_name)
        request.state.request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return service_name, request.state.request_id

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):
        start = time.perf_counter()
        try:
            request_id = _extract_request_id(request)
        except HTTPException as exc:
            request.state.request_id = str(uuid.uuid4())
            response = _error_response(exc.status_code, "invalid_request", "Request could not be processed", request)
            response.headers["X-Request-ID"] = request.state.request_id
            return response

        request.state.request_id = request_id
        request.state.service_name = getattr(request.state, "service_name", "public")
        if request.url.path != "/health":
            auth_service = _get_service_identity(request)
            if auth_service is not None:
                request.state.service_name = auth_service
        request.app.state.metrics["api_requests"] += 1

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        service_name = getattr(request.state, "service_name", "public")
        request.app.state.logger.info(
            "request.audit",
            extra={
                "context": {
                    "event": "request.audit",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "service": service_name,
                    "method": request.method,
                    "route": request.url.path,
                    "status_code": response.status_code,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                }
            },
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "invalid_request", "Request payload is invalid", request)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            request.app.state.metrics["http_401"] += 1
            return _error_response(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Authentication required", request)
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            request.app.state.metrics["http_403"] += 1
            return _error_response(status.HTTP_403_FORBIDDEN, "forbidden", "Permission denied", request)
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return _error_response(status.HTTP_404_NOT_FOUND, "not_found", "Resource not found", request)
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            request.app.state.metrics["http_429"] += 1
            return _error_response(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", "Rate limit exceeded", request)
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            return _error_response(status.HTTP_400_BAD_REQUEST, "invalid_request", "Request could not be processed", request)
        return _error_response(exc.status_code, "request_failed", "Request failed", request)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_server_error", "An unexpected error occurred", request)

    @app.get("/health")
    async def health(request: Request) -> JSONResponse:
        request.state.request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        response = JSONResponse(content={"status": "ok", "mode": settings["integration_mode"]})
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.post(
        "/intakes",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_auth)],
    )
    async def create_intake(
        request: Request,
        payload: IntakeCreateRequest,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> JSONResponse:
        try:
            record = intake_service.create_intake(
                caller_name=payload.caller_name,
                phone_number=payload.phone_number,
                email=payload.email,
                reason_for_call=payload.reason_for_call,
                urgency=payload.urgency,
                preferred_callback_time=payload.preferred_callback_time,
                consent_to_store=payload.consent_to_store,
            )
        except IntakeValidationError as exc:
            request.app.state.logger.warning(
                "intake.create.failed",
                extra={
                    "context": {
                        "event": "intake.create.failed",
                        "service": request.state.service_name,
                        "request_id": request.state.request_id,
                        "redacted_phone": IntakeService._redact_phone(payload.phone_number),
                        "redacted_email": IntakeService._redact_email(payload.email),
                    }
                },
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        request.app.state.logger.info(
            "intake.created",
            extra={
                "context": {
                    "event": "intake.created",
                    "service": request.state.service_name,
                    "request_id": request.state.request_id,
                    "intake_id": record["id"][:8],
                    "status": record["status"],
                    "urgency": record["urgency"],
                }
            },
        )
        response = JSONResponse(status_code=status.HTTP_201_CREATED, content=IntakeResponse(**record).model_dump())
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/intakes/{intake_id}", dependencies=[Depends(require_auth)])
    async def get_intake(
        request: Request,
        intake_id: str,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> JSONResponse:
        record = intake_service.retrieve_intake(intake_id)
        if not record:
            request.app.state.logger.warning(
                "intake.not_found",
                extra={
                    "context": {
                        "event": "intake.not_found",
                        "service": request.state.service_name,
                        "request_id": request.state.request_id,
                        "intake_id": intake_id[:8],
                    }
                },
            )
            raise HTTPException(status_code=404, detail="Intake not found")
        response = JSONResponse(content=IntakeResponse(**record).model_dump())
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/callbacks/pending", dependencies=[Depends(require_auth)])
    async def list_pending(
        request: Request,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> JSONResponse:
        request.app.state.logger.info(
            "callbacks.pending.listed",
            extra={"context": {"event": "callbacks.pending.listed", "service": request.state.service_name, "request_id": request.state.request_id}},
        )
        records = intake_service.list_pending_callbacks()
        response = JSONResponse(content=[IntakeResponse(**record).model_dump() for record in records])
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.patch("/intakes/{intake_id}/status", dependencies=[Depends(require_auth)])
    async def update_status(
        request: Request,
        intake_id: str,
        payload: IntakeStatusUpdate,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> JSONResponse:
        try:
            record = intake_service.update_status(intake_id, payload.status)
        except LookupError as exc:
            request.app.state.logger.warning(
                "intake.status.update.failed",
                extra={
                    "context": {
                        "event": "intake.status.update.failed",
                        "service": request.state.service_name,
                        "request_id": request.state.request_id,
                        "intake_id": intake_id[:8],
                    }
                },
            )
            raise HTTPException(status_code=404, detail="Intake not found") from exc
        request.app.state.logger.info(
            "intake.status.updated",
            extra={
                "context": {
                    "event": "intake.status.updated",
                    "service": request.state.service_name,
                    "request_id": request.state.request_id,
                    "intake_id": intake_id[:8],
                    "status": payload.status,
                }
            },
        )
        response = JSONResponse(content=IntakeResponse(**record).model_dump())
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/intakes/{intake_id}/summary", dependencies=[Depends(require_auth)])
    async def get_summary(
        request: Request,
        intake_id: str,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> JSONResponse:
        try:
            summary = intake_service.generate_redacted_summary(intake_id)
        except LookupError as exc:
            request.app.state.logger.warning(
                "intake.summary.failed",
                extra={
                    "context": {
                        "event": "intake.summary.failed",
                        "service": request.state.service_name,
                        "request_id": request.state.request_id,
                        "intake_id": intake_id[:8],
                    }
                },
            )
            raise HTTPException(status_code=404, detail="Intake not found") from exc
        request.app.state.logger.info(
            "intake.summary.generated",
            extra={
                "context": {
                    "event": "intake.summary.generated",
                    "service": request.state.service_name,
                    "request_id": request.state.request_id,
                    "intake_id": intake_id[:8],
                }
            },
        )
        response = JSONResponse(content=SummaryResponse(intake_id=intake_id, summary=summary).model_dump())
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def _integration_disabled_payload(request: Request, service: str) -> JSONResponse:
        payload = {"status": "disabled", "mode": "mock", "sandbox": True, "service": service, "enabled": False, "message": f"{service} integration is disabled"}
        payload["request_id"] = request.state.request_id
        response = JSONResponse(content=payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def _integration_response(request: Request, service: str, payload: dict[str, Any]) -> JSONResponse:
        response_payload = {"status": "ok", "mode": "mock", "sandbox": True, "service": service}
        response_payload.update(payload)
        response_payload["request_id"] = request.state.request_id
        response = JSONResponse(content=response_payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.post("/sandbox/twilio/inbound", dependencies=[Depends(require_auth)])
    async def twilio_inbound(request: Request, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        if not request.app.state.feature_flags.get("twilio", False):
            return _integration_disabled_payload(request, "twilio")
        adapter = TwilioAdapter(enabled=True, mode="mock")
        response = adapter.receive_inbound_call({"caller": "mock-caller", "phone": "5550001111"}, intake_service=intake_service)
        request.app.state.metrics["mock_appointments"] += 1
        return _integration_response(request, "twilio", response)

    @app.post("/sandbox/elevenlabs/transcript", dependencies=[Depends(require_auth)])
    async def elevenlabs_transcript(request: Request, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        if not request.app.state.feature_flags.get("elevenlabs", False):
            return _integration_disabled_payload(request, "elevenlabs")
        adapter = ElevenLabsAdapter(enabled=True, mode="mock")
        response = adapter.receive_transcript({"text": "mock transcript"}, intake_service=intake_service)
        return _integration_response(request, "elevenlabs", response)

    @app.get("/sandbox/calendar/slots", dependencies=[Depends(require_auth)])
    async def calendar_slots(request: Request) -> JSONResponse:
        if not request.app.state.feature_flags.get("google_calendar", False):
            return _integration_disabled_payload(request, "google_calendar")
        adapter = GoogleCalendarAdapter(enabled=True, mode="mock")
        response = adapter.get_mock_slots()
        return _integration_response(request, "google_calendar", response)

    @app.post("/sandbox/calendar/book", dependencies=[Depends(require_auth)])
    async def calendar_book(request: Request) -> JSONResponse:
        if not request.app.state.feature_flags.get("google_calendar", False):
            return _integration_disabled_payload(request, "google_calendar")
        adapter = GoogleCalendarAdapter(enabled=True, mode="mock")
        response = adapter.create_mock_booking({"slot": "mock-slot"})
        request.app.state.metrics["mock_appointments"] += 1
        return _integration_response(request, "google_calendar", response)

    @app.post("/sandbox/sheets/intakes/{intake_id}", dependencies=[Depends(require_auth)])
    async def sheets_intake(request: Request, intake_id: str, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        if not request.app.state.feature_flags.get("google_sheets", False):
            return _integration_disabled_payload(request, "google_sheets")
        adapter = GoogleSheetsAdapter()
        response = adapter.append_redacted_intake(intake_id, intake_service=intake_service)
        if response.get("status") == "mock":
            request.app.state.metrics["mock_sheet_writes"] += 1
        return _integration_response(request, "google_sheets", response)

    @app.post("/sandbox/gmail/follow-up/{intake_id}", dependencies=[Depends(require_auth)])
    async def gmail_follow_up(request: Request, intake_id: str, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        if not request.app.state.feature_flags.get("gmail", False):
            return _integration_disabled_payload(request, "gmail")
        adapter = GmailAdapter(enabled=True, mode="mock")
        response = adapter.send_follow_up(intake_id, intake_service=intake_service)
        request.app.state.metrics["mock_follow_up_emails"] += 1
        return _integration_response(request, "gmail", response)

    @app.post("/sandbox/n8n/events/{intake_id}", dependencies=[Depends(require_auth)])
    async def n8n_event(request: Request, intake_id: str, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        if not request.app.state.feature_flags.get("n8n", False):
            return _integration_disabled_payload(request, "n8n")
        adapter = N8NAdapter(enabled=True, mode="mock")
        response = adapter.deliver_event(intake_id, intake_service=intake_service)
        request.app.state.metrics["mock_n8n_events"] += 1
        return _integration_response(request, "n8n", response)

    @app.get("/integrations/status", dependencies=[Depends(require_auth)])
    async def integrations_status(request: Request) -> JSONResponse:
        response_payload = {"status": "ok", "mode": settings["integration_mode"], "sandbox": True, "integrations": request.app.state.integration_health}
        response_payload["request_id"] = request.state.request_id
        response = JSONResponse(content=response_payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/reports/daily", dependencies=[Depends(require_auth)])
    async def daily_report(request: Request, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        reporting = ReportingService(intake_service=intake_service, metrics=request.app.state.metrics, integration_health=request.app.state.integration_health)
        payload = reporting.daily_report()
        payload["request_id"] = request.state.request_id
        response = JSONResponse(content=payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/reports/summary", dependencies=[Depends(require_auth)])
    async def summary_report(request: Request, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        reporting = ReportingService(intake_service=intake_service, metrics=request.app.state.metrics, integration_health=request.app.state.integration_health)
        payload = reporting.summary_report()
        payload["request_id"] = request.state.request_id
        response = JSONResponse(content=payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/reports/integrations", dependencies=[Depends(require_auth)])
    async def integrations_report(request: Request, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        reporting = ReportingService(intake_service=intake_service, metrics=request.app.state.metrics, integration_health=request.app.state.integration_health)
        payload = reporting.integrations_report()
        payload["request_id"] = request.state.request_id
        response = JSONResponse(content=payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/reports/security", dependencies=[Depends(require_auth)])
    async def security_report(request: Request, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        reporting = ReportingService(intake_service=intake_service, metrics=request.app.state.metrics, integration_health=request.app.state.integration_health)
        payload = reporting.security_report()
        payload["request_id"] = request.state.request_id
        response = JSONResponse(content=payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/system/status", dependencies=[Depends(require_auth)])
    async def system_status(request: Request, intake_service: IntakeService = Depends(get_intake_service)) -> JSONResponse:
        reporting = ReportingService(intake_service=intake_service, metrics=request.app.state.metrics, integration_health=request.app.state.integration_health)
        payload = reporting.system_status()
        payload["request_id"] = request.state.request_id
        response = JSONResponse(content=payload)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    return app


app = create_app()
