import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.mentor_profile import MentorProfile
    from app.models.session import Session


class TimeSlot(Base, UUIDMixin):
    __tablename__ = "time_slots"

    mentor_id: Mapped[uuid.UUID] = mapped_column(
        "mentor_user_id",
        UUID(as_uuid=True),
        ForeignKey("mentor_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    mentor: Mapped["MentorProfile"] = relationship(lazy="joined")
    sessions: Mapped[list["Session"]] = relationship(back_populates="slot")

