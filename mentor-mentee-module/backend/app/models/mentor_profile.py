import uuid
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.mentor_tier import MentorTier
    from app.models.mentorship_connection import MentorshipConnection
    from app.models.mentorship_request import MentorshipRequest


class MentorProfile(Base):
    __tablename__ = "mentor_profiles"

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
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    expertise: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    requests: Mapped[list["MentorshipRequest"]] = relationship(
        "MentorshipRequest",
        foreign_keys="MentorshipRequest.receiver_user_id",
    )
    connections: Mapped[list["MentorshipConnection"]] = relationship(
        "MentorshipConnection",
        foreign_keys="MentorshipConnection.mentor_user_id",
    )

