import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text, text

from app.constants.mentorship_request import DEFAULT_INTRO_MESSAGE

class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    receiver_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=True,
        default="PENDING",
    )
    intro_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=DEFAULT_INTRO_MESSAGE,
        server_default=text("'I''d like to request a mentorship connection with you.'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    # Note: relationships will need care if we still want them pointing to profiles
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_user_id])
    receiver: Mapped["User"] = relationship("User", foreign_keys=[receiver_user_id])
