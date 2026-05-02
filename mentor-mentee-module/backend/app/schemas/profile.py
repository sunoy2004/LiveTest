import uuid
from pydantic import BaseModel, ConfigDict, Field

class MenteeProfileCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    learning_goals: list[str] = Field(default_factory=list)
    education_level: str | None = None

class MentorProfileCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    expertise_areas: list[str] = Field(default_factory=list, alias="expertise")
    experience_years: int = 0

    model_config = ConfigDict(populate_by_name=True)

class MenteeProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    learning_goals: list[str] = []
    education_level: str | None = None
    cached_credit_score: int = 0

class MentorProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    expertise: list[str] = []
    experience_years: int = 0

class ProfileMeResponse(BaseModel):
    mentee_profile: MenteeProfileRead | None = Field(default=None, alias="mentee")
    mentor_profile: MentorProfileRead | None = Field(default=None, alias="mentor")
    is_admin: bool = False
    
    model_config = ConfigDict(populate_by_name=True)
