import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin
from app.models.enums import MentorshipRequestStatus

if TYPE_CHECKING:
    from app.models.mentee_profile import MenteeProfile
    from app.models.mentor_profile import MentorProfile


class MentorshipRequest(Base, UUIDMixin):
    __tablename__ = "mentorship_requests"

    mentee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentee_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mentor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[MentorshipRequestStatus] = mapped_column(
        SAEnum(MentorshipRequestStatus, name="mentorship_request_status_enum", native_enum=False),
        nullable=False,
        default=MentorshipRequestStatus.PENDING,
    )
    intro_message: Mapped[str] = mapped_column(Text, nullable=False)

    mentee: Mapped["MenteeProfile"] = relationship(back_populates="requests", foreign_keys=[mentee_id])
    mentor: Mapped["MentorProfile"] = relationship(back_populates="requests", foreign_keys=[mentor_id])
