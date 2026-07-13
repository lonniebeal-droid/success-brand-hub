from collections import defaultdict, deque
from time import monotonic
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from agents.jessie.integrations.google_sheets_adapter import GoogleSheetsAdapter, GoogleSheetsSandboxError
from agents.jessie.src.intake_service import IntakeService
from core.auth import require_role
from core.database.database import Database
from .service import GoogleSheetsSandboxService


def create_google_sheets_router(database: Database, adapter: GoogleSheetsAdapter | None = None, intake_service: IntakeService | None = None) -> APIRouter:
    router = APIRouter(prefix="/sandbox/google-sheets", tags=["google-sheets-sandbox"])
    service = GoogleSheetsSandboxService(database, adapter, intake_service or IntakeService(os.getenv("JESSE_DATA_PATH", "agents/jessie/data/intakes.json")))
    limits: dict[str, deque] = defaultdict(deque)

    def request_id(request: Request) -> str:
        value = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", value): raise HTTPException(400, "invalid request ID")
        return value

    def check_limit(user: dict, request: Request) -> None:
        key = f"{user['sub']}:{request.url.path}"
        now = monotonic(); bucket = limits[key]
        while bucket and bucket[0] < now - 60: bucket.popleft()
        if len(bucket) >= 5: raise HTTPException(429, "rate limit exceeded")
        bucket.append(now)

    def response(payload: dict, rid: str, status_code: int = 200) -> JSONResponse:
        safe = {key: value for key, value in payload.items() if key not in {"spreadsheet_id", "credentials", "service_account"}}
        result = JSONResponse(safe, status_code=status_code); result.headers["X-Request-ID"] = rid; return result

    def write_guard(request: Request, user: dict = Depends(require_role("manager"))) -> tuple[dict, str]:
        check_limit(user, request); return user, request_id(request)

    @router.get("/status")
    def status_route(request: Request, user: dict = Depends(require_role("viewer"))):
        check_limit(user, request); rid = request_id(request); return response(service.status(), rid)

    @router.post("/intakes/{intake_id}")
    def write_intake(intake_id: str, request: Request, auth=Depends(write_guard)):
        _, rid = auth
        try: return response(service.write_intake(intake_id, rid), rid)
        except GoogleSheetsSandboxError as exc: raise HTTPException(409, str(exc)) from exc

    @router.post("/leads/{lead_id}")
    def write_lead(lead_id: str, request: Request, auth=Depends(write_guard)):
        _, rid = auth
        try: return response(service.write_lead(lead_id, rid), rid)
        except GoogleSheetsSandboxError as exc: raise HTTPException(409, str(exc)) from exc

    @router.post("/test-connection")
    def test_connection(request: Request, auth=Depends(write_guard)):
        _, rid = auth
        try: return response(service.adapter.test_connection(), rid)
        except GoogleSheetsSandboxError as exc: raise HTTPException(400, str(exc)) from exc

    return router
