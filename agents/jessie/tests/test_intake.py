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
    assert "4567" in captured


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
    assert "4567" in summary
    assert "ada@example.com" not in summary
    assert "example.com" not in summary
