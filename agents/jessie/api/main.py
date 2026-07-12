from typing import Callable, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agents.jessie.api.dependencies import get_service
from agents.jessie.api.schemas import IntakeCreateRequest, IntakeResponse, IntakeStatusUpdate, SummaryResponse
from agents.jessie.src.intake_service import IntakeService, IntakeValidationError


def create_app(service: Optional[IntakeService] = None) -> FastAPI:
    app = FastAPI(title="Jesse local intake API", version="0.1.0")

    def get_intake_service() -> IntakeService:
        if service is not None:
            return service
        return get_service()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.errors()})

    @app.exception_handler(IntakeValidationError)
    async def intake_validation_exception_handler(_: Request, exc: IntakeValidationError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/intakes", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
    async def create_intake(payload: IntakeCreateRequest, intake_service: IntakeService = Depends(get_intake_service)) -> IntakeResponse:
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
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return IntakeResponse(**record)

    @app.get("/intakes/{intake_id}", response_model=IntakeResponse)
    async def get_intake(intake_id: str, intake_service: IntakeService = Depends(get_intake_service)) -> IntakeResponse:
        record = intake_service.retrieve_intake(intake_id)
        if not record:
            raise HTTPException(status_code=404, detail="Intake not found")
        return IntakeResponse(**record)

    @app.get("/callbacks/pending", response_model=list[IntakeResponse])
    async def list_pending(intake_service: IntakeService = Depends(get_intake_service)) -> list[IntakeResponse]:
        records = intake_service.list_pending_callbacks()
        return [IntakeResponse(**record) for record in records]

    @app.patch("/intakes/{intake_id}/status", response_model=IntakeResponse)
    async def update_status(intake_id: str, payload: IntakeStatusUpdate, intake_service: IntakeService = Depends(get_intake_service)) -> IntakeResponse:
        try:
            record = intake_service.update_status(intake_id, payload.status)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Intake not found") from exc
        return IntakeResponse(**record)

    @app.get("/intakes/{intake_id}/summary", response_model=SummaryResponse)
    async def get_summary(intake_id: str, intake_service: IntakeService = Depends(get_intake_service)) -> SummaryResponse:
        try:
            summary = intake_service.generate_redacted_summary(intake_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Intake not found") from exc
        return SummaryResponse(intake_id=intake_id, summary=summary)

    return app


app = create_app()
