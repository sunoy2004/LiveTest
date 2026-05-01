import uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym

from app.db import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = synonym("user_id")
    email = Column(Text, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(32), nullable=False, default="MENTEE")  # MENTOR, MENTEE, BOTH, ADMIN
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

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

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    id = synonym("user_id")

    user = relationship("User", back_populates="admin_profile")


class MentorTier(Base):
    __tablename__ = "mentor_tiers"

    tier_id = Column(String(32), primary_key=True)
    tier_name = Column(String(128), nullable=False)
    session_credit_cost = Column(Integer, nullable=False, default=100)


class MenteeProfile(Base):
    __tablename__ = "mentee_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    id = synonym("user_id")
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)

    learning_goals = Column(ARRAY(Text), nullable=True)
    education_level = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="mentee_profile")
    mentorship_requests = relationship(
        "MentorshipRequest",
        foreign_keys="MentorshipRequest.sender_user_id",
    )


class MentorProfile(Base):
    __tablename__ = "mentor_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    id = synonym("user_id")
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)

    bio = Column(Text, nullable=True)
    expertise = Column(ARRAY(Text), nullable=True)
    experience_years = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="mentor_profile")
    tier = relationship("MentorTier", lazy="joined")
    mentorship_requests = relationship(
        "MentorshipRequest",
        foreign_keys="MentorshipRequest.receiver_user_id",
    )


class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    sender_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    receiver_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = Column(String(32), nullable=True, default="PENDING")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships updated to new column names
    sender = relationship("User", foreign_keys=[sender_user_id])
    receiver = relationship("User", foreign_keys=[receiver_user_id])


class MentorshipConnection(Base):
    __tablename__ = "mentorship_connections"

    mentor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    mentee_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = Column(String(32), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column("slot_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column("session_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    mentee_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )


class SessionBookingRequest(Base):
    __tablename__ = "session_booking_requests"

    id = Column("request_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    mentee_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    requested_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=True, default="PENDING")
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )


class Goal(Base):
    __tablename__ = "goals"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    goal = Column(Text, primary_key=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )


class SessionHistory(Base):
    __tablename__ = "session_histories"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        primary_key=True,
    )
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )


class ReportDispute(Base):
    __tablename__ = "reports_and_disputes"

    id = Column("report_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raised_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    target_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="SET NULL"),
        nullable=True,
    )
    reason = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="OPEN")
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )


class CreditLedgerEntry(Base):
    """Append-only YANC / credits movements for a user (mentee wallet)."""

    __tablename__ = "credit_ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
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
