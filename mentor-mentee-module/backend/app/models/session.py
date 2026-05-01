import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.session_history import SessionHistory

if TYPE_CHECKING:
    from app.models.mentorship_connection import MentorshipConnection
    from app.models.session_history import SessionHistory
    from app.models.time_slot import TimeSlot


from datetime import datetime, timezone
from sqlalchemy import DateTime, String

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        "session_id",
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("time_slots.slot_id", ondelete="SET NULL"),
        nullable=True,
    )
    mentor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    mentee_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    slot: Mapped["TimeSlot | None"] = relationship("TimeSlot", back_populates="sessions")
    mentor: Mapped["User"] = relationship("User", foreign_keys=[mentor_user_id])
    mentee: Mapped["User"] = relationship("User", foreign_keys=[mentee_user_id])
    history: Mapped["SessionHistory | None"] = relationship(back_populates="session", uselist=False)

