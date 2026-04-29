import uuid
from typing import TYPE_CHECKING

from datetime import datetime, timezone
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.models.base import Base, UUIDMixin
from app.models.enums import GuardianConsentStatus

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
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    learning_goals: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    requests: Mapped[list["MentorshipRequest"]] = relationship(
        back_populates="mentee",
        foreign_keys="MentorshipRequest.mentee_id",
    )
    connections: Mapped[list["MentorshipConnection"]] = relationship(
        back_populates="mentee",
        foreign_keys="MentorshipConnection.mentee_id",
    )
