import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin
from app.models.enums import MentorshipConnectionStatus

if TYPE_CHECKING:
    from app.models.mentee_profile import MenteeProfile
    from app.models.mentor_profile import MentorProfile


class MentorshipConnection(Base, UUIDMixin):
    __tablename__ = "mentorship_connections"
    __table_args__ = (
        UniqueConstraint("mentee_id", "mentor_id", name="uq_mentorship_connections_mentee_mentor"),
    )

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
    status: Mapped[MentorshipConnectionStatus] = mapped_column(
        SAEnum(MentorshipConnectionStatus, name="mentorship_connection_status_enum", native_enum=False),
        nullable=False,
        default=MentorshipConnectionStatus.ACTIVE,
    )

    mentee: Mapped["MenteeProfile"] = relationship(back_populates="connections", foreign_keys=[mentee_id])
    mentor: Mapped["MentorProfile"] = relationship(back_populates="connections", foreign_keys=[mentor_id])
