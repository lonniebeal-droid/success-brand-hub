from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntakeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caller_name: str = Field(min_length=1)
    phone_number: str
    email: str
    reason_for_call: str = Field(min_length=1)
    urgency: str = "normal"
    preferred_callback_time: Optional[str] = None
    consent_to_store: bool

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, value: str) -> str:
        allowed = {"low", "normal", "high", "urgent"}
        if value.lower() not in allowed:
            raise ValueError("urgency must be one of: low, normal, high, urgent")
        return value.lower()


class IntakeStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)


class IntakeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    caller_name: str
    status: str
    urgency: str
    created_at: str
    preferred_callback_time: Optional[str] = None


class SummaryResponse(BaseModel):
    intake_id: str
    summary: str
