import json
from pathlib import Path

import pytest

from agents.jessie.src.intake_service import (
    IntakeService,
    IntakeValidationError,
    create_intake,
    generate_redacted_summary,
    list_pending_callbacks,
    retrieve_intake,
    update_status,
)


@pytest.fixture()
def temp_service(tmp_path):
    data_file = tmp_path / "intakes.json"
    return IntakeService(data_file=str(data_file))


def test_valid_intake(temp_service):
    intake = create_intake(
        service=temp_service,
        caller_name="Ada Lovelace",
        phone_number="(555) 123-4567",
        email="ada@example.com",
        reason_for_call="Consultation",
        urgency="normal",
        preferred_callback_time="tomorrow",
        consent_to_store=True,
    )

    assert intake["caller_name"] == "Ada Lovelace"
    assert intake["status"] == "new"
    assert intake["urgency"] == "normal"
    assert intake["consent_to_store"] is True
    assert intake["id"]


def test_invalid_phone(temp_service):
    with pytest.raises(IntakeValidationError) as excinfo:
        create_intake(
            service=temp_service,
            caller_name="Ada Lovelace",
            phone_number="invalid-phone",
            email="ada@example.com",
            reason_for_call="Consultation",
            urgency="normal",
            preferred_callback_time="tomorrow",
            consent_to_store=True,
        )

    assert "phone" in str(excinfo.value).lower()


def test_invalid_email(temp_service):
    with pytest.raises(IntakeValidationError) as excinfo:
        create_intake(
            service=temp_service,
            caller_name="Ada Lovelace",
            phone_number="(555) 123-4567",
            email="not-an-email",
            reason_for_call="Consultation",
            urgency="normal",
            preferred_callback_time="tomorrow",
            consent_to_store=True,
        )

    assert "email" in str(excinfo.value).lower()


def test_missing_consent(temp_service):
    with pytest.raises(IntakeValidationError) as excinfo:
        create_intake(
            service=temp_service,
            caller_name="Ada Lovelace",
            phone_number="(555) 123-4567",
            email="ada@example.com",
            reason_for_call="Consultation",
            urgency="normal",
            preferred_callback_time="tomorrow",
            consent_to_store=False,
        )

    assert "consent" in str(excinfo.value).lower()


def test_redacted_logs(temp_service, capsys):
    create_intake(
        service=temp_service,
        caller_name="Ada Lovelace",
        phone_number="(555) 123-4567",
        email="ada@example.com",
        reason_for_call="Consultation",
        urgency="high",
        preferred_callback_time="tomorrow",
        consent_to_store=True,
    )

    temp_service.log_intake_event("created", "ada@example.com")
    captured = capsys.readouterr().out
    assert "ada@example.com" not in captured
    assert "example.com" not in captured
    assert "4567" not in captured
    assert "Event=created" in captured
    assert "Sensitive=[redacted email]" in captured
    assert "Phone=[on file]" in captured

    temp_service.log_intake_event("callback", "(555) 123-4567")
    captured = capsys.readouterr().out
    assert "4567" not in captured and "555" not in captured
    assert "Event=callback Sensitive=[redacted phone]" in captured

    temp_service.log_intake_event("heartbeat")
    assert "Sensitive=[redacted none]" in capsys.readouterr().out


def test_local_storage(temp_service):
    intake = create_intake(
        service=temp_service,
        caller_name="Ada Lovelace",
        phone_number="(555) 123-4567",
        email="ada@example.com",
        reason_for_call="Consultation",
        urgency="normal",
        preferred_callback_time="tomorrow",
        consent_to_store=True,
    )

    stored = json.loads(Path(temp_service.data_file).read_text())
    assert len(stored) == 1
    assert stored[0]["id"] == intake["id"]


def test_status_updates(temp_service):
    intake = create_intake(
        service=temp_service,
        caller_name="Ada Lovelace",
        phone_number="(555) 123-4567",
        email="ada@example.com",
        reason_for_call="Consultation",
        urgency="normal",
        preferred_callback_time="tomorrow",
        consent_to_store=True,
    )

    updated = update_status(service=temp_service, intake_id=intake["id"], status="scheduled")
    assert updated["status"] == "scheduled"
    assert retrieve_intake(service=temp_service, intake_id=intake["id"])["status"] == "scheduled"


def test_pending_callbacks(temp_service):
    create_intake(
        service=temp_service,
        caller_name="Ada Lovelace",
        phone_number="(555) 123-4567",
        email="ada@example.com",
        reason_for_call="Consultation",
        urgency="normal",
        preferred_callback_time="tomorrow",
        consent_to_store=True,
    )
    create_intake(
        service=temp_service,
        caller_name="Grace Hopper",
        phone_number="(555) 765-4321",
        email="grace@example.com",
        reason_for_call="Callback",
        urgency="high",
        preferred_callback_time="today",
        consent_to_store=True,
    )

    pending = list_pending_callbacks(service=temp_service)
    assert len(pending) == 2
    assert all(item["status"] == "new" for item in pending)


def test_redacted_summary(temp_service):
    intake = create_intake(
        service=temp_service,
        caller_name="Ada Lovelace",
        phone_number="(555) 123-4567",
        email="ada@example.com",
        reason_for_call="Consultation",
        urgency="high",
        preferred_callback_time="tomorrow",
        consent_to_store=True,
    )

    summary = generate_redacted_summary(service=temp_service, intake_id=intake["id"])
    assert "Ada Lovelace" in summary
    assert "4567" not in summary
    assert "Phone: [on file]" in summary
    assert f"Intake {intake['id'][:8]}" in summary
    assert "Urgency: high" in summary
    assert "ada@example.com" not in summary
    assert "example.com" not in summary


@pytest.mark.parametrize(
    "email,expected",
    [
        ("ada@example.com", True),
        ("  ada@example.com  ", True),
        ("a@b.c", True),
        ("a@b.c.", True),  # same as the previous regex: some dot has characters on both sides
        ("a@sub.example.co.uk", True),
        ("", False),
        ("ada", False),
        ("ada@", False),
        ("@example.com", False),
        ("ada@example", False),
        ("ada@.com", False),
        ("ada@example.", False),
        ("ada@@example.com", False),
        ("ada@exa@mple.com", False),
        ("ada lovelace@example.com", False),
        ("ada@exam ple.com", False),
    ],
)
def test_email_validation_semantics(email, expected):
    assert IntakeService._is_valid_email(email) is expected


def test_email_validation_is_linear_on_pathological_input():
    import time

    # CodeQL py/polynomial-redos: the old regex backtracked polynomially on
    # strings starting with "!@!." followed by many repetitions of "!.".
    pathological = "!@!." + "!." * 50_000 + "@"
    start = time.perf_counter()
    assert IntakeService._is_valid_email(pathological) is False
    assert IntakeService._is_valid_email("!@!." + "!." * 50_000 + " ") is True  # trailing space is stripped
    assert IntakeService._is_valid_email("!@!." + "!." * 50_000 + " x") is False
    assert time.perf_counter() - start < 0.5


def test_presence_marker_never_contains_value():
    assert IntakeService._presence("(555) 123-4567") == "[on file]"
    assert IntakeService._presence("") == "[not provided]"
    assert IntakeService._presence(None) == "[not provided]"
    assert IntakeService._presence("   ") == "[not provided]"


def test_daily_report_only_contains_integer_counts(temp_service):
    from agents.jessie.src.reporting_service import ReportingService

    report = ReportingService(
        temp_service,
        metrics={"mock_appointments": "3", "mock_sheet_writes": 2, "mock_follow_up_emails": {"to": "x@example.com"}},
        integration_health={},
    ).daily_report()
    assert report["integrations"] == {
        "mock_appointments": 3,
        "mock_sheet_writes": 2,
        "mock_follow_up_emails": 0,
        "mock_n8n_events": 0,
    }
    assert "example.com" not in json.dumps(report)
