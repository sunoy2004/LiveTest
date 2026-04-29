import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.mentee_profile import MenteeProfile
    from app.models.mentor_profile import MentorProfile


from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text

class MentorshipConnection(Base):
    __tablename__ = "mentorship_connections"

    mentor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    mentee_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    mentee: Mapped["MenteeProfile"] = relationship(back_populates="connections", foreign_keys=[mentee_user_id])
    mentor: Mapped["MentorProfile"] = relationship(back_populates="connections", foreign_keys=[mentor_user_id])
