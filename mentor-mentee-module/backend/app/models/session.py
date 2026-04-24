import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin
from app.models.enums import SessionStatus

if TYPE_CHECKING:
    from app.models.mentorship_connection import MentorshipConnection
    from app.models.session_history import SessionHistory
    from app.models.time_slot import TimeSlot


class Session(Base, UUIDMixin):
    __tablename__ = "sessions"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentorship_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("time_slots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status_enum", native_enum=False),
        nullable=False,
        default=SessionStatus.SCHEDULED,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    connection: Mapped["MentorshipConnection"] = relationship(lazy="joined")
    slot: Mapped["TimeSlot"] = relationship(back_populates="sessions", lazy="joined")
    history: Mapped["SessionHistory | None"] = relationship(back_populates="session", uselist=False)

