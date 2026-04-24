from typing import Literal

from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    mentor_id: str
    score: float = Field(ge=0, le=1)
    mentor_profile_id: str | None = None
    display_name: str | None = None
    expertise_areas: list[str] | None = None
    tier_id: str | None = None
    session_credit_cost: int | None = None


class FeedbackBody(BaseModel):
    target_user_id: str
    interaction_type: Literal["REJECTED_SUGGESTION", "SUCCESSFUL_MENTORSHIP"]
