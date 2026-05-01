import uuid
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.models.base import Base

if TYPE_CHECKING:
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
    # `tier_id` may exist on newer DBs (Alembic 001); production without that column uses
    # global `mentor_tiers` + default tier in services instead of a profile FK.
    # Names come from users.email (synced JWT user); not stored on mentor_profiles per DB schema.
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    expertise: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    # receiver_user_id FK is to users.user_id, not mentor_profiles — explicit join required
    requests: Mapped[list["MentorshipRequest"]] = relationship(
        "MentorshipRequest",
        primaryjoin="MentorProfile.id == MentorshipRequest.receiver_user_id",
        foreign_keys="MentorshipRequest.receiver_user_id",
        overlaps="receiver",
    )
    connections: Mapped[list["MentorshipConnection"]] = relationship(
        "MentorshipConnection",
        back_populates="mentor",
        primaryjoin="MentorProfile.id == MentorshipConnection.mentor_user_id",
        foreign_keys="MentorshipConnection.mentor_user_id",
    )

