import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.mentor_tier import MentorTier
    from app.models.mentorship_connection import MentorshipConnection
    from app.models.mentorship_request import MentorshipRequest


class MentorProfile(Base, UUIDMixin):
    __tablename__ = "mentor_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    tier_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("mentor_tiers.tier_id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_accepting_requests: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expertise_areas: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    total_hours_mentored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tier: Mapped["MentorTier"] = relationship("MentorTier", lazy="joined")
    requests: Mapped[list["MentorshipRequest"]] = relationship(
        back_populates="mentor",
        foreign_keys="MentorshipRequest.mentor_id",
    )
    connections: Mapped[list["MentorshipConnection"]] = relationship(
        back_populates="mentor",
        foreign_keys="MentorshipConnection.mentor_id",
    )

