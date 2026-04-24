import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.session import Session


class SessionHistory(Base, UUIDMixin):
    __tablename__ = "session_histories"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    notes_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    mentor_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    mentee_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="history", lazy="joined")

