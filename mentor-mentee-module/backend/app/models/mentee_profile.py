import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.models.base import Base, UUIDMixin
from app.models.enums import GuardianConsentStatus

if TYPE_CHECKING:
    from app.models.mentorship_connection import MentorshipConnection
    from app.models.mentorship_request import MentorshipRequest


class MenteeProfile(Base):
    __tablename__ = "mentee_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    user_id = synonym("id")
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    learning_goals: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    education_level: Mapped[str] = mapped_column(String(64), nullable=False)
    is_minor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    guardian_consent_status: Mapped[GuardianConsentStatus] = mapped_column(
        SAEnum(GuardianConsentStatus, name="guardian_consent_status_enum", native_enum=False),
        nullable=False,
    )
    cached_credit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    requests: Mapped[list["MentorshipRequest"]] = relationship(
        back_populates="mentee",
        foreign_keys="MentorshipRequest.mentee_id",
    )
    connections: Mapped[list["MentorshipConnection"]] = relationship(
        back_populates="mentee",
        foreign_keys="MentorshipConnection.mentee_id",
    )
