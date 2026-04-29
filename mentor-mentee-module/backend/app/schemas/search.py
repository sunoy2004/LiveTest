import uuid
from enum import Enum

from pydantic import BaseModel, Field


class SearchRole(str, Enum):
    mentor = "mentor"
    mentee = "mentee"
    all = "all"


class SearchResult(BaseModel):
    user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    role: SearchRole
    expertise: list[str] = Field(default_factory=list)
    tier: str | None = None

