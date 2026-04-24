import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GuardianConsentStatus


class MenteeProfileCreate(BaseModel):
    learning_goals: list[str] = Field(default_factory=list)
    education_level: str = Field(..., min_length=1, max_length=64)
    is_minor: bool = False


class MentorProfileCreate(BaseModel):
    tier_id: str = Field(..., min_length=1, max_length=32)
    expertise_areas: list[str] = Field(default_factory=list)
    is_accepting_requests: bool = True


class MenteeProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    learning_goals: list[str]
    education_level: str
    is_minor: bool
    guardian_consent_status: GuardianConsentStatus
    cached_credit_score: int


class MentorProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    tier_id: str
    is_accepting_requests: bool
    expertise_areas: list[str]
    total_hours_mentored: int


class ProfileMeResponse(BaseModel):
    mentee: MenteeProfileRead | None = None
    mentor: MentorProfileRead | None = None
