import json
import logging
import os
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agents.jessie.api.dependencies import get_service
from agents.jessie.api.schemas import IntakeCreateRequest, IntakeResponse, IntakeStatusUpdate, SummaryResponse
from agents.jessie.src.intake_service import IntakeService, IntakeValidationError


FEATURE_FLAG_NAMES = {
    "twilio": "JESSE_TWILIO_ENABLED",
    "elevenlabs": "JESSE_ELEVENLABS_ENABLED",
    "google_calendar": "JESSE_GOOGLE_CALENDAR_ENABLED",
    "gmail": "JESSE_GMAIL_ENABLED",
    "google_sheets": "JESSE_GOOGLE_SHEETS_ENABLED",
    "n8n": "JESSE_N8N_ENABLED",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
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


def _get_settings() -> dict[str, Any]:
    return {
        "api_key": os.getenv("JESSE_API_KEY", "").strip(),
        "environment": os.getenv("JESSE_ENVIRONMENT", "development"),
        "data_path": os.getenv("JESSE_DATA_PATH", "agents/jessie/data/intakes.json"),
        "log_level": os.getenv("JESSE_LOG_LEVEL", "INFO").upper(),
        "feature_flags": {
            name: _get_bool_env(env_name, False)
            for name, env_name in FEATURE_FLAG_NAMES.items()
        },
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


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def create_app(service: Optional[IntakeService] = None) -> FastAPI:
    app = FastAPI(title="Jesse local intake API", version="0.1.0")
    settings = _get_settings()
    app.state.settings = settings
    app.state.feature_flags = settings["feature_flags"]
    app.state.logger = _build_logger(settings["log_level"])

    def get_intake_service() -> IntakeService:
        if service is not None:
            return service
        return get_service(data_file=settings["data_path"])

    async def require_api_key(request: Request) -> None:
        expected_key = request.app.state.settings["api_key"]
        provided_key = request.headers.get("X-API-Key", "")
        if not expected_key or provided_key != expected_key:
            request.app.state.logger.warning(
                "auth.failed",
                extra={"context": {"event": "auth.failed", "environment": request.app.state.settings["environment"]}},
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "invalid_request", "Request payload is invalid")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return _error_response(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Authentication required")
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return _error_response(status.HTTP_404_NOT_FOUND, "not_found", "Resource not found")
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            return _error_response(status.HTTP_400_BAD_REQUEST, "invalid_request", "Request could not be processed")
        return _error_response(exc.status_code, "request_failed", "Request failed")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_server_error", "An unexpected error occurred")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/intakes",
        response_model=IntakeResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_api_key)],
    )
    async def create_intake(
        request: Request,
        payload: IntakeCreateRequest,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> IntakeResponse:
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
                extra={"context": {"event": "intake.create.failed", "redacted_phone": IntakeService._redact_phone(payload.phone_number), "redacted_email": IntakeService._redact_email(payload.email)}}
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        request.app.state.logger.info(
            "intake.created",
            extra={"context": {"event": "intake.created", "intake_id": record["id"][:8], "status": record["status"], "urgency": record["urgency"]}},
        )
        return IntakeResponse(**record)

    @app.get("/intakes/{intake_id}", response_model=IntakeResponse, dependencies=[Depends(require_api_key)])
    async def get_intake(
        request: Request,
        intake_id: str,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> IntakeResponse:
        record = intake_service.retrieve_intake(intake_id)
        if not record:
            request.app.state.logger.warning("intake.not_found", extra={"context": {"event": "intake.not_found", "intake_id": intake_id[:8]}})
            raise HTTPException(status_code=404, detail="Intake not found")
        return IntakeResponse(**record)

    @app.get("/callbacks/pending", response_model=list[IntakeResponse], dependencies=[Depends(require_api_key)])
    async def list_pending(
        request: Request,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> list[IntakeResponse]:
        request.app.state.logger.info("callbacks.pending.listed", extra={"context": {"event": "callbacks.pending.listed"}})
        records = intake_service.list_pending_callbacks()
        return [IntakeResponse(**record) for record in records]

    @app.patch("/intakes/{intake_id}/status", response_model=IntakeResponse, dependencies=[Depends(require_api_key)])
    async def update_status(
        request: Request,
        intake_id: str,
        payload: IntakeStatusUpdate,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> IntakeResponse:
        try:
            record = intake_service.update_status(intake_id, payload.status)
        except LookupError as exc:
            request.app.state.logger.warning("intake.status.update.failed", extra={"context": {"event": "intake.status.update.failed", "intake_id": intake_id[:8]}})
            raise HTTPException(status_code=404, detail="Intake not found") from exc
        request.app.state.logger.info("intake.status.updated", extra={"context": {"event": "intake.status.updated", "intake_id": intake_id[:8], "status": payload.status}})
        return IntakeResponse(**record)

    @app.get("/intakes/{intake_id}/summary", response_model=SummaryResponse, dependencies=[Depends(require_api_key)])
    async def get_summary(
        request: Request,
        intake_id: str,
        intake_service: IntakeService = Depends(get_intake_service),
    ) -> SummaryResponse:
        try:
            summary = intake_service.generate_redacted_summary(intake_id)
        except LookupError as exc:
            request.app.state.logger.warning("intake.summary.failed", extra={"context": {"event": "intake.summary.failed", "intake_id": intake_id[:8]}})
            raise HTTPException(status_code=404, detail="Intake not found") from exc
        request.app.state.logger.info("intake.summary.generated", extra={"context": {"event": "intake.summary.generated", "intake_id": intake_id[:8]}})
        return SummaryResponse(intake_id=intake_id, summary=summary)

    return app


app = create_app()
