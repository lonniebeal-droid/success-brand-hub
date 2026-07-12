import argparse
import json
import os
import sys
from pathlib import Path

from agents.jessie.api.main import create_app
from agents.jessie.api.dependencies import get_service
from agents.jessie.src.intake_service import IntakeService
from agents.jessie.integrations.google_calendar_adapter import GoogleCalendarAdapter
from agents.jessie.integrations.google_sheets_adapter import GoogleSheetsAdapter
from agents.jessie.integrations.gmail_adapter import GmailAdapter
from agents.jessie.integrations.n8n_adapter import N8NAdapter
from agents.jessie.src.reporting_service import ReportingService
from fastapi.testclient import TestClient


def _service() -> IntakeService:
    data_file = os.getenv("JESSE_DATA_PATH", "agents/jessie/data/intakes.json")
    return get_service(data_file=data_file)


def create_intake(args: argparse.Namespace) -> int:
    service = _service()
    record = service.create_intake(
        caller_name=args.caller_name,
        phone_number=args.phone_number,
        email=args.email,
        reason_for_call=args.reason_for_call,
        urgency=args.urgency,
        preferred_callback_time=args.preferred_callback_time,
        consent_to_store=True,
    )
    print(json.dumps({"id": record["id"], "status": record["status"]}, indent=2))
    return 0


def get_intake(args: argparse.Namespace) -> int:
    service = _service()
    record = service.retrieve_intake(args.intake_id)
    print(json.dumps(record or {}, indent=2))
    return 0


def pending_callbacks(_: argparse.Namespace) -> int:
    service = _service()
    print(json.dumps(service.list_pending_callbacks(), indent=2))
    return 0


def update_status(args: argparse.Namespace) -> int:
    service = _service()
    print(json.dumps(service.update_status(args.intake_id, args.status), indent=2))
    return 0


def summary(args: argparse.Namespace) -> int:
    service = _service()
    print(service.generate_redacted_summary(args.intake_id))
    return 0


def health(_: argparse.Namespace) -> int:
    app = create_app(service=_service())
    with TestClient(app) as client:
        print(json.dumps(client.get("/health").json(), indent=2))
    return 0


def integration_status(_: argparse.Namespace) -> int:
    app = create_app(service=_service())
    token = os.getenv("JESSE_ADMIN_TOKEN", "")
    with TestClient(app) as client:
        response = client.get("/integrations/status", headers={"X-API-Key": token})
        print(json.dumps(response.json(), indent=2))
    return 0


def daily_report(_: argparse.Namespace) -> int:
    service = _service()
    reporting = ReportingService(intake_service=service, metrics={}, integration_health={})
    print(json.dumps(reporting.daily_report(), indent=2))
    return 0


def run_demo(_: argparse.Namespace) -> int:
    service = _service()
    record = service.create_intake(
        caller_name="Demo User",
        phone_number="(555) 123-4567",
        email="demo@example.com",
        reason_for_call="Sandbox demo",
        urgency="normal",
        preferred_callback_time="tomorrow",
        consent_to_store=True,
    )
    print("Created intake:", record["id"])
    print(service.generate_redacted_summary(record["id"]))
    print(json.dumps(GoogleCalendarAdapter(enabled=True, mode="mock").get_mock_slots(), indent=2))
    print(json.dumps(GoogleSheetsAdapter(enabled=True, mode="mock").append_redacted_intake(record["id"], intake_service=service), indent=2))
    print(json.dumps(GmailAdapter(enabled=True, mode="mock").send_follow_up(record["id"], intake_service=service), indent=2))
    print(json.dumps(N8NAdapter(enabled=True, mode="mock").deliver_event(record["id"], intake_service=service), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agents.jessie.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-intake")
    create.add_argument("--caller-name", required=True)
    create.add_argument("--phone-number", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--reason-for-call", required=True)
    create.add_argument("--urgency", default="normal")
    create.add_argument("--preferred-callback-time", default=None)
    create.set_defaults(func=create_intake)

    get = subparsers.add_parser("get-intake")
    get.add_argument("--intake-id", required=True)
    get.set_defaults(func=get_intake)

    pending = subparsers.add_parser("pending-callbacks")
    pending.set_defaults(func=pending_callbacks)

    update = subparsers.add_parser("update-status")
    update.add_argument("--intake-id", required=True)
    update.add_argument("--status", required=True)
    update.set_defaults(func=update_status)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--intake-id", required=True)
    summary_parser.set_defaults(func=summary)

    health_parser = subparsers.add_parser("health")
    health_parser.set_defaults(func=health)

    integration = subparsers.add_parser("integration-status")
    integration.set_defaults(func=integration_status)

    report = subparsers.add_parser("daily-report")
    report.set_defaults(func=daily_report)

    demo = subparsers.add_parser("run-demo")
    demo.set_defaults(func=run_demo)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
