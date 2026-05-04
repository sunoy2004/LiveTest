import uuid
from typing import TYPE_CHECKING

from datetime import datetime, timezone
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.models.base import Base
if TYPE_CHECKING:
    from app.models.mentorship_connection import MentorshipConnection
    from app.models.mentorship_request import MentorshipRequest


class MenteeProfile(Base):
    __tablename__ = "mentee_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    user_id = synonym("id")
    # Do not map `full_name` unless present on the physical table (avoids SELECT errors on slim DBs).
    learning_goals: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cached_credit_score: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    # sender_user_id FK is to users.user_id, not mentee_profiles — explicit join required
    requests: Mapped[list["MentorshipRequest"]] = relationship(
        "MentorshipRequest",
        primaryjoin="MenteeProfile.id == MentorshipRequest.sender_user_id",
        foreign_keys="MentorshipRequest.sender_user_id",
        overlaps="sender",
    )
    # mentee_user_id FK is to users.user_id, not mentee_profiles — explicit join required
    connections: Mapped[list["MentorshipConnection"]] = relationship(
        "MentorshipConnection",
        back_populates="mentee",
        primaryjoin="MenteeProfile.id == MentorshipConnection.mentee_user_id",
        foreign_keys="MentorshipConnection.mentee_user_id",
    )
