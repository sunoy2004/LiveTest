import uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="MENTEE")  # MENTOR, MENTEE, BOTH
    is_admin = Column(Boolean, default=False, nullable=False)

    admin_profile = relationship(
        "AdminProfile",
        back_populates="user",
        uselist=False,
    )
    mentor_profile = relationship(
        "MentorProfile",
        back_populates="user",
        uselist=False,
    )
    mentee_profile = relationship(
        "MenteeProfile",
        back_populates="user",
        uselist=False,
    )


class AdminProfile(Base):
    __tablename__ = "admin_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    user = relationship("User", back_populates="admin_profile")


class MentorTier(Base):
    __tablename__ = "mentor_tiers"

    tier_id = Column(String(32), primary_key=True)
    tier_name = Column(String(128), nullable=False)
    session_credit_cost = Column(Integer, nullable=False, default=100)


class MenteeProfile(Base):
    __tablename__ = "mentee_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    learning_goals = Column(ARRAY(String), nullable=True)
    education_level = Column(String(128), nullable=True)

    is_minor = Column(Boolean, default=False, nullable=False)
    guardian_consent_status = Column(String(32), default="NOT_REQUIRED", nullable=False)

    cached_credit_score = Column(Integer, default=100, nullable=False)

    user = relationship("User", back_populates="mentee_profile")
    mentorship_requests = relationship(
        "MentorshipRequest",
        back_populates="mentee",
        foreign_keys="MentorshipRequest.mentee_id",
    )


class MentorProfile(Base):
    __tablename__ = "mentor_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    tier_id = Column(String(32), ForeignKey("mentor_tiers.tier_id", ondelete="RESTRICT"), nullable=False)
    # Admin band (TIER_1 | TIER_2 | TIER_3) — row in mentor_tiers with same tier_id supplies default price.
    pricing_tier = Column(String(16), nullable=False, default="TIER_2")
    # When set, used as session price instead of tier table (admin-controlled).
    base_credit_override = Column(Integer, nullable=True)
    is_accepting_requests = Column(Boolean, default=True, nullable=False)

    expertise_areas = Column(ARRAY(String), nullable=True)
    total_hours_mentored = Column(Integer, default=0, nullable=False)

    # Rich profile fields (optional; used for viewing + AI similarity)
    headline = Column(String(256), nullable=True)
    bio = Column(Text, nullable=True)
    current_title = Column(String(128), nullable=True)
    current_company = Column(String(128), nullable=True)
    years_experience = Column(Integer, nullable=True)
    professional_experiences = Column(JSON, nullable=True)

    user = relationship("User", back_populates="mentor_profile")
    tier = relationship("MentorTier", lazy="joined")
    mentorship_requests = relationship(
        "MentorshipRequest",
        back_populates="mentor",
        foreign_keys="MentorshipRequest.mentor_id",
    )


class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentee_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mentor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(32), nullable=False, default="PENDING")
    intro_message = Column(Text, nullable=False, default="")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    mentee = relationship("MenteeProfile", foreign_keys=[mentee_id], back_populates="mentorship_requests")
    mentor = relationship("MentorProfile", foreign_keys=[mentor_id], back_populates="mentorship_requests")


class MentorshipConnection(Base):
    __tablename__ = "mentorship_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentee_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mentor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(32), nullable=False, default="ACTIVE")


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)
    cost_credits = Column(Integer, nullable=False, default=5)
    pending_request_id = Column(UUID(as_uuid=True), nullable=True, index=True)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentorship_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mentor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentor_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mentee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentee_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("time_slots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False)
    meeting_url = Column(String(1024), nullable=True)
    # Credits charged at booking (gamification deduct amount); source of truth for display/refunds.
    price_charged = Column(Integer, nullable=True)


class SessionBookingRequest(Base):
    """Mentee requests a slot; mentor accept creates Session + credit deduct."""

    __tablename__ = "session_booking_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentorship_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("time_slots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(32), nullable=False, default="PENDING")
    agreed_cost = Column(Integer, nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Goal(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mentorship_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE")


class SessionHistory(Base):
    __tablename__ = "session_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    notes_data = Column(JSON, nullable=True)
    mentor_rating = Column(Integer, nullable=True)
    mentee_rating = Column(Integer, nullable=True)


class ReportDispute(Base):
    __tablename__ = "reports_and_disputes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(32), nullable=False, default="OPEN")
    kind = Column(String(64), nullable=False, default="OTHER")
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opened_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class CreditLedgerEntry(Base):
    """Append-only YANC / credits movements for a user (mentee wallet)."""

    __tablename__ = "credit_ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delta = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reason = Column(String(512), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
