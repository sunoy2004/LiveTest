from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    """Credentials identity; ``is_admin`` comes from ``users.is_admin``."""

    id: UUID
    email: str
    is_admin: bool = False

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    token: str
    user: UserPublic


class MeResponse(BaseModel):
    user: UserPublic


class MenteeProfilePublic(BaseModel):
    id: UUID
    user_id: UUID
    learning_goals: list[str] | None
    education_level: str | None
    is_minor: bool
    guardian_consent_status: str
    cached_credit_score: int

    model_config = {"from_attributes": True}


class MentorProfilePublic(BaseModel):
    id: UUID
    user_id: UUID
    tier_id: str
    pricing_tier: str = "TIER_2"
    base_credit_override: int | None = None
    is_accepting_requests: bool
    expertise_areas: list[str] | None
    total_hours_mentored: int
    headline: str | None = None
    bio: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    years_experience: int | None = None
    professional_experiences: list[dict] | None = None

    model_config = {"from_attributes": True}


class MentorProfileDetail(BaseModel):
    """Public mentor profile details for mentees (requires auth)."""

    mentor_profile: MentorProfilePublic
    email: str
    display_name: str


class FullProfileResponse(BaseModel):
    """Mentor/mentee roles from profile rows; admin from ``users.is_admin``."""

    user_id: UUID
    email: str
    is_admin: bool
    mentor_profile: MentorProfilePublic | None
    mentee_profile: MenteeProfilePublic | None


class MentoringProfileMeResponse(BaseModel):
    """Aligned with mentor-mentee-module GET /api/v1/profiles/me (`mentee` / `mentor` keys)."""

    mentee: MenteeProfilePublic | None = None
    mentor: MentorProfilePublic | None = None


class MentorshipRequestCreate(BaseModel):
    mentor_id: UUID
    intro_message: str = Field(min_length=1, max_length=4000)


class MentorshipRequestRead(BaseModel):
    id: UUID
    mentee_id: UUID
    mentor_id: UUID
    status: str
    intro_message: str

    model_config = {"from_attributes": True}


class MentorshipRequestIncomingItem(BaseModel):
    id: UUID
    mentee_id: UUID
    mentor_id: UUID
    status: str
    intro_message: str
    mentee_name: str


class MentorshipRequestStatusUpdate(BaseModel):
    status: Literal["ACCEPTED", "DECLINED"]


class MentorTierUpdate(BaseModel):
    tier_name: str | None = None
    session_credit_cost: int | None = Field(default=None, ge=0)


class MentorUpcomingBrief(BaseModel):
    id: UUID
    name: str
    tier: str


class MenteeUpcomingBrief(BaseModel):
    id: UUID
    name: str


class AdminMentorPricingBody(BaseModel):
    """PUT /admin/mentor/{mentor_id} — admin band + optional per-mentor price override."""

    tier: Literal["TIER_1", "TIER_2", "TIER_3"]
    base_credit_override: int | None = Field(
        default=None,
        ge=1,
        description="When null, clears override (tier table price applies).",
    )


class AdminMentorListItem(BaseModel):
    """GET /admin/mentors — mentor pricing (session booking price, not wallet)."""

    id: UUID
    name: str
    email: str
    tier: str
    base_credit_override: int | None


class AdminMenteeListItem(BaseModel):
    """GET /admin/mentees — mentee directory (no wallet fields)."""

    id: UUID
    name: str
    email: str
    status: str


class AdminConnectionItem(BaseModel):
    connection_id: UUID
    mentor_profile_id: UUID
    mentee_profile_id: UUID
    mentor_user_id: UUID
    mentee_user_id: UUID
    mentor_email: str
    mentee_email: str
    status: str


class AdminConnectionCreateBody(BaseModel):
    mentor_user_id: UUID
    mentee_user_id: UUID


class AdminUserListItem(BaseModel):
    user_id: UUID
    email: str
    is_admin: bool
    is_mentor: bool
    is_mentee: bool


class AdminUserRoleUpdate(BaseModel):
    is_mentor: bool
    is_mentee: bool


class AdminCreditTopUpBody(BaseModel):
    amount: int = Field(ge=1, le=1_000_000)


class AdminCreditGrantBody(BaseModel):
    """Preferred body for POST /admin/credits (avoids nested /users/{id}/credits paths)."""

    user_id: UUID
    amount: int = Field(ge=1, le=1_000_000)


class AdminCreditTopUpResponse(BaseModel):
    user_id: UUID
    amount: int
    balance_after: int | None = None


class AdminSessionItem(BaseModel):
    session_id: UUID
    connection_id: UUID
    mentor_name: str
    mentee_name: str
    start_time: datetime
    status: str
    price: int


class AdminDisputeItem(BaseModel):
    id: UUID
    status: str
    kind: str
    session_id: UUID | None
    reason: str | None = None
    opened_by_user_id: UUID | None
    created_at: datetime
    resolved_at: datetime | None = None
    credits_associated: int | None = Field(
        default=None,
        description="Session booking amount (price_charged or resolved mentor price) when session-linked.",
    )

    model_config = {"from_attributes": True}


class DisputeResolveBody(BaseModel):
    resolution: str = Field(default="RESOLVED", max_length=64)
    refund_credits: int = Field(default=0, ge=0)
    apply_mentor_penalty: bool = Field(
        default=True,
        description="When true and session-linked, deduct mentor via MENTOR_NO_SHOW_PENALTY after mentee refund.",
    )


class UpcomingSessionResponse(BaseModel):
    """When no upcoming session exists, identifiers and times are null."""

    session_id: UUID | None = None
    booking_request_id: UUID | None = Field(
        default=None,
        description="Set when the next item is a pending/rejected session booking request.",
    )
    start_time: datetime | None = None
    meeting_url: str | None = None
    status: str | None = None
    partner_name: str | None = None
    session_credit_cost: int | None = None
    price: int | None = None
    mentor: MentorUpcomingBrief | None = None
    mentee: MenteeUpcomingBrief | None = None


class UpcomingSessionItem(BaseModel):
    session_id: UUID | None = None
    booking_request_id: UUID | None = None
    start_time: datetime
    meeting_url: str | None = None
    status: str
    partner_name: str | None = None
    session_credit_cost: int | None = None
    price: int | None = None
    mentor: MentorUpcomingBrief | None = None
    mentee: MenteeUpcomingBrief | None = None

    @model_validator(mode="after")
    def one_identifier(self) -> Self:
        if self.session_id is None and self.booking_request_id is None:
            raise ValueError("session_id or booking_request_id required")
        return self


class GoalItem(BaseModel):
    id: UUID
    title: str
    status: str


class VaultItem(BaseModel):
    session_id: UUID
    start_time: datetime
    notes: dict
    mentor_rating: int | None = None
    mentee_rating: int | None = None
    partner_name: str | None = None


class DashboardStatsResponse(BaseModel):
    """GET /dashboard/stats — aggregates across ACTIVE mentorship connections."""

    active_partners: int = Field(ge=0, description="Mentors (mentee view) or mentees (mentor view)")
    hours_total: float = Field(ge=0)
    hours_this_week: float = Field(ge=0)
    sessions_completed: int = Field(ge=0)
    active_sessions: int = Field(ge=0, description="Scheduled sessions not yet completed")


class TimeSlotPublic(BaseModel):
    id: UUID
    start_time: datetime
    end_time: datetime
    cost_credits: int

    model_config = {"from_attributes": True}


class BookingContextResponse(BaseModel):
    connection_id: UUID
    mentor_display_name: str
    cached_credit_score: int
    slots: list[TimeSlotPublic]


class BookSessionRequest(BaseModel):
    connection_id: UUID
    slot_id: UUID
    agreed_cost: int = Field(ge=0)


class BookSessionResponse(BaseModel):
    request_id: UUID
    status: str
    session_id: UUID | None = None
    meeting_url: str | None = None
    start_time: datetime


class SessionCompleteResponse(BaseModel):
    session_id: UUID
    status: str


class ConnectedMentorItem(BaseModel):
    connection_id: UUID
    mentor_id: UUID
    mentor_name: str
    expertise: list[str] = Field(default_factory=list)
    total_hours: int = 0
    tier: str | None = None
    session_credit_cost: int | None = None


class AvailableSlotItem(BaseModel):
    slot_id: UUID
    start_time: datetime
    end_time: datetime
    cost_credits: int = 0


class BookSessionSimpleRequest(BaseModel):
    connection_id: UUID
    slot_id: UUID


class BookSessionSimpleResponse(BaseModel):
    request_id: UUID
    status: str
    session_id: UUID | None = None
    meeting_url: str | None = None
    start_time: datetime


class SessionBookingRequestIncomingItem(BaseModel):
    request_id: UUID
    connection_id: UUID
    slot_id: UUID
    start_time: datetime
    end_time: datetime
    agreed_cost: int
    mentee_name: str
    status: str


class CreditLedgerItem(BaseModel):
    id: UUID
    delta: int
    balance_after: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
