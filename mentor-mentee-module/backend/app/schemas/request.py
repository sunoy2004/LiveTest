import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import MentorshipRequestStatus


class MentorshipRequestCreate(BaseModel):
    mentor_id: uuid.UUID = Field(..., description="Mentor profile id (mentor_profiles.id)")
    intro_message: str = Field(..., min_length=1, max_length=8000)


class MentorshipRequestStatusUpdate(BaseModel):
    status: MentorshipRequestStatus = Field(..., description="ACCEPTED or DECLINED")

    @field_validator("status")
    @classmethod
    def not_pending(cls, v: MentorshipRequestStatus) -> MentorshipRequestStatus:
        if v == MentorshipRequestStatus.PENDING:
            raise ValueError("Use ACCEPTED or DECLINED")
        return v


class MentorshipRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mentee_id: uuid.UUID
    mentor_id: uuid.UUID
    status: MentorshipRequestStatus
    intro_message: str
